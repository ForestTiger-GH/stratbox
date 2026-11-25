"""Reusable exact operation scenarios and frozen scenario membership.

These builders describe dataflow only. They never select a publisher parser,
infer an economic relationship or execute work while authoring a graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

from stratbox.capabilities.model import (
    AcceptanceContract, Call, CapabilityRef, CascadeDefinition,
    CollectionMembership, GraphBody, InputRef, OutputRef, ParameterRef,
    ScenarioDefinition,
)
from stratbox.capabilities.model.graph import frozen_mapping
from stratbox.shared.identifiers import safe_token


def operation_scenario(snapshot, operation_id, *, scenario_id=None,
                       method_id=None, profile_id=None, group_id=None,
                       parameters=None, selection=None):
    """Expose one exact functional transition as an independently useful task.

    All ports, semantic qualifications, fixed conditions and completion effects
    remain those of the resolved operation. Applications can use the same
    returned definition in several cascades; occurrences stay independent.
    """
    binding = snapshot.resolve(operation_id, method_id=method_id,
        profile_id=profile_id, group_id=group_id, parameters=parameters,
        selection=selection)
    operation = binding.definition
    if operation.kind != "operation":
        raise ValueError("workflow.operation_required")
    identifier = scenario_id or "scenario." + operation_id
    names = set(binding.parameters) | set(operation.required_parameters)
    call = Call("execute", operation_id,
        {name: InputRef(name) for name in operation.inputs},
        {name: ParameterRef(name) for name in names},
        method_id=binding.method.method_id if binding.method else None,
        profile_id=binding.profile.profile_id if binding.profile else None,
        group_id=binding.group.group_id if binding.group else None,
        selection=binding.selection,
        reference=CapabilityRef(operation.id, operation.revision, operation.fingerprint),
        binding_identities=binding.identities)
    return ScenarioDefinition(identifier, GraphBody((call,),
        {name: OutputRef("execute", name) for name in operation.outputs},
        required_effects=("execute",) if operation.effects else ()),
        inputs=operation.inputs, outputs=operation.outputs,
        parameters=binding.parameters,
        required_parameters=tuple(name for name in operation.required_parameters
                                  if name not in binding.parameters),
        fixed=operation.fixed, effects=operation.effects,
        acceptance=operation.acceptance,
        purpose=operation.summary or "Execute " + operation_id + " with its exact completion contract.")


@dataclass(frozen=True, slots=True)
class ScenarioMember:
    """A pinned definition and source selection, separate from runtime values."""
    name: str
    reference: CapabilityRef
    selection: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    required: bool = True

    def __post_init__(self):
        safe_token(self.name)
        if not self.name.isidentifier() or self.name.startswith("_"):
            raise ValueError("workflow.member_name_invalid")
        if not isinstance(self.reference, CapabilityRef) or type(self.required) is not bool:
            raise ValueError("workflow.member_invalid")
        object.__setattr__(self, "selection", frozen_mapping(self.selection))
        object.__setattr__(self, "parameters", frozen_mapping(self.parameters))


def scenario_members(snapshot, *, capability_ids=None, query=None, required=True,
                     selection=None):
    """Freeze catalog membership once; later catalog additions cannot widen it."""
    if capability_ids is not None and query is not None:
        raise ValueError("workflow.selector_conflict")
    if capability_ids is None:
        definitions = tuple(item for item in snapshot.scenarios
                            if query is None or query.casefold() in item.capability_id.casefold())
    else:
        identifiers = tuple(capability_ids)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("workflow.duplicate_selection")
        definitions = tuple(snapshot.definition(identifier) for identifier in identifiers)
    if not definitions or any(item.kind != "scenario" for item in definitions):
        raise ValueError("workflow.scenario_selection_required")
    return tuple(ScenarioMember("member_" + str(index),
        CapabilityRef(item.capability_id, item.revision, item.fingerprint),
        selection=selection or {}, required=required)
        for index, item in enumerate(definitions))


def cascade_definition(snapshot, cascade_id, members, *, coherent=False,
                       policy="continue"):
    """Coordinate references without inventing a cross-source calculation.

    Namespaced ports carry the actual inputs, so the prepared plan pins their
    version vector through ordinary value admission. ``coherent`` adds a
    whole-release barrier; otherwise independently accepted outputs are usable
    before an unrelated member completes. Optional member failure does not
    discharge or invalidate the required members' obligations.
    """
    members = tuple(members)
    if not members or any(not isinstance(item, ScenarioMember) for item in members):
        raise ValueError("workflow.members_required")
    if len({item.name for item in members}) != len(members):
        raise ValueError("workflow.duplicate_member")
    if type(coherent) is not bool:
        raise ValueError("workflow.coherence_invalid")
    calls, inputs, outputs, references, defaults, required_parameters = [], {}, {}, {}, {}, []
    effects, required_calls, coherent_outputs = set(), [], []
    for member in members:
        definition = snapshot.definition(member.reference.capability_id)
        if definition.kind != "scenario":
            raise ValueError("workflow.scenario_required")
        if ((member.reference.revision is not None and member.reference.revision != definition.revision)
                or (member.reference.fingerprint is not None and member.reference.fingerprint != definition.fingerprint)):
            raise ValueError("workflow.definition_changed")
        binding = snapshot.resolve(definition.capability_id,
            parameters=member.parameters, selection=member.selection)
        prefix = member.name + "__"
        for name, port in definition.inputs.items():
            inputs[prefix + name] = port
        names = set(binding.parameters) | set(definition.required_parameters)
        for name in names:
            if name in binding.parameters:
                defaults[prefix + name] = binding.parameters[name]
            else:
                required_parameters.append(prefix + name)
        calls.append(Call(member.name, definition.capability_id,
            {name: InputRef(prefix + name) for name in definition.inputs},
            {name: ParameterRef(prefix + name) for name in names},
            selection=member.selection, required=member.required,
            reference=CapabilityRef(definition.id, definition.revision, definition.fingerprint),
            binding_identities=binding.identities))
        for name, port in definition.outputs.items():
            outputs[prefix + name] = port if member.required else replace(port, required=False)
            references[prefix + name] = OutputRef(member.name, name)
            if member.required and port.required:
                coherent_outputs.append(prefix + name)
        effects.update(definition.effects)
        if member.required:
            required_calls.append(member.name)
    names = tuple(item.name for item in members)
    required = frozenset(item.name for item in members if item.required)
    return CascadeDefinition(cascade_id,
        GraphBody(tuple(calls), references, required_completions=tuple(required_calls)),
        inputs=inputs, outputs=outputs, parameters=defaults,
        required_parameters=tuple(sorted(required_parameters)),
        effects=frozenset(effects), policy=policy,
        acceptance=AcceptanceContract(coherent_outputs=tuple(coherent_outputs) if coherent else (),
                                      partial_allowed=any(not item.required for item in members)),
        membership=CollectionMembership(names, True, required, frozenset(names)))
