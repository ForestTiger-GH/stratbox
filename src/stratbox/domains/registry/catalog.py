"""Uniform source metadata and qualified operation support projections."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping

from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import ProcessingStage
from stratbox.shared.data.sources import SourceGroup


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
    source_groups: tuple[SourceGroup, ...] = ()

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
                or not isinstance(self.source_groups, tuple) or any(not isinstance(group, SourceGroup) for group in self.source_groups)
                or len({group.group_id for group in self.source_groups}) != len(self.source_groups)
                or not isinstance(self.qualifications, tuple) or any(type(q) is not str for q in self.qualifications)):
            raise ValueError("catalog.source_card_invalid")


@dataclass(frozen=True, slots=True)
class SourceBindingAssessment:
    binding: SourceOperation
    state: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceSelection:
    source: SourceCard
    groups: tuple[SourceGroup, ...]
    assessments: tuple[SourceBindingAssessment, ...]
    state: str
    reasons: tuple[str, ...] = ()
    format: str | None = None
    group_id: str | None = None
    edition: str | None = None

    @property
    def bindings(self):
        return tuple(replace(item.binding, state=item.state, reason=item.binding.reason or "; ".join(item.reasons))
                     for item in self.assessments if item.state != "inapplicable")


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    sources: tuple[SourceCard, ...]
    _operation_catalog: object | None = field(default=None, repr=False, compare=False)
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

    def selection(self, series_id, *, format=None, group_id=None, edition=None):
        source = self.source(series_id)
        if source is None:
            raise ValueError("catalog.source_unknown")
        selected = tuple(group for group in source.source_groups if group_id is None or group.group_id == group_id)
        reasons = []
        if group_id is not None and not selected:
            reasons.append("source.group_unavailable")
        if format is not None and (format not in source.formats or selected and not any(not group.formats or format in group.formats for group in selected)):
            reasons.append("source.format_unavailable")
        edition_known = any(edition in (*group.layout_editions, *group.semantic_profile_editions) for group in selected) if edition else True
        edition_declared = any(group.layout_editions or group.semantic_profile_editions for group in selected)
        if edition is not None and not edition_known and edition_declared:
            reasons.append("source.edition_unavailable")
        assessments = []
        for binding in source.operations:
            binding_reasons = list(reasons)
            state = binding.state
            if format is not None and binding.formats and format not in binding.formats:
                binding_reasons.append("source.operation_format_unavailable")
            if binding_reasons:
                state = "inapplicable"
            elif edition is not None and not edition_known:
                state = "conditional"
                binding_reasons.append("source.edition_unreviewed")
            policy = self._operation_catalog.metadata(binding.operation_id) if self._operation_catalog is not None else None
            stages = tuple(stage.value for stage in policy.processing.stages) if policy is not None and policy.processing else ()
            if state != "inapplicable" and any(stage in {"integrate", "calculate"} for stage in stages) and selected and any(group.qualification != "supported" for group in selected):
                state = "conditional"
                binding_reasons.append("source.semantic_profile_admission_required")
            if binding.reason:
                binding_reasons.append(binding.reason)
            assessments.append(SourceBindingAssessment(binding, state, tuple(dict.fromkeys(binding_reasons))))
        return SourceSelection(source, selected, tuple(assessments),
            "inapplicable" if reasons else "conditional" if edition and not edition_known else "declared", tuple(reasons), format, group_id, edition)

    def template(self, series_id):
        """Explain the reusable template and concrete slots for one source."""
        from stratbox.domains.registry.declarations import source_route, template_document
        route = source_route(series_id)
        return template_document(route.owner_id, route.template_id)

    def slots(self, series_id, *, format=None):
        """Return applicable named operation bindings without implying a linear flow."""
        from stratbox.domains.registry.declarations import source_route
        allowed = {binding.operation_id for binding in self.bindings(series_id, format=format)}
        return tuple((name, binding) for name, binding in source_route(series_id).slots
                     if binding.operation_id in allowed)

    def bindings(self, series_id, *, format=None, group_id=None, edition=None):
        return self.selection(series_id, format=format, group_id=group_id, edition=edition).bindings

    def describe(self, series_id, *, operations, format=None, group_id=None, edition=None):
        """Explain the same selected applicability used by binding and planning."""
        from stratbox.operations.discovery import describe_operation
        from stratbox.domains.registry.declarations import source_route
        from stratbox.domains.registry.routes import stage_transitions
        selection = self.selection(series_id, format=format, group_id=group_id, edition=edition)
        source, selected, selection_reasons = selection.source, selection.groups, selection.reasons
        descriptions = []
        stage_map = {stage.value: [] for stage in ProcessingStage}
        for assessment in selection.assessments:
            binding, state, reasons = assessment.binding, assessment.state, assessment.reasons
            value = describe_operation(operations, operations.reference(binding.operation_id))
            stages = value["processing"]["stages"] if value["processing"] else ()
            projection = {"operation_id": binding.operation_id, "state": state, "declared_state": binding.state,
                          "reason": binding.reason, "reasons": tuple(dict.fromkeys(reasons)), "formats": binding.formats,
                          "parameters": dict(binding.parameters), "identity_parameter": binding.identity_parameter,
                          "auxiliary_sources": dict(binding.auxiliary_sources), "context_scope": binding.context_scope}
            value["source_binding"] = projection
            descriptions.append(value)
            for stage in stages:
                stage_map[stage].append(projection)
        route = source_route(series_id)
        coverage = {item.stage.value: item for item in operations.coverage(route.owner_id)}
        stages = []
        for stage, bindings in stage_map.items():
            declared = coverage.get(stage)
            states = {binding["state"] for binding in bindings}
            if selection_reasons:
                state = "inapplicable"
            elif not bindings:
                state = declared.state if declared is not None and declared.state in {"missing", "inapplicable", "unassessed"} else "undeclared"
            elif "supported" in states:
                state = "supported"
            elif states == {"delegated"}:
                state = "delegated"
            elif states == {"inapplicable"}:
                state = "inapplicable"
            else:
                state = "conditional"
            reasons = tuple(dict.fromkeys(reason for binding in bindings for reason in binding["reasons"])) or tuple(selection_reasons)
            if not bindings and declared is not None and declared.reason:
                reasons += (declared.reason,)
            stages.append({"stage": stage, "operations": tuple(binding["operation_id"] for binding in bindings if binding["state"] != "inapplicable"),
                           "state": state, "reasons": reasons, "bindings": tuple(bindings),
                           "qualification": "Declared applicability requires actual value, domain and environment admission."})
        transitions = stage_transitions(operations, replace(route, operations=selection.bindings), format=format, group_id=group_id, edition=edition) if not selection_reasons else ()
        return {"source": source, "operations": tuple(descriptions),
                "selection": {"format": format, "group_id": group_id, "edition": edition,
                              "groups": selected, "state": selection.state,
                              "reasons": tuple(selection_reasons)},
                "route": {"profile_id": route.profile_id, "template_id": route.template_id,
                          "slots": tuple({"slot": name, "operation_id": binding.operation_id}
                                         for name, binding in route.slots),
                          "stages": tuple(stage.value for stage in route.stages),
                          "transitions": tuple({"from": before.value, "to": after.value} for before, after in transitions),
                          "qualification": "Stage transitions derive from exact compatible operation ports."},
                "stages": tuple(stages)}


def source_catalog(operation_catalog) -> SourceCatalog:
    from stratbox.domains.registry.declarations import source_cards
    cards = []
    for registration in operation_catalog.registrations:
        supplied = source_cards(registration.owner_id)
        for card in supplied:
            for binding in card.operations:
                operation_catalog.reference(binding.operation_id)
        cards.extend(supplied)
    return SourceCatalog(tuple(sorted(cards, key=lambda c: c.series_id)), operation_catalog)
