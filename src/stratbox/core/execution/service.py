"""One direct, bounded execution service for every prepared callable kind.

The coordinator owns dependencies and waits. Workers execute a single bound
command and never rebuild an operation definition or resolve a publisher.
"""
from __future__ import annotations

from collections import deque, OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timezone
from threading import Condition, Event, RLock, Thread, current_thread, local
from time import monotonic
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4
from contextlib import contextmanager

from stratbox.shared.data.values import fingerprint
from .errors import OperationFailure, ExecutionFailure, error_code
from .owned_values import _size, _isolate, _value_keys, OwnedValues, seal_plan_inputs
from .boundary_accounting import account_inputs, account_outputs
from .context import CommandContext
from .results import RunHandle, RunResult
from .admission import inspect_plan, snapshot_plan, replace_record, AdmissionRejected
from .observers import ObserverDispatcher
from .output_uses import output_use, referenced_uses, member_assessment, unsuccessful
from stratbox.core.observability.journal.stream import JournalFact, MemoryJournal
from stratbox.core.limits import ExecutionBudget, BudgetMeter, BudgetError
from stratbox.shared.data.materials import staged_references
from stratbox.core.storage.staged_values import StagedValueStore




@dataclass(frozen=True)
class ExecutionSettings:
    max_workers: int = 4
    active_runs: int = 8
    capacities: Mapping[str, int] = field(default_factory=lambda: {
        "worker": 4, "network": 2, "parse": 2, "cpu": 4, "solver": 1,
        "render": 2, "storage_io": 4, "storage_read": 4, "storage_write": 2,
        "converter": 1, "notification": 2,
    })
    max_retained_bytes: int = 256 * 1024 * 1024
    event_capacity: int = 10000
    run_limits: ExecutionBudget = field(default_factory=ExecutionBudget)
    effect_capacity: int = 10000
    max_accepted_values: int = 10000
    max_open_runs: int = 128
    max_pending_runs: int = 64
    max_plan_nodes: int = 10000
    max_plan_bytes: int = 64 * 1024 * 1024
    max_admitted_nodes: int = 100000
    max_admitted_plan_bytes: int = 128 * 1024 * 1024
    observer_queue_capacity: int = 256
    observer_queue_bytes: int = 4 * 1024 * 1024
    observer_diagnostic_capacity: int = 256
    max_staged_bytes: int = 16 * 1024**3
    max_staged_objects: int = 10000
    max_staged_readers: int = 64
    staging_directory: str | None = None

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in (
                self.max_workers, self.active_runs, self.max_retained_bytes, self.event_capacity, self.effect_capacity, self.max_accepted_values,
                self.max_open_runs,self.max_pending_runs,self.max_plan_nodes,self.max_plan_bytes,
                self.max_admitted_nodes,self.max_admitted_plan_bytes,self.observer_queue_capacity,
                self.observer_queue_bytes,self.observer_diagnostic_capacity,
                self.max_staged_bytes,self.max_staged_objects,self.max_staged_readers)):
            raise ValueError("execution.invalid_settings")
        if any(type(n) is not int or n < 1 for n in self.capacities.values()):
            raise ValueError("execution.invalid_capacity")
        object.__setattr__(self, "capacities", MappingProxyType(dict(self.capacities)))
        if isinstance(self.run_limits, Mapping):
            object.__setattr__(self, "run_limits", ExecutionBudget(**self.run_limits))
        if not isinstance(self.run_limits, ExecutionBudget):
            raise TypeError("execution.invalid_run_limits")


@dataclass(frozen=True)
class CommandCompletion:
    outputs: Mapping[str, object]
    outcome: str = "succeeded"
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectReceipt:
    effect_id: str
    kind: str
    status: str
    value: object = None
    resource: str | None = None
    finding: str | None = None
    intent: object = None
    revision: int = 0
    claim_id: str | None = None
    evidence: object = None

    def __post_init__(self):
        from stratbox.shared.data.values import immutable
        object.__setattr__(self, "value", immutable(_isolate(self.value)))
        object.__setattr__(self, "intent", immutable(_isolate(self.intent)))
        object.__setattr__(self, 'evidence', immutable(_isolate(self.evidence)))
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError('effect.invalid_revision')
        if self.claim_id is not None and (not isinstance(self.claim_id, str) or not self.claim_id):
            raise ValueError('effect.invalid_claim')


def _identity(value):
    return fingerprint(value)




def _sources(value):
    result = set()
    direct = getattr(value, "source_id", None)
    if direct:
        result.add(direct)
    claim = getattr(value, "claim", None)
    if claim is not None and getattr(claim, "source_id", None):
        result.add(claim.source_id)
    material = getattr(value, "material", None)
    if material is not None and material is not value:
        result.update(_sources(material))
    if isinstance(value, Mapping):
        for item in value.values():
            result.update(_sources(item))
    elif isinstance(value, (tuple, list)):
        for item in value:
            result.update(_sources(item))
    return result


def _validate(port, value):
    validate = getattr(port, "validate", None)
    if validate:
        validate(value)
    expected = getattr(port, "value_type", object)
    if expected is not object and not isinstance(value, expected):
        raise ExecutionFailure("acceptance.value_type_mismatch")




@dataclass
class _Task:
    spec: object
    state: str = "pending"
    outputs: dict = field(default_factory=dict)
    findings: tuple = ()
    future: Future | None = None
    claims: dict = field(default_factory=dict)
    work_key: str | None = None
    physical_id: str | None = None
    expansion: dict | None = None
    cancelled: bool = False
    owned_inputs: object = None
    bound_parameters: object = None
    wait_ticket: int | None = None
    accepted_keys: set = field(default_factory=set)
    input_keys: set = field(default_factory=set)
    effect_ids: set = field(default_factory=set)
    output_uses: dict = field(default_factory=dict)
    generation_id: str | None = None
    physical_producer: bool = False
    reused: bool = False
    output_records: dict = field(default_factory=dict)
    physical_outcome: str | None = None


@dataclass
class _WorkGeneration:
    generation_id: str
    work_key: str | None
    demands: dict
    future: Future | None = None
    state: str = 'running'
    cancel: Event = field(default_factory=Event)
    consumers: set = field(default_factory=set)


@dataclass
class _Run:
    run_id: str
    plan: object
    tasks: dict
    future: Future = field(default_factory=Future)
    cancel: Event = field(default_factory=Event)
    deadline: float | None = None
    diagnostics: list = field(default_factory=list)
    scopes: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    started: bool = False
    closed: bool = False
    extra_scopes: list = field(default_factory=list)
    effect_ids: set = field(default_factory=set)
    meter: object = None
    accepted_scopes: set = field(default_factory=set)
    root_ids: tuple[str, ...] = ()
    journal_failed: bool = False
    started_work: bool = False
    admission_bytes: int = 0
    admission_nodes: int = 0


@dataclass(frozen=True)
class _TaskSummary:
    task_id: str
    scope_id: str
    required: bool = True
    origin: str = "data"












