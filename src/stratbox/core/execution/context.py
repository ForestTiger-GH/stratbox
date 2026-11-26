"""The bound method context and synchronized cumulative run budget."""
from __future__ import annotations

from dataclasses import replace
from time import monotonic

from stratbox.shared.data.values import fingerprint
from .errors import ExecutionFailure
from .owned_values import _isolate


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


class CommandContext:
    def __init__(self, service, run, task, inputs):
        self.service, self.run, self.task = service, run, task
        self.run_id, self.task_id = run.run_id, task.spec.task_id
        self.parameters = _isolate(service._resolve(run, task.spec.command.parameters))
        self.target = task.spec.command.target if task.spec.command.target is not None else getattr(run.plan, "target", None)
        self.inputs = inputs
        self.evidence = []
        self.effect_receipts = {}
        self._active_effects = set()
        self.budget = _LockedMeter(run.meter, service._condition)

    def spend(self, resource, amount):
        self.budget.charge(resource, amount)

    def remaining_seconds(self):
        self.checkpoint()
        with self.service._condition:
            consumers = [(run, task) for run in self.service._runs.values() for task in run.tasks.values()
                if task is self.task or self.task.work_key is not None and task.work_key == self.task.work_key]
            deadlines = [float("inf") if run.deadline is None else max(0.0,run.deadline-monotonic())
                for run,task in consumers if not run.cancel.is_set() and not task.cancelled]
        return max(deadlines, default=0.0)

    def accepted_input(self, name):
        key = fingerprint(self.inputs[name])
        with self.service._condition:
            record = self.service._accepted.get(key)
            if record is not None: self.service._accepted.move_to_end(key)
            return record

    def provider(self, role):
        declared = self.task.spec.command.required_providers | self.task.spec.command.optional_providers
        if role not in declared: raise ExecutionFailure("provider.undeclared:" + role)
        return self.service.resolve_provider(role)

    def checkpoint(self):
        self.budget.checkpoint()
        if self.service.state == "failed": raise ExecutionFailure("execution.coordinator_failed")
        if self.run.journal_failed: raise ExecutionFailure("journal.publication_failed")
        if self.run.deadline is not None and monotonic() >= self.run.deadline and not self.service._producer_needed(self.task):
            raise ExecutionFailure("execution.deadline", outcome="cancelled")
        # A shared producer is cancelled only when all its consumers detach.
        if (self.run.cancel.is_set() or self.task.cancelled) and not self.service._producer_needed(self.task):
            raise ExecutionFailure("execution.cancelled", outcome="cancelled")

    def check_cancelled(self):
        self.checkpoint()

    def use(self, evidence):
        self.evidence.append(evidence)

    def effect(self, kind, effect_id, action, *, reconcile=None, resource=None, intent=None):
        if kind not in self.task.spec.command.effects:
            raise ExecutionFailure("effect.undeclared:" + kind)
        try:
            receipt = self.service._effect(self, kind, effect_id, action, reconcile, resource, intent)
        finally:
            self._active_effects.discard(effect_id)
        self.effect_receipts[effect_id] = receipt
        return receipt

    def update_effect_intent(self, effect_id, intent):
        """Seal newly observed exact bytes before the current effect commits them."""
        if effect_id not in self._active_effects: raise ExecutionFailure("effect.inactive_authority")
        with self.service._condition:
            self.checkpoint()
            previous = self.service.lookup_effect(effect_id)
            if previous is None or previous.status != "unknown": raise ExecutionFailure("effect.intent_already_settled")
            self.service._save_effect(replace(previous, intent=intent))
            self.service._fact(self.run, "effect.intent_updated", self.task, effect_id=effect_id, effect_kind=previous.kind)
