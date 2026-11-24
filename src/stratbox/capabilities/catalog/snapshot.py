"""Immutable canonical catalog and deterministic specialization resolver."""
from __future__ import annotations

from dataclasses import dataclass, field
from json import dumps
from types import MappingProxyType
from typing import Mapping
from types import SimpleNamespace

from stratbox.capabilities.model import (
    CapabilityDefinition, CommandDefinition, OperationDefinition, ScenarioDefinition,
    CascadeDefinition, GraphBody, InputRef, OutputRef, ParameterRef, Call, CollectCall, MapCall, PortContract,
    declaration_fingerprint, declaration_tree,
)
from stratbox.capabilities.model.graph import MethodSlot, frozen_mapping
from .descriptors import (
    CatalogContribution, MethodDefinition, ProfileDefinition, ProcessingGroup,
    RecipeDefinition, ReferenceDefinition, SchemaDefinition,
)


class CatalogError(ValueError):
    @property
    def code(self):
        return self.args[0]


def _index(items, field_name, kind):
    if not isinstance(items, tuple) or any(not isinstance(item, kind) for item in items):
        raise CatalogError("catalog.invalid_contribution")
    result = {getattr(item, field_name): item for item in items}
    if len(result) != len(items):
        raise CatalogError("catalog.duplicate_identity")
    return MappingProxyType(result)


def _walk_refs(value):
    if isinstance(value, (InputRef, OutputRef, ParameterRef)):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_refs(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk_refs(item)


@dataclass(frozen=True, slots=True)
class ResolvedBinding:
    definition: CapabilityDefinition
    body: GraphBody | None
    parameters: Mapping[str, object]
    method: MethodDefinition | None = None
    profile: ProfileDefinition | None = None
    group: ProcessingGroup | None = None
    identities: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "parameters", frozen_mapping(self.parameters))
        object.__setattr__(self, "identities", frozen_mapping(self.identities))


@dataclass(frozen=True, slots=True)
class Readiness:
    capability_id: str
    metadata: bool
    typed: bool
    executable: bool
    machine: bool
    missing: tuple[str, ...] = ()


