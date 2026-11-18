"""Auditable territory name resolution with explicit code, time and perimeter scope."""

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
        if any(key is None for key in self._keys):
            raise ValueError("Territory aliases must have nonempty labels")

    def resolve(self, name: str, *, context: RegionNameContext | None = None) -> RegionNameMatch:
        if not isinstance(name, str):
            raise TypeError("Region name must be a string")
        key = normalize_region_label(name)
        if key is None:
            return RegionNameMatch(name, "", "unmatched", None, None, None, self.edition_id)
        context = context or RegionNameContext()
        # Code identity is preferred only if the caller supplies its verified namespace.
        # A code with a contradictory label is rejected rather than silently relabelled.
        qualified = [
            (rule, label) for rule, label in zip(self.rules, self._keys)
            if (context.source_code is None or
                (rule.subject_id == context.source_code and rule.subject_namespace == context.code_namespace))
            and (context.source_family is None or rule.source_family is None or
                 rule.source_family == context.source_family)
            and (context.observed_kind is None or rule.kind == context.observed_kind)
            and (context.perimeter_hint is None or rule.perimeter_id == context.perimeter_hint)
            and (context.as_of is not None or (
                rule.effective_from is None and rule.effective_to is None))
            and (context.as_of is None or (
                (rule.effective_from is None or context.as_of >= rule.effective_from) and
                (rule.effective_to is None or context.as_of <= rule.effective_to)))
        ]
        matches = [rule for rule, label in qualified if label == key]
        if not matches:
            all_matching = [rule for rule, label in zip(self.rules, self._keys) if label == key]
            status = "out_of_scope" if all_matching or (
                context.source_code is not None and any(r.subject_id == context.source_code and
                     r.subject_namespace == context.code_namespace for r in self.rules)
            ) else "unmatched"
            return RegionNameMatch(name, key, status, None, None, None, self.edition_id)
        identities = {(r.subject_namespace, r.subject_id, r.perimeter_id, r.canonical_name) for r in matches}
        if len(identities) != 1:
            return RegionNameMatch(name, key, "ambiguous", None, None, None,
                self.edition_id, candidates=tuple(sorted(
                    f"{r.subject_namespace}:{r.subject_id}:{r.perimeter_id or ''}" for r in matches)))
        winner = min(matches, key=lambda r: (
            normalize_region_label(r.alias) != normalize_region_label(r.canonical_name), r.rule_id))
        state = "exact" if key == normalize_region_label(winner.canonical_name) else "alias"
        return RegionNameMatch(name, key, state, SubjectRef(winner.subject_namespace, winner.subject_id),
            winner.canonical_name, winner.perimeter_id, self.edition_id, winner.rule_id)

    def resolve_many(self, names: Iterable[str], *, context: RegionNameContext | None = None) -> tuple[RegionNameMatch, ...]:
        return tuple(self.resolve(name, context=context) for name in names)
