"""One direct, bounded execution service for every prepared callable kind.

The coordinator owns dependencies and waits. Workers execute a single bound
command and never rebuild an operation definition or resolve a publisher.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timezone
from threading import Condition, Event, RLock, Thread
from time import monotonic
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4
import copy
import sys

from stratbox.shared.data.values import fingerprint
from .errors import OperationFailure
from stratbox.core.observability.journal.stream import JournalFact, MemoryJournal
from stratbox.core.limits import ExecutionBudget, BudgetMeter


class ExecutionFailure(OperationFailure):
    def __init__(self, code, *, outcome="failed"):
        self.code, self.outcome = str(code), outcome
        super().__init__(self.code, outcome=outcome)


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

    def __post_init__(self):
        if self.max_workers < 1 or self.active_runs < 1 or self.max_retained_bytes < 1 or self.event_capacity < 1 or self.effect_capacity < 1:
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






def _identity(value):
    custom = getattr(value, "fingerprint", None)
    if isinstance(custom, str):
        return custom
    identity = getattr(value, "identity", None)
    if hasattr(identity, "sha256"):
        # Source ancestry remains a separate component of semantic work identity.
        return fingerprint((identity.sha256, getattr(value, "source_id", None), getattr(value, "lineage", ())))
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


def _size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    if isinstance(value, bytes):
        return len(value)
    data = getattr(value, "data", None)
    if isinstance(data, bytes):
        return len(data)
    if isinstance(value, Mapping):
        return sys.getsizeof(value) + sum(_size(k, seen) + _size(x, seen) for k, x in value.items())
    if isinstance(value, (tuple, list)):
        return sys.getsizeof(value) + sum(_size(x, seen) for x in value)
    if hasattr(value, "memory_usage"):
        try:
            return int(value.memory_usage(deep=True).sum())
        except Exception:
            pass
    if is_dataclass(value):
        return sys.getsizeof(value) + sum(_size(getattr(value, item.name), seen) for item in fields(value))
    return sys.getsizeof(value)


def _cells(value):
    """Count actual supplied semantic cells, without inferring Cartesian coverage."""
    from stratbox.shared.data.values import SourceDataset, TableEvidenceSet, WorkbookEvidence
    from stratbox.shared.data.workbook_cells import WorkbookCells, WorkbookCell
    if isinstance(value, WorkbookCell): return 1
    if isinstance(value, SourceDataset): return sum(len(row) for row in value.rows)
    if isinstance(value, WorkbookEvidence): return _cells(value.workbook)
    if isinstance(value, WorkbookCells): return sum(len(sheet.cells) for sheet in value.sheets)
    if isinstance(value, TableEvidenceSet): return sum(_cells(item) for item in value.tables)
    if isinstance(value, Mapping): return sum(_cells(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_cells(item) if isinstance(item, (Mapping, tuple, list)) or is_dataclass(item) else 1 for item in value)
    if hasattr(value, "shape") and len(value.shape) == 2: return int(value.shape[0] * value.shape[1])
    if is_dataclass(value): return sum(_cells(getattr(value, field.name)) for field in fields(value))
    return 0


def _isolate(value):
    """Give mutable tabular payloads a private owner without copying immutable bytes."""
    if hasattr(value, "memory_usage") and hasattr(value, "copy"):
        return value.copy(deep=True)
    if isinstance(value, Mapping): return {key: _isolate(item) for key, item in value.items()}
    if isinstance(value, tuple): return tuple(_isolate(item) for item in value)
    if isinstance(value, list): return [_isolate(item) for item in value]
    if is_dataclass(value):
        updates = {item.name: _isolate(getattr(value, item.name)) for item in fields(value)}
        try:
            return replace(value, **updates)
        except (TypeError, ValueError):
            return copy.deepcopy(value)
    return value


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


@dataclass(frozen=True)
class _TaskSummary:
    task_id: str
    scope_id: str


class _LockedMeter:
    """A single cumulative meter shared by parallel producers of one run."""
    def __init__(self, meter, lock):
        self._meter, self._lock = meter, lock

    def __getattr__(self, name):
        value = getattr(self._meter, name)
        if not callable(value): return value
        def locked(*args, **kwargs):
            with self._lock:
                return value(*args, **kwargs)
        return locked


class RunResult:
    def __init__(self, service, run, outcome, outputs, diagnostics, scopes):
        self._service, self._run = service, run
        self.run_id, self.outcome = run.run_id, outcome
        self.outputs, self.scopes = MappingProxyType(_isolate(dict(outputs))), MappingProxyType(dict(scopes))
        self.diagnostics, self._closed = tuple(diagnostics), False
        self._retention_charge = _size(outputs)
        self.effects = MappingProxyType({key: service.lookup_effect(key) for key in run.effect_ids})
        self.resources = MappingProxyType(dict(run.meter.usage()))

    def output(self, name="value"):
        if self._closed:
            raise ExecutionFailure("value.result_closed")
        if name not in self.outputs and name == "value" and len(self.outputs) == 1:
            return next(iter(self.outputs.values()))
        return self.outputs[name]

    def close(self):
        if not self._closed:
            with self._service._condition:
                self._service._retained_bytes -= self._retention_charge
                self.outputs = MappingProxyType({})
                for task in self._run.tasks.values():
                    task.outputs.clear()
                self._closed = True
                self._service._runs.pop(self.run_id, None)
                try: self._service._order.remove(self.run_id)
                except ValueError: pass
                self._service._condition.notify_all()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class RunHandle:
    def __init__(self, service, run):
        self.service, self._run, self.run_id = service, run, run.run_id

    def result(self, timeout=None):
        return self._run.future.result(timeout=timeout)

    def done(self):
        return self._run.future.done()

    def cancel(self, scope_id=None):
        with self.service._condition:
            if self.done():
                return False
            if scope_id is None:
                self._run.cancel.set()
            else:
                for task in self._run.tasks.values():
                    if task.spec.scope_id.startswith(scope_id) and task.state == "pending":
                        task.state = "cancelled"
            self.service._condition.notify_all()
            return True

    def snapshot(self):
        with self.service._condition:
            return {"run_id": self.run_id, "tasks": {k: t.state for k, t in self._run.tasks.items()},
                    "scopes": dict(self._run.scopes), "done": self.done()}


class CommandContext:
    def __init__(self, service, run, task, inputs):
        self.service, self.run, self.task = service, run, task
        self.run_id, self.task_id = run.run_id, task.spec.task_id
        self.parameters = service._resolve(run, task.spec.command.parameters)
        self.target, self.inputs = getattr(run.plan, "target", None), inputs
        self.evidence = []
        self.effect_receipts = {}
        self.budget = _LockedMeter(run.meter, service._condition)

    def spend(self, resource, amount):
        self.budget.charge(resource, amount)

    def remaining_seconds(self):
        self.checkpoint()
        return float("inf") if self.run.deadline is None else max(0.0, self.run.deadline - monotonic())

    def accepted_input(self, name):
        return self.service._accepted.get(fingerprint(self.inputs[name]))

    def provider(self, role):
        return self.service.resolve_provider(role)

    def checkpoint(self):
        self.budget.checkpoint()
        if self.run.deadline is not None and monotonic() >= self.run.deadline:
            raise ExecutionFailure("execution.deadline", outcome="cancelled")
        # A shared producer is cancelled only when all its consumers detach.
        if self.run.cancel.is_set() and not self.service._producer_needed(self.task):
            raise ExecutionFailure("execution.cancelled", outcome="cancelled")

    def check_cancelled(self):
        self.checkpoint()

    def use(self, evidence):
        self.evidence.append(evidence)

    def effect(self, kind, effect_id, action, *, reconcile=None, resource=None, intent=None):
        if kind not in self.task.spec.command.effects:
            raise ExecutionFailure("effect.undeclared:" + kind)
        self.run.effect_ids.add(effect_id)
        receipt = self.service._effect(self, kind, effect_id, action, reconcile, resource, intent)
        self.effect_receipts[effect_id] = receipt
        return receipt


class ExecutionService:
    """A multicall session with one coordinator, shared resources and value owners."""
    def __init__(self, *, providers=None, settings=None, journal=None, observer=None):
        self.providers, self.settings = dict(providers or {}), settings or ExecutionSettings()
        from stratbox.core.notifications import MemoryNotificationState
        self.providers.setdefault("notification_state", MemoryNotificationState())
        self.journal, self.observer = journal or MemoryJournal(self.settings.event_capacity), observer
        self._condition = Condition(RLock())
        self._pool = ThreadPoolExecutor(max_workers=self.settings.max_workers, thread_name_prefix="stratbox")
        self._runs, self._order, self._used = {}, deque(), {}
        self._work, self._completed, self._effects, self._accepted = {}, {}, {}, {}
        self._retained_bytes, self._cache_bytes, self._closing, self._stopped = 0, 0, False, False
        self._thread = Thread(target=self._coordinate, name="stratbox-coordinator", daemon=True)
        self._thread.start()

    def _fact(self, run, kind, task=None, output_name=None, scope_id=None, **data):
        if task is not None:
            command = getattr(task.spec, "command", None)
            data.setdefault("capability_id", getattr(command, "id", None))
            data.setdefault("capability_kind", "command" if command else getattr(task.spec, "kind", "command"))
        kwargs = dict(kind=kind, run_id=run.run_id, scope_id=scope_id if scope_id is not None else getattr(getattr(task, "spec", None), "scope_id", ""),
            command_id=getattr(getattr(getattr(task, "spec", None), "command", None), "id", None),
            output_name=output_name, physical_work_id=getattr(task, "physical_id", None),
            attempt_id=(task.physical_id + ":1") if task and task.physical_id else None, data=data)
        fact = self.journal.append(**kwargs)
        if self.observer:
            try:
                self.observer(fact)
            except Exception:
                run.diagnostics.append("observation.optional_sink_failed")
        return fact

    def submit(self, plan, *, timeout=None):
        with self._condition:
            if self._closing:
                raise ExecutionFailure("execution.service_closed")
            ids = [task.task_id for task in plan.tasks]
            if len(ids) != len(set(ids)):
                raise ExecutionFailure("plan.duplicate_task")
            run = _Run(uuid4().hex, plan, {task.task_id: _Task(task) for task in plan.tasks},
                       deadline=None if timeout is None else monotonic() + timeout)
            run.meter = BudgetMeter(self.settings.run_limits)
            for task in run.tasks.values():
                if set(getattr(task.spec, "deps", ())) - run.tasks.keys():
                    raise ExecutionFailure("plan.unknown_dependency")
                for resource, amount in self._claims(task).items():
                    if amount > self._capacity(resource):
                        raise ExecutionFailure("resource.impossible_claim:" + resource)
            from graphlib import TopologicalSorter, CycleError
            try:
                tuple(TopologicalSorter({key: set(getattr(task.spec, "deps", ())) for key, task in run.tasks.items()}).static_order())
            except CycleError:
                raise ExecutionFailure("plan.cycle") from None
            self._runs[run.run_id] = run
            self._order.append(run.run_id)
            self._fact(run, "run.admitted")
            self._condition.notify_all()
            return RunHandle(self, run)

    def run(self, plan, *, timeout=None):
        return self.submit(plan, timeout=timeout).result(timeout=timeout)

    def status(self, run_id):
        return RunHandle(self, self._runs[run_id]).snapshot()

    def cancel(self, run_id, scope_id=None):
        return RunHandle(self, self._runs[run_id]).cancel(scope_id)

    def result(self, run_id, timeout=None):
        return self._runs[run_id].future.result(timeout)

    def resolve_provider(self, role):
        with self._condition:
            if role in self.providers: return self.providers[role]
            if role in {"http", "filestore", "secrets"}:
                from stratbox.core.runtime.providers import active_providers, local_providers
                bundle = active_providers() or local_providers()
                for name in ("http", "filestore", "secrets"):
                    self.providers.setdefault(name, getattr(bundle, name))
                return self.providers[role]
            raise ExecutionFailure("provider.missing:" + role)

    def lookup_effect(self, effect_id):
        with self._condition:
            current = self._effects.get(effect_id)
            if current is None and "effect_state" in self.providers:
                current = self.providers["effect_state"].get(effect_id)
                if current is not None: self._effects[effect_id] = current
            return current

    def _save_effect(self, receipt):
        if "effect_state" in self.providers:
            self.providers["effect_state"].put(receipt)
        self._effects[receipt.effect_id] = receipt

    def reconcile_effect(self, effect_id, lookup):
        with self._condition:
            previous = self.lookup_effect(effect_id)
            if previous is None: raise ExecutionFailure("effect.not_found")
            if previous.status == "confirmed": return previous
        found = lookup(effect_id)
        if found is None: return previous
        status = getattr(found, "status", None)
        if status in {"unknown", "failed", "rejected"}: return previous
        recovered = EffectReceipt(effect_id, previous.kind, "confirmed", found, previous.resource, intent=previous.intent)
        with self._condition:
            self._save_effect(recovered)
        return recovered

    def _capacity(self, resource):
        return self.settings.max_workers if resource == "worker" else self.settings.capacities.get(resource, 1)

    def _claims(self, task):
        if getattr(task.spec, "kind", "command") != "command":
            return {}
        claims = dict(getattr(task.spec.command, "resources", {}) or {})
        claims["worker"] = 1
        return claims

    def _resolve(self, run, value):
        if hasattr(value, "task_id") and hasattr(value, "port"):
            resolved = run.tasks[value.task_id].outputs[value.port]
            for part in getattr(value, "path", "").split(".") if getattr(value, "path", "") else ():
                resolved = resolved[part] if isinstance(resolved, Mapping) else getattr(resolved, part)
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
        reuse = getattr(command, "reuse", None)
        if reuse is not None and not getattr(reuse, "inflight_eligible", getattr(reuse, "shareable", True)):
            return None
        if command.effects and not command.effects <= frozenset({"network.receive", "network.read"}):
            return None
        try:
            # Physical decode is neutral to source-use attribution; semantic work is not.
            if command.id == "command.material.fetch":
                request = inputs["request"]
                if request.freshness == "fresh": return None
                basis = (request.method, request.url, request.headers, request.body, request.form,
                         request.max_bytes, request.timeout, request.read_only, request.freshness,
                         request.observation_id or run.run_id, request.metadata.get("access_scope"))
            elif command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode")):
                basis = {name: (getattr(getattr(item, "material", item), "data", item)) for name, item in inputs.items()}
            else:
                basis = {name: _identity(item) for name, item in inputs.items()}
            return fingerprint((command.id, str(command.method), command.settings, command.parameters,
                basis, getattr(run.plan, "build_identity", ""),
                tuple((key, id(value)) for key, value in sorted(self.providers.items()))))
        except (ValueError, TypeError):
            return None

    def _producer_needed(self, task):
        if not task.work_key:
            return False
        return any(t.work_key == task.work_key and t.state in {"running", "waiting_shared"} and not r.cancel.is_set()
                   for r in self._runs.values() for t in r.tasks.values())

    def _execute(self, run, task, inputs):
        context = CommandContext(self, run, task, inputs)
        context.checkpoint()
        context.budget.charge("input_bytes", _size(inputs))
        context.budget.charge("cells", _cells(inputs))
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
        if getattr(task.spec.command.reuse, "mutation", "immutable") == "isolated":
            inputs = _isolate(inputs)
        answer = method(inputs, task.spec.command.settings, context)
        if any(receipt.status == "unknown" for receipt in context.effect_receipts.values()):
            raise ExecutionFailure("effect.unconfirmed", outcome="unknown")
        if isinstance(answer, CommandCompletion) or hasattr(answer, "outputs") and hasattr(answer, "outcome"):
            outputs, outcome, findings = dict(answer.outputs), answer.outcome, getattr(answer, "findings", ())
        elif isinstance(answer, Mapping):
            outputs, outcome, findings = dict(answer), "succeeded", ()
        elif len(task.spec.command.outputs) == 1:
            outputs, outcome, findings = {next(iter(task.spec.command.outputs)): answer}, "succeeded", ()
        else:
            raise ExecutionFailure("output.mapping_required")
        if set(outputs) - task.spec.command.outputs.keys():
            raise ExecutionFailure("output.unknown:" + ",".join(set(outputs) - task.spec.command.outputs.keys()))
        for name, port in task.spec.command.outputs.items():
            if name in outputs:
                _validate(port, outputs[name])
            elif getattr(port, "required", True):
                raise ExecutionFailure("output.required:" + name)
        acceptance = getattr(task.spec.command, "acceptance", None)
        if acceptance is not None and hasattr(acceptance, "validate"):
            acceptance.validate(outputs)
        # Boundary payload accounting is cumulative and applies to the complete
        # owned value, including physical evidence and native scientific tables.
        context.budget.charge("output_bytes", _size(outputs), completed=True)
        return outputs, outcome, tuple(findings)

    def _settle(self):
        for run in self._runs.values():
            for task in tuple(run.tasks.values()):
                if task.state not in {"running", "waiting_shared"} or not task.future.done():
                    continue
                producer = task.state == "running"
                if producer:
                    for resource, amount in task.claims.items():
                        self._used[resource] -= amount
                    if task.work_key is not None:
                        self._work.pop(task.work_key, None)
                try:
                    outputs, outcome, findings = task.future.result()
                    task.outputs, task.state, task.findings = self._logical_outputs(run, task, outputs), outcome, findings
                    if run.cancel.is_set():
                        task.outputs, task.state = {}, "cancelled"
                    else:
                        for name in outputs:
                            self._register_value(run, task, name, task.outputs[name])
                            self._fact(run, "output.accepted", task, output_name=name)
                    reuse = getattr(task.spec.command, "reuse", None)
                    if producer and task.work_key and outcome == "succeeded" and getattr(reuse, "completed_eligible", True):
                        amount = _size(outputs)
                        if self._cache_bytes + self._retained_bytes + amount <= self.settings.max_retained_bytes:
                            self._completed[task.work_key] = (outputs, outcome, findings)
                            self._cache_bytes += amount
                except Exception as error:
                    task.state = getattr(error, "outcome", "failed")
                    task.findings = (getattr(error, "code", str(error)),)
                    run.diagnostics.extend(task.findings)
                self._fact(run, "work.finished", task, outcome=task.state, findings=task.findings)

    def _register_value(self, run, task, name, value):
        from stratbox.shared.data.values import IdentifiedMaterial
        from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
        inputs = self._resolve(run, task.spec.inputs)
        basis, uses = [], list(getattr(value, "source_uses", ()))
        for item in inputs.values():
            try:
                key = fingerprint(item)
            except (ValueError, TypeError):
                continue
            previous = self._accepted.get(key)
            if previous:
                basis.extend(previous["basis"]); uses.extend(previous["source_uses"])
            basis.append(key)
            identity = getattr(item, "identity", None)
            if hasattr(identity, "sha256"): basis.append(identity.sha256)
            uses.extend(getattr(item, "source_uses", ()))
        if isinstance(value, IdentifiedMaterial):
            uses.append(SourceUse(SourceCoordinate(value.claim.source_id, issue_id=value.claim.issue_id or None,
                asset_id=value.claim.asset_id, material_identity=value.identity), "material", value.claim.attribution))
        try:
            key = fingerprint(value)
        except (ValueError, TypeError):
            return
        self._accepted[key] = {"id": fingerprint((run.run_id, task.spec.task_id, name, key)),
            "basis": tuple(dict.fromkeys(basis)), "source_uses": tuple(dict.fromkeys(uses))}

    def _logical_outputs(self, run, task, outputs):
        """Attach each consumer's source use to a shared neutral decoder payload."""
        if task.spec.command.id == "command.material.fetch":
            request = self._resolve(run, task.spec.inputs)["request"]
            material = outputs.get("material")
            if material is not None:
                return {**outputs, "material": replace(material, source_id=request.source_id,
                    metadata={**dict(material.metadata), **dict(request.metadata)})}
            return dict(outputs)
        if not task.spec.command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode")):
            return dict(outputs)
        from stratbox.shared.data.values import Material, IdentifiedMaterial, WorkbookEvidence, JsonEvidence, DocumentEvidence, DbfEvidence
        original = self._resolve(run, task.spec.inputs).get("material")
        from stratbox.core.commands.standard import _material
        original = _material(original) if isinstance(original, IdentifiedMaterial) else original
        if not isinstance(original, Material): return dict(outputs)
        return {name: replace(value, material=original) if isinstance(value, (WorkbookEvidence, JsonEvidence, DocumentEvidence, DbfEvidence)) else value
                for name, value in outputs.items()}

    def _ready(self, run, task):
        deps = [run.tasks[key] for key in getattr(task.spec, "deps", ())]
        if any(dep.state in {"failed", "cancelled", "blocked", "unknown"} for dep in deps):
            task.state = "blocked"
            return False
        if not all(dep.state in {"succeeded", "skipped"} for dep in deps): return False
        for guard in getattr(task.spec, "input_guards", ()):
            try:
                guard.contract.validate(self._resolve(run, guard.value))
            except KeyError:
                return False
            except (ValueError, TypeError, ExecutionFailure) as error:
                task.state, task.findings = "blocked", (str(error),)
                run.diagnostics.extend(task.findings)
                return False
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

    def _obligations(self, run, scope, names):
        pending, errors = False, []
        for name in names:
            task = run.tasks.get(name) or run.tasks.get(scope.scope_id + "/" + name)
            if task is None:
                reference = scope.outputs.get(name)
                task = run.tasks.get(getattr(reference, "task_id", None))
            if task is None:
                errors.append("acceptance.unknown_obligation:" + name)
            elif task.state in {"pending", "expanding", "running", "waiting_shared"}:
                pending = True
            elif task.state != "succeeded":
                errors.append("acceptance.required_obligation_failed:" + name)
        return pending, tuple(errors)

    def _scope_assessment(self, run, scope):
        values, settled, invalid = {}, set(), {}
        for name, reference in scope.outputs.items():
            try:
                value = self._resolve(run, reference)
                _validate(scope.output_contracts[name], value)
                values[name] = value
                settled.add(name)
            except KeyError:
                producer = getattr(reference, "task_id", None)
                if producer in run.tasks and run.tasks[producer].state in {"failed", "cancelled", "blocked", "unknown", "skipped"}:
                    settled.add(name)
            except (ValueError, TypeError, ExecutionFailure) as error:
                invalid[name] = (str(error),)
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
            self._fact(run, "output.accepted", output_name=name, scope_id=scope.scope_id,
                capability_id=scope.capability_id, capability_kind=scope.kind)
            run.accepted_scopes.add(key)

    def _instantiate(self, run, template, bindings, prefix):
        """Unroll a bounded member; its commands use the ordinary admission path."""
        from stratbox.capabilities.plan.models import TemplateInput, ValueRef
        local = {item.task_id for item in template.tasks}
        def substitute(value):
            if isinstance(value, TemplateInput): return bindings[value.name]
            if isinstance(value, ValueRef):
                return replace(value, task_id=prefix + value.task_id) if value.task_id in local else value
            if isinstance(value, Mapping): return {k: substitute(v) for k, v in value.items()}
            if isinstance(value, tuple): return tuple(substitute(v) for v in value)
            if isinstance(value, list): return [substitute(v) for v in value]
            if type(value).__name__ == "Condition":
                return replace(value, value=substitute(value.value))
            return value
        children = []
        for original in template.tasks:
            updates = {"task_id": prefix + original.task_id,
                       "deps": tuple(prefix + key if key in local else key for key in original.deps),
                       "scope_id": prefix + original.scope_id}
            for name in ("inputs", "items", "initial", "selector", "condition"):
                if hasattr(original, name): updates[name] = substitute(getattr(original, name))
            if hasattr(original, "command"):
                updates["command"] = replace(original.command, parameters=substitute(original.command.parameters))
            local_scopes = {scope.scope_id for scope in template.scopes}
            updates["guards"] = tuple(replace(guard, scope_id=prefix + guard.scope_id) if guard.scope_id in local_scopes else guard
                                      for guard in getattr(original, "guards", ()))
            updates["input_guards"] = tuple(replace(guard, value=substitute(guard.value)) for guard in getattr(original, "input_guards", ()))
            child = _Task(replace(original, **updates))
            for resource, amount in self._claims(child).items():
                if amount > self._capacity(resource): raise ExecutionFailure("resource.impossible_claim:" + resource)
            run.tasks[child.spec.task_id] = child
            children.append(child.spec.task_id)
        for scope in template.scopes:
            run.extra_scopes.append(replace(scope, scope_id=prefix + scope.scope_id,
                parent_id=prefix + scope.parent_id if scope.parent_id else prefix.rstrip("/"),
                outputs=substitute(scope.outputs), required_tasks=tuple(prefix + key for key in scope.required_tasks),
                required_scopes=tuple(prefix + key for key in scope.required_scopes),
                required_checks=tuple(prefix + key for key in scope.required_checks),
                required_effects=tuple(prefix + key for key in scope.required_effects)))
        return tuple(children), substitute(template.outputs)

    def _structural(self, run, task):
        spec, kind = task.spec, getattr(task.spec, "kind", "command")
        if kind == "collect":
            task.outputs, task.state = {"items": self._resolve(run, spec.items)}, "succeeded"
            return
        if task.expansion is None:
            if kind == "map":
                items = tuple(self._resolve(run, spec.items))
                if len(items) > spec.max_items: raise ExecutionFailure("map.item_limit")
                task.expansion = {"items": items, "next": 0, "active": {}, "results": {}, "statuses": {}}
            elif kind == "repeat":
                task.expansion = {"state": self._resolve(run, spec.initial), "pass": 0, "active": None}
            elif kind == "dispatch":
                selected = self._resolve(run, spec.selector)
                material = getattr(selected, "material", selected)
                data = getattr(material, "data", b"")
                name = str(getattr(material, "metadata", {}).get("member", getattr(material, "metadata", {}).get("filename", "")))
                suffix = name.rsplit(".", 1)[-1].lower()
                if data.startswith(b"PK"):
                    from io import BytesIO
                    from zipfile import ZipFile
                    with ZipFile(BytesIO(data)) as archive:
                        names = set(archive.namelist())
                    fmt = "xlsx" if "xl/workbook.xml" in names else "xlsb" if "xl/workbook.bin" in names else "docx" if "word/document.xml" in names else "archive"
                elif data.startswith(b"%PDF-"): fmt = "pdf"
                elif data.startswith(b"\xd0\xcf\x11\xe0"):
                    fmt = "doc" if suffix == "doc" or "msword" in getattr(material, "media_type", "") else "xls"
                elif data.lstrip().startswith((b"{", b"[")): fmt = "json"
                elif data.startswith((b"Rar!", b"7z\xbc\xaf\x27\x1c")): fmt = "archive"
                elif suffix in {"csv", "dbf", "html", "htm", "xls", "doc"}: fmt = "html" if suffix == "htm" else suffix
                elif "html" in getattr(material, "media_type", ""): fmt = "html"
                elif "csv" in getattr(material, "media_type", ""): fmt = "csv"
                else: raise ExecutionFailure("format.unrecognized")
                template = spec.alternatives.get(fmt)
                if template is None: raise ExecutionFailure("format.unsupported:" + fmt)
                task.expansion = {"active": self._instantiate(run, template, {spec.input_name: selected}, f"{spec.task_id}/{fmt}/")}
            else:
                raise ExecutionFailure("plan.unknown_structural_kind")
            task.state = "expanding"
        state = task.expansion
        if kind == "dispatch":
            keys, outputs = state["active"]
            children = [run.tasks[key] for key in keys]
            if not all(child.state in {"succeeded", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children): return
            if any(child.state != "succeeded" for child in children if child.spec.required):
                task.state = "failed"; return
            task.outputs = {"dataset": self._resolve(run, outputs)[spec.output_port]}
            task.state = "succeeded"
            return
        if kind == "map":
            for index, (keys, outputs) in tuple(state["active"].items()):
                children = [run.tasks[key] for key in keys]
                if all(child.state in {"succeeded", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children):
                    status = "succeeded" if all(child.state == "succeeded" for child in children if child.spec.required) else "failed"
                    state["statuses"][index] = status
                    if status == "succeeded": state["results"][index] = self._resolve(run, outputs)[spec.item_output]
                    del state["active"][index]
            while len(state["active"]) < spec.window and state["next"] < len(state["items"]):
                index = state["next"]
                state["active"][index] = self._instantiate(run, spec.template, {spec.item_input: state["items"][index]}, f"{spec.task_id}/item{index}/")
                state["next"] += 1
            if not state["active"] and state["next"] == len(state["items"]):
                task.outputs = {"items": tuple(state["results"][index] for index in sorted(state["results"])),
                                "outcomes": tuple((index, state["statuses"][index]) for index in sorted(state["statuses"]))}
                subset = spec.completion == "eligible_subset" and (bool(state["results"]) or not state["items"])
                task.state = "succeeded" if subset or all(s == "succeeded" for s in state["statuses"].values()) else "failed"
                task.findings = tuple(f"map.unit:{index}:{status}" for index, status in state["statuses"].items())
                self._fact(run, "map.completed", units=len(state["items"]), statuses=state["statuses"])
        else:
            if state["active"] is not None:
                keys, outputs = state["active"]
                children = [run.tasks[key] for key in keys]
                if not all(child.state in {"succeeded", "failed", "cancelled", "blocked", "unknown", "skipped"} for child in children): return
                if any(child.state != "succeeded" for child in children if child.spec.required):
                    task.state = "failed"; return
                state["state"] = self._resolve(run, outputs)[spec.state_output]
                stop = spec.stop
                converged = stop.accepts(state["state"]) if hasattr(stop, "accepts") else bool(stop(state["state"])) if callable(stop) else bool(getattr(state["state"], "converged", False))
                self._fact(run, "iteration.assessed", pass_number=state["pass"], converged=converged)
                if converged:
                    task.outputs, task.state = {"state": state["state"]}, "succeeded"; return
                if state["pass"] >= spec.max_passes:
                    task.state, task.findings = "failed", ("iteration.limit_without_convergence",)
                    run.diagnostics.extend(task.findings); return
            state["pass"] += 1
            state["active"] = self._instantiate(run, spec.template, {spec.state_input: state["state"]}, f"{spec.task_id}/pass{state['pass']}/")

    def _finish(self, run):
        roots = [run.tasks[spec.task_id] for spec in run.plan.tasks]
        good = all(task.state in {"succeeded", "skipped"} for task in roots if getattr(task.spec, "required", True))
        uncertain = any(task.state == "unknown" for task in roots if getattr(task.spec, "required", True))
        outcome = "cancelled" if run.cancel.is_set() else "succeeded" if good else "unknown" if uncertain else "failed"
        scopes = {scope.scope_id: scope for scope in (*getattr(run.plan, "scopes", ()), *run.extra_scopes)}
        available = {}
        visiting = set()
        def settle_scope(scope):
            if scope.scope_id in run.scopes: return run.scopes[scope.scope_id]
            if scope.scope_id in visiting: raise ExecutionFailure("scope.cycle")
            visiting.add(scope.scope_id)
            children_ok = all(settle_scope(scopes[key]) == "succeeded" for key in scope.required_scopes)
            required = [run.tasks[key] for key in scope.required_tasks if key in run.tasks]
            values, errors, pending = self._scope_assessment(run, scope)
            waiting, findings = self._obligations(run, scope, scope.required_effects)
            accepted = {name: value for name, value in values.items() if name not in errors and name not in pending}
            available[scope.scope_id] = accepted
            for name in accepted: self._publish_scope_output(run, scope, name)
            state = "succeeded" if children_ok and all(t.state == "succeeded" for t in required) and not errors and not pending and not waiting and not findings else "failed"
            run.scopes[scope.scope_id] = state
            run.diagnostics.extend(code for codes in errors.values() for code in codes)
            run.diagnostics.extend(findings)
            self._fact(run, "scope.completed", scope_id=scope.scope_id, capability_id=scope.capability_id,
                capability_kind=scope.kind, outcome=state)
            visiting.remove(scope.scope_id)
            return state
        for scope in scopes.values(): settle_scope(scope)
        root_scopes = [scope for scope in scopes.values() if scope.parent_id is None and scope.required]
        if any(run.scopes[scope.scope_id] != "succeeded" for scope in root_scopes) and outcome not in {"unknown", "cancelled"}:
            outcome = "failed"
        outputs = {}
        accepted_names = set().union(*(available[scope.scope_id].keys() for scope in root_scopes)) if root_scopes else set(run.plan.outputs)
        for name, reference in run.plan.outputs.items():
            if name in accepted_names:
                try: outputs[name] = self._resolve(run, reference)
                except (KeyError, AttributeError): pass
        amount = _size(outputs)
        if self._retained_bytes + self._cache_bytes + amount > self.settings.max_retained_bytes:
            self._completed.clear()
            self._cache_bytes = 0
        if self._retained_bytes + amount > self.settings.max_retained_bytes:
            outputs, outcome = {}, "failed"
            run.diagnostics.append("value.retention_capacity_exhausted")
            amount = 0
        self._retained_bytes += amount
        self._fact(run, "run.finished", outcome=outcome)
        run.future.set_result(RunResult(self, run, outcome, outputs, run.diagnostics, run.scopes))
        # A completed run keeps its result owner and diagnostics, not every
        # intermediate or worker Future that happened to produce that result.
        for task in run.tasks.values():
            task.outputs = {}
            task.future = None
            task.spec = _TaskSummary(task.spec.task_id, task.spec.scope_id)
            task.expansion = None
        run.plan = None

    def _coordinate(self):
        try:
            while True:
                with self._condition:
                    self._settle()
                    remaining = [run for run in self._runs.values() if not run.future.done()]
                    if self._closing and not remaining:
                        self._stopped = True
                        self._condition.notify_all()
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
                                try:
                                    self._structural(run, task)
                                except Exception as error:
                                    task.state, task.findings = "failed", (str(error),)
                                    run.diagnostics.append(str(error))
                                continue
                            if task.state != "pending":
                                continue
                            if run.cancel.is_set():
                                task.state = "cancelled"
                                continue
                            if not self._ready(run, task):
                                continue
                            if getattr(task.spec, "kind", "command") != "command":
                                try:
                                    self._structural(run, task)
                                except Exception as error:
                                    task.state, task.findings = "failed", (str(error),)
                                    run.diagnostics.append(str(error))
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
                            inputs = self._resolve(run, task.spec.inputs)
                            try:
                                for role in getattr(task.spec.command, "required_providers", ()):
                                    self.resolve_provider(role)
                            except ExecutionFailure as error:
                                task.state, task.findings = "failed", (error.code,)
                                run.diagnostics.append(error.code)
                                continue
                            key = self._key(run, task, inputs)
                            if key in self._completed:
                                outputs, task.state, task.findings = self._completed[key]
                                task.outputs = self._logical_outputs(run, task, outputs)
                                for name, value in task.outputs.items(): self._register_value(run, task, name, value)
                                self._fact(run, "work.reused", task)
                                continue
                            if key is not None and key in self._work:
                                task.future, task.physical_id = self._work[key]
                                task.state, task.work_key = "waiting_shared", key
                                self._fact(run, "work.joined", task)
                                continue
                            claims = self._claims(task)
                            if any(self._used.get(r, 0) + n > self._capacity(r) for r, n in claims.items()):
                                continue
                            for r, n in claims.items():
                                self._used[r] = self._used.get(r, 0) + n
                            task.state, task.claims, task.work_key, task.physical_id = "running", claims, key, uuid4().hex
                            self._fact(run, "work.started", task)
                            task.future = self._pool.submit(self._execute, run, task, inputs)
                            task.future.add_done_callback(lambda _future: self._wake())
                            if key is not None:
                                self._work[key] = task.future, task.physical_id
                            # One newly admitted producer per run per fair pass.
                            break
                        if all(t.state not in {"pending", "running", "waiting_shared", "expanding"} for t in run.tasks.values()):
                            self._finish(run)
                    self._condition.wait(0.01)
        except BaseException as error:
            with self._condition:
                for run in self._runs.values():
                    if not run.future.done():
                        run.future.set_exception(error)
                self._stopped = True
                self._condition.notify_all()

    def _wake(self):
        with self._condition:
            self._condition.notify_all()

    def _effect(self, context, kind, effect_id, action, reconcile, resource, intent):
        with self._condition:
            previous = self.lookup_effect(effect_id)
            if previous:
                if previous.kind != kind or previous.resource != resource:
                    raise ExecutionFailure("effect.identity_conflict")
                if previous.status == "confirmed":
                    return previous
                if previous.status == "unknown":
                    if reconcile is None:
                        return previous
                    recovered = reconcile(previous)
                    if recovered is not None:
                        receipt = EffectReceipt(effect_id, kind, "confirmed", recovered, resource, intent=previous.intent)
                        self._save_effect(receipt)
                        return receipt
                    return previous
            if len(self._effects) >= self.settings.effect_capacity:
                raise ExecutionFailure("effect.state_capacity_exhausted")
            self._save_effect(EffectReceipt(effect_id, kind, "unknown", resource=resource, intent=intent))
        try:
            value = action()
            receipt = EffectReceipt(effect_id, kind, "confirmed", value, resource, intent=intent)
        except Exception as error:
            from stratbox.core.storage.filestore import MutationRejected
            status = "rejected" if isinstance(error, MutationRejected) else "unknown"
            receipt = EffectReceipt(effect_id, kind, status, resource=resource, finding=str(error), intent=intent)
        with self._condition:
            try:
                self._save_effect(receipt)
            except Exception as error:
                receipt = EffectReceipt(effect_id, kind, "unknown", resource=resource,
                    finding="Effect ran but durable acknowledgement failed: " + str(error), intent=intent)
                self._effects[effect_id] = receipt
            self._fact(context.run, "effect.settled" if receipt.status == "confirmed" else "effect.unknown", context.task,
                effect_id=effect_id, effect_kind=kind, outcome=receipt.status)
        return receipt

    def close(self, *, wait=True, cancel=False):
        with self._condition:
            self._closing = True
            if cancel:
                for run in self._runs.values():
                    run.cancel.set()
            self._condition.notify_all()
        if wait:
            self._thread.join()
        self._pool.shutdown(wait=wait)
        self._completed.clear()
        self._cache_bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
