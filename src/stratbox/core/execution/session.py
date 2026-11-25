"""One bounded, fair execution coordinator for operations and workflow graphs."""
from __future__ import annotations

from collections import OrderedDict, deque
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field, replace, fields, is_dataclass
from hashlib import sha256
from math import isfinite
from queue import Empty, SimpleQueue
from threading import Condition as ThreadCondition, Event, Thread, current_thread
from time import monotonic
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4

from stratbox.core.execution.contracts import Correlation, Diagnostic, ExecutionContext, OperationResult
from stratbox.core.execution.handoff import (PreparedInput, ProjectedOutput, ResultReference,
    collect_inputs, project_output, resolve_output)
from stratbox.core.execution.resources import ResourceLedger, ScopedResourceLedger
from stratbox.core.execution.retention import ResultSpillStore, SpilledResult, ResultMapping, AttemptMapping, ValueMapping, retained_size
from stratbox.core.execution.values.placement import ManagedResult, ManagedProjection, ManagedCollection, ValueReadScope, resolve_managed

_TERMINAL = frozenset({"succeeded", "partial", "failed", "cancelled", "unknown", "blocked", "skipped"})
_GOOD = frozenset({"succeeded", "partial"})


def _token(value):
    """Paths are displayed in snapshots; bounded opaque IDs enter event records."""
    return "t." + sha256(value.encode()).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class ExecutionSettings:
    max_workers: int = 4
    active_runs: int = 2
    pending_runs: int = 64
    ready_tasks: int = 64
    map_window: int = 16
    network: int = 4
    per_origin: int = 2
    parsers: int = 2
    heavy_parsers: int = 1
    cpu: int = 1
    notifications: int = 1
    retained_bytes: int = 256 * 1024 * 1024
    temporary_bytes: int = 1024 * 1024 * 1024
    event_capacity: int = 4096
    expansion_tasks: int = 4096
    expansion_items: int = 100000
    cache_bytes: int = 64 * 1024 * 1024
    staging_bytes: int = 256 * 1024 * 1024
    publication_capacity: int = 4096
    expenditure: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        for name in ("max_workers", "active_runs", "pending_runs", "ready_tasks", "map_window",
                     "network", "per_origin", "parsers", "heavy_parsers", "cpu", "notifications",
                     "retained_bytes", "temporary_bytes", "event_capacity", "expansion_tasks",
                     "expansion_items", "cache_bytes", "staging_bytes", "publication_capacity"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError("execution.invalid_settings")
        object.__setattr__(self, "expenditure", MappingProxyType(dict(self.expenditure)))


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    task_id: str
    operation_id: str | None
    scope_id: str
    state: str
    attempts: int
    reason: str | None = None
    item_key: str | None = None
    invocation_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    run_id: str
    plan_id: str
    state: str
    tasks: tuple[TaskSnapshot, ...]
    queued_at: float
    started_at: float | None
    finished_at: float | None
    cancellation_requested: bool
    revision: int = 0
    event_cursor: int = 0
    total_known: bool = True
    task_count: int | None = None
    completed_count: int | None = None
    task_details_complete: bool = True
    physical_work_count: int = 0
    logical_use_count: int = 0
    scopes: Mapping[str, str] = field(default_factory=dict)

    @property
    def completed(self):
        return self.completed_count if self.completed_count is not None else sum(task.state in _TERMINAL for task in self.tasks)

    @property
    def total(self):
        return self.task_count if self.task_count is not None else len(self.tasks)


@dataclass(frozen=True, slots=True)
class MapOutput:
    """Ordered keyed values with explicit missing and incomplete item states."""
    items: tuple[tuple[str, object], ...]
    states: tuple[tuple[str, str], ...]

    @property
    def outcome(self):
        return "succeeded" if all(state == "succeeded" for _, state in self.states) else "partial"

    @property
    def values(self):
        return tuple(value for _, value in self.items)


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    plan_id: str
    outcome: str
    outputs: Mapping[str, object]
    results: Mapping[str, OperationResult]
    tasks: tuple[TaskSnapshot, ...]
    diagnostics: tuple[str, ...] = ()
    attempts: Mapping[str, tuple[OperationResult, ...]] = field(default_factory=dict)
    _spill: object | None = field(default=None, repr=False, compare=False)
    _ownership: object | None = field(default=None, repr=False, compare=False)
    scopes: Mapping[str, str] = field(default_factory=dict)
    scope_outputs: Mapping[str, Mapping[str, object]] = field(default_factory=dict)

    def close(self):
        """Release this result's ownership; existing read leases remain valid."""
        for name in ("outputs", "results", "attempts", "scope_outputs"):
            object.__setattr__(self, name, MappingProxyType({}))
        if self._ownership is not None:
            self._ownership.close()
        elif self._spill is not None:
            self._spill.close()

    def read(self, name):
        """Hold a result lease while reading a retained output."""
        if self._ownership is None:
            from contextlib import nullcontext
            return nullcontext(self.output(name))
        value = self.outputs._owned(name) if isinstance(self.outputs, ValueMapping) else self.outputs[name]
        value = value.value if isinstance(value, (ProjectedOutput, PreparedInput)) else value
        return self._ownership.lease(value)

    def output(self, name):
        if self._ownership is not None and self._ownership.closed:
            raise RuntimeError("result.closed")
        value = self.outputs[name]
        value = value.value if isinstance(value, (ProjectedOutput, PreparedInput)) else value
        return ExecutionSession._isolate(value)

    @property
    def effects(self):
        # A shared task has one physical result even when it has many aliases.
        return self.results.effects if isinstance(self.results, ResultMapping) else tuple(
            effect for result in self.results.values() for effect in result.effects)


@dataclass
class _Task:
    spec: object
    state: str = "pending"
    attempts: int = 0
    reason: str | None = None
    result: OperationResult | None = None
    outputs: dict = field(default_factory=dict)
    next_attempt: float = 0.0
    item_key: str | None = None
    token: Event = field(default_factory=Event)
    map_state: object | None = None
    attempt_results: list = field(default_factory=list)
    retained_owner: str | None = None
    selected: bool = False
    shared_work_id: str | None = None
    physical_key: str | None = None


@dataclass
class _MapState:
    iterator: object
    window: int
    keys: set = field(default_factory=set)
    next_index: int = 0
    exhausted: bool = False
    active: dict = field(default_factory=dict)
    completed: dict = field(default_factory=dict)
    order: list = field(default_factory=list)
    pending: tuple | None = None


@dataclass
class _Run:
    plan: object
    run_id: str
    context: ExecutionContext
    future: Future = field(default_factory=Future)
    token: Event = field(default_factory=Event)
    state: str = "queued"
    tasks: dict = field(default_factory=dict)
    archived: dict = field(default_factory=dict)
    order: list = field(default_factory=list)
    aliases: dict = field(default_factory=dict)
    queued_at: float = field(default_factory=monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    deadline: float | None = None
    cancelled_scopes: set = field(default_factory=set)
    diagnostics: list = field(default_factory=list)
    retained_owners: list = field(default_factory=list)
    scopes_started: set = field(default_factory=set)
    scope_ledgers: dict = field(default_factory=dict)
    spill: object | None = None
    scope_states: dict = field(default_factory=dict)
    scope_outputs: dict = field(default_factory=dict)
    scope_output_states: dict = field(default_factory=dict)
    scope_output_errors: dict = field(default_factory=dict)
    published_outputs: set = field(default_factory=set)
    scopes_finished: set = field(default_factory=set)
    scope_specs: dict = field(default_factory=dict)
    physical_work_count: int = 0
    logical_use_count: int = 0
    expanded_items: int = 0
    final_snapshot: object | None = None


@dataclass
class _PhysicalWork:
    key: str
    work_id: str
    consumers: dict = field(default_factory=dict)
    future: object | None = None
    result: object | None = None
    size: int = 0
    cache_owner: str | None = None
    assessment: object | None = None


class _SharedCancellation:
    def __init__(self, session, work):
        self.session, self.work = session, work

    def is_set(self):
        # A producer remains live while any eligible logical use needs it.
        return not any(not self.session._cancelled(run, task)
                       for run, task in tuple(self.work.consumers.values()))


class _Cancellation:
    def __init__(self, *tokens):
        self.tokens = tokens

    def is_set(self):
        return any(token is not None and token.is_set() for token in self.tokens)


class RunHandle:
    def __init__(self, session, run):
        self._session, self._run = session, run
        self.run_id = run.run_id

    def result(self, timeout=None):
        """Wait only; a timeout does not release slots or stop live effects."""
        return self._run.future.result(timeout)

    def done(self):
        return self._run.future.done()

    def snapshot(self):
        with self._session._condition:
            if self._run.final_snapshot is not None:
                return self._run.final_snapshot
            return self._session.snapshot(self.run_id)

    def cancel(self, scope_id=None):
        return False if self.done() else self._session.cancel(self.run_id, scope_id=scope_id)

    def events(self, after=0):
        return self._session.events(after=after, run_id=self.run_id)

    def output(self, name):
        """Read an already accepted output without waiting for sibling scopes."""
        with self._session._condition:
            if self.done():
                return self.result().output(name)
            with ValueReadScope():
                value = self._session._accepted_output(self._run, self._run.plan.outputs[name])
                if isinstance(value, (PreparedInput, ProjectedOutput)):
                    value = value.value
                return self._session._isolate(value)

    def scope_states(self):
        with self._session._condition:
            return dict(self._run.scope_states)


class ExecutionSession:
    """Own a single coordinator and worker pool across all submitted graphs.

    Handlers execute through their canonical OperationCall. Structural maps,
    joins, conditions and scenario scopes never occupy worker slots.
    """

    def __init__(self, catalog, *, settings=None, context=None, observer=None,
                 operation_options=None, result_resolver=None, network=None, providers=None):
        self.catalog = catalog
        self.settings = settings or ExecutionSettings()
        self.context = context or ExecutionContext()
        if providers:
            from stratbox.core.runtime.capabilities import ProviderBinding, CapabilityRequirement
            bindings = tuple(ProviderBinding("session." + name, CapabilityRequirement(name), "ready", provider)
                             for name, provider in providers.items())
            roles = {binding.capability.role for binding in bindings}
            self.context = replace(self.context, bindings=tuple(binding for binding in self.context.bindings
                if binding.capability.role not in roles) + bindings)
        self.session_id = uuid4().hex
        self.operation_options = dict(operation_options or {})
        self.result_resolver = result_resolver
        self.ledger = ResourceLedger({"worker": self.settings.max_workers, "network": self.settings.network,
            "parse": self.settings.parsers, "heavy_parse": self.settings.heavy_parsers,
            "cpu": self.settings.cpu, "notification": self.settings.notifications,
            "retained_bytes": self.settings.retained_bytes, "temporary_bytes": self.settings.temporary_bytes,
            "cache_bytes": self.settings.cache_bytes, "staging_bytes": self.settings.staging_bytes}, expenditure=self.settings.expenditure,
            per_origin=self.settings.per_origin)
        from stratbox.core.observability.capture.orchestration import OrchestrationJournal
        self.journal = OrchestrationJournal(self.session_id, max_records=self.settings.event_capacity,
            max_pending_runs=self.settings.publication_capacity, telemetry_sink=observer)
        self._network = network
        self._networks = {}
        self._owns_network = network is None
        self._condition = ThreadCondition()
        self._completions = SimpleQueue()
        self._runs = {}
        self._history = OrderedDict()
        self._pending = deque()
        self._active = deque()
        self._running = {}
        self._shared_work = OrderedDict()
        from stratbox.core.execution.effects import EffectAuthority
        self.effects = EffectAuthority()
        self._closing = False
        self._closed = False
        self._pool = None
        self._thread = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close(cancel=exc_type is not None)

    def _start(self):
        if self._thread is None:
            self._pool = ThreadPoolExecutor(max_workers=self.settings.max_workers,
                                            thread_name_prefix="stratbox-worker")
            self._thread = Thread(target=self._coordinate, name="stratbox-coordinator", daemon=True)
            self._thread.start()

    def submit(self, plan, *, context=None, timeout=None):
        from stratbox.composition.models import ExecutionPlan
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("execution.plan_required")
        from stratbox.composition import validate_plan
        validate_plan(plan, self.catalog)
        plan = self._isolate(plan)
        if timeout is not None and (not isinstance(timeout, (int, float)) or not isfinite(timeout) or timeout < 0):
            raise ValueError("execution.invalid_timeout")
        with self._condition:
            if self._closing:
                raise RuntimeError("execution.session_closed")
            if len(self._pending) >= self.settings.pending_runs:
                raise RuntimeError("execution.run_queue_full")
            run = _Run(plan, uuid4().hex, context or self.context)
            run.deadline = None if timeout is None else monotonic() + timeout
            try:
                self._add_scopes(run, plan.scopes)
                self._add_tasks(run, plan.tasks)
                self._select_outputs(run, plan.outputs)
                self.journal.reserve_run(run.run_id, publications=self._publication_budget(plan.tasks, plan.scopes))
                self.effects.begin_run(run.run_id)
            except Exception:
                self.journal.release_run(run.run_id)
                raise
            self._runs[run.run_id] = run
            self._pending.append(run.run_id)
            self._emit(run, "run.queued", state="queued")
            self._start()
            self._condition.notify_all()
            return RunHandle(self, run)

    def _publication_budget(self, tasks, scopes):
        values = sum(getattr(scope, "kind", None) == "operation" and
            getattr(getattr(port, "schema", None), "role", None) is not None
            for scope in scopes for port in getattr(scope, "output_contracts", {}).values())
        effects = sum(len({kind for kind in self.catalog.get(task.operation_id).possible_effects
            if not kind.startswith(("notification.", "notifications."))})
            for task in tasks if task.operation_id is not None)
        return values + effects

    def run(self, plan, **options):
        return self.submit(plan, **options).result()

    def _admit_specs(self, run, specs):
        """Apply the same ceilings and provider preparation to every expansion."""
        others = [other for other in self._runs.values() if other is not run]
        occupied = sum(task.state not in _TERMINAL for other in (*others, run)
                       for task in other.tasks.values())
        if occupied + len(specs) > self.settings.expansion_tasks:
            raise ValueError("execution.expansion_capacity")
        for spec in specs:
            if spec.operation_id is None:
                continue
            self.ledger.validate(self._requirements(spec))
            definition = self.catalog.get(spec.operation_id)
            if "http" in definition.required_capabilities | definition.optional_capabilities:
                self._prepare_network(run.context)

    def _add_tasks(self, run, specs, *, item_key=None, admitted=False):
        specs = tuple(specs)
        if not admitted:
            self._admit_specs(run, specs)
        for spec in specs:
            if spec.task_id in run.tasks:
                raise ValueError("execution.duplicate_task")
            run.tasks[spec.task_id] = _Task(spec, item_key=item_key)
            run.order.append(spec.task_id)
            for alias in spec.aliases:
                run.aliases[alias] = spec.task_id

    def _select_outputs(self, run, outputs):
        from stratbox.composition import iter_references
        for reference in iter_references(outputs):
            if reference.task in run.tasks:
                run.tasks[reference.task].selected = True

    def snapshot(self, run_id):
        with self._condition:
            return self._snapshot_run(self._runs[run_id]) if run_id in self._runs else self._history[run_id]

    def _snapshot_run(self, run):
        return RunSnapshot(run.run_id, run.plan.plan_id, run.state,
            tuple(self._task_snapshot(task) for task in self._all_tasks(run)),
            run.queued_at, run.started_at, run.finished_at,
            run.token.is_set() or bool(run.cancelled_scopes),
            revision=self.journal.health_snapshot().emitted,
            event_cursor=self.journal.event_cursor,
            total_known=all(task.spec.map is None or (task.map_state is not None and task.map_state.exhausted)
                            for task in run.tasks.values()),
            physical_work_count=run.physical_work_count,
            logical_use_count=run.logical_use_count,
            scopes=MappingProxyType(dict(run.scope_states)))

    def _add_scopes(self, run, scopes):
        for scope in scopes:
            run.scope_specs[scope.scope_id] = scope
            run.scope_states[scope.scope_id] = "waiting"
            run.scope_output_states[scope.scope_id] = {name: "waiting" for name in scope.outputs}
            parent = run.scope_ledgers.get(scope.parent_id, self.ledger)
            # A dynamic item inherits its enclosing map scope.
            if scope.parent_id is None:
                candidates = [name for name in run.scope_ledgers if scope.scope_id.startswith(name + "/")]
                if candidates:
                    parent = run.scope_ledgers[max(candidates, key=len)]
            limits = getattr(scope, "expenditure", {})
            run.scope_ledgers[scope.scope_id] = ScopedResourceLedger(parent, limits) if limits else parent
            if run.started_at is not None:
                run.scopes_started.add(scope.scope_id)
                self._scope_event(run, scope.scope_id, "scope.started", "running")

    @staticmethod
    def _task_snapshot(task):
        return TaskSnapshot(task.spec.task_id, task.spec.operation_id, task.spec.scope_id,
            task.state, task.attempts, task.reason, task.item_key,
            task.result.invocation_id if task.result else None, _token(task.spec.task_id))

    def events(self, after=0, run_id=None):
        records = self.journal.events(after=after)
        if callable(records):
            records = records()
        return tuple(record for record in records if getattr(record, "offset", getattr(record, "sequence", 0)) > after
            and (run_id is None or getattr(getattr(record, "correlation", None), "run_id", None) == run_id))

    def cancel(self, run_id, *, scope_id=None):
        with self._condition:
            run = self._runs.get(run_id)
            if run is None or run.future.done():
                return False
            if scope_id is None:
                run.token.set()
                run.state = "cancelling"
            else:
                if not any(task.spec.scope_id == scope_id or task.spec.scope_id.startswith(scope_id + "/")
                           for task in run.tasks.values()):
                    raise ValueError("execution.scope_unknown")
                run.cancelled_scopes.add(scope_id)
                for task in run.tasks.values():
                    if self._scope_cancelled(run, task):
                        task.token.set()
            for task in run.tasks.values():
                if scope_id is None or self._scope_cancelled(run, task):
                    correlation = self._correlation(run, task)
                    self.effects.invalidate_attempt(run.run_id, correlation.workflow_scope_id,
                        correlation.task_id, correlation.attempt_id)
            self._emit(run, "run.cancelling", state="cancelling")
            self._condition.notify_all()
            return True

    def close(self, *, wait=True, cancel=False):
        with self._condition:
            self._closing = True
            if cancel:
                for run in self._runs.values():
                    if not run.future.done():
                        run.token.set()
                        self._invalidate_attempts(run)
            self._condition.notify_all()
        if wait and self._thread is not None and current_thread() is not self._thread:
            self._thread.join()
        if self._thread is None:
            self._finish_close()

    def _invalidate_attempts(self, run):
        for task in run.tasks.values():
            correlation = self._correlation(run, task)
            self.effects.invalidate_attempt(run.run_id, correlation.workflow_scope_id,
                correlation.task_id, correlation.attempt_id)

    def _finish_close(self):
        if self._closed:
            return
        if self._pool:
            self._pool.shutdown(wait=True)
        for work in self._shared_work.values():
            if work.cache_owner is not None:
                self.ledger.release(work.cache_owner)
        self._shared_work.clear()
        if self._network is not None and self._owns_network:
            self._network.close()
        for network in self._networks.values():
            network.close()
        close = getattr(self.journal, "close", None)
        if close:
            close()
        self._closed = True

    def _correlation(self, run, task=None):
        fields = dict(session_id=self.session_id, run_id=run.run_id, plan_id=run.plan.plan_id)
        if task:
            fields.update(task_id=_token(task.spec.task_id), step_id=_token(task.spec.task_id),
                workflow_scope_id=_token(task.spec.scope_id), item_key=_token(task.item_key) if task.item_key else None,
                attempt_id=_token(f"{run.run_id}:{task.spec.task_id}:{task.attempts}"),
                shared_work_id=task.shared_work_id)
        return Correlation(**fields)

    def _emit(self, run, kind, task=None, **fields):
        try:
            self.journal.emit(kind, self._correlation(run, task), **fields)
        except Exception:
            # Observation failure never rewrites an accepted operation outcome.
            if "execution.observation_degraded" not in run.diagnostics:
                run.diagnostics.append("execution.observation_degraded")

    def _scope_event(self, run, scope_id, kind, state):
        try:
            self.journal.emit(kind, replace(self._correlation(run), workflow_scope_id=_token(scope_id)),
                state=state, outcome=state if state in {"succeeded", "partial", "failed", "cancelled", "unknown"} else None)
        except Exception:
            if "execution.observation_degraded" not in run.diagnostics:
                run.diagnostics.append("execution.observation_degraded")

    def _waiting(self, run, task, state, reason):
        if (task.state, task.reason) != (state, reason):
            task.state, task.reason = state, reason
            self._emit(run, "task.ready" if state == "ready" else "task.waiting", task, state=state, reason=reason)

    def _task(self, run, task_id):
        key = run.aliases.get(task_id, task_id)
        return run.tasks[key] if key in run.tasks else run.archived[key]

    def _all_tasks(self, run):
        return (self._task(run, key) for key in run.order)

    def _scope_cancelled(self, run, task):
        return any(task.spec.scope_id == scope or task.spec.scope_id.startswith(scope + "/")
                   for scope in run.cancelled_scopes)

    def _cancelled(self, run, task):
        return run.token.is_set() or task.token.is_set() or self._scope_cancelled(run, task) or (
            run.context.cancellation is not None and run.context.cancellation.is_set())

    def _requirements(self, spec):
        requirements = dict(spec.resources)
        dynamic = getattr(self.catalog, "resource_requirements", None)
        if dynamic is not None:
            try:
                claims = dynamic(spec.operation_id, spec.parameters)
            except ValueError:
                from stratbox.composition import iter_references
                if not tuple(iter_references(spec.parameters)):
                    raise
                # Deferred references have no concrete amount yet. Every
                # expanded/resolved task enters this same admission again.
                claims = {}
            for resource, amount in claims.items():
                requirements[resource] = max(requirements.get(resource, 0), amount)
        requirements["worker"] = max(1, requirements.get("worker", 0))
        definition = self.catalog.get(spec.operation_id)
        roles = definition.required_capabilities | definition.optional_capabilities
        if "http" in roles:
            requirements.setdefault("network", 1)
            try:
                from stratbox.core.network import network_resources
                requirements.update({name: amount for name, amount in network_resources({"parameters": spec.parameters, "inputs": spec.inputs}).items()
                                     if name not in requirements})
            except ImportError:
                pass
        stages = {stage.value for stage in definition.processing.stages} if definition.processing else set()
        if stages & {"parse", "extract"}:
            requirements.setdefault("parse", 1)
        if "calculate" in stages:
            requirements.setdefault("cpu", 1)
        if "notification.handoff" in definition.possible_effects or spec.operation_id.startswith(("notifications.", "notification.")):
            requirements.setdefault("notification", 1)
            requirements.setdefault("network", 1)
        return requirements

    def _coordinate(self):
        try:
            while True:
                with self._condition:
                    self._drain()
                    self.journal.flush_transitions()
                    while self._pending and len(self._active) < self.settings.active_runs:
                        rid = self._pending.popleft()
                        run = self._runs[rid]
                        run.started_at = monotonic()
                        run.state = "cancelling" if run.token.is_set() else "running"
                        self._active.append(rid)
                        self._emit(run, "run.started", state=run.state)
                        for scope in run.plan.scopes:
                            run.scopes_started.add(scope.scope_id)
                            self._scope_event(run, scope.scope_id, "scope.started", "running")
                    progress = False
                    for _ in range(len(self._active)):
                        rid = self._active.popleft()
                        run = self._runs[rid]
                        if run.deadline is not None and monotonic() >= run.deadline:
                            run.token.set()
                            self._invalidate_attempts(run)
                            if "execution.deadline" not in run.diagnostics:
                                run.diagnostics.append("execution.deadline")
                        progress |= self._advance(run)
                        self._refresh_scopes(run)
                        if all(task.state in _TERMINAL for task in run.tasks.values()):
                            self._finish(run)
                            progress = True
                        else:
                            self._active.append(rid)
                    if self._active:
                        self._active.rotate(-1)
                    if self._closing and not self._active and not self._pending and not self._running:
                        break
                    if not progress and not self._running:
                        future_retry = any(task.state == "retry_wait" and task.next_attempt > monotonic()
                            for rid in self._active for task in self._runs[rid].tasks.values())
                        if not future_retry:
                            blocked = next(((self._runs[rid], task) for rid in self._active
                                for task in self._runs[rid].tasks.values()
                                if task.state == "waiting" and task.reason == "resource"), None)
                            if blocked is not None:
                                self._terminal(*blocked, "blocked", "resource.unavailable")
                                progress = True
                    if not progress:
                        self._condition.wait(timeout=0.025)
        except BaseException as error:
            with self._condition:
                for run in self._runs.values():
                    if not run.future.done():
                        run.future.set_exception(error)
        finally:
            self._finish_close()

    def _advance(self, run):
        progress = False
        ready = 0
        for task in tuple(run.tasks.values()):
            if task.state in _TERMINAL or task.state == "running":
                continue
            if task.state == "shared_wait":
                if self._cancelled(run, task):
                    work = self._shared_work.get(task.physical_key)
                    if work is not None:
                        work.consumers.pop((run.run_id, task.spec.task_id), None)
                    self._terminal(run, task, "cancelled", "execution.cancelled")
                    progress = True
                continue
            if task.state == "expanding":
                progress |= self._advance_map(run, task)
                continue
            if self._cancelled(run, task) or task.token.is_set():
                self._terminal(run, task, "cancelled", "execution.cancelled")
                progress = True
                continue
            if task.next_attempt > monotonic():
                continue
            dependencies = [self._task(run, key) for key in task.spec.dependencies]
            if any(dep.state not in _TERMINAL for dep in dependencies):
                self._waiting(run, task, "waiting", "dependencies")
                continue
            from stratbox.composition.plan import task_conditions
            conditions = task_conditions(task.spec)
            if conditions:
                try:
                    selected = all(self._condition_matches(run, condition) for condition in conditions)
                except (ValueError, KeyError, TypeError, AttributeError):
                    self._terminal(run, task, "failed", "execution.condition_invalid")
                    progress = True
                    continue
                if not selected:
                    self._terminal(run, task, "skipped", "execution.condition_false")
                    progress = True
                    continue
            self._refresh_scopes(run)
            failed = [dep for dep in dependencies if dep.state not in _GOOD and dep.state != "skipped"]
            guarded_states = {condition.task for condition in conditions if condition.statuses}
            if guarded_states:
                from stratbox.composition.compiler import iter_references
                data_deps = {ref.task for ref in iter_references((task.spec.inputs, task.spec.parameters))}
                failed = [dep for dep in failed if dep.spec.task_id not in guarded_states
                          or dep.spec.task_id in data_deps]
            partial_collection = task.spec.collect is not None and task.spec.collect.allow_partial
            if failed and not partial_collection:
                self._terminal(run, task, "blocked", "execution.dependency_failed")
                progress = True
                continue
            if ready >= self.settings.ready_tasks:
                continue
            ready += 1
            if task.spec.map is not None:
                try:
                    value = self._resolve(run, task.spec.map.items)
                    if isinstance(value, (ProjectedOutput, PreparedInput)):
                        value = value.value
                    if isinstance(value, MapOutput):
                        value = value.values
                    if isinstance(value, Mapping):
                        iterator = iter(value.items())
                    else:
                        iterator = enumerate(iter(value))
                    task.map_state = _MapState(iterator, min(task.spec.map.window or self.settings.map_window,
                                                            self.settings.map_window))
                    task.state, task.reason = "expanding", None
                    progress = True
                except Exception:
                    self._terminal(run, task, "failed", "execution.map_input_invalid")
                continue
            acceptance_scope = getattr(task.spec, "acceptance_scope", None)
            if acceptance_scope is not None:
                self._refresh_scopes(run, accepting=acceptance_scope)
                outcome = run.scope_states.get(acceptance_scope, "failed")
                self._terminal(run, task, outcome,
                    None if outcome in _GOOD else "acceptance.scope_failed")
                progress = True
                continue
            if task.spec.collect is not None:
                try:
                    task.outputs["value"] = self._collect(run, task.spec.collect)
                    self._terminal(run, task, task.outputs["value"].outcome)
                except Exception:
                    self._terminal(run, task, "failed", "execution.collection_invalid")
                progress = True
                continue
            assessment = self._work_assessment(run, task)
            key = assessment.key if assessment.inflight_allowed else None
            shared = self._shared_work.get(key) if key is not None else None
            if shared is not None and (shared.assessment is None or not assessment.can_consume(
                    shared.assessment, completed=shared.result is not None)):
                # This consumer executes separately without displacing an
                # independently eligible producer or completed cache entry.
                shared, key = None, None
            if shared is not None:
                self._shared_work.move_to_end(key)
                shared.consumers[(run.run_id, task.spec.task_id)] = (run, task)
                task.physical_key, task.shared_work_id = key, shared.work_id
                task.attempts += 1
                run.logical_use_count += 1 + len(task.spec.aliases)
                task.state, task.reason = "shared_wait", "shared_work"
                self._emit(run, "shared_work.attached", task, state="waiting")
                if shared.result is not None:
                    self._emit(run, "shared_work.reused", task, state="reused")
                    self._accept_completion(run, task, shared.cache_owner, shared.result, shared.size)
                    shared.consumers.pop((run.run_id, task.spec.task_id), None)
                progress = True
                continue
            if len(self._running) >= self.settings.max_workers:
                self._waiting(run, task, "ready", "worker")
                continue
            owner = f"{run.run_id}:{task.spec.task_id}"
            try:
                requirements = self._requirements(replace(task.spec,
                    parameters=self._parameter_values(self._resolve(run, task.spec.parameters)),
                    inputs=self._resolve(run, task.spec.inputs)))
                reserved = self.ledger.reserve(owner, requirements)
            except (ValueError, KeyError, TypeError) as error:
                code = str(error) if isinstance(error, ValueError) else "execution.input_unavailable"
                self._terminal(run, task, "blocked", code)
                progress = True
                continue
            if not reserved:
                self._waiting(run, task, "waiting", "resource")
                continue
            task.attempts += 1
            task.state, task.reason = "running", None
            self._emit(run, "task.started", task, state="running")
            work = None
            if key is not None:
                work = _PhysicalWork(key, "shared-" + uuid4().hex,
                    {(run.run_id, task.spec.task_id): (run, task)}, assessment=assessment)
                task.physical_key, task.shared_work_id = key, work.work_id
                self._shared_work[key] = work
                self._emit(run, "shared_work.started", task, state="running")
            run.physical_work_count += 1
            run.logical_use_count += 1 + len(task.spec.aliases)
            future = self._pool.submit(self._execute, run, task, owner, work)
            if work is not None:
                work.future = future
            self._running[future] = (run.run_id, task.spec.task_id, owner, work)
            future.add_done_callback(self._completed)
            progress = True
            # Round-robin one admission per run; structural transitions continue
            # on the next pass without starving another ready run.
            break
        return progress

    def _condition_matches(self, run, condition):
        task = self._task(run, condition.task)
        if condition.statuses:
            return task.state in condition.statuses
        from stratbox.composition.models import PlanOutputRef
        value = self._resolve(run, getattr(condition, "reference", None) or PlanOutputRef(condition.task, condition.port))
        if isinstance(value, (ProjectedOutput, PreparedInput)):
            value = value.value
        for name in condition.field.split(".") if condition.field else ():
            value = value[name] if isinstance(value, Mapping) else getattr(value, name)
        return value == condition.equals

    def _resolve(self, run, value):
        from stratbox.composition.models import PlanOutputRef
        from stratbox.composition.plan import ScopeOutputRef
        if isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)):
            return resolve_managed(value)
        if isinstance(value, ScopeOutputRef):
            if run.scope_output_states.get(value.scope_id, {}).get(value.port) != "accepted":
                raise ValueError("acceptance.output_unavailable")
            return self._resolve(run, run.scope_outputs[value.scope_id][value.port])
        if isinstance(value, PlanOutputRef):
            task = self._task(run, value.task)
            result = resolve_managed(task.result) if isinstance(task.result, ManagedResult) else (
                task.result.resolve() if isinstance(task.result, SpilledResult) else task.result)
            projected = project_output(result, value.port) if result else task.outputs[value.port]
            if value.item is not None:
                if not isinstance(projected, MapOutput):
                    raise ValueError("execution.item_reference_requires_map")
                projected = dict(projected.items)[value.item]
            return resolve_managed(projected)
        if isinstance(value, ResultReference):
            if self.result_resolver is None:
                raise ValueError("execution.result_resolver_required")
            return resolve_output(value, self.result_resolver)
        if isinstance(value, Mapping):
            return {name: self._resolve(run, item) for name, item in value.items()}
        if isinstance(value, tuple):
            return tuple(self._resolve(run, item) for item in value)
        if isinstance(value, list):
            return [self._resolve(run, item) for item in value]
        return value

    @staticmethod
    def _isolate(value):
        if isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)):
            return value
        if isinstance(value, (ProjectedOutput, PreparedInput)):
            return replace(value, value=deepcopy(value.value))
        if isinstance(value, Mapping):
            return {name: ExecutionSession._isolate(item) for name, item in value.items()}
        if isinstance(value, tuple):
            return tuple(ExecutionSession._isolate(item) for item in value)
        if is_dataclass(value) and not isinstance(value, type):
            return replace(value, **{member.name: ExecutionSession._isolate(getattr(value, member.name))
                                     for member in fields(value) if member.init})
        return deepcopy(value)

    def _work_assessment(self, run, task):
        from stratbox.core.execution.sharing import assess_work
        with ValueReadScope():
            try:
                inputs = self._resolve(run, task.spec.inputs)
                parameters = self._resolve(run, task.spec.parameters)
            except (KeyError, ValueError, TypeError, AttributeError):
                return assess_work(replace(task.spec, reuse_eligible=False), inputs={}, parameters={},
                    context=run.context, run_id=run.run_id)
            return assess_work(task.spec, inputs=inputs, parameters=parameters,
                context=run.context, run_id=run.run_id,
                effects=self.catalog.get(task.spec.operation_id).possible_effects,
                attempt=task.attempts + 1)

    def _work_key(self, run, task):
        return self._work_assessment(run, task).key

    def _execute(self, run, task, owner, work=None):
        try:
            with ValueReadScope():
                return self._execute_owned(run, task, owner, work)
        finally:
            correlation = self._correlation(run, task)
            self.effects.finish_attempt(run.run_id, correlation.workflow_scope_id,
                correlation.task_id, correlation.attempt_id)

    def _execute_owned(self, run, task, owner, work=None):
        from stratbox.core.execution.values.placement import isolate_managed
        inputs = isolate_managed(self._resolve(run, task.spec.inputs), self.ledger)
        parameters = self._isolate(self._parameter_values(self._resolve(run, task.spec.parameters)))
        from stratbox.core.execution.methods import method_descriptor
        definition, handler, _ = self.catalog.resolve(task.spec.operation_id)
        fingerprint = method_descriptor(definition, work=None if definition.method_refs else handler).identity.sha256
        if definition.method_id != task.spec.method_id or fingerprint != task.spec.method_fingerprint:
            raise ValueError("execution.method_changed")
        correlation = self._correlation(run, task)
        self.effects.begin_attempt(run.run_id, correlation.workflow_scope_id,
            correlation.task_id, correlation.attempt_id)
        enclosing = [(name, binding) for name, binding in run.plan.selected_bindings.items()
            if task.spec.scope_id.startswith(name + "/") or task.spec.scope_id == name]
        semantic = [item for item in enclosing if item[1].get("kind") == "operation"]
        selected_scope, selected = max(semantic or enclosing, key=lambda item: len(item[0]), default=(None, {}))
        actual = dict(selected.get("identities", {}))
        if selected_scope is not None:
            actual.update(("implementation:" + member.spec.task_id, member.spec.method_fingerprint)
                for member in tuple(self._all_tasks(run))
                if member.spec.method_fingerprint is not None and member.state in _GOOD
                and (member.spec.scope_id == selected_scope or member.spec.scope_id.startswith(selected_scope + "/")))
        if task.spec.method_fingerprint is not None:
            actual["implementation:" + task.spec.task_id] = task.spec.method_fingerprint
        identities = tuple(sorted(actual.items()))
        context = replace(run.context, correlation=correlation, effect_authority=self.effects,
            binding_identities=identities,
            effect_admitter=lambda kind, effect_id: self.journal.admit_effect(correlation, kind, effect_id,
                allowance=len({item for item in definition.possible_effects
                    if not item.startswith(("notification.", "notifications."))})),
            cancellation=(_SharedCancellation(self, work) if work is not None else
                          _Cancellation(run.token, task.token, run.context.cancellation)),
            resource_ledger=run.scope_ledgers.get(task.spec.scope_id, self.ledger),
            sink=self.journal.operation_sink(run.context.sink))
        from stratbox.core.runtime.capabilities import ProviderBinding, CapabilityRequirement
        from stratbox.core.network import AccessScope
        bindings = []
        has_http = False
        observation_id = run.run_id
        if "network.receive" in definition.possible_effects:
            observation_id = parameters.get("observation_id") or run.run_id
            if parameters.get("freshness") == "fresh":
                observation_id = f"{run.run_id}:{task.spec.task_id}:{task.attempts}"
            observation_id = "observation-" + sha256(str(observation_id).encode()).hexdigest()
        for binding in context.bindings:
            if binding.capability.role == "http":
                has_http = True
                network = self._networks.get(id(binding.provider))
                if network is not None:
                    transport = network.transport_for(observation_id,
                        scope=AccessScope(binding.provider_id, binding.scope_id or
                            getattr(getattr(binding.provider, "scope", None), "scope_id", "public"), profile=context.profile),
                        reservation_owner=owner, ledger=self.ledger,
                        run_id=run.run_id, task_id=_token(task.spec.task_id))
                    binding = replace(binding, provider=transport)
            bindings.append(binding)
        if not has_http and self._network is not None:
            transport = self._network.transport_for(observation_id, scope=AccessScope(profile=context.profile),
                reservation_owner=owner, ledger=self.ledger,
                        run_id=run.run_id, task_id=_token(task.spec.task_id))
            bindings.append(ProviderBinding("session.http", CapabilityRequirement("http"), "ready", transport))
        context = replace(context, bindings=tuple(bindings))
        if task.spec.source is not None:
            source = task.spec.source
            call = self.catalog.bind_source(source.series_id, format=source.format, group_id=source.group_id,
                edition=source.edition).bind(task.spec.operation_id, inputs=inputs, parameters=parameters)
        else:
            call = self.catalog.bind(task.spec.operation_id, inputs=inputs, parameters=parameters)
        result = call.invoke(context=context, **self.operation_options.get(task.spec.operation_id, {}))
        return result, retained_size(result.value)

    def _prepare_network(self, context):
        from stratbox.core.network import SessionNetwork
        http = [binding for binding in context.bindings if binding.capability.role == "http"]
        for binding in http:
            if id(binding.provider) not in self._networks:
                self._networks[id(binding.provider)] = SessionNetwork(transport=binding.provider, owned=False, journal=self.journal,
                    per_origin=self.settings.per_origin, max_bytes=self.settings.cache_bytes,
                    max_staging_bytes=self.settings.staging_bytes, staging_ledger=self.ledger)
        if not http and self._network is None:
            self._network = SessionNetwork(journal=self.journal, per_origin=self.settings.per_origin,
                                           max_bytes=self.settings.cache_bytes,
                                           max_staging_bytes=self.settings.staging_bytes, staging_ledger=self.ledger)

    @staticmethod
    def _parameter_values(value):
        if isinstance(value, (ProjectedOutput, PreparedInput)):
            return value.value
        if isinstance(value, Mapping):
            return {key: ExecutionSession._parameter_values(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return type(value)(ExecutionSession._parameter_values(item) for item in value)
        return value

    def _completed(self, future):
        self._completions.put(future)
        with self._condition:
            self._condition.notify_all()

    def _drain(self):
        while True:
            try:
                future = self._completions.get_nowait()
            except Empty:
                return
            rid, tid, owner, work = self._running.pop(future)
            self.ledger.release(owner)
            consumers = (((self._runs[rid], self._runs[rid].tasks[tid]),) if work is None else
                         tuple(work.consumers.values()))
            try:
                result, size = future.result()
                error = None
            except BaseException as failure:
                result, size, error = None, 0, failure
            if work is not None:
                work.consumers.clear()
                if error is None and result.outcome == "succeeded" and all(
                        effect.kind == "network.receive" and effect.state == "confirmed" for effect in result.effects):
                    self._cache_work(work, result, size)
                else:
                    self._shared_work.pop(work.key, None)
            for run, task in consumers:
                if task.state in _TERMINAL:
                    continue
                self._accept_completion(run, task, owner, result, size, error)

    def _cache_work(self, work, result, size):
        if work.assessment is None or not work.assessment.completed_allowed:
            self._shared_work.pop(work.key, None)
            work.future = None
            return
        completed = [key for key, candidate in self._shared_work.items() if candidate.cache_owner is not None]
        while len(completed) >= self.settings.ready_tasks:
            retired = self._shared_work.pop(completed.pop(0))
            self.ledger.release(retired.cache_owner)
        owner = "cache:" + work.work_id
        while True:
            try:
                reserved = self.ledger.reserve(owner, {"cache_bytes": size})
            except ValueError:
                reserved = False
            if reserved:
                work.result, work.size, work.cache_owner = result, size, owner
                work.future = None
                return
            self.ledger.release(owner)
            victim = next((key for key, candidate in self._shared_work.items()
                           if key != work.key and candidate.cache_owner is not None), None)
            if victim is None:
                self._shared_work.pop(work.key, None)
                return
            retired = self._shared_work.pop(victim)
            self.ledger.release(retired.cache_owner)

    def _accept_completion(self, run, task, owner, result, size, error=None):
        try:
            if error is not None:
                raise error
            logically_cancelled = self._cancelled(run, task) and result.outcome != "unknown"
            if not isinstance(result, OperationResult):
                raise TypeError("execution.result_required")
            task.retained_owner = None
            if result.value is not None:
                try:
                    from stratbox.core.execution.values.ownership import accept_owned_value
                    from stratbox.shared.data.processing import DataContract
                    processing = result.definition.processing
                    contract = (processing.outputs[0].contract if processing and len(processing.outputs) == 1
                                else DataContract("execution.command-result"))
                    def validate(value):
                        snapshot = getattr(self.catalog, "snapshot", None)
                        if snapshot is not None and getattr(task.spec, "capability_kind", "operation") == "command":
                            authored = snapshot.definition(task.spec.operation_id)
                            outputs = ({next(iter(authored.outputs)): value} if len(authored.outputs) == 1 else
                                {name: value[name] if isinstance(value, Mapping) else getattr(value, name)
                                 for name in authored.outputs})
                            for name, port in authored.outputs.items():
                                port.validate(outputs[name])
                            authored.acceptance.validate(outputs)
                        elif processing is not None:
                            detached = replace(result, value=value)
                            for port in processing.outputs:
                                project_output(detached, port.name)
                    transfer = accept_owned_value(result.value, contract, ledger=self.ledger,
                        max_resident_bytes=self.settings.retained_bytes,
                        max_staging_bytes=self.settings.staging_bytes, checks=(validate,))
                    result = replace(result, value=transfer.value)
                    run.retained_owners.append(transfer.owner)
                    task.retained_owner = transfer.owner
                except (ValueError, TypeError) as error:
                    code = str(error)
                    code = code if code.startswith(("resource.", "acceptance.")) else "acceptance.value_rejected"
                    result = replace(result, value=None,
                        outcome="unknown" if result.outcome == "unknown" else "failed",
                        diagnostics=(*result.diagnostics, Diagnostic(code)))
            managed = ManagedResult(result, ledger=self.ledger, reservation_owner=task.retained_owner)
            task.result = managed
            task.attempt_results.append(managed)
            try:
                self.journal.capture_result(result, correlation=self._correlation(run, task))
            except Exception:
                if "execution.observation_degraded" not in run.diagnostics:
                    run.diagnostics.append("execution.observation_degraded")
            retry = task.spec.retry
            codes = {diagnostic.code for diagnostic in result.diagnostics}
            may_retry = (result.outcome in {"failed", "partial"} and not result.effects
                and task.attempts < retry.max_attempts and bool(codes & set(retry.retry_codes))
                and not self._cancelled(run, task))
            if logically_cancelled:
                self._terminal(run, task, "cancelled", "execution.cancelled")
            elif may_retry:
                task.state, task.reason = "retry_wait", "retry"
                task.next_attempt = monotonic() + retry.delay
                self._emit(run, "task.retry", task, state="retry_wait")
            else:
                self._terminal(run, task, result.outcome,
                    result.diagnostics[0].code if result.diagnostics else None)
        except BaseException as error:
            code = getattr(error, "code", None)
            self._terminal(run, task, "failed", code if isinstance(code, str) else "execution.task_error")
        self._refresh_scopes(run)
        self._reclaim(run)
        if run.plan.policy == "fail_fast" and task.spec.required and task.state in {"failed", "unknown"}:
            run.token.set()

    def _reclaim(self, run):
        # A completed producer can leave memory when every admitted consumer
        # has finished and its payload is not a selected output of its scope.
        pending = set()
        for candidate in run.tasks.values():
            if candidate.state not in _TERMINAL:
                pending.update(candidate.spec.dependencies)
        for task in run.tasks.values():
            if (task.state not in _TERMINAL or task.selected or task.spec.task_id in pending
                    or task.retained_owner is None or not isinstance(task.result, ManagedResult)
                    or not task.result.has_value):
                continue
            try:
                if run.spill is None:
                    run.spill = ResultSpillStore(max_bytes=self.settings.temporary_bytes, ledger=self.ledger)
                task.result.spill(run.spill)
            except Exception as error:
                if str(error) == "resource.temporary_bytes" and "resource.temporary_bytes" not in run.diagnostics:
                    run.diagnostics.append("resource.temporary_bytes")
                # Values without a local codec continue to consume their real
                # quota; they are never discarded or counted as released.
                continue
            if task.result.reservation_owner is None:
                if task.retained_owner in run.retained_owners:
                    run.retained_owners.remove(task.retained_owner)
                task.retained_owner = None

    def _terminal(self, run, task, state, reason=None):
        self.ledger.release(f"{run.run_id}:{task.spec.task_id}")
        task.state, task.reason = state, reason
        self._emit(run, "task.finished", task, state=state,
                   outcome=state if state in {"succeeded", "partial", "failed", "cancelled", "unknown"} else None,
                   reason=reason, invocation_id=task.result.invocation_id if task.result else None,
                   operation_id=task.spec.operation_id)

    def _collect(self, run, spec):
        members, missing = [], False
        for reference in spec.inputs:
            try:
                value = self._value_reference(run, reference)
                if isinstance(value, MapOutput):
                    missing |= value.outcome == "partial"
                    members.extend(value.values)
                else:
                    members.append(value)
            except (KeyError, ValueError):
                if not spec.allow_partial:
                    raise
                missing = True
        if missing and not spec.allow_partial:
            raise ValueError("execution.collection_incomplete")
        collection = ManagedCollection(tuple(members), spec.contract, spec.element_contract,
            outcome="partial" if missing else "succeeded", allow_empty=spec.allow_empty)
        with ValueReadScope():
            accepted = resolve_managed(collection)
            if accepted.outcome == "partial":
                if not spec.allow_partial:
                    raise ValueError("execution.collection_incomplete")
                collection = replace(collection, outcome="partial")
        return collection

    def _advance_map(self, run, task):
        from stratbox.composition.compiler import expand_map_item
        state = task.map_state
        progress = False
        for key, plan in tuple(state.active.items()):
            children = [self._task(run, spec.task_id) for spec in plan.tasks]
            if all(child.state in _TERMINAL for child in children):
                outcome = self._outcome(children)
                outputs = {}
                for name, reference in plan.outputs.items():
                    try:
                        outputs[name] = self._value_reference(run, reference)
                    except (KeyError, ValueError):
                        outcome = "failed"
                state.completed[key] = (outcome, outputs)
                del state.active[key]
                self._archive_item(run, plan)
                progress = True
        if self._cancelled(run, task):
            state.exhausted = True
            for plan in state.active.values():
                for spec in plan.tasks:
                    self._task(run, spec.task_id).token.set()
        # A nested map is a structural parent: it does not reserve a worker or
        # shared expansion credit that its descendants would need to progress.
        while not state.exhausted and len(state.active) < state.window:
            try:
                if state.pending is not None:
                    key, plan = state.pending
                else:
                    try:
                        input_key, value = next(state.iterator)
                    except StopIteration:
                        state.exhausted = True
                        self._emit(run, "map.closed", task, state="expanding", total=len(state.order))
                        break
                    except Exception:
                        state.exhausted = True
                        task.reason = "execution.map_discovery_failed"
                        break
                    maximum = getattr(task.spec.map, "max_items", None)
                    if run.expanded_items >= self.settings.expansion_items or (
                            maximum is not None and state.next_index >= maximum):
                        state.exhausted = True
                        task.reason = "execution.expansion_items"
                        break
                    field = task.spec.map.key_field
                    key = str((value[field] if isinstance(value, Mapping) else getattr(value, field)) if field else input_key)
                    if key in state.keys:
                        raise ValueError("execution.map_duplicate_key")
                    state.keys.add(key)
                    state.order.append(key)
                    state.next_index += 1
                    run.expanded_items += 1
                    selected = replace(task.spec, map=replace(task.spec.map,
                        inputs=self._resolve(run, task.spec.map.inputs)))
                    plan = expand_map_item(run.plan, selected, key, value, self.catalog)
                    state.pending = key, plan
                try:
                    self._admit_specs(run, plan.tasks)
                except ValueError as error:
                    if str(error) != "execution.expansion_capacity":
                        raise
                    # Keep this exact item and its selected bindings while
                    # another admitted item drains. No worker waits for credit.
                    live = [candidate for other in self._runs.values() for candidate in other.tasks.values()
                            if candidate.state not in _TERMINAL]
                    if not self._running and not any(candidate.spec.operation_id is not None for candidate in live):
                        raise ValueError("execution.expansion_unsatisfiable")
                    break
                try:
                    self.journal.reserve_publications(run.run_id, self._publication_budget(plan.tasks, plan.scopes))
                except ValueError as error:
                    if str(error) != "orchestration.publication_capacity":
                        raise
                    # An acknowledged journal transition frees credit on the
                    # next coordinator pass. No worker waits for publication.
                    break
                self._add_scopes(run, plan.scopes)
                self._add_tasks(run, plan.tasks, item_key=key, admitted=True)
                self._select_outputs(run, plan.outputs)
                state.active[key] = plan
                state.pending = None
                self._emit(run, "map.expanded", task, state="expanding", completed=len(state.order),
                    total=None, denominator_open=True)
            except Exception as error:
                state.exhausted = True
                state.pending = None
                code = str(error)
                task.reason = code if code.startswith(("execution.", "resource.", "capability.", "orchestration.")) else "execution.map_expansion_failed"
            progress = True
        if state.exhausted and not state.active:
            names = set(task.spec.map.body.outputs)
            task.outputs = {name: MapOutput(tuple((key, state.completed[key][1][name])
                for key in state.order if key in state.completed and name in state.completed[key][1]),
                tuple((key, state.completed.get(key, ("failed", {}))[0]) for key in state.order)) for name in names}
            outcomes = [state.completed.get(key, ("failed", {}))[0] for key in state.order]
            if any(outcome == "unknown" for outcome in outcomes):
                outcome = "unknown"
            elif self._cancelled(run, task):
                outcome = "cancelled"
            elif task.reason or any(outcome not in _GOOD for outcome in outcomes):
                outcome = "partial" if task.spec.map.allow_partial else "failed"
            elif any(outcome == "partial" for outcome in outcomes):
                outcome = "partial"
            else:
                outcome = "succeeded"
            self._terminal(run, task, outcome, task.reason)
            return True
        return progress

    def _archive_item(self, run, plan):
        self._reclaim(run)
        prefix = plan.scopes[0].scope_id + "/" if plan.scopes else ""
        for key, child in tuple(run.tasks.items()):
            if prefix and key.startswith(prefix) and child.state in _TERMINAL:
                # Keep compact identity and evidence; completed request values
                # and dynamic templates no longer belong to the ready graph.
                child.spec = replace(child.spec, inputs={}, parameters={}, dependencies=(), map=None, collect=None)
                child.map_state = None
                child.outputs = {}
                run.archived[key] = child
                del run.tasks[key]
        for scope in tuple(run.scope_ledgers):
            if prefix and (scope + "/").startswith(prefix):
                if scope in run.scopes_started and scope not in run.scopes_finished:
                    self._scope_event(run, scope, "scope.finished", self._outcome(
                        self._task(run, spec.task_id) for spec in plan.tasks))
                    run.scopes_started.remove(scope)
                del run.scope_ledgers[scope]

    @staticmethod
    def _outcome(tasks):
        tasks = tuple(tasks)
        required = [task for task in tasks if task.spec.required]
        # Unknown effects remain material even for an optional branch.
        if any(task.state == "unknown" for task in tasks):
            return "unknown"
        if any(task.state in {"failed", "blocked"} for task in required):
            return "failed"
        if any(task.state == "cancelled" for task in required):
            return "cancelled"
        if any(task.state == "partial" or task.state in {"failed", "blocked", "cancelled"}
               for task in tasks):
            return "partial"
        return "succeeded"

    def _required_effect_confirmed(self, run, key):
        root = self._task(run, key)
        scope_id = getattr(root.spec, "acceptance_scope", None)
        candidates = ([root] if root.spec.operation_id is not None else
            [task for task in self._all_tasks(run) if task.spec.operation_id is not None and
                scope_id is not None and (task.spec.scope_id == scope_id or task.spec.scope_id.startswith(scope_id + "/"))
                and task.spec.required])
        effectful = [task for task in candidates if self.catalog.get(task.spec.operation_id).possible_effects]
        if not effectful:
            return False
        for task in effectful:
            result = task.result
            if result is None or not result.effects or any(effect.state != "confirmed" for effect in result.effects):
                return False
        return True

    def _value_reference(self, run, value):
        """Retain a placement owner instead of an independently held payload."""
        from stratbox.composition.models import PlanOutputRef
        from stratbox.composition.plan import ScopeOutputRef
        if isinstance(value, ScopeOutputRef):
            if run.scope_output_states.get(value.scope_id, {}).get(value.port) != "accepted":
                raise ValueError("acceptance.output_unavailable")
            return run.scope_outputs[value.scope_id][value.port]
        if isinstance(value, PlanOutputRef):
            task = self._task(run, value.task)
            if isinstance(task.result, ManagedResult) and value.item is None:
                ports = tuple(port for port in getattr(task.result.definition.processing, "outputs", ())
                    if port.name == value.port)
                if (task.state not in _GOOD or not task.result.has_value or len(ports) != 1
                        or task.result.outcome not in ports[0].outcomes):
                    raise ValueError("acceptance.output_unavailable")
                return task.result.project(value.port)
            result = task.outputs[value.port] if task.result is None else self._resolve(run, value)
            return dict(result.items)[value.item] if value.item is not None else result
        if isinstance(value, Mapping):
            return {name: self._value_reference(run, item) for name, item in value.items()}
        if isinstance(value, (tuple, list)):
            return type(value)(self._value_reference(run, item) for item in value)
        return value

    @staticmethod
    def _public_scope_value(value):
        if isinstance(value, ManagedProjection):
            return value.owner.project(value.port, unwrap=True)
        if isinstance(value, (PreparedInput, ProjectedOutput)):
            return value.value
        return value

    def _refresh_scopes(self, run, accepting=None):
        if getattr(run, "refreshing_scopes", False):
            return
        run.refreshing_scopes = True
        try:
            with ValueReadScope():
                self._refresh_scopes_owned(run, accepting)
        finally:
            run.refreshing_scopes = False

    def _refresh_scopes_owned(self, run, accepting=None):
        """Named output acceptance and aggregate completion are separate facts."""
        for scope_id, scope in reversed(tuple(run.scope_specs.items())):
            if scope_id in run.scopes_finished:
                continue
            members = [task for task in self._all_tasks(run)
                if (task.spec.scope_id == scope_id or task.spec.scope_id.startswith(scope_id + "/"))
                and getattr(task.spec, "acceptance_scope", None) != scope_id]
            finished = all(task.state in _TERMINAL for task in members)
            states = run.scope_output_states.setdefault(scope_id, {})
            errors = run.scope_output_errors.setdefault(scope_id, {})
            outputs = run.scope_outputs.setdefault(scope_id, {})
            activation = getattr(scope, "conditions", ())
            if activation:
                try:
                    conditions_ready = all(self._task(run, condition.task).state in _TERMINAL for condition in activation)
                    active = conditions_ready and all(self._condition_matches(run, condition) for condition in activation)
                except (KeyError, ValueError, TypeError, AttributeError):
                    active, conditions_ready = False, False
                if not active:
                    if conditions_ready and finished:
                        for name in scope.outputs:
                            states[name] = "skipped"
                        run.scope_states[scope_id] = "skipped"
                        run.scopes_finished.add(scope_id)
                        self._scope_event(run, scope_id, "scope.finished", "skipped")
                    continue
            checks = tuple(getattr(scope, "required_checks", ()))
            checks_ready = all(self._task(run, key).state in _TERMINAL for key in checks)
            checks_good = checks_ready and all(self._task(run, key).state == "succeeded" for key in checks)
            if not checks_ready:
                run.scope_states[scope_id] = "running"
                continue
            values, candidates = {}, {}
            for name, reference in scope.outputs.items():
                port = scope.output_contracts.get(name)
                try:
                    from stratbox.composition import iter_references
                    if any(self._task(run, ref.task).state not in _TERMINAL for ref in iter_references(reference)):
                        continue
                    projected = self._resolve(run, reference)
                    value = projected.value if isinstance(projected, (PreparedInput, ProjectedOutput)) else projected
                    if port is not None:
                        port.validate(value)
                        if port.schema is not None and isinstance(projected, (PreparedInput, ProjectedOutput)) and projected.contract != port.schema:
                            raise ValueError("acceptance.schema_mismatch")
                        if not port.qualifications <= getattr(projected, "qualifications", frozenset()):
                            raise ValueError("acceptance.qualification_missing")
                        if not port.expected_coverage <= getattr(projected, "coverage", frozenset()):
                            raise ValueError("acceptance.coverage_missing")
                    if not checks_good:
                        raise ValueError("acceptance.obligation_unconfirmed")
                    values[name] = value
                    candidates[name] = self._value_reference(run, reference)
                except (KeyError, ValueError, TypeError, AttributeError) as error:
                    if finished or not checks_good:
                        states[name] = "rejected"
                        outputs.pop(name, None)
                        code = str(error)
                        errors[name] = (code if code.startswith("acceptance.") else "acceptance.output_unavailable",)
            acceptance = getattr(scope, "acceptance", None)
            if acceptance is not None:
                settled = set(values) | {name for name, state in states.items() if state in {"rejected", "skipped"}}
                if finished:
                    settled.update(scope.outputs)
                predicate_errors, pending_outputs = acceptance.assess_outputs(values,
                    names=tuple(scope.outputs), settled=settled)
                for name in pending_outputs:
                    states[name] = "waiting"
                    candidates.pop(name, None)
                    values.pop(name, None)
                    outputs.pop(name, None)
                for name, codes in predicate_errors.items():
                    states[name] = "rejected"
                    errors[name] = codes
                    outputs.pop(name, None)
                    values.pop(name, None)
                    candidates.pop(name, None)
            for name, reference in candidates.items():
                states[name] = "accepted"
                outputs[name] = reference
                errors.pop(name, None)
            if getattr(scope, "kind", None) == "operation":
                fresh = {name: values[name] for name in candidates if (scope_id, name) not in run.published_outputs}
                if fresh:
                    self._accepted_facts(run, scope, fresh, "succeeded")
                    run.published_outputs.update((scope_id, name) for name in fresh)
            if not finished:
                run.scope_states[scope_id] = "running"
                continue
            outcome = self._outcome(members)
            required_missing = [name for name, port in scope.output_contracts.items()
                if port.required and states.get(name) != "accepted"]
            effects = tuple(getattr(scope, "required_effects", ()))
            effect_good = all(self._task(run, key).state == "succeeded" and self._required_effect_confirmed(run, key) for key in effects)
            if (required_missing or not checks_good or not effect_good) and outcome not in {"unknown", "cancelled"}:
                outcome = "failed"
            if outcome == "partial" and acceptance is not None and not acceptance.partial_allowed:
                outcome = "failed"
            for codes in errors.values():
                run.diagnostics.extend(code for code in codes if code not in run.diagnostics)
            if not effect_good and "acceptance.effect_unconfirmed" not in run.diagnostics:
                run.diagnostics.append("acceptance.effect_unconfirmed")
            run.scope_states[scope_id] = outcome
            run.scopes_finished.add(scope_id)
            self._scope_event(run, scope_id, "scope.finished", outcome)

    def _accepted_facts(self, run, scope, outputs, outcome):
        from stratbox.core.execution.values import value_identity
        for name, value in outputs.items():
            port = getattr(scope, "output_contracts", {}).get(name)
            role = getattr(getattr(port, "schema", None), "role", None)
            if role is None:
                continue
            try:
                identity = value_identity(value)
                acceptance_id = _token(f"{run.run_id}:{scope.scope_id}:{name}")
                value_id = _token(f"{scope.definition_id}:{name}:{identity.sha256}")
                from stratbox.shared.data.assessment import value_evidence
                actual = value_evidence(value)
                qualification = next(iter(sorted(actual.qualifications)), "unqualified")
                coverage = actual.coverage
                complete = getattr(coverage, "status", None) == "complete"
                from stratbox.core.execution.value_context import value_context
                source_ids = value_context(value, port.schema).source_ids
                source_id = next(iter(source_ids)) if len(source_ids) == 1 else getattr(value, "source_id", None)
                self.journal.accepted_value(replace(self._correlation(run),
                    workflow_scope_id=_token(scope.scope_id)), value_id=value_id,
                    stage=scope.definition_id, role=role.value, identity=identity,
                    source_id=source_id, qualification=qualification,
                    complete=complete, acceptance_id=acceptance_id)
            except Exception:
                if "execution.observation_degraded" not in run.diagnostics:
                    run.diagnostics.append("execution.observation_degraded")

    def _accepted_output(self, run, reference):
        from stratbox.composition.plan import ScopeOutputRef
        if isinstance(reference, ScopeOutputRef):
            return self._resolve(run, reference)
        # Transitional physical references have no separate public scope owner.
        return self._resolve(run, reference)

    def _finish(self, run):
        all_tasks = tuple(self._all_tasks(run))
        outputs, diagnostics = {}, [*run.diagnostics, *(task.reason for task in all_tasks
            if task.reason and task.state in {"failed", "blocked", "partial", "unknown", "cancelled"})]
        outcome = self._outcome(run.tasks[spec.task_id] for spec in run.plan.tasks)
        root_scopes = [scope for scope in run.plan.scopes if scope.parent_id is None]
        if root_scopes:
            outcome = run.scope_states.get(root_scopes[0].scope_id, outcome)
        root_contracts = getattr(root_scopes[0], "output_contracts", {}) if root_scopes else {}
        for name, reference in run.plan.outputs.items():
            try:
                outputs[name] = self._value_reference(run, reference)
            except (KeyError, ValueError):
                port = root_contracts.get(name)
                if port is not None and not port.required:
                    continue
                diagnostics.append("execution.output_unavailable")
                if outcome in _GOOD:
                    outcome = "failed"
        run.state, run.finished_at = outcome, monotonic()
        from stratbox.core.execution.retention import ResultOwnership
        managed = tuple(dict.fromkeys(result for task in all_tasks
            for result in (task.result, *task.attempt_results) if isinstance(result, ManagedResult)))
        ownership = ResultOwnership(self.ledger, tuple(run.retained_owners), run.spill, managed=managed,
            on_close=lambda: self.effects.release_run(run.run_id))
        self.effects.finish_run(run.run_id)
        self.journal.release_publications(run.run_id)
        result = RunResult(run.run_id, run.plan.plan_id, outcome, ValueMapping(outputs),
            ResultMapping({task.spec.task_id: task.result for task in all_tasks if task.result is not None}),
            tuple(self._task_snapshot(task) for task in all_tasks), tuple(dict.fromkeys(diagnostics)),
            AttemptMapping({task.spec.task_id: tuple(task.attempt_results) for task in all_tasks if task.attempt_results}), run.spill,
            ownership, MappingProxyType(dict(run.scope_states)),
            MappingProxyType({key: ValueMapping(value, unwrap=True) for key, value in run.scope_outputs.items()}))
        counters = {state: sum(task.state == state for task in all_tasks) for state in _TERMINAL}
        counters.update(physical_work=run.physical_work_count, logical_uses=run.logical_use_count)
        for scope in run.scopes_started - run.scopes_finished:
            scoped = [task for task in all_tasks if task.spec.scope_id == scope or task.spec.scope_id.startswith(scope + "/")]
            try:
                self.journal.emit("scope.finished", replace(self._correlation(run), workflow_scope_id=_token(scope)),
                    state=self._outcome(scoped), outcome=self._outcome(scoped))
            except Exception:
                pass
        self._emit(run, "run.finished", state=outcome, outcome=outcome,
                   completed=len(all_tasks), total=len(all_tasks), counters=counters,
                   service=bool([task for task in all_tasks if task.spec.operation_id]) and
                       all(task.spec.operation_id.startswith(("notifications.", "notification.", "subscription."))
                           for task in all_tasks if task.spec.operation_id))
        snapshot = self._snapshot_run(run)
        detail_limit = self.settings.event_capacity
        self._history[run.run_id] = replace(snapshot, tasks=snapshot.tasks[-detail_limit:],
            task_count=snapshot.total, completed_count=snapshot.completed,
            task_details_complete=len(snapshot.tasks) <= detail_limit)
        while (len(self._history) > self.settings.event_capacity or
               sum(len(item.tasks) for item in self._history.values()) > detail_limit):
            self._history.popitem(last=False)
        self._runs.pop(run.run_id, None)
        run.final_snapshot = self._history.get(run.run_id, snapshot)
        # A RunHandle retains its lightweight run record. Payload ownership has
        # transferred to RunResult, so the handle must not keep a second graph.
        run.tasks.clear()
        run.archived.clear()
        run.order.clear()
        run.scope_specs.clear()
        run.scope_outputs.clear()
        run.plan, run.spill = None, None
        run.future.set_result(result)
