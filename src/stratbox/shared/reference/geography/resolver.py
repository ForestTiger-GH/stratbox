"""Auditable, indexed territory-name resolution with explicit context admission."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict

from stratbox.shared.data.observations import SubjectRef
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.reference.assets import ReferenceError, load_reference
from .models import RegionNameContext, RegionNameMatch, RegionNameRule
from .names import normalize_region_label
from .registry import read_rules, validate_region_rules

_PACKAGE = "stratbox.shared.reference.geography"


def _ruleset_identity(rules: tuple[RegionNameRule, ...]) -> ByteIdentity:
    """Canonical digest of the full reviewed/supplied rule meanings."""
    return ByteIdentity.of(canonical_manifest_bytes({
        "schema": "stratbox.geography.rules.v1",
        "rules": [asdict(rule) for rule in sorted(rules, key=lambda item: item.rule_id)],
    }))


def _admitted(rule: RegionNameRule, context: RegionNameContext) -> bool:
    """Fail closed for every declared rule restriction missing from context."""
    if context.source_code is not None and (
        rule.subject_id != context.source_code or
        rule.subject_namespace != context.code_namespace
    ):
        return False
    if rule.source_family is not None and rule.source_family != context.source_family:
        return False
    if context.observed_kind is not None and rule.kind != context.observed_kind:
        return False
    if rule.perimeter_id is not None and rule.perimeter_id != context.perimeter_hint:
        return False
    if context.perimeter_hint is not None and rule.perimeter_id != context.perimeter_hint:
        return False
    if context.as_of is None:
        return rule.effective_from is None and rule.effective_to is None
    return (
        (rule.effective_from is None or context.as_of >= rule.effective_from)
        and (rule.effective_to is None or context.as_of <= rule.effective_to)
    )


class RegionNameResolver:
    def __init__(self, *, edition_id: str | None = None,
                 rules: Iterable[RegionNameRule] | None = None):
        if rules is None:
            source_rules, self.edition_id = read_rules(edition_id=edition_id)
            self.rules = validate_region_rules(source_rules)
            edition = load_reference(_PACKAGE, edition_id=self.edition_id)
            self.reference_id = edition.edition.reference_id
            self.reference_snapshot_identity = edition.snapshot_identity
            self.provenance = "packaged"
        else:
            if edition_id is not None:
                raise ReferenceError(
                    "Supplied region rules cannot claim a packaged reference edition"
                )
            self.rules = validate_region_rules(tuple(rules))
            self.reference_id = None
            self.reference_snapshot_identity = None
            self.provenance = "supplied"
        self.ruleset_identity = _ruleset_identity(self.rules)
        if self.provenance == "supplied":
            self.edition_id = "supplied-" + self.ruleset_identity.sha256
        index: dict[str, list[RegionNameRule]] = {}
        for rule in self.rules:
            key = normalize_region_label(rule.alias)
            assert key is not None  # Guaranteed by validate_region_rules.
            index.setdefault(key, []).append(rule)
        self._index = {key: tuple(values) for key, values in index.items()}
        self._subject_keys = frozenset(
            (rule.subject_namespace, rule.subject_id) for rule in self.rules
        )

    def _result(self, raw: str, normalized: str, status: str,
                subject: SubjectRef | None = None, canonical_name: str | None = None,
                perimeter_id: str | None = None, rule_id: str | None = None,
                candidates: tuple[str, ...] = ()) -> RegionNameMatch:
        return RegionNameMatch(
            raw, normalized, status, subject, canonical_name, perimeter_id,
            self.edition_id, rule_id, candidates,
            self.ruleset_identity, self.reference_id,
            self.reference_snapshot_identity, self.provenance,
        )

    def resolve(self, name: str, *, context: RegionNameContext | None = None) -> RegionNameMatch:
        if not isinstance(name, str):
            raise TypeError("Region name must be a string")
        key = normalize_region_label(name)
        if key is None:
            return self._result(name, "", "unmatched")
        context = context or RegionNameContext()
        all_matching = self._index.get(key, ())
        matches = [rule for rule in all_matching if _admitted(rule, context)]
        if not matches:
            status = "out_of_scope" if all_matching or (
                context.source_code is not None and
                (context.code_namespace, context.source_code) in self._subject_keys
            ) else "unmatched"
            return self._result(name, key, status)
        identities = {
            (rule.subject_namespace, rule.subject_id, rule.perimeter_id, rule.canonical_name)
            for rule in matches
        }
        if len(identities) > 1:
            return self._result(name, key, "ambiguous", candidates=tuple(sorted(
                f"{r.subject_namespace}:{r.subject_id}:{r.perimeter_id or ''}" for r in matches
            )))
        winner = min(matches, key=lambda rule: (
            -(rule.source_family is not None),
            -(rule.perimeter_id is not None),
            -(rule.effective_from is not None or rule.effective_to is not None),
            normalize_region_label(rule.alias) != normalize_region_label(rule.canonical_name),
            rule.rule_id,
        ))
        status = "exact" if key == normalize_region_label(winner.canonical_name) else "alias"
        return self._result(
            name, key, status, SubjectRef(winner.subject_namespace, winner.subject_id),
            winner.canonical_name, winner.perimeter_id, winner.rule_id,
        )

    def resolve_many(self, names: Iterable[str], *, context: RegionNameContext | None = None) -> tuple[RegionNameMatch, ...]:
        return tuple(self.resolve(name, context=context) for name in names)
