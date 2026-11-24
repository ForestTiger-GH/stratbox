"""Pure domain contributions and explicit specialization bindings."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping

from stratbox.shared.identifiers import safe_token
from stratbox.capabilities.model import CapabilityDefinition, GraphBody, declaration_fingerprint
from stratbox.capabilities.model.graph import frozen_mapping


@dataclass(frozen=True, slots=True)
class MethodDefinition:
    method_id: str
    operation_id: str
    body: GraphBody
    revision: str = "1"
    group_ids: tuple[str, ...] = ()
    profile_ids: tuple[str, ...] = ()
    defaults: Mapping[str, object] = field(default_factory=dict)
    fixed: Mapping[str, object] = field(default_factory=dict)
    selection: Mapping[str, object] = field(default_factory=dict)
    priority: int = 0

    def __post_init__(self):
        safe_token(self.method_id)
        safe_token(self.operation_id)
        if not isinstance(self.body, GraphBody) or not self.revision or type(self.priority) is not int:
            raise ValueError("catalog.invalid_method")
        for name in ("defaults", "fixed", "selection"):
            object.__setattr__(self, name, frozen_mapping(getattr(self, name)))

    @property
    def fingerprint(self):
        return declaration_fingerprint(self)


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    profile_id: str
    data: Mapping[str, object]
    revision: str = "1"
    method_id: str | None = None
    group_id: str | None = None

    def __post_init__(self):
        safe_token(self.profile_id)
        if not self.revision:
            raise ValueError("catalog.profile_revision_required")
        object.__setattr__(self, "data", frozen_mapping(self.data))

    @property
    def fingerprint(self):
        return declaration_fingerprint(self)


@dataclass(frozen=True, slots=True)
class ProcessingGroup:
    group_id: str
    source_ids: tuple[str, ...] = ()
    representations: tuple[str, ...] = ()
    editions: tuple[str, ...] = ()
    methods: Mapping[str, str] = field(default_factory=dict)
    profiles: Mapping[str, str] = field(default_factory=dict)
    defaults: Mapping[str, object] = field(default_factory=dict)
    fixed: Mapping[str, object] = field(default_factory=dict)
    selection: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        safe_token(self.group_id)
        for name in ("methods", "profiles", "defaults", "fixed", "selection"):
            object.__setattr__(self, name, frozen_mapping(getattr(self, name)))

    def applies(self, selection):
        selection = dict(selection or {})
        for name, options in (("source_id", self.source_ids), ("representation", self.representations), ("edition", self.editions)):
            if options and selection.get(name) not in options:
                return False
        return all(selection.get(key) == value for key, value in self.selection.items())


@dataclass(frozen=True, slots=True)
class RecipeDefinition:
    recipe_id: str
    goal: str
    capability_id: str
    selection: Mapping[str, object] = field(default_factory=dict)
    defaults: Mapping[str, object] = field(default_factory=dict)
    priority: int = 0

    def __post_init__(self):
        for value in (self.recipe_id, self.goal, self.capability_id):
            safe_token(value)
        object.__setattr__(self, "selection", frozen_mapping(self.selection))
        object.__setattr__(self, "defaults", frozen_mapping(self.defaults))


@dataclass(frozen=True, slots=True)
class SchemaDefinition:
    schema_id: str
    revision: str = "1"
    data: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        safe_token(self.schema_id)
        object.__setattr__(self, "data", frozen_mapping(self.data))

    @property
    def fingerprint(self):
        return declaration_fingerprint(self)


@dataclass(frozen=True, slots=True)
class ReferenceDefinition:
    reference_id: str
    revision: str
    fingerprint: str

    def __post_init__(self):
        safe_token(self.reference_id)
        if not self.revision or not self.fingerprint:
            raise ValueError("catalog.reference_identity_required")


@dataclass(frozen=True, slots=True)
class CatalogContribution:
    definitions: tuple[CapabilityDefinition, ...] = ()
    methods: tuple[MethodDefinition, ...] = ()
    profiles: tuple[ProfileDefinition, ...] = ()
    groups: tuple[ProcessingGroup, ...] = ()
    recipes: tuple[RecipeDefinition, ...] = ()
    schemas: tuple[SchemaDefinition, ...] = ()
    references: tuple[ReferenceDefinition, ...] = ()
