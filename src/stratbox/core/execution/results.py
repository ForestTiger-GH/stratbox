"""Public run handles and independently owned, explicitly closable results."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .errors import ExecutionFailure
from .owned_values import _isolate, _value_keys


class _OutputView(Mapping):
    def __init__(self, result): self._result = result
    def __iter__(self): return iter(self._result._outputs)
    def __len__(self): return len(self._result._outputs)
    def __getitem__(self, name):
        if name not in self._result._outputs: raise KeyError(name)
        return self._result.output(name)


class RunResult:
    def __init__(self, service, run, outcome, outputs, diagnostics, scopes, retention_charge):
        self._service, self._run = service, run
        self.run_id, self.outcome = run.run_id, outcome
        self._outputs, self.scopes = _isolate(dict(outputs)), MappingProxyType(dict(scopes))
        self.outputs = _OutputView(self)
        self._closed = False
        self._retention_charge = retention_charge
        effects,unresolved = {},[]
        for key in run.effect_ids:
            try: receipt=service.lookup_effect(key)
            except Exception:
                receipt=service._effects.get(key)
                run.diagnostics.append('effect.lookup_unavailable')
            if receipt is None: unresolved.append(key)
            else: effects[key]=receipt
        self.effect_ids=tuple(run.effect_ids)
        self.unresolved_effect_ids=tuple(unresolved)
        self.effects=MappingProxyType(effects)
        self.diagnostics=tuple(dict.fromkeys((*diagnostics,*run.diagnostics)))
        self.resources = MappingProxyType(dict(run.meter.usage()))
        self._accepted_keys = _value_keys(outputs.values())
        service.staging.pin(self._outputs, "result:" + self.run_id)

    def output(self, name="value"):
        if self._closed:
            raise ExecutionFailure("value.result_closed")
        if name not in self._outputs and name == "value" and len(self._outputs) == 1:
            return _isolate(next(iter(self._outputs.values())))
        return _isolate(self._outputs[name])

    def close(self):
        if not self._closed:
            with self._service._condition:
                if self._closed: return
                self._service._retained_bytes -= self._retention_charge
                self._outputs = {}
                self._service.staging.release("result:" + self.run_id)
                for task in self._run.tasks.values():
                    task.outputs.clear()
                    task.accepted_keys.clear()
                self._closed = True
                self._accepted_keys.clear()
                self._service._runs.pop(self.run_id, None)
                self._service._release_admission(self._run)
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
                matches = [task for task in self._run.tasks.values()
                    if task.spec.scope_id == scope_id or task.spec.scope_id.startswith(scope_id + "/")]
                if not matches: raise ExecutionFailure("execution.unknown_scope")
                for task in matches:
                    task.cancelled = True
                    if task.state in {"pending", "expanding"} and getattr(task.spec, 'kind', 'command') not in {'map', 'collect'}:
                        task.state = "cancelled"
            self.service._condition.notify_all()
            return True

    def snapshot(self):
        with self.service._condition:
            return {"run_id": self.run_id, "tasks": {k: t.state for k, t in self._run.tasks.items()},
                    "scopes": dict(self._run.scopes), "done": self.done()}