class ExecutionService:
    """A multicall session with one coordinator, shared resources and value owners."""
    def __init__(self, *, providers=None, settings=None, journal=None, observer=None, admission_guard=None):
        self.providers, self.settings = dict(providers or {}), settings or ExecutionSettings()
        from stratbox.core.notifications import MemoryNotificationState
        self.providers.setdefault("notification_state", MemoryNotificationState())
        self.journal, self.observer = journal or MemoryJournal(self.settings.event_capacity), observer
        if observer is not None and not callable(observer): raise TypeError("observation.callback_required")
        if admission_guard is not None and not callable(admission_guard): raise TypeError('admission.guard_callable_required')
        self.admission_guard = admission_guard
        self._condition = Condition(RLock())
        self._values = OwnedValues(max_bytes=self.settings.max_retained_bytes)
        self.staging = StagedValueStore(directory=self.settings.staging_directory,
            max_bytes=self.settings.max_staged_bytes,
            max_objects=self.settings.max_staged_objects,
            max_readers=self.settings.max_staged_readers)
        self._state, self._failure = "running", None
        self._closed_event, self._worker_local = Event(), local()
        self._admitting = self._plan_bytes = self._plan_nodes = 0
        self._admission_pauses = 0
        self._pool = ThreadPoolExecutor(max_workers=self.settings.max_workers, thread_name_prefix="stratbox")
        self._runs, self._order, self._used = {}, deque(), {}
        self._work, self._completed, self._effects, self._accepted = {}, {}, OrderedDict(), OrderedDict()
        self._generations = {}
        self._effect_authority = None
        self._effect_provider = None
        self._reconciling_effects = set()
        self._retained_bytes, self._cache_bytes = 0, 0
        self._observer_dispatcher = None if observer is None else ObserverDispatcher(observer,
            capacity=self.settings.observer_queue_capacity,byte_capacity=self.settings.observer_queue_bytes,
            diagnostic_capacity=self.settings.observer_diagnostic_capacity)
        self._next_ticket = 0
        self._thread = Thread(target=self._coordinate, name="stratbox-coordinator", daemon=True)
        self._thread.start()

    def _fact(self, run, kind, task=None, output_name=None, scope_id=None, accepted_value=None, **data):
        if run.journal_failed: return None
        if task is not None:
            if output_name in task.output_uses:
                data.update(task.output_uses[output_name].fact())
            command = getattr(task.spec, "command", None)
            data.setdefault("capability_id", getattr(command, "id", None))
            data.setdefault("capability_kind", "command" if command else getattr(task.spec, "kind", "command"))
            data.setdefault("dependencies", tuple(getattr(task.spec, "deps", ())))
            data.setdefault("origin", self._task_origin(task))
            if kind == "output.accepted" and output_name in task.outputs:
                from .accepted_values import accepted_fact
                value = task.outputs[output_name]
                record = accepted_value
                if record is None:
                    try:
                        record = self._accepted.get(self._values.identity(value))
                    except (ValueError, TypeError):
                        record = None
                if record is not None:
                    data.update(record.get('fact', {}))
        if "origin" not in data:
            tasks = [run.tasks[key] for key in run.root_ids] if run.root_ids else list(run.tasks.values())
            data["origin"] = "notification" if tasks and all(self._task_origin(item) == "notification" for item in tasks) else "data"
        kwargs = dict(kind=kind, run_id=run.run_id, scope_id=scope_id if scope_id is not None else getattr(getattr(task, "spec", None), "scope_id", ""),
            command_id=getattr(getattr(getattr(task, "spec", None), "command", None), "id", None),
            output_name=output_name, physical_work_id=getattr(task, "physical_id", None),
            attempt_id=(task.physical_id + ":1") if task and task.physical_id else None, data=data)
        try:
            fact = self.journal.append(**kwargs)
        except Exception:
            active = any(item.state in {"running","waiting_shared"} for item in run.tasks.values())
            if not active and not run.effect_ids and not run.started_work: raise
            run.journal_failed = True
            run.diagnostics.append("journal.publication_failed")
            return None
        if self._observer_dispatcher is not None: self._observer_dispatcher.offer(fact)
        return fact

    @property
    def state(self):
        with self._condition: return self._state

    @property
    def failure(self):
        with self._condition: return self._failure

    @property
    def _closing(self): return self._state != "running"

    @property
    def _stopped(self): return self._closed_event.is_set()

    def observer_status(self):
        return None if self._observer_dispatcher is None else self._observer_dispatcher.status()

    def value_statistics(self):
        """Bounded ownership counters; inspecting them never visits payloads."""
        with self._values._lock:
            return {'resident_bytes': self._values.resident_bytes,
                'working_bytes': self._values.working_bytes,
                'sealed_values': self._values.sealed_values,
                'exact_identity_passes': self._values.identity_passes,
                'live_values': len(self._values._entries), 'owners': len(self._values._owners)}

    def wait_closed(self, timeout=None):
        if current_thread() is self._thread or getattr(self._worker_local,"active",False):
            raise ExecutionFailure("execution.reentrant_wait")
        return self._closed_event.wait(timeout)

    def _task_origin(self, task, memo=None):
        memo = {} if memo is None else memo
        if id(task.spec) in memo: return memo[id(task.spec)]
        command = getattr(task.spec,"command",None)
        if command is None:
            templates = (getattr(task.spec,"template",None),)
            if getattr(task.spec,"kind",None) == "dispatch": templates = tuple(task.spec.alternatives.values())
            children = [child for template in templates if template is not None for child in template.tasks]
            if children and all(self._task_origin(_Task(child),memo) == "notification" for child in children):
                memo[id(task.spec)] = "notification"
                return "notification"
            return getattr(task.spec,"origin","data")
        return "notification" if command.effects and command.effects <= {"notification.state","notification.deliver"} else "data"

    def _scope_origin(self,run,scope):
        # Origin describes all work owned by the scope, including optional
        # work and nested composites; completion obligations are a different set.
        tasks = [task for task in run.tasks.values() if task.spec.scope_id == scope.scope_id
            or task.spec.scope_id.startswith(scope.scope_id + '/')]
        return "notification" if tasks and all(self._task_origin(task) == "notification" for task in tasks) else "data"

    def _check_accepting(self):
        if self._state == "failed": raise ExecutionFailure("execution.service_failed")
        if self._state != "running": raise ExecutionFailure("execution.service_closed")
        if self._admission_pauses: raise ExecutionFailure('execution.admission_paused')

    @property
    def active_physical_count(self):
        with self._condition:
            return sum(generation.future is None or not generation.future.done()
                for generation in self._generations.values())

    @property
    def quiescent(self):
        with self._condition:
            return not self._admitting and not any(not run.future.done() for run in self._runs.values())

    @contextmanager
    def admission_pause(self, *, timeout=None):
        """Drain admitted work and hold a stable, reversible admission barrier.

        Unknown durable effects remain evidence. This waits for actual worker
        settlement, without closing the service or discarding open results.
        """
        from math import isfinite
        if timeout is not None and (type(timeout) not in (int, float) or not isfinite(timeout) or timeout < 0):
            raise ValueError('execution.invalid_timeout')
        if current_thread() is self._thread or getattr(self._worker_local, 'active', False):
            raise ExecutionFailure('execution.reentrant_wait')
        deadline = None if timeout is None else monotonic() + timeout
        with self._condition:
            if self._state != 'running':
                raise ExecutionFailure('execution.service_closed')
            self._admission_pauses += 1
        try:
            with self._condition:
                while not self.quiescent:
                    remaining = None if deadline is None else deadline - monotonic()
                    if remaining is not None and remaining <= 0:
                        raise ExecutionFailure('execution.quiescence_timeout')
                    self._condition.wait(remaining)
                if self._state != 'running':
                    raise ExecutionFailure('execution.service_closed')
            yield self
        finally:
            with self._condition:
                self._admission_pauses -= 1
                self._condition.notify_all()

    def _reserve_admission(self,nodes,size,run=None):
        if run is not None and run.admission_nodes+nodes > self.settings.max_plan_nodes:
            raise ExecutionFailure("admission.plan_nodes")
        if run is not None and run.admission_bytes+size > self.settings.max_plan_bytes:
            raise ExecutionFailure("admission.plan_bytes")
        if self._plan_nodes+nodes > self.settings.max_admitted_nodes: raise ExecutionFailure("admission.total_nodes")
        if self._plan_bytes+size > self.settings.max_admitted_plan_bytes: raise ExecutionFailure("admission.total_plan_bytes")
        self._plan_nodes += nodes; self._plan_bytes += size
        if run is not None:
            run.admission_nodes += nodes; run.admission_bytes += size

    def _release_admission(self,run):
        self._plan_nodes -= run.admission_nodes; self._plan_bytes -= run.admission_bytes
        run.admission_nodes = run.admission_bytes = 0

    def _compact_admission(self,run):
        nodes = min(run.admission_nodes,len(run.tasks)+len(run.scopes)+1)
        size = min(run.admission_bytes,_size((run.tasks,run.scopes,run.diagnostics)))
        self._plan_nodes -= run.admission_nodes-nodes; self._plan_bytes -= run.admission_bytes-size
        run.admission_nodes,run.admission_bytes = nodes,size

    def submit(self, plan, *, timeout=None):
        from math import isfinite
        if timeout is not None and (type(timeout) not in (int,float) or not isfinite(timeout) or timeout < 0):
            raise ValueError("execution.invalid_timeout")
        with self._condition:
            self._check_accepting()
            if len(self._runs)+self._admitting >= self.settings.max_open_runs: raise ExecutionFailure("admission.open_runs")
            pending = sum(not run.started and not run.future.done() for run in self._runs.values())
            if pending+self._admitting >= self.settings.max_pending_runs: raise ExecutionFailure("admission.pending_runs")
            self._admitting += 1
        reservation = None
        stage_owner = None
        value_owner = 'admission:' + uuid4().hex
        accepted = False
        try:
            footprint = inspect_plan(plan,max_nodes=self.settings.max_plan_nodes,max_bytes=self.settings.max_plan_bytes)
            with self._condition:
                self._check_accepting()
                self._reserve_admission(footprint.nodes,footprint.bytes)
                reservation = footprint
            # No service lock is held while scientific literals are copied.
            owned = snapshot_plan(plan, max_bytes=self.settings.max_plan_bytes)
            actual = inspect_plan(owned,max_nodes=self.settings.max_plan_nodes,max_bytes=self.settings.max_plan_bytes)
            from stratbox.capabilities.plan.validation import validate_plan
            try:
                owned = validate_plan(owned, capacities={**dict(self.settings.capacities), 'worker': self.settings.max_workers})
            except ValueError as error:
                raise ExecutionFailure(str(error)) from None
            if self.admission_guard is not None:
                self.admission_guard(owned)
            seal_plan_inputs(self._values, owned, value_owner)
            owned_references = tuple(staged_references(owned))
            actual = inspect_plan(owned,max_nodes=self.settings.max_plan_nodes,max_bytes=self.settings.max_plan_bytes)
            with self._condition:
                self._check_accepting()
                if actual.nodes > footprint.nodes or actual.bytes > footprint.bytes:
                    self._reserve_admission(max(0,actual.nodes-footprint.nodes),max(0,actual.bytes-footprint.bytes))
                    from .admission import PlanFootprint
                    reservation = PlanFootprint(max(actual.nodes,footprint.nodes),max(actual.bytes,footprint.bytes))
                ids = [task.task_id for task in owned.tasks]
                if len(ids) != len(set(ids)): raise ExecutionFailure("plan.duplicate_task")
                durations = [value for value in (timeout, self.settings.run_limits.seconds) if value is not None]
                run = _Run(value_owner.split(':', 1)[1],owned,{task.task_id:_Task(task) for task in owned.tasks},
                    deadline=monotonic()+min(durations) if durations else None)
                # Deadline belongs to active logical demand. A producer's run
                # clock cannot terminate another consumer of its generation.
                run.meter = BudgetMeter(replace(self.settings.run_limits, seconds=None))
                for task in run.tasks.values():
                    if set(getattr(task.spec,"deps",()))-run.tasks.keys(): raise ExecutionFailure("plan.unknown_dependency")
                    for resource,amount in self._claims(task).items():
                        if amount > self._capacity(resource): raise ExecutionFailure("resource.impossible_claim:"+resource)
                stage_owner = "admission:" + run.run_id
                self.staging.pin(owned_references, stage_owner)
                self._fact(run,"run.admitted")
                run.root_ids = tuple(ids)
                run.plan = replace_record(owned,tasks=())
                run.admission_nodes,run.admission_bytes = reservation.nodes,reservation.bytes
                self._runs[run.run_id] = run
                accepted = True
                self._order.append(run.run_id)
                reservation = None
                stage_owner = None
                self._condition.notify_all()
                return RunHandle(self,run)
        except AdmissionRejected as error:
            raise ExecutionFailure(error.code) from None
        finally:
            with self._condition:
                self._admitting -= 1
                if reservation is not None:
                    self._plan_nodes -= reservation.nodes; self._plan_bytes -= reservation.bytes
                if stage_owner is not None:
                    self.staging.release(stage_owner)
                if not accepted:
                    self._values.release(value_owner)
                self._condition.notify_all()

    def run(self, plan, *, timeout=None):
        return self.submit(plan, timeout=timeout).result()

    def status(self, run_id):
        return RunHandle(self, self._runs[run_id]).snapshot()

    def cancel(self, run_id, scope_id=None):
        return RunHandle(self, self._runs[run_id]).cancel(scope_id)

    def result(self, run_id, timeout=None):
        return self._runs[run_id].future.result(timeout)

    def resolve_provider(self, role):
        with self._condition:
            if role in self.providers:
                from stratbox.core.runtime.capabilities import ProviderBinding, CapabilityRequirement, select_provider
                value = self.providers[role]
                if isinstance(value, ProviderBinding):
                    try: return select_provider(CapabilityRequirement(role), (value,)).provider
                    except ValueError as error: raise ExecutionFailure(error_code(error)) from error
                if value is None: raise ExecutionFailure("provider.unavailable:"+role)
                return value
            if role in {"http", "filestore", "secrets"}:
                from stratbox.core.runtime.providers import active_providers, local_providers
                bundle = active_providers() or local_providers()
                for name in ("http", "filestore", "secrets"):
                    self.providers.setdefault(name, getattr(bundle, name))
                return self.providers[role]
            raise ExecutionFailure("provider.missing:" + role)

    def _effect_cache_slot(self,effect_id,*,required):
        if effect_id in self._effects or len(self._effects) < self.settings.effect_capacity: return True
        if "effect_state" in self.providers:
            pinned = set(self._reconciling_effects)
            for run in self._runs.values(): pinned.update(run.effect_ids)
            victim = next((key for key,receipt in self._effects.items()
                if receipt.status in {"confirmed","rejected","failed"} and key not in pinned),None)
            if victim is not None:
                self._effects.pop(victim)
                return True
        if required: raise ExecutionFailure("effect.state_capacity_exhausted")
        return False

    def _bound_effect_state(self):
        """A cached receipt is authoritative only inside its original ledger."""
        provider = self.providers.get('effect_state')
        binding = ('memory',) if provider is None else (
            'durable', getattr(provider, 'provider_id', type(provider).__qualname__),
            getattr(provider, 'scope_id', None) or id(provider))
        if self._effect_authority is None:
            self._effect_authority = binding
        elif self._effect_authority != binding:
            raise ExecutionFailure('effect.authority_changed')
        changed = provider is not self._effect_provider
        self._effect_provider = provider
        return provider, changed

    def lookup_effect(self,effect_id):
        with self._condition:
            provider, changed = self._bound_effect_state()
            current = self._effects.get(effect_id)
            if current is not None and current.status == 'confirmed' and not changed:
                self._effects.move_to_end(effect_id)
                return current
            if provider is not None:
                authoritative = provider.get(effect_id)
                if authoritative is None and current is not None:
                    raise ExecutionFailure('effect.authority_disappeared')
                if authoritative is not None:
                    current = authoritative
                    if self._effect_cache_slot(effect_id,required=False):
                        self._effects[effect_id] = current
            return current

    def _save_effect(self,receipt):
        provider, _ = self._bound_effect_state()
        self._effect_cache_slot(receipt.effect_id,required=True)
        if provider is not None:
            receipt = provider.put(receipt)
        self._effects[receipt.effect_id] = receipt
        self._effects.move_to_end(receipt.effect_id)
        return receipt

    def _reconcile_observation(self,previous,callback,context):
        from .effect_evidence import admit_evidence, evidence_summary
        key = previous.effect_id
        with self._condition:
            if key in self._reconciling_effects: return previous
            self._reconciling_effects.add(key)
        try:
            # Lookup may block or reenter the service. It owns no coordinator lock.
            found = callback()
            with self._condition:
                current = self.lookup_effect(key)
                if current is not None and current.status == "confirmed": return current
                previous = current or previous
                admitted = admit_evidence(previous, found, source='lookup')
                if admitted.outcome not in {'confirmed', 'rejected'}:
                    if context is not None and admitted.finding:
                        context.run.diagnostics.append(admitted.finding)
                    return previous
                recovered = self._save_effect(replace(previous, status=admitted.outcome,
                    value=admitted.value, finding=admitted.finding, evidence=evidence_summary(admitted.evidence)))
                if context is not None:
                    self._fact(context.run,"effect.settled",context.task,effect_id=key,
                        effect_kind=previous.kind,outcome="confirmed",reconciled=True)
                return recovered
        finally:
            with self._condition:
                self._reconciling_effects.discard(key)
                self._condition.notify_all()

    def reconcile_effect(self,effect_id,lookup,*,context=None):
        with self._condition:
            previous = self.lookup_effect(effect_id)
            if previous is None: raise ExecutionFailure("effect.not_found")
            if previous.status == "confirmed": return previous
        return self._reconcile_observation(previous,lambda:lookup(effect_id),context)

    def _capacity(self, resource):
        return self.settings.max_workers if resource == "worker" else self.settings.capacities.get(resource, 1)

    def _claims(self, task):
        if getattr(task.spec, "kind", "command") != "command":
            return {}
        claims = dict(getattr(task.spec.command, "resources", {}) or {})
        if any(type(amount) is not int or amount < 0 for amount in claims.values()):
            raise ExecutionFailure("resource.invalid_claim")
        claims["worker"] = 1
        return claims

    def _resident_size(self):
        return self._values.resident_bytes + self._values.working_bytes

    def _reservation_waiter(self):
        waiting = [task for run in self._runs.values() for task in run.tasks.values()
            if task.state == "pending" and task.wait_ticket is not None and not task.cancelled and not run.cancel.is_set()]
        return min(waiting, key=lambda task: task.wait_ticket) if waiting else None

    def _release_unused(self):
        def refs(value):
            if hasattr(value, "task_id") and hasattr(value, "port"): return {value.task_id}
            parts = value.values() if isinstance(value, Mapping) else value if isinstance(value, (tuple, list)) else ()
            return set().union(*(refs(part) for part in parts)) if parts else set()
        for run in self._runs.values():
            if run.future.done(): continue
            needed = refs(run.plan.outputs)
            for scope in (*run.plan.scopes, *run.extra_scopes): needed.update(refs(scope.outputs))
            for task in run.tasks.values():
                if task.state in {"pending", "expanding", "preparing_inputs"}:
                    needed.update(refs(task.expansion))
                    if getattr(task.spec, 'kind', 'command') == 'collect':
                        from .members import dependency_members
                        for item in task.spec.items:
                            needed.update(child.spec.task_id for child in dependency_members(run, item))
                    if getattr(task.spec, 'kind', 'command') == 'map' and task.expansion:
                        for keys, _ in task.expansion['active'].values():
                            needed.update(keys)
                    for name in ("inputs", "items", "initial", "selector", "forwarded"):
                        needed.update(refs(getattr(task.spec, name, ())))
                    if hasattr(task.spec, "command"): needed.update(refs(task.spec.command.parameters))
            for key, task in run.tasks.items():
                if key not in needed and task.state not in {"pending", "expanding", "running", "waiting_shared", "awaiting_acceptance", "accepting", "preparing_inputs"}:
                    self.staging.release("output:" + run.run_id + ":" + key)
                    self._values.release("output:" + run.run_id + ":" + key)
                    task.outputs.clear()
                    task.accepted_keys.clear()
                    task.spec = _TaskSummary(task.spec.task_id, task.spec.scope_id, task.spec.required, self._task_origin(task))

    def _resolve(self, run, value):
        if hasattr(value, "task_id") and hasattr(value, "port"):
            resolved = run.tasks[value.task_id].outputs[value.port]
            for part in getattr(value, "path", "").split(".") if getattr(value, "path", "") else ():
                if isinstance(resolved, Mapping): resolved = resolved[part]
                elif is_dataclass(resolved) and part in {item.name for item in fields(resolved)}:
                    resolved = object.__getattribute__(resolved, part)
                else: raise ExecutionFailure("value.field_projection_required")
            return resolved
        if isinstance(value, Mapping):
            return {key: self._resolve(run, item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(self._resolve(run, item) for item in value)
        if isinstance(value, list):
            return [self._resolve(run, item) for item in value]
        return value

    def _key(self, run, task, inputs):
        command = task.spec.command
        if command.id in {"command.material.read", "command.material.list", "command.release.assemble", "command.source.state.read"}: return None
        reuse = getattr(command, "reuse", None)
        if reuse is not None and not getattr(reuse, "inflight_eligible", getattr(reuse, "shareable", True)):
            return None
        if command.effects and not command.effects <= frozenset({"network.receive", "network.read"}):
            return None
        try:
            parameters, settings = task.bound_parameters, command.settings
            logical = {"source_id", "series_id", "issue_id", "asset_id", "issue", "as_of", "target"}
            # Physical decode is neutral to source-use attribution; semantic work is not.
            if command.id == "command.material.fetch":
                request = inputs["request"]
                if request.freshness == "fresh": return None
                descriptor = self._values.descriptor(request)
                basis = (descriptor.physical_identity, request.freshness,
                         request.observation_id or run.run_id, request.metadata.get("access_scope"),
                         self._values.work_identity(inputs.get("retained")))
                placement = parameters.get('placement',settings.get('placement','buffered')
                    if isinstance(settings,Mapping) else getattr(settings,'placement','buffered'))
                if placement == "staged" or "retained" in inputs:
                    basis = (*basis, request.source_id, self._values.work_identity(request.metadata))
                parameters = {key:value for key,value in parameters.items() if key not in logical}
                if getattr(command.method, "locator", "") == "stratbox.core.commands.materials:material_fetch": settings = None
            elif command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode")):
                basis = {name: (self._values.descriptor(item).physical_identity,
                    getattr(getattr(item, "material", item), "charset", None)) for name, item in inputs.items()}
                parameters = {key:value for key,value in parameters.items() if key not in logical}
            else:
                basis = {name: self._values.work_identity(item) for name, item in inputs.items()}
            from .code_identity import code_identity
            neutral = command.id == "command.material.fetch" or command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode"))
            target = command.target if command.target is not None else run.plan.target
            return fingerprint((command.id, code_identity(command.method),
                self._values.work_identity(settings), self._values.work_identity(parameters),
                None if neutral else self._values.work_identity(target),
                basis, getattr(run.plan, "build_identity", ""),
                tuple((key, id(value)) for key, value in sorted(self.providers.items()))))
        except Exception:
            return None

    def _producer_needed(self,task):
        with self._condition:
            generation = self._generations.get(task.generation_id)
            return bool(generation and self._active_demands(generation))

    def _active_demands(self, generation):
        """Detach ended demand once; cancellation makes a generation non-joinable."""
        now = monotonic()
        for key, (run, task) in tuple(generation.demands.items()):
            if (run.future.done() or run.cancel.is_set() or task.cancelled
                    or run.deadline is not None and now >= run.deadline):
                generation.demands.pop(key)
        if not generation.demands and generation.state == 'running':
            generation.state = 'cancelling'
            generation.cancel.set()
            if self._work.get(generation.work_key) is generation:
                self._work.pop(generation.work_key, None)
        return tuple(generation.demands.values())

    def _remaining_seconds(self, task):
        with self._condition:
            generation = self._generations.get(task.generation_id)
            demands = self._active_demands(generation) if generation is not None else ()
            now = monotonic()
            return max((float('inf') if run.deadline is None else max(0.0, run.deadline - now)
                for run, _ in demands), default=0.0)

    def _execute(self,run,task,inputs):
        self._worker_local.active = True
        try: return self._execute_command(run,task,_isolate(inputs, max_bytes=self.settings.max_retained_bytes))
        finally:
            self._values.release_working(task.physical_id)
            self._worker_local.active = False

    def _prepare_inputs(self, run, task, inputs, parameters):
        """Describe an exposed private field on the existing bounded worker pool.

        A typed payload's field can become a first-class later graph input.
        Its parent remains pinned while this worker constructs the descriptor.
        """
        self._worker_local.active = True
        try:
            owner = 'input:' + run.run_id + ':' + task.spec.task_id
            return (self._values.seal(inputs, owner, as_bundle=True),
                self._values.seal(parameters, owner, as_bundle=True))
        finally:
            self._worker_local.active = False

    def _execute_command(self, run, task, inputs):
        context = CommandContext(self, run, task, inputs)
        context.checkpoint()
        if task.spec.command.scientific_limitations:
            raise ExecutionFailure('scientific.binding_unavailable:' + task.spec.command.scientific_limitations[0])
        cells_before = account_inputs(context.budget, inputs)
        method = task.spec.command.method
        method = method.resolve() if hasattr(method, "resolve") else method
        for provider in getattr(task.spec.command, "required_providers", ()):
            context.provider(provider)
        for name, port in task.spec.command.inputs.items():
            if name in inputs:
                _validate(port, inputs[name])
            elif getattr(port, "required", True):
                raise ExecutionFailure("input.required:" + name)
        # Each source-qualified port validates its actual typed SourceUse facts.
        # Labels projected from an entire input bundle cannot replace that check.
        # Every method receives an independent owner for mutable scientific
        # buffers; immutable source bytes remain shared by reference.
        answer = method(inputs, _isolate(task.spec.command.settings,
            max_bytes=self.settings.max_retained_bytes), context)
        if isinstance(answer, CommandCompletion) or hasattr(answer, "outputs") and hasattr(answer, "outcome"):
            outputs, outcome, findings = dict(answer.outputs), answer.outcome, getattr(answer, "findings", ())
        elif isinstance(answer, Mapping):
            outputs, outcome, findings = dict(answer), "succeeded", ()
        elif len(task.spec.command.outputs) == 1:
            outputs, outcome, findings = {next(iter(task.spec.command.outputs)): answer}, "succeeded", ()
        else:
            raise ExecutionFailure("output.mapping_required")
        if outcome not in {"succeeded", "partial", "failed", "unknown", "cancelled"}:
            raise ExecutionFailure("completion.invalid_outcome")
        if any(receipt.status == "unknown" for receipt in context.effect_receipts.values()):
            outcome = "unknown"
        # Even a rejected/unknown result consumes its real boundary byte budget.
        account_outputs(context.budget, outputs, cells_before=cells_before,
                        output_owner=(run.run_id, task.spec.task_id))
        sealed = self._values.seal(outputs, 'producer:' + task.physical_id, detach=True, as_bundle=True)
        return sealed, outcome, tuple(findings)

    def _accept_outputs(self, task, outputs, outcome):
        command = task.spec.command
        if outcome == "partial" and not command.acceptance.partial_allowed:
            raise ExecutionFailure("completion.partial_not_allowed")
        if set(outputs) - command.outputs.keys(): raise ExecutionFailure("output.unknown")
        selected = {}
        for name, port in command.outputs.items():
            if outcome not in port.outcomes: continue
            if name in outputs:
                _validate(port, outputs[name]); selected[name] = outputs[name]
            elif port.required:
                raise ExecutionFailure("output.required:" + name)
        if not selected and outcome not in {"succeeded", "partial"}:
            return selected
        command.acceptance.validate(selected)
        return selected

    def _prepare_acceptance(self, run, task, completion, accepted_index):
        """Seal, validate and describe a logical use on a bounded worker."""
        self._worker_local.active = True
        try:
            from .accepted_values import accepted_record, accepted_fact
            from .context import _LockedMeter
            from stratbox.shared.data.processing import processing_basis
            outputs, outcome, findings = completion
            logical = self._logical_outputs(run, task, outputs)
            cancelled = run.cancel.is_set() or task.cancelled
            outcome = 'cancelled' if cancelled and outcome != 'unknown' else outcome
            selected = self._accept_outputs(task, logical, outcome)
            owner = 'acceptance:' + run.run_id + ':' + task.spec.task_id
            # A neutral decoder can acquire new logical attribution; this is a
            # new sealed value, not permission to mutate the shared physical one.
            selected = self._values.seal(selected, owner, as_bundle=True)
            if not task.physical_producer and not run.journal_failed and (not cancelled or selected):
                meter = _LockedMeter(run.meter, self._condition)
                cells_before = account_inputs(meter, task.owned_inputs)
                account_outputs(meter, selected if cancelled else logical,
                    cells_before=cells_before, output_owner=(run.run_id, task.spec.task_id))
            records = {}
            if outcome in {'succeeded', 'partial'}:
                command = task.spec.command
                # Dynamic graph containers are sealed here; their children are
                # already private and retain their existing descriptors.
                self._values.seal(task.owned_inputs, owner, as_bundle=True)
                try:
                    basis = processing_basis(task.owned_inputs, capability_id=command.id,
                        method=command.method, settings=command.settings, parameters=task.bound_parameters,
                        build_identity=run.plan.build_identity, _input_identity=self._values.processing_identity)
                except ValueError as error:
                    if str(error) != 'value.unsealed_processing_input':
                        raise
                    # A safely owned native runtime value can execute without
                    # acquiring fabricated reusable or portable authority.
                    basis = None
                for name, value in selected.items():
                    key = self._values.identity(value)
                    if key is None or basis is None:
                        continue
                    record = accepted_record(self, run, task, name, value, task.owned_inputs,
                        value_identity=key, basis=basis, accepted_index=accepted_index)
                    record['fact'] = accepted_fact(record, value, inputs=task.owned_inputs, outputs=selected)
                    records[name] = MappingProxyType(record)
            return selected, outcome, findings, records
        finally:
            self._worker_local.active = False

    def _settled_task(self, run, task):
        self._fact(run, 'work.reused' if task.reused else 'work.finished' if task.physical_producer
            else 'work.consumer_finished', task, outcome=task.state, findings=task.findings)
        task.owned_inputs = None
        task.bound_parameters = None
        owner = run.run_id + ':' + task.spec.task_id
        self.staging.release('input:' + owner)
        self._values.release('input:' + owner)
        self._values.release('acceptance:' + owner)
        self.staging.release('plan-input:' + owner)
        self._values.release('plan-input:' + owner)
        task.input_keys.clear()
        task.future = None
        generation = self._generations.get(task.generation_id)
        if generation is not None:
            generation.demands.pop((run.run_id, task.spec.task_id), None)
            generation.consumers.discard((run.run_id, task.spec.task_id))
            if not generation.consumers and generation.future.done():
                self.staging.release('producer:' + generation.generation_id)
                self._values.release('producer:' + generation.generation_id)
                self._generations.pop(generation.generation_id, None)

    def _settle(self):
        for run in self._runs.values():
            for task in tuple(run.tasks.values()):
                if task.state == 'preparing_inputs':
                    if not task.future.done():
                        continue
                    self._release_claims(task)
                    try:
                        task.owned_inputs, task.bound_parameters = task.future.result()
                        task.state = 'pending'
                    except Exception as error:
                        task.state, task.findings = 'failed', (error_code(error),)
                        run.diagnostics.extend(task.findings)
                        self._values.release('input:' + run.run_id + ':' + task.spec.task_id)
                    task.future = None
                    continue
                if task.state in {'running', 'waiting_shared'} and task.future.done():
                    if task.physical_producer:
                        self._release_claims(task)
                        generation = self._generations.get(task.generation_id)
                        if generation is not None:
                            generation.state = 'settling'
                        if self._work.get(task.work_key) is generation:
                            self._work.pop(task.work_key, None)
                    task.state = 'awaiting_acceptance'
                if task.state == 'awaiting_acceptance':
                    try:
                        completion = task.future.result()
                        task.physical_outcome = completion[1]
                    except Exception as error:
                        task.state, task.findings = getattr(error, 'outcome', 'failed'), (error_code(error),)
                        run.diagnostics.extend(task.findings)
                        self._settled_task(run, task)
                        continue
                    if self._used.get('worker', 0) >= self.settings.max_workers:
                        continue
                    self._used['worker'] = self._used.get('worker', 0) + 1
                    task.claims = {'worker': 1}
                    task.state = 'accepting'
                    task.future = self._pool.submit(self._prepare_acceptance, run, task,
                        completion, dict(self._accepted))
                    task.future.add_done_callback(lambda _future: self._wake())
                    continue
                if task.state != 'accepting' or not task.future.done():
                    continue
                self._release_claims(task)
                effective_outcome = None
                try:
                    selected, outcome, findings, records = task.future.result()
                    cancelled = run.cancel.is_set() or task.cancelled
                    effective_outcome = 'cancelled' if cancelled and outcome != 'unknown' else outcome
                    if effective_outcome != outcome:
                        selected = {name: value for name, value in selected.items()
                            if effective_outcome in task.spec.command.outputs[name].outcomes}
                    task.outputs, task.state, task.findings = dict(selected), effective_outcome, findings
                    task.output_records = records
                    if effective_outcome != 'succeeded':
                        run.diagnostics.extend(findings)
                    if run.journal_failed:
                        task.outputs, task.state = {}, 'failed'
                    else:
                        owner = 'output:' + run.run_id + ':' + task.spec.task_id
                        self.staging.pin(self._values.references(task.outputs), owner)
                        self._values.pin_graph(task.outputs, owner)
                        self._register_outputs(run, task)
                    generation = self._generations.get(task.generation_id)
                    reuse = task.spec.command.reuse
                    if task.physical_producer and task.work_key and outcome == 'succeeded' and reuse.completed_eligible:
                        outputs, physical_outcome, physical_findings = generation.future.result()
                        if not self._values.references(outputs):
                            amount = self._values.size(outputs)
                            if self._cache_bytes + self._retained_bytes + amount <= self.settings.max_retained_bytes:
                                self._completed[task.work_key] = (outputs, physical_outcome, physical_findings)
                                self._values.pin(outputs, 'cache:' + task.work_key)
                                self._cache_bytes += amount
                except Exception as error:
                    owner = 'output:' + run.run_id + ':' + task.spec.task_id
                    self.staging.release(owner)
                    self._values.release(owner)
                    task.state = 'unknown' if effective_outcome == 'unknown' or task.physical_outcome == 'unknown' else getattr(error, 'outcome', 'failed')
                    task.outputs, task.findings = {}, (error_code(error),)
                    run.diagnostics.extend(task.findings)
                self._settled_task(run, task)

    def _reserve_accepted(self,task,outputs):
        incoming = self._values.keys(outputs.values())
        needed = max(0,len(self._accepted)+len(incoming-self._accepted.keys())-self.settings.max_accepted_values)
        if needed:
            pinned = set(incoming)
            for run in self._runs.values():
                for other in run.tasks.values(): pinned.update(other.accepted_keys | other.input_keys)
                if run.future.done() and not run.future.exception(): pinned.update(run.future.result()._accepted_keys)
            victims = [key for key in self._accepted if key not in pinned]
            if len(victims) < needed: raise ExecutionFailure("value.acceptance_metadata_capacity_exhausted")
            for key in victims[:needed]: self._accepted.pop(key)
        task.accepted_keys.update(incoming)

    def _register_outputs(self, run, task):
        """Reuse identities only within acceptance of these private outputs."""
        task.output_uses = {name: output_use(run, task, name) for name in task.outputs}
        if task.state not in {"succeeded", "partial"}:
            # A checked diagnostic value reports an unsuccessful command; it
            # grants neither successful-stage nor source/certificate authority.
            for name in task.outputs:
                fact = self._fact(run, "output.reported", task, output_name=name, outcome=task.state)
                if fact is not None:
                    run.accepted_scopes.add((task.spec.scope_id, name))
            return
        self._reserve_accepted(task, task.outputs)
        for name, value in task.outputs.items():
            record = task.output_records.get(name)
            if record is not None:
                key = record['value_identity']
                self._accepted[key] = record
                self._accepted.move_to_end(key)
                task.accepted_keys.add(key)
            fact = self._fact(run, 'output.accepted', task, output_name=name, accepted_value=record)
            if fact is not None:
                run.accepted_scopes.add((task.spec.scope_id, name))

    def _logical_outputs(self, run, task, outputs):
        """Attach each consumer's source use to a shared neutral decoder payload."""
        if task.spec.command.id == "command.material.fetch":
            request = self._resolve(run, task.spec.inputs)["request"]
            material = outputs.get("material")
            if material is not None:
                from stratbox.shared.data.materials import StagedMaterialRef
                from stratbox.shared.data.values import ImmutableMaterialRef
                if isinstance(material, (StagedMaterialRef, ImmutableMaterialRef)):
                    return dict(outputs)
                return {**outputs, "material": replace(material, source_id=request.source_id,
                    metadata={**dict(material.metadata), **dict(request.metadata)}),
                    **({'request':replace(outputs['request'],source_id=request.source_id,
                        metadata=request.metadata,observation_id=request.observation_id)} if 'request' in outputs else {})}
            return dict(outputs)
        if not task.spec.command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode")):
            return dict(outputs)
        from stratbox.shared.data.values import Material, IdentifiedMaterial, WorkbookEvidence, JsonEvidence, DocumentEvidence, DbfEvidence
        original = self._resolve(run, task.spec.inputs).get("material")
        from stratbox.core.commands._values import _material
        if isinstance(original, IdentifiedMaterial) and isinstance(original.material, Material):
            original = _material(original)
        if original is None: return dict(outputs)
        return {name: replace(value, material=original) if isinstance(value, (WorkbookEvidence, JsonEvidence, DocumentEvidence, DbfEvidence)) else value
                for name, value in outputs.items()}

    def _ready(self, run, task):
        deps = [run.tasks[key] for key in getattr(task.spec, "deps", ())]
        collection = getattr(task.spec, "kind", "command") == "collect"
        cancelled_structure = (run.cancel.is_set() or task.cancelled) and getattr(task.spec, 'kind', 'command') in {'collect', 'map'}
        if not collection and not cancelled_structure and any(dep.state in {"failed", "cancelled", "blocked", "unknown"} for dep in deps):
            task.state = "blocked"; return False
        if any(dep.state in {"pending", "expanding", "running", "waiting_shared", "awaiting_acceptance", "accepting", "preparing_inputs"} for dep in deps): return False
        if cancelled_structure:
            return True
        try:
            if not self._condition_matches(run, getattr(task.spec, "condition", None)):
                task.state = "skipped"; return False
        except KeyError:
            task.state, task.findings = "blocked", ("input.condition_unavailable",)
            return False
        for guard in getattr(task.spec, "input_guards", ()):
            try:
                guard.contract.validate(self._resolve(run, guard.value))
            except (KeyError, ValueError, TypeError, ExecutionFailure) as error:
                task.state, task.findings = "blocked", (error_code(error),)
                run.diagnostics.extend(task.findings); return False
        scopes = {scope.scope_id: scope for scope in (*run.plan.scopes, *run.extra_scopes)}
        for guard in getattr(task.spec, "guards", ()):
            scope = scopes[guard.scope_id]
            values, errors, pending = self._scope_assessment(run, scope)
            if guard.port in pending: return False
            if guard.port in errors or guard.port not in values:
                task.state, task.findings = "blocked", tuple(errors.get(guard.port, ("acceptance.output_unavailable",)))
                run.diagnostics.extend(task.findings); return False
            self._publish_scope_output(run, scope, guard.port)
        return True

    def _condition_matches(self, run, condition):
        if condition is None: return True
        for clause in condition if isinstance(condition, tuple) else (condition,):
            value = self._resolve(run, clause.value)
            for part in clause.path.split(".") if clause.path else ():
                value = value[part] if isinstance(value, Mapping) else getattr(value, part)
            if value != clause.equals: return False
        return True

    def _obligations(self, run, scope, names):
        pending, errors = False, []
        for name in names:
            task = run.tasks.get(name) or run.tasks.get(scope.scope_id + "/" + name)
            if task is None:
                reference = scope.outputs.get(name)
                task = run.tasks.get(getattr(reference, "task_id", None))
            if task is None:
                errors.append("acceptance.unknown_obligation:" + name)
            elif task.state in {"pending", "expanding", "running", "waiting_shared", "awaiting_acceptance", "accepting", "preparing_inputs"}:
                pending = True
            elif task.state != "succeeded":
                errors.append("acceptance.required_obligation_failed:" + name)
        return pending, tuple(errors)

    def _reported_outcome(self, run, reference):
        """Find unsuccessful command origins without changing structural reports."""
        uses = tuple(referenced_uses(run, reference))
        reported = tuple(use.outcome for use in uses if use.disposition == 'reported')
        return unsuccessful(reported) if reported else None

    def _scope_assessment(self, run, scope):
        values, settled, invalid = {}, set(), {}
        try:
            if not self._condition_matches(run, getattr(scope, "condition", None)):
                return {}, {name:("acceptance.condition_not_satisfied",) for name in scope.outputs}, frozenset()
        except KeyError:
            return {}, {}, frozenset(scope.outputs)
        for name, reference in scope.outputs.items():
            try:
                reported = self._reported_outcome(run, reference)
                if reported is not None and reported not in scope.output_contracts[name].outcomes:
                    raise ExecutionFailure("acceptance.output_outcome_not_admitted:" + reported)
                value = self._resolve(run, reference)
                _validate(scope.output_contracts[name], value)
                values[name] = value
                settled.add(name)
            except KeyError:
                producer = getattr(reference, "task_id", None)
                if not scope.output_contracts[name].required: settled.add(name)
                if producer in run.tasks and run.tasks[producer].state in {"succeeded", "partial", "failed", "cancelled", "blocked", "unknown", "skipped"}:
                    settled.add(name)
            except (ValueError, TypeError, ExecutionFailure) as error:
                invalid[name] = (error_code(error),)
                settled.add(name)
        errors, pending = scope.acceptance.assess_outputs(values, names=tuple(scope.outputs), settled=settled)
        errors.update(invalid)
        waiting, findings = self._obligations(run, scope, (*scope.required_checks,
            *scope.acceptance.required_checks, *scope.acceptance.required_effects))
        if findings:
            for name in scope.outputs: errors[name] = (*errors.get(name, ()), *findings)
        if waiting: pending = frozenset((*pending, *scope.outputs))
        pending = frozenset((*pending, *(name for name in scope.outputs if name not in settled)))
        return values, errors, pending

    def _publish_scope_output(self, run, scope, name):
        key = scope.scope_id, name
        if key not in run.accepted_scopes:
            reported = self._reported_outcome(run, scope.outputs[name])
            if reported is not None:
                kind, metadata = "output.reported", {"outcome": reported}
            else:
                from .accepted_values import accepted_fact
                value = self._resolve(run, scope.outputs[name])
                try:
                    record = self._accepted.get(self._values.identity(value))
                except (ValueError, TypeError):
                    record = None
                kind = "output.accepted"
                metadata = dict(record.get('fact', {})) if record is not None else {}
            uses = tuple(referenced_uses(run, scope.outputs[name]))
            metadata.update(output_disposition='reported' if reported is not None else 'accepted',
                producer_outcome=reported or unsuccessful(use.outcome for use in uses),
                output_role=scope.output_contracts[name].role or
                    ('diagnostic' if uses and all(use.role == 'diagnostic' for use in uses) else 'data'),
                origin_uses=tuple(dict.fromkeys(origin for use in uses for origin in (use.origins or (use.origin,)))))
            self._fact(run, kind, output_name=name, scope_id=scope.scope_id,
                capability_id=scope.capability_id, capability_kind=scope.kind, parent_scope_id=scope.parent_id,
                origin=self._scope_origin(run,scope), **metadata)
            if not run.journal_failed: run.accepted_scopes.add(key)

    def _template_values(self, run, outputs, prefix):
        for scope in run.extra_scopes:
            if scope.scope_id.startswith(prefix) and scope.required:
                _, errors, pending = self._scope_assessment(run, scope)
                if errors or pending:
                    run.diagnostics.extend(code for values in errors.values() for code in values)
                    raise ExecutionFailure("acceptance.dynamic_scope_rejected")
        return self._resolve(run, outputs)

    def _instantiate(self, run, template, bindings, prefix, parent_task):
        """Unroll a bounded member; its commands use the ordinary admission path."""
        from stratbox.capabilities.plan.models import TemplateInput, ValueRef
        local = {item.task_id for item in template.tasks}
        def substitute(value):
            if isinstance(value, TemplateInput): return bindings[value.name]
            if isinstance(value, ValueRef):
                return replace(value, task_id=prefix + value.task_id) if value.task_id in local else value
            descriptor = self._values.descriptor(value)
            if descriptor is not None and not descriptor.expressions:
                return value
            if isinstance(value, Mapping): return {k: substitute(v) for k, v in value.items()}
            if isinstance(value, tuple): return tuple(substitute(v) for v in value)
            if isinstance(value, list): return [substitute(v) for v in value]
            if type(value).__name__ == "Condition":
                return replace(value, value=substitute(value.value))
            return value
        children,scopes = [],[]
        local_scopes = {scope.scope_id for scope in template.scopes}
        def captured(plan, input_names, shadow_tasks=(), shadow_scopes=()):
            """Rebind parent captures while preserving each nested namespace."""
            task_names = set(shadow_tasks) | {child.task_id for child in plan.tasks}
            scope_names = set(shadow_scopes) | {scope.scope_id for scope in plan.scopes}
            def task_key(key):
                return prefix + key if key in local and key not in task_names else key
            def scope_key(key):
                return prefix + key if key in local_scopes and key not in scope_names else key
            def expression(value):
                if isinstance(value, TemplateInput):
                    return bindings[value.name] if value.name in bindings and value.name not in input_names else value
                if isinstance(value, ValueRef):
                    return replace(value, task_id=task_key(value.task_id))
                descriptor = self._values.descriptor(value)
                if descriptor is not None and not descriptor.expressions:
                    return value
                if isinstance(value, Mapping): return {key: expression(part) for key, part in value.items()}
                if isinstance(value, tuple): return tuple(expression(part) for part in value)
                if isinstance(value, list): return [expression(part) for part in value]
                if type(value).__name__ == 'Condition': return replace(value, value=expression(value.value))
                return value
            nested_tasks = []
            for child in plan.tasks:
                changes = {'deps': tuple(task_key(key) for key in child.deps),
                    'guards': tuple(replace(guard, scope_id=scope_key(guard.scope_id)) for guard in child.guards),
                    'input_guards': tuple(replace(guard, value=expression(guard.value)) for guard in child.input_guards)}
                for name in ('inputs', 'items', 'initial', 'selector', 'forwarded', 'condition'):
                    if hasattr(child, name): changes[name] = expression(getattr(child, name))
                if hasattr(child, 'command'):
                    changes['command'] = replace_record(child.command, parameters=expression(child.command.parameters))
                if hasattr(child, 'item_guards'):
                    changes['item_guards'] = {index: tuple(replace(guard, scope_id=scope_key(guard.scope_id))
                        for guard in guards) for index, guards in child.item_guards.items()}
                if getattr(child, 'template', None) is not None:
                    name = child.item_input if child.kind == 'map' else child.state_input
                    changes['template'] = captured(child.template, {*input_names, name}, task_names, scope_names)
                if getattr(child, 'alternatives', None) is not None:
                    changes['alternatives'] = {key: captured(branch, {*input_names, child.input_name}, task_names, scope_names)
                        for key, branch in child.alternatives.items()}
                nested_tasks.append(replace_record(child, **changes))
            nested_scopes = tuple(replace_record(scope, parent_id=scope_key(scope.parent_id),
                outputs=expression(scope.outputs), condition=expression(scope.condition),
                required_tasks=tuple(task_key(key) for key in scope.required_tasks),
                required_scopes=tuple(scope_key(key) for key in scope.required_scopes),
                required_checks=tuple(task_key(key) for key in scope.required_checks),
                required_effects=tuple(task_key(key) for key in scope.required_effects)) for scope in plan.scopes)
            return replace_record(plan, tasks=tuple(nested_tasks), scopes=nested_scopes, outputs=expression(plan.outputs))
        for original in template.tasks:
            updates = {"task_id":prefix+original.task_id,
                "deps":tuple(prefix+key if key in local else key for key in original.deps),
                "scope_id":prefix+original.scope_id}
            for name in ("inputs","items","initial","selector","forwarded","condition"):
                if hasattr(original,name): updates[name] = substitute(getattr(original,name))
            if hasattr(original,"command"):
                updates["command"] = replace_record(original.command,parameters=substitute(original.command.parameters))
            if getattr(original, 'template', None) is not None:
                name = original.item_input if original.kind == 'map' else original.state_input
                updates['template'] = captured(original.template, {name})
            if getattr(original, 'alternatives', None) is not None:
                updates['alternatives'] = {key: captured(branch, {original.input_name})
                    for key, branch in original.alternatives.items()}
            updates["guards"] = tuple(replace(guard,scope_id=prefix+guard.scope_id) if guard.scope_id in local_scopes else guard
                for guard in original.guards)
            updates["input_guards"] = tuple(replace(guard,value=substitute(guard.value)) for guard in original.input_guards)
            if hasattr(original,"item_guards"):
                updates["item_guards"] = {index:tuple(replace(guard,scope_id=prefix+guard.scope_id) if guard.scope_id in local_scopes else guard
                    for guard in guards) for index,guards in original.item_guards.items()}
            child = replace_record(original,**updates)
            for resource,amount in self._claims(_Task(child)).items():
                if amount > self._capacity(resource): raise ExecutionFailure("resource.impossible_claim:"+resource)
            children.append(child)
        for scope in template.scopes:
            scopes.append(replace_record(scope,scope_id=prefix+scope.scope_id,
                parent_id=(prefix + scope.parent_id if scope.parent_id in local_scopes
                    else scope.parent_id or parent_task),
                outputs=substitute(scope.outputs),
                required_tasks=tuple(prefix+key if key in local else key for key in scope.required_tasks),
                required_scopes=tuple(prefix+key if key in local_scopes else key for key in scope.required_scopes),
                required_checks=tuple(prefix+key if key in local else key for key in scope.required_checks),
                required_effects=tuple(prefix+key if key in local else key for key in scope.required_effects),
                condition=substitute(scope.condition)))
        candidate = replace_record(template,tasks=tuple(children),scopes=tuple(scopes),outputs=substitute(template.outputs))
        try:
            owned = candidate
            footprint = inspect_plan(owned,max_nodes=self.settings.max_plan_nodes-run.admission_nodes,
                max_bytes=self.settings.max_plan_bytes-run.admission_bytes,
                owned_descriptor=self._values.descriptor)
        except AdmissionRejected as error: raise ExecutionFailure(error.code) from None
        ids = {child.task_id for child in owned.tasks}
        if len(ids) != len(owned.tasks) or ids & run.tasks.keys(): raise ExecutionFailure("plan.duplicate_task")
        if any(set(child.deps)-(run.tasks.keys()|ids) for child in owned.tasks): raise ExecutionFailure("plan.unknown_dependency")
        from stratbox.capabilities.plan.validation import validate_plan, output_names
        external_ports = {key: output_names(task.spec) if not isinstance(task.spec, _TaskSummary)
            else frozenset(task.outputs) for key, task in run.tasks.items()}
        try:
            owned = validate_plan(owned, external_ports=external_ports,
                external_scopes={scope.scope_id: scope for scope in (*run.plan.scopes, *run.extra_scopes)},
                capacities={**dict(self.settings.capacities), 'worker': self.settings.max_workers})
        except ValueError as error:
            raise ExecutionFailure(str(error)) from None
        self._reserve_admission(footprint.nodes,footprint.bytes,run)
        for child in owned.tasks:
            for name in ('inputs', 'items', 'initial', 'selector', 'forwarded'):
                value = getattr(child, name, None)
                owner = 'plan-input:' + run.run_id + ':' + child.task_id
                self._values.pin_graph(value, owner)
                self.staging.pin(self._values.references(value), owner)
        # Publish the complete validated slice atomically under the coordinator.
        run.tasks.update({child.task_id:_Task(child) for child in owned.tasks})
        run.extra_scopes.extend(owned.scopes)
        return tuple(child.task_id for child in owned.tasks),owned.outputs

    def _member_effect_state(self, children):
        keys = {key for child in children for key in child.effect_ids}
        receipts = [self.lookup_effect(key) for key in keys]
        if any(receipt is None or receipt.status == 'unknown' for receipt in receipts):
            return 'unknown'
        if any(receipt.status == 'rejected' for receipt in receipts):
            return 'rejected'
        return 'confirmed' if receipts else None

    def _structural(self, run, task):
        from .members import outcome as member_outcome, dependency_members, referenced_tasks
        spec, kind = task.spec, getattr(task.spec, "kind", "command")
        def assess_member(outputs, children, port):
            reference = outputs[port]
            required = {child.spec.task_id for child in children if child.spec.required}
            relevant = [run.tasks[key] for key in required | referenced_tasks(reference)]
            effects = self._member_effect_state(relevant)
            status, uses = member_assessment(run, reference, required_tasks=required, effects=effects)
            return status, uses, effects
        if kind == "collect":
            values, outcomes, required_failures = [], [], []
            scopes = {scope.scope_id: scope for scope in (*run.plan.scopes, *run.extra_scopes)}
            for index, item in enumerate(spec.items):
                children = dependency_members(run, item)
                required = set()
                def member_scope(scope):
                    required.update(scope.required_tasks)
                    for child in scope.required_scopes:
                        member_scope(scopes[child])
                for guard in spec.item_guards.get(index, ()):
                    member_scope(scopes[guard.scope_id])
                from .members import referenced_tasks
                relevant = [run.tasks[key] for key in required or referenced_tasks(item)]
                effect_state = self._member_effect_state(relevant)
                status, value = 'succeeded', None
                try:
                    value = self._resolve(run, item)
                    status, uses = member_assessment(run, item, required_tasks=required, effects=effect_state)
                    if status is None:
                        return
                    accepted = True
                    for guard in spec.item_guards.get(index, ()):
                        _, errors, pending = self._scope_assessment(run, scopes[guard.scope_id])
                        if guard.port in pending: return
                        accepted &= guard.port not in errors
                    if not accepted:
                        status = unsuccessful((status, 'failed'))
                    if status in {'succeeded', 'partial'} or spec.completion == 'diagnostic':
                        values.append(value)
                    elif index not in spec.optional_items and spec.completion == 'all_selected':
                        required_failures.append(status)
                except (KeyError, ValueError, TypeError, ExecutionFailure):
                    value = None
                    status = ('unknown' if effect_state == 'unknown' or any(child.state == 'unknown' for child in children)
                              else 'cancelled' if any(child.state == 'cancelled' for child in children)
                              else 'failed')
                    if index not in spec.optional_items and spec.completion != 'eligible_subset':
                        required_failures.append(status)
                outcomes.append(member_outcome(item, index, status, children, value,
                    effect_state=effect_state, identity=self._values.identity(item)))
            task.outputs = {"items": tuple(values), "outcomes": tuple(outcomes)}
            if 'unknown' in required_failures:
                task.state = 'unknown'
            elif run.cancel.is_set() or task.cancelled or 'cancelled' in required_failures:
                task.state = 'cancelled'
            elif required_failures or len(values) < spec.min_items:
                task.state = 'failed'
            else:
                task.state = 'partial' if spec.completion != 'diagnostic' and any(value.outcome == 'partial' for value in outcomes) else 'succeeded'
            task.findings = tuple(f'collection.member:{item.ordinal}:{item.outcome}' for item in outcomes if item.outcome != 'succeeded')
            if len(values) < spec.min_items:
                run.diagnostics.append("collection.minimum_members_not_met")
            self._fact(run, 'collection.completed', units=len(spec.items), statuses={item.ordinal: item.outcome for item in outcomes})
            return
        if task.expansion is None:
            if kind == "map":
                try:
                    items = tuple(self._resolve(run, spec.items))
                except KeyError:
                    if not (run.cancel.is_set() or task.cancelled):
                        raise
                    task.outputs, task.state = {'items': (), 'outcomes': ()}, 'cancelled'
                    task.findings = ('map.membership_unavailable',)
                    return
                if len(items) > spec.max_items: raise ExecutionFailure("map.item_limit")
                task.expansion = {"items": items, "next": 0, "active": {}, "results": {}, "statuses": {}, "outcomes": {}, "origins": {}}
            elif kind == "repeat":
                task.expansion = {"state": self._resolve(run, spec.initial), "pass": 0, "active": None}
            elif kind == "dispatch":
                selected = self._resolve(run, spec.selector)
                if spec.selector_kind == "acquisition_kind":
                    from stratbox.shared.data.values import RequestSpec
                    locator = selected.url if isinstance(selected, RequestSpec) else getattr(selected, "locator", selected)
                    if isinstance(locator, Mapping): locator = locator.get("locator", locator.get("url"))
                    delivery = getattr(selected, "metadata", {}).get("delivery")
                    if delivery in {"filestore", "file", "local"}: fmt = "file"
                    elif isinstance(locator, str) and locator.startswith("https://"): fmt = "http"
                    elif isinstance(locator, str) and ("://" not in locator or locator.startswith("file://")): fmt = "file"
                    else: raise ExecutionFailure("acquisition.unsupported_locator")
                    template = spec.alternatives.get(fmt)
                    if template is None: raise ExecutionFailure("acquisition.unsupported_delivery:" + fmt)
                    prefix = f"{spec.task_id}/{fmt}/"
                    task.expansion = {"active": self._instantiate(run, template, {spec.input_name: selected}, prefix, spec.task_id), "prefix":prefix}
                    task.state = "expanding"
                    return
                from stratbox.shared.data.materials import MaterialInspection
                from stratbox.core.storage.readable import carrier
                forwarded = self._resolve(run, spec.forwarded)
                if not isinstance(selected, MaterialInspection):
                    raise ExecutionFailure("format.inspection_required")
                if selected.material_identity != getattr(carrier(forwarded), "identity", None):
                    raise ExecutionFailure("format.inspection_identity_mismatch")
                fmt = selected.format
                template = spec.alternatives.get(fmt)
                if template is None: raise ExecutionFailure("format.unsupported:" + fmt)
                prefix = f"{spec.task_id}/{fmt}/"
                task.expansion = {"active": self._instantiate(run, template, {spec.input_name: forwarded}, prefix, spec.task_id), "prefix":prefix}
            else:
                raise ExecutionFailure("plan.unknown_structural_kind")
            task.state = "expanding"
        state = task.expansion
        if kind == "dispatch":
            keys, outputs = state["active"]
            children = [run.tasks[key] for key in keys]
            if not all(child.state in {"succeeded", "partial", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children): return
            status, uses, _ = assess_member(outputs, children, spec.output_port)
            if status not in {'succeeded', 'partial'}:
                task.state = status; return
            task.outputs = {spec.output_port: self._template_values(run, outputs, state["prefix"])[spec.output_port]}
            state['origins'] = tuple(origin for use in uses for origin in (use.origins or (use.origin,)))
            task.state = status
            return
        if kind == "map":
            if run.cancel.is_set() or task.cancelled:
                for keys, _ in state['active'].values():
                    for key in keys:
                        child = run.tasks[key]
                        child.cancelled = True
                        if child.state in {'pending', 'expanding'} and getattr(child.spec, 'kind', 'command') not in {'map', 'collect'}:
                            child.state = 'cancelled'
            for index, (keys, outputs) in tuple(state["active"].items()):
                children = [run.tasks[key] for key in keys]
                if all(child.state in {"succeeded", "partial", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children):
                    status, uses, effect_state = assess_member(outputs, children, spec.item_output)
                    state["statuses"][index] = status
                    if status in {'succeeded', 'partial'}:
                        try:
                            state["results"][index] = self._template_values(run, outputs, f"{spec.task_id}/item{index}/")[spec.item_output]
                            state['origins'][index] = tuple(origin for use in uses for origin in (use.origins or (use.origin,)))
                        except (ExecutionFailure, KeyError, ValueError, TypeError):
                            status = "failed"; state["statuses"][index] = status
                    if status == "failed":
                        if effect_state == 'unknown' or any(child.state == "unknown" for child in children): status = "unknown"
                        elif any(child.state == "cancelled" for child in children): status = "cancelled"
                        state["statuses"][index] = status
                    state["outcomes"][index] = member_outcome(state["items"][index],index,status,
                        children,state["results"].get(index), effect_state=effect_state,
                        identity=self._values.identity(state['items'][index]))
                    del state["active"][index]
            if run.cancel.is_set() or task.cancelled:
                for index in range(state['next'], len(state['items'])):
                    state['statuses'][index] = 'cancelled'
                    state['outcomes'][index] = member_outcome(state['items'][index], index, 'cancelled',
                        identity=self._values.identity(state['items'][index]))
                state['next'] = len(state['items'])
            while len(state["active"]) < spec.window and state["next"] < len(state["items"]):
                index = state["next"]
                state["active"][index] = self._instantiate(run, spec.template, {spec.item_input: state["items"][index]}, f"{spec.task_id}/item{index}/", spec.task_id)
                state["next"] += 1
            if not state["active"] and state["next"] == len(state["items"]):
                task.outputs = {"items": tuple(state["results"][index] for index in sorted(state["results"])),
                                "outcomes": tuple(state["outcomes"][index] for index in sorted(state["outcomes"]))}
                subset = spec.completion == "eligible_subset" and (bool(state["results"]) or not state["items"])
                accepted = subset or all(s in {'succeeded', 'partial'} for s in state['statuses'].values())
                task.state = ('unknown' if 'unknown' in state['statuses'].values()
                              else 'cancelled' if run.cancel.is_set() or task.cancelled
                              else ('partial' if 'partial' in state['statuses'].values() else 'succeeded') if accepted else 'failed')
                task.findings = tuple(f"map.unit:{index}:{status}" for index, status in state["statuses"].items())
                self._fact(run, "map.completed", units=len(state["items"]), statuses=state["statuses"])
        else:
            if state["active"] is not None:
                keys, outputs = state["active"]
                children = [run.tasks[key] for key in keys]
                if not all(child.state in {"succeeded", "partial", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children): return
                status, uses, _ = assess_member(outputs, children, spec.state_output)
                if status not in {'succeeded', 'partial'}:
                    task.state = status; return
                state["state"] = self._template_values(run, outputs, f"{spec.task_id}/pass{state['pass']}/")[spec.state_output]
                state['origins'] = tuple(origin for use in uses for origin in (use.origins or (use.origin,)))
                stop = spec.stop
                converged = stop.accepts(state["state"]) if hasattr(stop, "accepts") else bool(stop(state["state"])) if callable(stop) else bool(getattr(state["state"], "converged", False))
                self._fact(run, "iteration.assessed", pass_number=state["pass"], converged=converged)
                if converged:
                    task.outputs, task.state = {"state": state["state"]}, "succeeded"; return
                if state["pass"] >= spec.max_passes:
                    task.state, task.findings = "failed", ("iteration.limit_without_convergence",)
                    run.diagnostics.extend(task.findings); return
            state["pass"] += 1
            state["active"] = self._instantiate(run, spec.template, {spec.state_input: state["state"]}, f"{spec.task_id}/pass{state['pass']}/", spec.task_id)

    def _structural_uses(self, run, task):
        """Structural forwarding retains origin, while reports have their own purpose."""
        references = getattr(task.spec, 'items', ())
        origins = tuple(origin for use in referenced_uses(run, references)
            for origin in (use.origins or (use.origin,)))
        if task.expansion and 'origins' in task.expansion:
            nested = task.expansion['origins']
            origins = tuple(origin for values in nested.values() for origin in values) if isinstance(nested, Mapping) else nested
        task.output_uses = {name: output_use(run, task, name,
            role='diagnostic' if name == 'outcomes' or getattr(task.spec, 'completion', None) == 'diagnostic' else 'data',
            accepted=True if name == 'outcomes' else None, origins=origins) for name in task.outputs}

    def _finish(self, run):
        roots = [run.tasks[key] for key in run.root_ids]
        good = all(task.state in {"succeeded", "partial", "skipped"} for task in roots if getattr(task.spec, "required", True))
        uncertain = any(task.state == "unknown" for task in roots if getattr(task.spec, "required", True))
        uncertain |= any(self.lookup_effect(key).status == "unknown" for key in run.effect_ids if self.lookup_effect(key) is not None)
        outcome = "cancelled" if run.cancel.is_set() else ("partial" if any(task.state == "partial" for task in roots if task.spec.required) else "succeeded") if good else "unknown" if uncertain else "failed"
        if uncertain: outcome = "unknown"
        scopes = {scope.scope_id: scope for scope in (*getattr(run.plan, "scopes", ()), *run.extra_scopes)}
        available = {}
        visiting = set()
        def settle_scope(scope):
            if scope.scope_id in run.scopes: return run.scopes[scope.scope_id]
            if scope.scope_id in visiting: raise ExecutionFailure("scope.cycle")
            visiting.add(scope.scope_id)
            child_states = tuple(settle_scope(scopes[key]) for key in scope.required_scopes)
            children_ok = all(state in {"succeeded", "partial"} for state in child_states)
            required = [run.tasks[key] for key in scope.required_tasks if key in run.tasks]
            values, errors, pending = self._scope_assessment(run, scope)
            waiting, findings = self._obligations(run, scope, scope.required_effects)
            accepted = {name: value for name, value in values.items() if name not in errors and name not in pending}
            available[scope.scope_id] = accepted
            for name in accepted: self._publish_scope_output(run, scope, name)
            partial = any(t.state == "partial" for t in required) or "partial" in child_states
            good_tasks = all(t.state in {"succeeded", "partial"} for t in required)
            state = ("partial" if partial else "succeeded") if children_ok and good_tasks and not errors and not pending and not waiting and not findings and (not partial or scope.acceptance.partial_allowed) else "failed"
            if state == 'failed':
                state = unsuccessful((*child_states, *(task.state for task in required), 'failed'))
            run.scopes[scope.scope_id] = state
            run.diagnostics.extend(code for codes in errors.values() for code in codes)
            run.diagnostics.extend(findings)
            self._fact(run, "scope.completed", scope_id=scope.scope_id, capability_id=scope.capability_id,
                capability_kind=scope.kind, parent_scope_id=scope.parent_id, required_scopes=scope.required_scopes, outcome=state,
                origin=self._scope_origin(run,scope))
            visiting.remove(scope.scope_id)
            return state
        for scope in scopes.values(): settle_scope(scope)
        root_scopes = [scope for scope in scopes.values() if scope.parent_id is None and scope.required]
        if any(run.scopes[scope.scope_id] not in {"succeeded", "partial"} for scope in root_scopes) and outcome not in {"unknown", "cancelled"}:
            outcome = "failed"
        outputs = {}
        accepted_names = set().union(*(available[scope.scope_id].keys() for scope in root_scopes)) if root_scopes else set(run.plan.outputs)
        for name, reference in run.plan.outputs.items():
            if name in accepted_names:
                try: outputs[name] = self._resolve(run, reference)
                except (KeyError, AttributeError): pass
        amount = self._values.size(outputs)
        if run.journal_failed:
            outputs, amount = {}, 0
            if outcome != "unknown": outcome = "failed"
        if self._retained_bytes + self._cache_bytes + amount > self.settings.max_retained_bytes:
            for key in self._completed:
                self._values.release('cache:' + key)
            self._completed.clear()
            self._cache_bytes = 0
        if self._retained_bytes + amount > self.settings.max_retained_bytes:
            outputs, outcome = {}, "failed"
            run.diagnostics.append("value.retention_capacity_exhausted")
            amount = 0
        self._retained_bytes += amount
        self._fact(run, "run.finished", outcome=outcome)
        if run.journal_failed:
            self._retained_bytes -= amount
            outputs, amount = {}, 0
            if outcome != "unknown": outcome = "failed"
        # A completed run keeps its result owner and diagnostics, not every
        # intermediate or worker Future that happened to produce that result.
        result = RunResult(self, run, outcome, outputs, run.diagnostics, run.scopes, amount)
        for task in run.tasks.values():
            self.staging.release("output:" + run.run_id + ":" + task.spec.task_id)
            self.staging.release("input:" + run.run_id + ":" + task.spec.task_id)
            self._values.release("output:" + run.run_id + ":" + task.spec.task_id)
            self._values.release("input:" + run.run_id + ":" + task.spec.task_id)
            self._values.release('plan-input:' + run.run_id + ':' + task.spec.task_id)
            self.staging.release('plan-input:' + run.run_id + ':' + task.spec.task_id)
            task.outputs = {}
            task.future = None
            task.owned_inputs = task.bound_parameters = None
            task.spec = _TaskSummary(task.spec.task_id, task.spec.scope_id, task.spec.required, self._task_origin(task))
            task.expansion = None
            task.accepted_keys.clear()
            task.input_keys.clear()
        run.plan = None
        self._compact_admission(run)
        self.staging.release("admission:" + run.run_id)
        self._values.release("admission:" + run.run_id)
        run.future.set_result(result)
        self._condition.notify_all()

    def _coordinate(self):
        try:
            while True:
                with self._condition:
                    self._settle()
                    self._release_unused()
                    remaining = [run for run in self._runs.values() if not run.future.done()]
                    if self._closing and not remaining:
                        return
                    for _ in range(len(self._order)):
                        run = self._runs[self._order.popleft()]
                        self._order.append(run.run_id)
                        if run.future.done():
                            continue
                        if not run.started:
                            active = sum(r.started and not r.future.done() for r in self._runs.values())
                            if active >= self.settings.active_runs:
                                continue
                            run.started = True
                            self._fact(run, "run.started")
                        if run.deadline is not None and monotonic() >= run.deadline:
                            run.cancel.set()
                        for task in tuple(run.tasks.values()):
                            if task.state == "expanding":
                                if run.journal_failed:
                                    task.state = "blocked"; continue
                                try:
                                    self._structural(run, task)
                                    self._structural_uses(run, task)
                                    owner = 'output:' + run.run_id + ':' + task.spec.task_id
                                    self.staging.pin(self._values.references((task.outputs, task.expansion)), owner)
                                    self._values.pin_graph((task.outputs, task.expansion), owner)
                                except Exception as error:
                                    task.state, task.findings = "failed", (error_code(error),)
                                    run.diagnostics.append(error_code(error))
                                continue
                            if task.state != "pending":
                                continue
                            if run.journal_failed:
                                task.state = "blocked"; continue
                            if (run.cancel.is_set() or task.cancelled) and getattr(task.spec, 'kind', 'command') not in {'map', 'collect'}:
                                task.state = "cancelled"
                                continue
                            if not self._ready(run, task):
                                continue
                            if getattr(task.spec, "kind", "command") != "command":
                                try:
                                    self._structural(run, task)
                                    self._structural_uses(run, task)
                                    owner = 'output:' + run.run_id + ':' + task.spec.task_id
                                    self.staging.pin(self._values.references((task.outputs, task.expansion)), owner)
                                    self._values.pin_graph((task.outputs, task.expansion), owner)
                                except Exception as error:
                                    task.state, task.findings = "failed", (error_code(error),)
                                    run.diagnostics.append(error_code(error))
                                continue
                            condition = getattr(task.spec, "condition", None)
                            if condition is not None:
                                conditions = condition if isinstance(condition, tuple) else (condition,)
                                matched = True
                                for clause in conditions:
                                    value = self._resolve(run, clause.value)
                                    for part in clause.path.split(".") if clause.path else ():
                                        value = value[part] if isinstance(value, Mapping) else getattr(value, part)
                                    matched &= value == clause.equals
                                if not matched:
                                    task.state = "skipped"
                                    continue
                            if task.spec.command.scientific_limitations:
                                # Competence belongs to this selected logical
                                # use; an existing physical result cannot waive it.
                                task.state = 'failed'
                                task.findings = ('scientific.binding_unavailable:'
                                    + task.spec.command.scientific_limitations[0],)
                                run.diagnostics.extend(task.findings)
                                continue
                            try:
                                inputs = self._resolve(run, task.spec.inputs)
                                task.bound_parameters = self._resolve(run, task.spec.command.parameters)
                                for name, port in task.spec.command.inputs.items():
                                    if name in inputs: _validate(port, inputs[name])
                                    elif port.required: raise ExecutionFailure("input.required:"+name)
                            except (KeyError, ValueError, TypeError, ExecutionFailure) as error:
                                task.state, task.findings = "blocked", (error_code(error),)
                                run.diagnostics.extend(task.findings); continue
                            try:
                                for role in getattr(task.spec.command, "required_providers", ()):
                                    self.resolve_provider(role)
                            except ExecutionFailure as error:
                                task.state, task.findings = "failed", (error.code,)
                                run.diagnostics.append(error.code)
                                continue
                            if not self._values.described((inputs, task.bound_parameters)):
                                if self._used.get('worker', 0) >= self.settings.max_workers:
                                    continue
                                self._used['worker'] = self._used.get('worker', 0) + 1
                                task.claims, task.state = {'worker': 1}, 'preparing_inputs'
                                task.future = self._pool.submit(self._prepare_inputs, run, task, inputs, task.bound_parameters)
                                task.future.add_done_callback(lambda _future: self._wake())
                                continue
                            key = self._key(run, task, inputs)
                            if key in self._completed and task.spec.command.reuse.completed_eligible:
                                task.owned_inputs = inputs
                                owner = 'input:' + run.run_id + ':' + task.spec.task_id
                                self._values.pin_graph((inputs, task.bound_parameters), owner)
                                self.staging.pin(self._values.references((inputs, task.bound_parameters)), owner)
                                task.input_keys = self._values.keys(inputs.values()) & self._accepted.keys()
                                task.future = Future()
                                task.future.set_result(self._completed[key])
                                task.state, task.reused = 'awaiting_acceptance', True
                                continue
                            if key is not None and key in self._work:
                                generation = self._work[key]
                                self._active_demands(generation)
                            else:
                                generation = None
                            if generation is not None and generation.state == 'running' and not generation.future.done():
                                self.staging.pin(self._values.references((inputs, task.bound_parameters)), "input:" + run.run_id + ":" + task.spec.task_id)
                                self._values.pin_graph((inputs, task.bound_parameters), "input:" + run.run_id + ":" + task.spec.task_id)
                                task.future, task.physical_id = generation.future, generation.generation_id
                                task.generation_id = generation.generation_id
                                generation.demands[(run.run_id, task.spec.task_id)] = (run, task)
                                generation.consumers.add((run.run_id, task.spec.task_id))
                                task.state, task.work_key = "waiting_shared", key
                                task.owned_inputs = inputs
                                task.input_keys = self._values.keys(inputs.values()) & self._accepted.keys()
                                self._fact(run, "work.joined", task)
                                continue
                            claims = self._claims(task)
                            waiter = self._reservation_waiter()
                            reserved = self._claims(waiter) if waiter is not None and waiter is not task else {}
                            if any(claims.get(r,0) > 0 and self._used.get(r, 0) + claims[r] + n > self._capacity(r) for r,n in reserved.items()) or any(self._used.get(r, 0) + n > self._capacity(r) for r, n in claims.items()):
                                if task.wait_ticket is None:
                                    task.wait_ticket = self._next_ticket
                                    self._next_ticket += 1
                                continue
                            task.physical_id = uuid4().hex
                            task.generation_id = task.physical_id
                            try:
                                self._values.reserve_working(task.physical_id,
                                    self._values.size(inputs) + self._values.size(task.spec.command.settings)
                                    + self._values.size(task.bound_parameters) + self._values.size(task.spec.command.target
                                        if task.spec.command.target is not None else run.plan.target))
                            except ValueError as error:
                                task.state, task.findings = 'failed', (error_code(error),)
                                run.diagnostics.extend(task.findings); continue
                            self._fact(run, "work.started", task)
                            if run.journal_failed:
                                self._values.release_working(task.physical_id)
                                task.state = "blocked"; continue
                            owned_inputs = inputs
                            self.staging.pin(self._values.references((inputs, task.bound_parameters)), "input:" + run.run_id + ":" + task.spec.task_id)
                            self._values.pin_graph((inputs, task.bound_parameters), "input:" + run.run_id + ":" + task.spec.task_id)
                            self._values.release('plan-input:' + run.run_id + ':' + task.spec.task_id)
                            self.staging.release('plan-input:' + run.run_id + ':' + task.spec.task_id)
                            for r, n in claims.items(): self._used[r] = self._used.get(r, 0) + n
                            task.state, task.claims, task.work_key = "running", claims, key
                            run.started_work = True
                            task.wait_ticket = None
                            task.owned_inputs = owned_inputs
                            task.input_keys = self._values.keys(inputs.values()) & self._accepted.keys()
                            generation = _WorkGeneration(task.physical_id, key, {(run.run_id, task.spec.task_id): (run, task)},
                                consumers={(run.run_id, task.spec.task_id)})
                            task.physical_producer = True
                            self._generations[task.physical_id] = generation
                            task.future = self._pool.submit(self._execute, run, task, task.owned_inputs)
                            generation.future = task.future
                            task.future.add_done_callback(lambda _future: self._wake())
                            if key is not None:
                                self._work[key] = generation
                            # One newly admitted producer per run per fair pass.
                            break
                        if all(t.state not in {"pending", "running", "waiting_shared", "expanding", "awaiting_acceptance", "accepting", "preparing_inputs"} for t in run.tasks.values()):
                            self._finish(run)
                    self._condition.wait(0.01)
        except BaseException as error:
            self._begin_failure(error)
            self._drain_failure()
        finally:
            # Only the coordinator owns pool shutdown. No accepted dependency
            # chain loses its executor when close(wait=False) begins draining.
            self._pool.shutdown(wait=True)
            if self._observer_dispatcher is not None: self._observer_dispatcher.close()
            with self._condition:
                for key in self._completed:
                    self._values.release('cache:' + key)
                self._completed.clear(); self._accepted.clear()
                self._cache_bytes = 0
                if self._state != "failed": self._state = "closed"
                self._closed_event.set()
                self._condition.notify_all()
                self.staging.close()

    def _release_claims(self,task):
        claims,task.claims = task.claims,{}
        for resource,amount in claims.items(): self._used[resource] -= amount

    def _begin_failure(self,error):
        with self._condition:
            self._state,self._failure = "failed",error_code(error)
            for run in self._runs.values():
                if run.future.done(): continue
                run.diagnostics.append("execution.coordinator_failed")
                for task in run.tasks.values():
                    if task.state in {"pending","expanding"}: task.state = "blocked"
            self._condition.notify_all()

    def _drain_failure(self):
        """Observe every already-dispatched physical future before ending its run."""
        while True:
            with self._condition:
                remaining = []
                for run in self._runs.values():
                    if run.future.done(): continue
                    live = False
                    for task in run.tasks.values():
                        if task.state not in {"running","waiting_shared", "awaiting_acceptance", "accepting", "preparing_inputs"}: continue
                        future = task.future
                        if future is not None and not future.done(): live = True; continue
                        self._release_claims(task)
                        if future is not None:
                            try: future.result()
                            except BaseException as error: run.diagnostics.append(error_code(error))
                        self.staging.release("input:" + run.run_id + ":" + task.spec.task_id)
                        self._values.release("input:" + run.run_id + ":" + task.spec.task_id)
                        self._values.release("acceptance:" + run.run_id + ":" + task.spec.task_id)
                        task.state,task.outputs,task.future,task.owned_inputs,task.bound_parameters = "failed",{},None,None,None
                        task.input_keys.clear(); task.accepted_keys.clear()
                    if live: remaining.append(run)
                    else: self._finish_failed(run)
                if not remaining:
                    self._work.clear()
                    for generation in self._generations.values():
                        self.staging.release('producer:' + generation.generation_id)
                        self._values.release('producer:' + generation.generation_id)
                        self._values.release_working(generation.generation_id)
                    self._generations.clear()
                    return
                self._condition.wait(0.01)

    def _finish_failed(self,run):
        uncertain = any(key not in self._effects or self._effects[key].status == "unknown" for key in run.effect_ids)
        for task in run.tasks.values():
            self.staging.release("output:" + run.run_id + ":" + task.spec.task_id)
            self.staging.release("input:" + run.run_id + ":" + task.spec.task_id)
            for prefix in ('output:', 'input:', 'acceptance:', 'plan-input:'):
                self._values.release(prefix + run.run_id + ':' + task.spec.task_id)
                self.staging.release(prefix + run.run_id + ':' + task.spec.task_id)
            task.outputs,task.future,task.owned_inputs,task.expansion,task.bound_parameters = {},None,None,None,None
            task.spec = _TaskSummary(task.spec.task_id,task.spec.scope_id,task.spec.required,self._task_origin(task))
            task.accepted_keys.clear(); task.input_keys.clear()
        run.plan = None
        self._compact_admission(run)
        self.staging.release("admission:" + run.run_id)
        self._values.release('admission:' + run.run_id)
        run.future.set_result(RunResult(self,run,"unknown" if uncertain else "failed",{},
            run.diagnostics,run.scopes,0))
        self._condition.notify_all()

    def _wake(self):
        with self._condition:
            self._condition.notify_all()

    def _effect(self,context,kind,effect_id,action,reconcile,resource,intent):
        from .effect_evidence import admit_evidence, same_effect_intent, evidence_summary
        previous_unknown = None
        with self._condition:
            context.checkpoint()
            previous = self.lookup_effect(effect_id)
            if previous:
                if (previous.kind != kind or previous.resource != resource
                        or not same_effect_intent(previous.intent, intent)):
                    raise ExecutionFailure("effect.identity_conflict")
                if previous.status == "confirmed":
                    context.run.effect_ids.add(effect_id)
                    context.task.effect_ids.add(effect_id)
                    return previous
                if previous.status == "unknown":
                    context.run.effect_ids.add(effect_id)
                    context.task.effect_ids.add(effect_id)
                    if reconcile is None: return previous
                    previous_unknown = previous
            if previous_unknown is None:
                self._effect_cache_slot(effect_id,required=True)
                proposed = EffectReceipt(effect_id,kind,"unknown",resource=resource,intent=intent)
                state = self.providers.get("effect_state")
                begin = getattr(state,"begin",None)
                if callable(begin):
                    authoritative,claimed = begin(proposed)
                    if (authoritative.kind != kind or authoritative.resource != resource
                            or not same_effect_intent(authoritative.intent, intent)):
                        raise ExecutionFailure("effect.identity_conflict")
                    self._effects[effect_id] = authoritative
                    self._effects.move_to_end(effect_id)
                    context.run.effect_ids.add(effect_id)
                    context.task.effect_ids.add(effect_id)
                    if not claimed:
                        if authoritative.status == "confirmed" or reconcile is None: return authoritative
                        previous_unknown = authoritative
                else:
                    self._save_effect(proposed)
                    context.run.effect_ids.add(effect_id)
                    context.task.effect_ids.add(effect_id)
                if previous_unknown is None: context._active_effects.add(effect_id)
        if previous_unknown is not None:
            return self._reconcile_observation(previous_unknown,lambda:reconcile(previous_unknown),context)
        try:
            value = action()
            action_error = None
        except Exception as error:
            from stratbox.core.storage.filestore import MutationRejected
            status = "rejected" if isinstance(error, MutationRejected) else "unknown"
            action_error = (status, error_code(error))
        with self._condition:
            latest = self.lookup_effect(effect_id)
            if latest is None:
                raise ExecutionFailure('effect.authority_disappeared')
            if latest.status == 'confirmed':
                return latest
            if action_error is None:
                admitted = admit_evidence(latest, value, source='action')
                receipt = replace(latest, status=admitted.outcome if admitted.outcome in {'confirmed', 'rejected'} else 'unknown',
                    value=admitted.value, finding=admitted.finding, evidence=evidence_summary(admitted.evidence))
            else:
                receipt = replace(latest, status=action_error[0], value=None, finding=action_error[1], evidence=None)
            try:
                receipt = self._save_effect(receipt)
            except Exception as error:
                receipt = replace(latest, status="unknown", value=None,
                    finding="effect.acknowledgement_persistence_failed:" + error_code(error), evidence=None)
                try:
                    authoritative = self.providers['effect_state'].get(effect_id) if 'effect_state' in self.providers else None
                except Exception:
                    authoritative = None
                if authoritative is not None and authoritative.status == 'confirmed':
                    context.run.diagnostics.append(receipt.finding)
                    receipt = authoritative
                self._effects[effect_id] = receipt
            event = "effect.settled" if receipt.status == "confirmed" else "effect.rejected" if receipt.status == "rejected" else "effect.unknown"
            self._fact(context.run, event, context.task,
                effect_id=effect_id, effect_kind=kind, outcome=receipt.status)
        return receipt

    def close(self, *, wait=True, cancel=False):
        with self._condition:
            if self._state == "running": self._state = "draining"
            if cancel:
                for run in self._runs.values():
                    if not run.future.done(): run.cancel.set()
            self._condition.notify_all()
        if wait and current_thread() is not self._thread and not getattr(self._worker_local,"active",False):
            self._closed_event.wait()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
