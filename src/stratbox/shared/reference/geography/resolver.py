"""Deterministic code-first and exact-alias territory name resolution."""

from __future__ import annotations

from collections.abc import Iterable

from stratbox.shared.data.observations import SubjectRef
from .models import RegionNameContext, RegionNameMatch, RegionNameRule
from .names import normalize_region_label
from .registry import read_rules


class RegionNameResolver:
    def __init__(self, *, edition_id: str | None = None,
                 rules: Iterable[RegionNameRule] | None = None):
        if rules is None:
            self.rules, self.edition_id = read_rules(edition_id=edition_id)
        else:
            self.rules = tuple(rules)
            self.edition_id = edition_id or "explicit-rules"
        self._keys = tuple(normalize_region_label(rule.alias) for rule in self.rules)

    def resolve(self, name: str, *, context: RegionNameContext | None = None) -> RegionNameMatch:
        if not isinstance(name, str):
            raise TypeError("Region name must be a string")
        key = normalize_region_label(name)
        if key is None:
            return RegionNameMatch(name, "", "unmatched", None, None, None, self.edition_id)
        context = context or RegionNameContext()
        exact = [(rule, label) for rule, label in zip(self.rules, self._keys) if label == key]
        if not exact:
            return RegionNameMatch(name, key, "unmatched", None, None, None, self.edition_id)
        candidates = []
        for rule, _ in exact:
            if context.source_family and rule.source_family and context.source_family != rule.source_family:
                continue
            if context.observed_kind and context.observed_kind != rule.kind:
                continue
            if context.perimeter_hint and context.perimeter_hint != rule.perimeter_id:
                continue
            if context.as_of is not None and (
                rule.effective_from is not None and context.as_of < rule.effective_from or
                rule.effective_to is not None and context.as_of > rule.effective_to
            ):
                continue
            candidates.append(rule)
        if not candidates:
            return RegionNameMatch(name, key, "out_of_scope", None, None, None, self.edition_id)
        if context.source_code is not None:
            code_candidates = [rule for rule in candidates if
                rule.subject_id == context.source_code and rule.subject_namespace == context.code_namespace]
            if not code_candidates:
                return RegionNameMatch(name, key, "out_of_scope", None, None, None,
                    self.edition_id, candidates=tuple(sorted({r.subject_id for r in candidates})))
            candidates = code_candidates
        identities = {(r.subject_namespace, r.subject_id, r.perimeter_id) for r in candidates}
        if len(identities) != 1:
            return RegionNameMatch(name, key, "ambiguous", None, None, None, self.edition_id,
                candidates=tuple(sorted(f"{r.subject_namespace}:{r.subject_id}:{r.perimeter_id or ''}" for r in candidates)))
        winner = min(candidates, key=lambda r: (normalize_region_label(r.alias) != normalize_region_label(r.canonical_name), r.rule_id))
        state = "exact" if key == normalize_region_label(winner.canonical_name) else "alias"
        return RegionNameMatch(name, key, state, SubjectRef(winner.subject_namespace, winner.subject_id),
            winner.canonical_name, winner.perimeter_id, self.edition_id, winner.rule_id)

    def resolve_many(self, names: Iterable[str], *, context: RegionNameContext | None = None) -> tuple[RegionNameMatch, ...]:
        return tuple(self.resolve(name, context=context) for name in names)
