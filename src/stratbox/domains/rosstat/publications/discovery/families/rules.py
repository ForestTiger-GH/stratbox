"""Source-family identity rules; no claim of a calibrated live HTML layout."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


@dataclass(frozen=True, slots=True)
class FamilyRule:
    profile_id: str
    profile_version: str
    issue_style: Literal["monthly", "annual"]
    primary_asset_id: str
    # Explicit publisher-label markers for multiple independently named assets.
    named_assets: tuple[tuple[str, str], ...] = ()

    def asset_id(self, label: str, filename: str) -> tuple[str | None, str, str]:
        lowered = label.casefold()
        appendix = re.search(
            r"(?:приложени[ея]|appendix|annex)\s*(?:№|no\.?\s*)?([0-9]{1,3})\b",
            lowered,
        )
        if appendix:
            return f"annex_{int(appendix.group(1))}", "annex", "label.appendix_number"
        for marker, asset in self.named_assets:
            if marker in lowered:
                return asset, "primary", "label.typed_asset"
        if any(marker in lowered for marker in ("приложен", "appendix", "annex")):
            return None, "annex", "label.annex_without_identity"
        return self.primary_asset_id, "primary", "profile.default_primary"


_YEAR_MONTH = re.compile(r"(?<!\d)(20\d{2})[-_. /](0?[1-9]|1[0-2])(?!\d)")
_MONTH_YEAR = re.compile(r"(?<!\d)(0?[1-9]|1[0-2])[-_. /](20\d{2})(?!\d)")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


def parse_issue(rule: FamilyRule, filename: str, label: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    """Source issue label is not a statistical observation period.

    Parse independent filename/anchor evidence. Conflict means unresolved; do
    not silently prefer one date that might identify another edition.
    """
    def periods(text):
        if rule.issue_style == "annual":
            return set(_YEAR.findall(text))
        matches = set(
            f"{int(year):04d}-{int(month):02d}"
            for year, month in _YEAR_MONTH.findall(text)
        )
        matches |= {
            f"{int(year):04d}-{int(month):02d}"
            for month, year in _MONTH_YEAR.findall(text)
        }
        return matches
    from_name, from_label = periods(filename), periods(label)
    if len(from_name) > 1 or len(from_label) > 1 or (
        from_name and from_label and from_name != from_label
    ):
        return None, None, ("issue_evidence_conflict",)
    found = from_label or from_name
    if not found:
        return None, None, ("issue_unresolved",)
    source = "filename_and_label" if from_name and from_label else (
        "publisher_label" if from_label else "publisher_filename"
    )
    return next(iter(found)), source, ()
