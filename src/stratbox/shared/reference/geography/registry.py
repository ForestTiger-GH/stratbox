"""Validate and decode independently reviewed territory name assertions."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO

from stratbox.shared.reference.assets import ReferenceError, load_reference
from .models import RegionNameRule

_PACKAGE = "stratbox.shared.reference.geography"
_FIELDS = {"rule_id", "alias", "canonical_name", "subject_namespace", "subject_id", "kind",
           "perimeter_id", "source_family", "effective_from", "effective_to", "review_basis"}


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
        rules.append(RegionNameRule(ident, alias, canonical, namespace, code, kind,
            item.get("perimeter_id") or None, item.get("source_family") or None,
            start, end, basis))
    return tuple(rules), bundle.edition.edition_id