class CatalogView:
    __slots__ = ("snapshot", "kind")

    def __init__(self, snapshot, kind):
        self.snapshot, self.kind = snapshot, kind

    def __iter__(self):
        return iter(self.list())

    def __len__(self):
        return sum(item.kind == self.kind for item in self.snapshot.definitions)

    def list(self):
        return tuple(item for item in self.snapshot.definitions if item.kind == self.kind)

    def get(self, capability_id):
        definition = self.snapshot.definition(capability_id)
        if definition.kind != self.kind:
            raise CatalogError("catalog.kind_mismatch")
        return definition

    def describe(self, capability_id):
        self.get(capability_id)
        return self.snapshot.describe(capability_id)


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    definitions: tuple[CapabilityDefinition, ...] = ()
    methods: tuple[MethodDefinition, ...] = ()
    profiles: tuple[ProfileDefinition, ...] = ()
    groups: tuple[ProcessingGroup, ...] = ()
    recipes: tuple[RecipeDefinition, ...] = ()
    schemas: tuple[SchemaDefinition, ...] = ()
    references: tuple[ReferenceDefinition, ...] = ()
    _definitions: Mapping = field(init=False, repr=False, compare=False)
    _methods: Mapping = field(init=False, repr=False, compare=False)
    _profiles: Mapping = field(init=False, repr=False, compare=False)
    _groups: Mapping = field(init=False, repr=False, compare=False)
    _recipes: Mapping = field(init=False, repr=False, compare=False)
    _schemas: Mapping = field(init=False, repr=False, compare=False)
    _references: Mapping = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        for plural, key, kind in (
            ("definitions", "capability_id", CapabilityDefinition),
            ("methods", "method_id", MethodDefinition), ("profiles", "profile_id", ProfileDefinition),
            ("groups", "group_id", ProcessingGroup), ("recipes", "recipe_id", RecipeDefinition),
            ("schemas", "schema_id", SchemaDefinition), ("references", "reference_id", ReferenceDefinition),
        ):
            object.__setattr__(self, "_" + plural, _index(getattr(self, plural), key, kind))
        self.validate()

    @classmethod
    def from_contributions(cls, *contributions):
        if any(not isinstance(item, CatalogContribution) for item in contributions):
            raise CatalogError("catalog.invalid_contribution")
        return cls(**{name: tuple(value for item in contributions for value in getattr(item, name))
                      for name in ("definitions", "methods", "profiles", "groups", "recipes", "schemas", "references")})

    @property
    def commands(self):
        return CatalogView(self, "command")

    @property
    def operations(self):
        return CatalogView(self, "operation")

    @property
    def scenarios(self):
        return CatalogView(self, "scenario")

    @property
    def cascades(self):
        return CatalogView(self, "cascade")

    @property
    def fingerprint(self):
        return declaration_fingerprint({name: getattr(self, name) for name in
            ("definitions", "methods", "profiles", "groups", "recipes", "schemas", "references")})

    def definition(self, capability_id):
        try:
            return self._definitions[capability_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.capability_unavailable") from None

    def method(self, method_id):
        try:
            return self._methods[method_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.method_unavailable") from None

    def profile(self, profile_id):
        try:
            return self._profiles[profile_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.profile_unavailable") from None

    def group(self, group_id):
        try:
            return self._groups[group_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.group_unavailable") from None

    def schema(self, schema_id):
        try:
            return self._schemas[schema_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.schema_unavailable") from None

    def reference(self, reference_id):
        try:
            return self._references[reference_id]
        except (KeyError, TypeError):
            raise CatalogError("catalog.reference_unavailable") from None

    def describe(self, capability_id):
        value = self.definition(capability_id)
        return {**declaration_tree(value), "fingerprint": value.fingerprint}

    def metadata_index(self):
        return {"version": 1, "catalog_fingerprint": self.fingerprint,
                "capabilities": [self.describe(item.capability_id) for item in sorted(self.definitions, key=lambda item: item.capability_id)]}

    def check_index(self, projection):
        if projection != self.metadata_index():
            raise CatalogError("catalog.stale_metadata_index")

    def overlay(self, *contributions, replace_ids=()):
        """Explicit replacements and additions pass the same whole-catalog admission."""
        if any(not isinstance(item, CatalogContribution) for item in contributions):
            raise CatalogError("catalog.invalid_contribution")
        replace_ids = frozenset(replace_ids)
        if not replace_ids <= self._definitions.keys():
            raise CatalogError("catalog.overlay_unknown_replacement")
        names = ("definitions", "methods", "profiles", "groups", "recipes", "schemas", "references")
        values = {name: tuple(item for item in getattr(self, name)
                    if name != "definitions" or item.capability_id not in replace_ids)
                    + tuple(value for contribution in contributions for value in getattr(contribution, name))
                  for name in names}
        if not replace_ids <= {item.capability_id for item in values["definitions"]}:
            raise CatalogError("catalog.overlay_replacement_missing")
        return CatalogSnapshot(**values)

    def _declared_effects(self, definition, visited=None):
        """Inspect declared physical effects rather than trusting a scope label."""
        visited = set() if visited is None else visited
        if definition.capability_id in visited:
            return frozenset()
        visited.add(definition.capability_id)
        if isinstance(definition, CommandDefinition):
            return definition.effects
        body = getattr(definition, "body", None)
        bodies = (body,) if body is not None else tuple(method.body for method in self.methods
            if method.operation_id == definition.capability_id)
        return frozenset(effect for candidate in bodies for step in candidate.steps
            if hasattr(step, "capability_id")
            for effect in self._declared_effects(self.definition(step.capability_id), visited))

    def _validate_body(self, owner, body):
        if not isinstance(body, GraphBody):
            raise CatalogError("catalog.body_required")
        allowed = {"operation": {"command"}, "scenario": {"operation", "scenario"}, "cascade": {"scenario"}}[owner.kind]
        steps = {step.step_id: step for step in body.steps}
        children = {}
        for step in body.steps:
            if isinstance(step, CollectCall):
                children[step.step_id] = SimpleNamespace(inputs={}, outputs={"value": step.contract}, effects=frozenset())
            elif isinstance(step, MapCall):
                child = self.definition(step.capability_id)
                if child.kind not in allowed or child.kind != "scenario":
                    raise CatalogError("catalog.invalid_map_body_kind")
                if step.item_input not in child.inputs or step.item_input in step.inputs:
                    raise CatalogError("catalog.invalid_map_item_input")
                if not set(step.inputs) <= child.inputs.keys():
                    raise CatalogError("catalog.unknown_input_port")
                if set(child.outputs) != {"value"}:
                    raise CatalogError("catalog.map_value_output_required")
                element = child.outputs["value"]
                contract = step.contract or PortContract(element.schema, value_type=object, collection=True,
                    qualifications=element.qualifications, expected_coverage=element.expected_coverage)
                children[step.step_id] = SimpleNamespace(inputs=child.inputs, outputs={"value": contract}, effects=child.effects)
            else:
                child = self.definition(step.capability_id)
                children[step.step_id] = child
                if child.kind not in allowed:
                    raise CatalogError("catalog.invalid_body_kind")
                if not set(step.inputs) <= child.inputs.keys():
                    raise CatalogError("catalog.unknown_input_port")
            if not set(step.depends_on) <= steps.keys():
                raise CatalogError("catalog.unknown_dependency")
        dependencies = {step.step_id: set(step.depends_on) for step in body.steps}
        for step in body.steps:
            condition = getattr(step, "condition", None)
            if condition is not None:
                if condition.step not in steps:
                    raise CatalogError("catalog.unknown_condition_step")
                dependencies[step.step_id].add(condition.step)
            values = (step.inputs, getattr(step, "parameters", {}), getattr(step, "items", None))
            for ref in _walk_refs(values):
                if isinstance(ref, InputRef) and ref.name not in owner.inputs:
                    raise CatalogError("catalog.unknown_graph_input")
                if isinstance(ref, OutputRef):
                    if ref.step not in children or ref.port not in children[ref.step].outputs:
                        raise CatalogError("catalog.unknown_output_port")
                    dependencies[step.step_id].add(ref.step)
            if isinstance(step, CollectCall):
                for ref in step.inputs:
                    producer_step = steps[ref.step]
                    producer_contract = (self.definition(producer_step.capability_id).outputs["value"]
                        if isinstance(producer_step, MapCall) else children[ref.step].outputs[ref.port])
                    if not step.element_contract.compatible_with(producer_contract):
                        raise CatalogError("catalog.collection_element_contract_mismatch")
                continue
            for name, value in step.inputs.items():
                if isinstance(value, OutputRef) and not children[step.step_id].inputs[name].compatible_with(children[value.step].outputs[value.port]):
                    raise CatalogError("catalog.port_contract_mismatch")
                if isinstance(value, InputRef) and not children[step.step_id].inputs[name].compatible_with(owner.inputs[value.name]):
                    raise CatalogError("catalog.port_contract_mismatch")
        if owner.kind == "operation":
            effects = frozenset(effect for child in children.values() for effect in child.effects)
            if not effects <= owner.effects:
                raise CatalogError("catalog.method_effect_escalation")
        if set(body.outputs) != set(owner.outputs):
            raise CatalogError("catalog.body_output_contract_mismatch")
        for roots in (owner.acceptance.required_checks, owner.acceptance.required_effects):
            if not set(roots) <= steps.keys():
                raise CatalogError("catalog.unknown_acceptance_root")
        effect_roots = (*body.required_effects, *owner.acceptance.required_effects)
        for name in effect_roots:
            step = steps[name]
            if not hasattr(step, "capability_id") or not self._declared_effects(self.definition(step.capability_id)):
                raise CatalogError("catalog.required_effect_without_effect")
        if isinstance(owner, CascadeDefinition) and owner.membership.closed:
            scenario_members = {step.step_id for step in body.steps if not isinstance(step, CollectCall)}
            if set(owner.membership.members) != scenario_members:
                raise CatalogError("catalog.cascade_membership_mismatch")
        for ref in _walk_refs(body.outputs):
            if isinstance(ref, InputRef) and ref.name not in owner.inputs:
                raise CatalogError("catalog.unknown_graph_input")
            if isinstance(ref, OutputRef) and (ref.step not in children or ref.port not in children[ref.step].outputs):
                raise CatalogError("catalog.unknown_output_port")
        for name, value in body.outputs.items():
            if isinstance(value, OutputRef):
                if not owner.outputs[name].compatible_with(children[value.step].outputs[value.port]):
                    raise CatalogError("catalog.port_contract_mismatch")
        visited, visiting = set(), set()
        def visit(name):
            if name in visiting:
                raise CatalogError("catalog.graph_cycle")
            if name in visited:
                return
            visiting.add(name)
            for dep in dependencies[name]:
                visit(dep)
            visiting.remove(name)
            visited.add(name)
        for name in steps:
            visit(name)

    def validate(self):
        for definition in self.definitions:
            if isinstance(definition, CommandDefinition):
                continue
            if not isinstance(definition, (OperationDefinition, ScenarioDefinition, CascadeDefinition)):
                raise CatalogError("catalog.invalid_definition_kind")
            if definition.body is not None:
                self._validate_body(definition, definition.body)
        for method in self.methods:
            owner = self.definition(method.operation_id)
            if not isinstance(owner, OperationDefinition) or owner.method_slot is None:
                raise CatalogError("catalog.method_slot_unavailable")
            self._validate_body(owner, method.body)
            used_effects = frozenset(effect for step in method.body.steps if hasattr(step, "capability_id") for effect in self.definition(step.capability_id).effects)
            allowed_effects = owner.effects
            if isinstance(owner.method_slot, MethodSlot):
                allowed_effects &= owner.method_slot.allowed_effects
            if not used_effects <= allowed_effects:
                raise CatalogError("catalog.method_effect_escalation")
            if not set(method.group_ids) <= self._groups.keys() or not set(method.profile_ids) <= self._profiles.keys():
                raise CatalogError("catalog.stale_method_binding")
        for profile in self.profiles:
            if profile.method_id is not None:
                self.method(profile.method_id)
            if profile.group_id is not None:
                self.group(profile.group_id)
        for group in self.groups:
            for operation_id, method_id in group.methods.items():
                method = self.method(method_id)
                if method.operation_id != operation_id:
                    raise CatalogError("catalog.group_method_mismatch")
            for operation_id, profile_id in group.profiles.items():
                self.definition(operation_id)
                self.profile(profile_id)
        for recipe in self.recipes:
            self.definition(recipe.capability_id)
        # Detect recursive scenario definitions independently of step graph cycles.
        visiting, visited = set(), set()
        def visit(identifier):
            if identifier in visiting:
                raise CatalogError("catalog.definition_cycle")
            if identifier in visited:
                return
            visiting.add(identifier)
            body = getattr(self.definition(identifier), "body", None)
            for step in body.steps if body else ():
                if hasattr(step, "capability_id"):
                    visit(step.capability_id)
            visiting.remove(identifier)
            visited.add(identifier)
        for definition in self.definitions:
            visit(definition.capability_id)
        return self

    def resolve(self, capability_id, *, method_id=None, profile_id=None, group_id=None, parameters=None, selection=None):
        definition = self.definition(capability_id)
        selection = dict(selection or {})
        group = self.group(group_id) if group_id is not None else None
        if group is None and selection:
            groups = [item for item in self.groups if item.applies(selection)]
            if len(groups) > 1:
                raise CatalogError("catalog.ambiguous_group")
            group = groups[0] if groups else None
        # An explicit profile may identify its group. Apply exactly the same
        # applicability and fixed-condition checks to inferred and explicit groups.
        if profile_id is None and group is not None:
            profile_id = group.profiles.get(capability_id)
        profile = self.profile(profile_id) if profile_id else None
        if profile and group is None and profile.group_id:
            group = self.group(profile.group_id)
        if group is not None and selection and not group.applies(selection):
            raise CatalogError("catalog.group_inapplicable")
        if profile:
            if group and profile.group_id and profile.group_id != group.group_id:
                raise CatalogError("catalog.profile_group_mismatch")
            if method_id and profile.method_id and profile.method_id != method_id:
                raise CatalogError("catalog.profile_method_mismatch")
            method_id = method_id or profile.method_id
        if group:
            method_id = method_id or group.methods.get(capability_id)
        method = None
        body = getattr(definition, "body", None)
        if isinstance(definition, OperationDefinition) and definition.method_slot is not None:
            if method_id:
                method = self.method(method_id)
                if method.operation_id != capability_id:
                    raise CatalogError("catalog.method_operation_mismatch")
                candidates = [method]
            else:
                candidates = [item for item in self.methods if item.operation_id == capability_id]
            candidates = [item for item in candidates
                if (not item.group_ids or group and group.group_id in item.group_ids)
                and (not item.profile_ids or profile and profile.profile_id in item.profile_ids)
                and all(selection.get(key) == value for key, value in item.selection.items())]
            if not candidates:
                raise CatalogError("catalog.method_inapplicable")
            best = max(item.priority for item in candidates)
            candidates = [item for item in candidates if item.priority == best]
            if len(candidates) != 1:
                raise CatalogError("catalog.ambiguous_method")
            method = candidates[0]
            body = method.body
        elif method_id is not None:
            raise CatalogError("catalog.method_slot_unavailable")
        fixed = {}
        values = dict(definition.parameters)
        for item in (group, method):
            if item:
                values.update(item.defaults)
        if profile:
            values["profile"] = profile.data
        for item in (definition, group, method):
            if item:
                for key, value in item.fixed.items():
                    if key in fixed and fixed[key] != value:
                        raise CatalogError("catalog.conflicting_fixed_parameter")
                    fixed[key] = value
        if parameters is not None and not isinstance(parameters, Mapping):
            raise CatalogError("catalog.parameters_mapping_required")
        supplied = dict(parameters or {})
        allowed_parameters = set(definition.parameters) | set(definition.fixed) | set(definition.required_parameters)
        for item in (group, method):
            if item:
                allowed_parameters.update(item.defaults)
                allowed_parameters.update(item.fixed)
        if profile:
            allowed_parameters.add("profile")
        if set(supplied) - allowed_parameters:
            raise CatalogError("catalog.parameter_unknown")
        if any(key in fixed and value != fixed[key] for key, value in supplied.items()):
            raise CatalogError("catalog.fixed_parameter_override")
        if profile and "profile" in supplied and supplied["profile"] != profile.data:
            raise CatalogError("catalog.profile_override")
        values.update(supplied)
        values.update(fixed)
        identities = {"definition": definition.fingerprint}
        if method:
            identities["method"] = method.fingerprint
        if profile:
            identities["profile"] = profile.fingerprint
        for schema in self.schemas:
            identities["schema:" + schema.schema_id] = schema.fingerprint
        for reference in self.references:
            identities["reference:" + reference.reference_id] = reference.fingerprint
        return ResolvedBinding(definition, body, values, method, profile, group, identities)

    def resolve_goal(self, goal, *, selection=None, recipe_id=None):
        selection = dict(selection or {})
        candidates = [item for item in self.recipes if item.goal == goal
                      and (recipe_id is None or item.recipe_id == recipe_id)
                      and all(selection.get(key) == value for key, value in item.selection.items())]
        if not candidates:
            raise CatalogError("catalog.recipe_unavailable")
        best = max(item.priority for item in candidates)
        candidates = [item for item in candidates if item.priority == best]
        if len(candidates) != 1:
            raise CatalogError("catalog.ambiguous_recipe")
        return candidates[0]

    def readiness(self, capability_id, *, implementations=(), machine_ids=()):
        definition = self.definition(capability_id)
        implementations = frozenset(implementations)
        needed = set()
        visited = set()
        def visit(value):
            if value.capability_id in visited:
                return
            visited.add(value.capability_id)
            if isinstance(value, CommandDefinition):
                if value.implementation_ref not in implementations:
                    needed.add(value.implementation_ref)
                return
            bodies = [value.body] if value.body else [item.body for item in self.methods if item.operation_id == value.capability_id]
            if not bodies:
                needed.add("method:" + value.capability_id)
            for body in bodies:
                for step in body.steps:
                    if hasattr(step, "capability_id"):
                        visit(self.definition(step.capability_id))
        visit(definition)
        return Readiness(capability_id, True, True, not needed, not needed and capability_id in machine_ids, tuple(sorted(needed)))
