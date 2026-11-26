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


class ExecutionFailure(OperationFailure):
    def __init__(self, code, *, outcome="failed"):
        self.code, self.outcome = str(code), outcome
        super().__init__(self.code)


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

    def __post_init__(self):
        if self.max_workers < 1 or self.active_runs < 1 or self.max_retained_bytes < 1 or self.event_capacity < 1:
            raise ValueError("execution.invalid_settings")
        if any(type(n) is not int or n < 1 for n in self.capacities.values()):
            raise ValueError("execution.invalid_capacity")
        object.__setattr__(self, "capacities", MappingProxyType(dict(self.capacities)))


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


@dataclass(frozen=True)
class JournalFact:
    sequence: int
    kind: str
    run_id: str
    scope_id: str
    command_id: str | None
    output_name: str | None
    physical_work_id: str | None
    attempt_id: str | None
    data: Mapping[str, object]
    occurred_at: datetime


class MemoryJournal:
    """Retained bounded fact stream; an exhausted journal applies backpressure."""
    def __init__(self, capacity=10000):
        self.capacity, self._facts, self._lock = capacity, [], RLock()

    def append(self, *, kind, run_id, scope_id="", command_id=None, output_name=None,
               physical_work_id=None, attempt_id=None, data=None):
        with self._lock:
            if len(self._facts) >= self.capacity:
                raise ExecutionFailure("journal.capacity_exhausted")
            fact = JournalFact(len(self._facts) + 1, kind, run_id, scope_id, command_id,
                output_name, physical_work_id, attempt_id, MappingProxyType(dict(data or {})), datetime.now(timezone.utc))
            self._facts.append(fact)
            return fact

    def read(self, after=0, limit=1000, *, run_id=None):
        if after < 0 or not 0 < limit <= self.capacity:
            raise ValueError("journal.invalid_page")
        with self._lock:
            return tuple(f for f in self._facts if f.sequence > after and (run_id is None or f.run_id == run_id))[:limit]


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
    source = getattr(port, "source", None)
    allowed = getattr(source, "series_ids", frozenset())
    actual = _sources(value)
    if allowed and (not actual or not actual <= set(allowed)):
        raise ExecutionFailure("source.context_conflict")


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


class RunResult:
    def __init__(self, service, run, outcome, outputs, diagnostics, scopes):
        self._service, self._run = service, run
        self.run_id, self.outcome = run.run_id, outcome
        self.outputs, self.scopes = MappingProxyType(dict(outputs)), MappingProxyType(dict(scopes))
        self.diagnostics, self._closed = tuple(diagnostics), False

    def output(self, name="value"):
        if self._closed:
            raise ExecutionFailure("value.result_closed")
        if name not in self.outputs and name == "value" and len(self.outputs) == 1:
            return next(iter(self.outputs.values()))
        return self.outputs[name]

    def close(self):
        if not self._closed:
            with self._service._condition:
                self._service._retained_bytes -= _size(self.outputs)
                self._closed = True
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

    def provider(self, role):
        try:
            return self.service.providers[role]
        except KeyError:
            raise ExecutionFailure("provider.missing:" + role) from None

    def checkpoint(self):
        if self.run.deadline is not None and monotonic() >= self.run.deadline:
            raise ExecutionFailure("execution.deadline", outcome="cancelled")
        # A shared producer is cancelled only when all its consumers detach.
        if self.run.cancel.is_set() and not self.service._producer_needed(self.task):
            raise ExecutionFailure("execution.cancelled", outcome="cancelled")

    def check_cancelled(self):
        self.checkpoint()

    def use(self, evidence):
        self.evidence.append(evidence)

    def effect(self, kind, effect_id, action, *, reconcile=None, resource=None):
        if kind not in self.task.spec.command.effects:
            raise ExecutionFailure("effect.undeclared:" + kind)
        return self.service._effect(self, kind, effect_id, action, reconcile, resource)


