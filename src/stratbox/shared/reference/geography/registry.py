"""Validate and decode independently reviewed territory name assertions."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO

from stratbox.shared.reference.assets import ReferenceError, load_reference
from .models import RegionNameRule, GEOGRAPHY_KINDS
from .names import normalize_region_label

_PACKAGE = "stratbox.shared.reference.geography"
_FIELDS = {"rule_id", "alias", "canonical_name", "subject_namespace", "subject_id", "kind",
           "perimeter_id", "source_family", "effective_from", "effective_to", "review_basis"}




def validate_region_rules(rules: tuple[RegionNameRule, ...] | list[RegionNameRule]) -> tuple[RegionNameRule, ...]:
    """One admission contract for packaged and supplied assertions.

    Duplicate aliases may deliberately identify different subjects; such
    conflicts are *ambiguities*, not arbitrary first-match assignments.
    """
    accepted, identities = [], set()
    for number, rule in enumerate(rules, 1):
        if not isinstance(rule, RegionNameRule):
            raise ReferenceError(f"Region rule {number} is not a RegionNameRule")
        if not all(isinstance(value, str) and value.strip() for value in (
            rule.rule_id, rule.alias, rule.canonical_name,
            rule.subject_namespace, rule.subject_id, rule.kind,
            rule.review_basis,
        )):
            raise ReferenceError(f"Region rule {number} lacks identity or review basis")
        if rule.rule_id in identities:
            raise ReferenceError(f"Duplicate geography rule identifier: {rule.rule_id}")
        identities.add(rule.rule_id)
        if rule.kind not in GEOGRAPHY_KINDS or normalize_region_label(rule.alias) is None:
            raise ReferenceError(f"Invalid geography kind/alias: {rule.rule_id}")
        for field in (rule.source_family, rule.perimeter_id):
            if field is not None and (not isinstance(field, str) or not field.strip()):
                raise ReferenceError(f"Invalid geography contextual restriction: {rule.rule_id}")
        if (rule.effective_from is not None and type(rule.effective_from) is not date) or (
            rule.effective_to is not None and type(rule.effective_to) is not date
        ):
            raise ReferenceError(f"Invalid geography validity date: {rule.rule_id}")
        if rule.effective_from and rule.effective_to and rule.effective_from > rule.effective_to:
            raise ReferenceError(f"Invalid geography validity interval: {rule.rule_id}")
        accepted.append(rule)
    if not accepted:
        raise ReferenceError("Geography ruleset must not be empty")
    return tuple(accepted)


def read_rules(*, edition_id: str | None = None) -> tuple[tuple[RegionNameRule, ...], str]:
    bundle = load_reference(_PACKAGE, edition_id=edition_id)
    data = bundle.read("aliases").decode("utf-8-sig")
    reader = csv.DictReader(StringIO(data))
    if reader.fieldnames is None or not _FIELDS.issubset(reader.fieldnames):
        raise ReferenceError("Geography aliases schema is incomplete")
    seen, rules = set(), []
    for number, item in enumerate(reader, 2):
        ident = (item.get("rule_id") or "").strip()
        alias = (item.get("alias") or "").strip()
        canonical = (item.get("canonical_name") or "").strip()
        namespace = (item.get("subject_namespace") or "").strip()
        code = (item.get("subject_id") or "").strip()
        kind = (item.get("kind") or "").strip()
        basis = (item.get("review_basis") or "").strip()
        if not ident or ident in seen or not all((alias, canonical, namespace, code, kind, basis)):
            raise ReferenceError(f"Invalid geography alias rule on row {number}")
        seen.add(ident)
        start = date.fromisoformat(item["effective_from"]) if item.get("effective_from") else None
        end = date.fromisoformat(item["effective_to"]) if item.get("effective_to") else None
        if start and end and start > end:
            raise ReferenceError(f"Invalid geography validity interval on row {number}")
        if kind not in {"country", "federal_district", "subject", "statistical_aggregate", "other"}:
            raise ReferenceError(f"Invalid geography kind on row {number}")
        rules.append(RegionNameRule(ident, alias, canonical, namespace, code, kind,
            item.get("perimeter_id") or None, item.get("source_family") or None,
            start, end, basis))
    return validate_region_rules(rules), bundle.edition.edition_id
