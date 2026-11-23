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
from stratbox.core.execution.retention import ResultSpillStore, SpilledResult, ResultMapping, AttemptMapping, retained_size

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
    expenditure: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        for name in ("max_workers", "active_runs", "pending_runs", "ready_tasks", "map_window",
                     "network", "per_origin", "parsers", "heavy_parsers", "cpu", "notifications",
                     "retained_bytes", "temporary_bytes", "event_capacity"):
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

    def close(self):
        """Release temporary intermediate files; selected outputs stay available."""
        if self._spill is not None:
            self._spill.close()

    def output(self, name):
        value = self.outputs[name]
        return value.value if isinstance(value, (ProjectedOutput, PreparedInput)) else value

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
            return self._session._snapshot_run(self._run)

    def cancel(self, scope_id=None):
        return False if self.done() else self._session.cancel(self.run_id, scope_id=scope_id)

    def events(self, after=0):
        return self._session.events(after=after, run_id=self.run_id)


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
            "retained_bytes": self.settings.retained_bytes, "temporary_bytes": self.settings.temporary_bytes}, expenditure=self.settings.expenditure,
            per_origin=self.settings.per_origin)
        from stratbox.core.observability.capture.orchestration import OrchestrationJournal
        self.journal = OrchestrationJournal(self.session_id, max_records=self.settings.event_capacity,
                                             telemetry_sink=observer)
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
            self._add_scopes(run, plan.scopes)
            self._add_tasks(run, plan.tasks)
            self._select_outputs(run, plan.outputs)
            for task in run.tasks.values():
                if task.spec.operation_id is not None:
                    self.ledger.validate(self._requirements(task.spec))
            if any(task.spec.operation_id is not None and "http" in (
                    self.catalog.get(task.spec.operation_id).required_capabilities |
                    self.catalog.get(task.spec.operation_id).optional_capabilities)
                   for task in run.tasks.values()):
                self._prepare_network(run.context)
            self.journal.reserve_run(run.run_id)
            self._runs[run.run_id] = run
            self._pending.append(run.run_id)
            self._emit(run, "run.queued", state="queued")
            self._start()
            self._condition.notify_all()
            return RunHandle(self, run)

    def run(self, plan, **options):
        return self.submit(plan, **options).result()

    def _add_tasks(self, run, specs, *, item_key=None):
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
                            for task in run.tasks.values()))

    def _add_scopes(self, run, scopes):
        for scope in scopes:
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
            self._condition.notify_all()
        if wait and self._thread is not None and current_thread() is not self._thread:
            self._thread.join()
        if self._thread is None:
            self._finish_close()

    def _finish_close(self):
        if self._closed:
            return
        if self._pool:
            self._pool.shutdown(wait=True)
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
                attempt_id=_token(f"{run.run_id}:{task.spec.task_id}:{task.attempts}"))
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
                            if "execution.deadline" not in run.diagnostics:
                                run.diagnostics.append("execution.deadline")
                        progress |= self._advance(run)
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
            if task.spec.condition is not None:
                try:
                    selected = self._condition_matches(run, task.spec.condition)
                except (ValueError, KeyError, TypeError, AttributeError):
                    self._terminal(run, task, "failed", "execution.condition_invalid")
                    progress = True
                    continue
                if not selected:
                    self._terminal(run, task, "skipped", "execution.condition_false")
                    progress = True
                    continue
            failed = [dep for dep in dependencies if dep.state not in _GOOD and dep.state != "skipped"]
            if task.spec.condition is not None and task.spec.condition.statuses:
                from stratbox.composition.compiler import iter_references
                data_deps = {ref.task for ref in iter_references((task.spec.inputs, task.spec.parameters))}
                failed = [dep for dep in failed if dep.spec.task_id != task.spec.condition.task
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
                    task.state = "expanding"
                    progress = True
                except Exception:
                    self._terminal(run, task, "failed", "execution.map_input_invalid")
                continue
            if task.spec.collect is not None:
                try:
                    task.outputs["value"] = self._collect(run, task.spec.collect)
                    self._terminal(run, task, task.outputs["value"].outcome)
                except Exception:
                    self._terminal(run, task, "failed", "execution.collection_invalid")
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
            future = self._pool.submit(self._execute, run, task, owner)
            self._running[future] = (run.run_id, task.spec.task_id, owner)
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
        value = self._resolve(run, PlanOutputRef(condition.task, condition.port))
        if isinstance(value, (ProjectedOutput, PreparedInput)):
            value = value.value
        for name in condition.field.split(".") if condition.field else ():
            value = value[name] if isinstance(value, Mapping) else getattr(value, name)
        return value == condition.equals

    def _resolve(self, run, value):
        from stratbox.composition.models import PlanOutputRef
        if isinstance(value, PlanOutputRef):
            task = self._task(run, value.task)
            result = task.result.resolve() if isinstance(task.result, SpilledResult) else task.result
            projected = project_output(result, value.port) if result else task.outputs[value.port]
            if value.item is not None:
                if not isinstance(projected, MapOutput):
                    raise ValueError("execution.item_reference_requires_map")
                projected = dict(projected.items)[value.item]
            return projected
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

    def _execute(self, run, task, owner):
        inputs = self._isolate(self._resolve(run, task.spec.inputs))
        parameters = self._isolate(self._parameter_values(self._resolve(run, task.spec.parameters)))
        from stratbox.core.execution.methods import method_descriptor
        definition, handler, _ = self.catalog.resolve(task.spec.operation_id)
        fingerprint = method_descriptor(definition, work=None if definition.method_refs else handler).identity.sha256
        if definition.method_id != task.spec.method_id or fingerprint != task.spec.method_fingerprint:
            raise ValueError("execution.method_changed")
        context = replace(run.context, correlation=self._correlation(run, task),
            cancellation=_Cancellation(run.token, task.token, run.context.cancellation),
            resource_ledger=run.scope_ledgers.get(task.spec.scope_id, self.ledger),
            sink=self.journal.operation_sink(run.context.sink))
        from stratbox.core.runtime.capabilities import ProviderBinding, CapabilityRequirement
        from stratbox.core.network import AccessScope
        bindings = []
        has_http = False
        for binding in context.bindings:
            if binding.capability.role == "http":
                has_http = True
                network = self._networks.get(id(binding.provider))
                if network is not None:
                    transport = network.transport_for(run.run_id,
                        scope=AccessScope(binding.provider_id, binding.scope_id or
                            getattr(getattr(binding.provider, "scope", None), "scope_id", "public"), profile=context.profile),
                        reservation_owner=owner, ledger=self.ledger,
                        run_id=run.run_id, task_id=_token(task.spec.task_id))
                    binding = replace(binding, provider=transport)
            bindings.append(binding)
        if not has_http and self._network is not None:
            transport = self._network.transport_for(run.run_id, scope=AccessScope(profile=context.profile),
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
                    per_origin=self.settings.per_origin, max_bytes=self.settings.retained_bytes)
        if not http and self._network is None:
            self._network = SessionNetwork(journal=self.journal, per_origin=self.settings.per_origin,
                                           max_bytes=self.settings.retained_bytes)

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
            rid, tid, owner = self._running.pop(future)
            self.ledger.release(owner)
            run, task = self._runs[rid], self._runs[rid].tasks[tid]
            try:
                result, size = future.result()
                if not isinstance(result, OperationResult):
                    raise TypeError("execution.result_required")
                if result.value is not None:
                    retained_owner = owner + ":retained:" + str(task.attempts)
                    try:
                        retained = self.ledger.reserve(retained_owner, {"retained_bytes": size})
                    except ValueError:
                        retained = False
                    if retained:
                        run.retained_owners.append(retained_owner)
                        task.retained_owner = retained_owner
                    else:
                        result = replace(result, value=None,
                            outcome="unknown" if result.outcome == "unknown" else "failed",
                            diagnostics=(*result.diagnostics, Diagnostic("resource.retained_bytes")))
                task.result = result
                task.attempt_results.append(result)
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
                if may_retry:
                    task.state, task.reason = "retry_wait", "retry"
                    task.next_attempt = monotonic() + retry.delay
                    self._emit(run, "task.retry", task, state="retry_wait")
                else:
                    self._terminal(run, task, result.outcome,
                        result.diagnostics[0].code if result.diagnostics else None)
            except BaseException as error:
                # Handler exceptions are usually qualified by its runner. A
                # binder or contract failure has no fabricated operation result.
                code = getattr(error, "code", None)
                self._terminal(run, task, "failed", code if isinstance(code, str) else "execution.task_error")
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
                    or task.retained_owner is None or not isinstance(task.result, OperationResult)
                    or task.result.value is None):
                continue
            try:
                if run.spill is None:
                    run.spill = ResultSpillStore(max_bytes=self.settings.temporary_bytes, ledger=self.ledger)
                retained = run.spill.put(task.result)
            except Exception as error:
                if str(error) == "resource.temporary_bytes" and "resource.temporary_bytes" not in run.diagnostics:
                    run.diagnostics.append("resource.temporary_bytes")
                # Values without a local codec continue to consume their real
                # quota; they are never discarded or counted as released.
                continue
            task.attempt_results = [retained if result is task.result else result for result in task.attempt_results]
            task.result = retained
            self.ledger.release(task.retained_owner)
            run.retained_owners.remove(task.retained_owner)
            task.retained_owner = None

    def _terminal(self, run, task, state, reason=None):
        task.state, task.reason = state, reason
        self._emit(run, "task.finished", task, state=state,
                   outcome=state if state in {"succeeded", "partial", "failed", "cancelled", "unknown"} else None,
                   reason=reason, invocation_id=task.result.invocation_id if task.result else None,
                   operation_id=task.spec.operation_id)

    def _collect(self, run, spec):
        members = []
        missing = False
        for reference in spec.inputs:
            try:
                value = self._resolve(run, reference)
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
        if not members:
            if not spec.allow_empty:
                raise ValueError("execution.collection_empty")
            return PreparedInput(spec.contract, (), outcome="partial" if missing else "succeeded")
        result = collect_inputs(tuple(members), contract=spec.contract, element_contract=spec.element_contract)
        if result.outcome == "partial" and not spec.allow_partial:
            raise ValueError("execution.collection_incomplete")
        return replace(result, outcome="partial") if missing else result

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
                        outputs[name] = self._resolve(run, reference)
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
                input_key, value = next(state.iterator)
            except StopIteration:
                state.exhausted = True
                self._emit(run, "map.closed", task, state="expanding", total=len(state.order))
                break
            except Exception:
                state.exhausted = True
                task.reason = "execution.map_discovery_failed"
                break
            try:
                field = task.spec.map.key_field
                key = str((value[field] if isinstance(value, Mapping) else getattr(value, field)) if field else input_key)
                if key in state.keys:
                    raise ValueError("execution.map_duplicate_key")
                state.keys.add(key)
                state.order.append(key)
                state.next_index += 1
                selected = replace(task.spec, map=replace(task.spec.map,
                    inputs=self._resolve(run, task.spec.map.inputs)))
                plan = expand_map_item(run.plan, selected, key, value, self.catalog)
                self._add_scopes(run, plan.scopes)
                self._add_tasks(run, plan.tasks, item_key=key)
                self._select_outputs(run, plan.outputs)
                state.active[key] = plan
                self._emit(run, "map.expanded", task, state="expanding", completed=len(state.order))
            except Exception:
                state.exhausted = True
                task.reason = "execution.map_expansion_failed"
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
                if scope in run.scopes_started:
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

    def _finish(self, run):
        all_tasks = tuple(self._all_tasks(run))
        outputs, diagnostics = {}, [*run.diagnostics, *(task.reason for task in all_tasks
            if task.reason and task.state in {"failed", "blocked", "partial", "unknown", "cancelled"})]
        outcome = self._outcome(run.tasks[spec.task_id] for spec in run.plan.tasks)
        for name, reference in run.plan.outputs.items():
            try:
                outputs[name] = self._resolve(run, reference)
            except (KeyError, ValueError):
                diagnostics.append("execution.output_unavailable")
                if outcome in _GOOD:
                    outcome = "failed"
        run.state, run.finished_at = outcome, monotonic()
        result = RunResult(run.run_id, run.plan.plan_id, outcome, MappingProxyType(outputs),
            ResultMapping({task.spec.task_id: task.result for task in all_tasks if task.result is not None}),
            tuple(self._task_snapshot(task) for task in all_tasks), tuple(dict.fromkeys(diagnostics)),
            AttemptMapping({task.spec.task_id: tuple(task.attempt_results) for task in all_tasks if task.attempt_results}), run.spill)
        counters = {state: sum(task.state == state for task in all_tasks) for state in _TERMINAL}
        for scope in run.scopes_started:
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
        for owner in run.retained_owners:
            self.ledger.release(owner)
        if run.spill is not None:
            run.spill.release_capacity()
        snapshot = self._snapshot_run(run)
        detail_limit = self.settings.event_capacity
        self._history[run.run_id] = replace(snapshot, tasks=snapshot.tasks[-detail_limit:],
            task_count=snapshot.total, completed_count=snapshot.completed,
            task_details_complete=len(snapshot.tasks) <= detail_limit)
        while (len(self._history) > self.settings.event_capacity or
               sum(len(item.tasks) for item in self._history.values()) > detail_limit):
            self._history.popitem(last=False)
        self._runs.pop(run.run_id, None)
        run.future.set_result(result)
