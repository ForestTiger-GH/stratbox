"""Uniform source metadata and qualified operation support projections."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import ProcessingStage


@dataclass(frozen=True, slots=True)
class SourceProfile:
    profile_id: str
    kind: str
    formats: tuple[str, ...] = ()
    scope: str = ""

    def __post_init__(self):
        safe_token(self.profile_id)
        if (not isinstance(self.kind, str) or not self.kind
                or not isinstance(self.scope, str) or not isinstance(self.formats, tuple)
                or any(not isinstance(value, str) or not value for value in self.formats)
                or len(set(self.formats)) != len(self.formats)):
            raise ValueError("catalog.profile_invalid")


@dataclass(frozen=True, slots=True)
class SourceOperation:
    operation_id: str
    state: str = "supported"
    reason: str = ""
    parameters: tuple[tuple[str, str], ...] = ()
    formats: tuple[str, ...] = ()
    identity_parameter: str | None = None
    auxiliary_sources: tuple[tuple[str, tuple[str, ...]], ...] = ()
    context_scope: str = "source"

    def __post_init__(self):
        safe_token(self.operation_id)
        if (self.context_scope not in {"source", "family", "catalog"}
                or self.state not in {"supported", "conditional", "delegated"}
                or not isinstance(self.reason, str) or self.state != "supported" and not self.reason
                or not isinstance(self.parameters, tuple) or any(not isinstance(p, tuple)
                    or len(p) != 2 or any(type(v) is not str for v in p) for p in self.parameters)
                or len({k for k, _ in self.parameters}) != len(self.parameters)
                or not isinstance(self.formats, tuple) or any(not isinstance(f, str) or not f for f in self.formats)
                or len(set(self.formats)) != len(self.formats)
                or self.identity_parameter is not None and (
                    not isinstance(self.identity_parameter, str) or not self.identity_parameter.isidentifier())
                or not isinstance(self.auxiliary_sources, tuple)
                or any(not isinstance(p, tuple) or len(p) != 2 or not isinstance(p[0], str)
                       or not isinstance(p[1], tuple) or not p[1] for p in self.auxiliary_sources)
                or len({p[0] for p in self.auxiliary_sources}) != len(self.auxiliary_sources)):
            raise ValueError("catalog.source_binding_invalid")
        for port, identities in self.auxiliary_sources:
            safe_token(port)
            if len(set(identities)) != len(identities):
                raise ValueError("catalog.source_binding_invalid")
            for identity in identities:
                safe_token(identity)


@dataclass(frozen=True, slots=True)
class SourceCard:
    publisher_id: str
    family_id: str
    series_id: str
    title: str
    issue_model: str
    formats: tuple[str, ...]
    profiles: tuple[SourceProfile, ...] = ()
    operations: tuple[SourceOperation, ...] = ()
    qualifications: tuple[str, ...] = ()

    def __post_init__(self):
        for value in (self.publisher_id, self.family_id, self.series_id):
            safe_token(value)
        if (not isinstance(self.title, str) or not self.title or not isinstance(self.issue_model, str)
                or not self.issue_model or not isinstance(self.formats, tuple) or not self.formats
                or any(not isinstance(value, str) or not value for value in self.formats)
                or len(set(self.formats)) != len(self.formats)
                or not isinstance(self.profiles, tuple) or any(not isinstance(p, SourceProfile) for p in self.profiles)
                or not isinstance(self.operations, tuple) or any(not isinstance(p, SourceOperation) for p in self.operations)
                or len({o.operation_id for o in self.operations}) != len(self.operations)
                or not isinstance(self.qualifications, tuple) or any(type(q) is not str for q in self.qualifications)):
            raise ValueError("catalog.source_card_invalid")


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    sources: tuple[SourceCard, ...]
    _index: Mapping[str, SourceCard] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if (not isinstance(self.sources, tuple) or any(not isinstance(s, SourceCard) for s in self.sources)
                or len({s.series_id for s in self.sources}) != len(self.sources)):
            raise ValueError("catalog.sources_invalid")
        object.__setattr__(self, "_index", MappingProxyType({card.series_id: card for card in self.sources}))

    def source(self, series_id):
        return self._index.get(series_id)

    def select(self, *, publisher_id=None, family_id=None, format=None):
        return tuple(s for s in self.sources if (publisher_id is None or s.publisher_id == publisher_id)
                     and (family_id is None or s.family_id == family_id)
                     and (format is None or format in s.formats))

    @property
    def families(self):
        return tuple(sorted({s.family_id for s in self.sources}))

    def describe(self, series_id, *, operations):
        source = self.source(series_id)
        if source is None:
            raise ValueError("catalog.source_unknown")
        from stratbox.core.registry.discovery import describe_operation
        from stratbox.core.registry.sources import source_route
        descriptions = []
        stage_map = {stage.value: [] for stage in ProcessingStage}
        for binding in source.operations:
            value = describe_operation(operations, operations.reference(binding.operation_id))
            value["source_binding"] = {"state": binding.state, "reason": binding.reason,
                                       "parameters": dict(binding.parameters), "formats": binding.formats,
                                       "identity_parameter": binding.identity_parameter,
                                       "auxiliary_sources": dict(binding.auxiliary_sources),
                                       "context_scope": binding.context_scope}
            descriptions.append(value)
            for stage in value["processing"]["stages"] if value["processing"] else ():
                stage_map[stage].append(binding)
        route = source_route(series_id)
        coverage = {item.stage.value: item for item in operations.coverage(route.owner_id)}
        stages = []
        for stage, bindings in stage_map.items():
            declared = coverage.get(stage)
            states = {binding.state for binding in bindings}
            if not bindings:
                state = declared.state if declared is not None and declared.state in {"missing", "inapplicable", "unassessed"} else "undeclared"
            elif "supported" in states:
                state = "supported"
            elif states == {"delegated"}:
                state = "delegated"
            else:
                state = "conditional"
            reasons = tuple(dict.fromkeys(binding.reason for binding in bindings if binding.reason))
            if not bindings and declared is not None and declared.reason:
                reasons += (declared.reason,)
            stages.append({"stage": stage, "operations": tuple(binding.operation_id for binding in bindings),
                           "state": state, "reasons": reasons,
                           "bindings": tuple({"operation_id": binding.operation_id, "state": binding.state,
                                              "reason": binding.reason, "formats": binding.formats} for binding in bindings),
                           "qualification": "Declared source support requires compatible values and runtime admission."})
        return {"source": source, "operations": tuple(descriptions),
                "route": {"profile_id": route.profile_id,
                          "stages": tuple(stage.value for stage in route.stages),
                          "transitions": tuple({"from": before.value, "to": after.value}
                                               for before, after in route.transitions),
                          "qualification": "Stages classify processing; exact port contracts determine value handoff."},
                "stages": tuple(stages)}


def source_catalog(operation_catalog) -> SourceCatalog:
    from stratbox.core.registry.sources import source_cards
    cards = []
    for registration in operation_catalog.registrations:
        supplied = source_cards(registration.owner_id)
        for card in supplied:
            for binding in card.operations:
                operation_catalog.reference(binding.operation_id)
        cards.extend(supplied)
    return SourceCatalog(tuple(sorted(cards, key=lambda c: c.series_id)))