class ExecutionService:
    """A multicall session with one coordinator, shared resources and value owners."""
    def __init__(self, *, providers=None, settings=None, journal=None, observer=None):
        self.providers, self.settings = dict(providers or {}), settings or ExecutionSettings()
        self.journal, self.observer = journal or MemoryJournal(self.settings.event_capacity), observer
        self._condition = Condition(RLock())
        self._pool = ThreadPoolExecutor(max_workers=self.settings.max_workers, thread_name_prefix="stratbox")
        self._runs, self._order, self._used = {}, deque(), {}
        self._work, self._completed, self._effects = {}, {}, {}
        self._retained_bytes, self._cache_bytes, self._closing, self._stopped = 0, 0, False, False
        self._thread = Thread(target=self._coordinate, name="stratbox-coordinator", daemon=True)
        self._thread.start()

    def _fact(self, run, kind, task=None, output_name=None, **data):
        kwargs = dict(kind=kind, run_id=run.run_id, scope_id=getattr(getattr(task, "spec", None), "scope_id", ""),
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
            if command.id.endswith(("workbook.decode", "json.decode", "document.decode", "dbf.decode")):
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
        method = task.spec.command.method
        method = method.resolve() if hasattr(method, "resolve") else method
        for provider in getattr(task.spec.command, "required_providers", ()):
            context.provider(provider)
        for name, port in task.spec.command.inputs.items():
            if name in inputs:
                _validate(port, inputs[name])
            elif getattr(port, "required", True):
                raise ExecutionFailure("input.required:" + name)
        for requirement in task.spec.command.source_requirements:
            allowed, actual = set(getattr(requirement, "series_ids", ())), _sources(inputs)
            if allowed and actual and not actual <= allowed:
                raise ExecutionFailure("source.context_conflict")
        answer = method(inputs, task.spec.command.settings, context)
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
                try:
                    outputs, outcome, findings = task.future.result()
                    task.outputs, task.state, task.findings = outputs, outcome, findings
                    if run.cancel.is_set():
                        task.outputs, task.state = {}, "cancelled"
                    else:
                        for name in outputs:
                            self._fact(run, "output.accepted", task, output_name=name)
                    reuse = getattr(task.spec.command, "reuse", None)
                    if producer and task.work_key and outcome == "succeeded" and getattr(reuse, "completed_eligible", True):
                        amount = _size(outputs)
                        if self._cache_bytes + amount <= self.settings.max_retained_bytes:
                            self._completed[task.work_key] = (outputs, outcome, findings)
                            self._cache_bytes += amount
                except Exception as error:
                    task.state = getattr(error, "outcome", "failed")
                    task.findings = (getattr(error, "code", str(error)),)
                    run.diagnostics.extend(task.findings)
                self._fact(run, "work.finished", task, outcome=task.state, findings=task.findings)

    def _ready(self, run, task):
        deps = [run.tasks[key] for key in getattr(task.spec, "deps", ())]
        if any(dep.state in {"failed", "cancelled", "blocked", "unknown"} for dep in deps):
            task.state = "blocked"
            return False
        return all(dep.state == "succeeded" for dep in deps)

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
            return value
        children = []
        for original in template.tasks:
            updates = {"task_id": prefix + original.task_id,
                       "deps": tuple(prefix + key if key in local else key for key in original.deps),
                       "scope_id": prefix + original.scope_id}
            for name in ("inputs", "items", "initial"):
                if hasattr(original, name): updates[name] = substitute(getattr(original, name))
            if hasattr(original, "command"):
                updates["command"] = replace(original.command, parameters=substitute(original.command.parameters))
            child = _Task(replace(original, **updates))
            for resource, amount in self._claims(child).items():
                if amount > self._capacity(resource): raise ExecutionFailure("resource.impossible_claim:" + resource)
            run.tasks[child.spec.task_id] = child
            children.append(child.spec.task_id)
        for scope in template.scopes:
            run.extra_scopes.append(replace(scope, scope_id=prefix + scope.scope_id,
                parent_id=prefix + scope.parent_id if scope.parent_id else None,
                outputs=substitute(scope.outputs), required_tasks=tuple(prefix + key for key in scope.required_tasks),
                required_scopes=tuple(prefix + key for key in scope.required_scopes)))
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
            else:
                raise ExecutionFailure("plan.unknown_structural_kind")
            task.state = "expanding"
        state = task.expansion
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
                task.outputs = {"items": tuple(state["results"][index] for index in sorted(state["results"]))}
                task.state = "succeeded" if spec.completion == "eligible_subset" or all(s == "succeeded" for s in state["statuses"].values()) else "failed"
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
        good = all(task.state == "succeeded" for task in run.tasks.values() if getattr(task.spec, "required", True))
        outcome = "cancelled" if run.cancel.is_set() else "succeeded" if good else "failed"
        for scope in reversed((*getattr(run.plan, "scopes", ()), *run.extra_scopes)):
            required = [run.tasks[key] for key in getattr(scope, "required_tasks", ()) if key in run.tasks]
            state = "succeeded" if all(t.state == "succeeded" for t in required) else "failed"
            try:
                values = self._resolve(run, scope.outputs)
                for name, port in getattr(scope, "output_contracts", {}).items():
                    if name in values:
                        _validate(port, values[name])
                acceptance = getattr(scope, "acceptance", None)
                if acceptance and hasattr(acceptance, "validate"):
                    acceptance.validate(values)
            except Exception as error:
                state = "failed"
                run.diagnostics.append(getattr(error, "code", str(error)))
            run.scopes[scope.scope_id] = state
            self._fact(run, "scope.completed", capability_id=scope.capability_id, capability_kind=scope.kind, scope=scope.scope_id, outcome=state)
            if scope.parent_id is None and getattr(scope, "required", True) and state != "succeeded": outcome = "failed"
        try:
            outputs = self._resolve(run, run.plan.outputs) if outcome == "succeeded" else {}
        except (KeyError, AttributeError):
            outputs, outcome = {}, "failed"
        amount = _size(outputs)
        if self._retained_bytes + amount > self.settings.max_retained_bytes:
            outputs, outcome = {}, "failed"
            run.diagnostics.append("value.retention_capacity_exhausted")
            amount = 0
        self._retained_bytes += amount
        self._fact(run, "run.finished", outcome=outcome)
        run.future.set_result(RunResult(self, run, outcome, outputs, run.diagnostics, run.scopes))

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
                        if run.deadline is not None and monotonic() >= run.deadline:
                            run.cancel.set()
                        for task in tuple(run.tasks.values()):
                            if task.state == "expanding":
                                self._structural(run, task)
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
                                value = self._resolve(run, condition.value)
                                for part in condition.path.split(".") if condition.path else ():
                                    value = value[part] if isinstance(value, Mapping) else getattr(value, part)
                                if value != condition.equals:
                                    task.state = "skipped"
                                    continue
                            inputs = self._resolve(run, task.spec.inputs)
                            key = self._key(run, task, inputs)
                            if key in self._completed:
                                task.outputs, task.state, task.findings = self._completed[key]
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

    def _effect(self, context, kind, effect_id, action, reconcile, resource):
        with self._condition:
            previous = self._effects.get(effect_id)
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
                        receipt = EffectReceipt(effect_id, kind, "confirmed", recovered, resource)
                        self._effects[effect_id] = receipt
                        return receipt
                    return previous
            self._effects[effect_id] = EffectReceipt(effect_id, kind, "unknown", resource=resource)
        try:
            value = action()
            receipt = EffectReceipt(effect_id, kind, "confirmed", value, resource)
        except Exception as error:
            receipt = EffectReceipt(effect_id, kind, "unknown", resource=resource, finding=str(error))
        with self._condition:
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

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
