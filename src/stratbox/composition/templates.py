"""Typed method slots specialize a declared scenario without copying its graph."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping
from .models import (
    CompositionError, OperationStep, ScenarioDefinition, ScenarioStep,
    _mapping, _name,
)


@dataclass(frozen=True, slots=True)
class TemplateSlot:
    name: str
    step_id: str
    fixed_parameters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        _name(self.name)
        _name(self.step_id)
        object.__setattr__(self, "fixed_parameters", _mapping(self.fixed_parameters))


@dataclass(frozen=True, slots=True)
class TemplateDefinition:
    template_id: str
    scenario: ScenarioDefinition
    slots: tuple[TemplateSlot, ...]

    def __post_init__(self):
        _name(self.template_id)
        if not isinstance(self.scenario, ScenarioDefinition) or not isinstance(self.slots, tuple) or any(not isinstance(slot, TemplateSlot) for slot in self.slots):
            raise CompositionError("composition.invalid_template")
        if len({slot.name for slot in self.slots}) != len(self.slots) or len({slot.step_id for slot in self.slots}) != len(self.slots):
            raise CompositionError("composition.duplicate_slot")
        operations = {step.step_id for step in self.scenario.steps if isinstance(step, OperationStep)}
        if any(slot.step_id not in operations for slot in self.slots):
            raise CompositionError("composition.slot_unknown")


def bind_template(template, bindings, *, parameters=None, scenario_id=None):
    """Substitute an operation or an explicit subgraph at each selected slot.

    Subgraphs expose the same named inputs/outputs as the replaced operation.
    Contract validation belongs to compilation against the actual catalog.
    Fixed source/template parameters are invariants, not last-writer wins.
    """
    if not isinstance(template, TemplateDefinition):
        raise CompositionError("composition.template_required")
    slots = {slot.name: slot for slot in template.slots}
    if set(bindings) - set(slots) or set(parameters or {}) - set(slots):
        raise CompositionError("composition.slot_unknown")
    selected = {slot.step_id: slot for slot in template.slots}
    steps = []
    for original in template.scenario.steps:
        slot = selected.get(original.step_id)
        if slot is None:
            steps.append(original)
            continue
        replacement = bindings.get(slot.name, original.operation_id)
        values = dict(original.parameters)
        values.update((parameters or {}).get(slot.name, {}))
        for name, value in slot.fixed_parameters.items():
            if name in values and values[name] != value:
                raise CompositionError("composition.fixed_parameter_conflict")
            values[name] = value
        if isinstance(replacement, str):
            steps.append(replace(original, operation_id=replacement, parameters=values))
        elif isinstance(replacement, ScenarioDefinition):
            child_inputs = {**original.inputs, **values}
            if set(child_inputs) != set(replacement.inputs):
                raise CompositionError("composition.slot_inputs_mismatch")
            if original.condition is not None or original.share_key is not None:
                raise CompositionError("composition.subgraph_policy_requires_explicit_steps")
            steps.append(ScenarioStep(original.step_id, replacement, child_inputs, original.depends_on, original.required))
        else:
            raise CompositionError("composition.invalid_slot_binding")
    return replace(template.scenario, scenario_id=scenario_id or template.scenario.scenario_id, steps=tuple(steps))
