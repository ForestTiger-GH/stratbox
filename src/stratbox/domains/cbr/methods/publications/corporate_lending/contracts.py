"""Typed publication assets for the debt and issuance source routes."""
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpSourceLink:
    """One discovered debt-stock publication asset."""

    source_id: str
    url: str
    source_name: str
    report_date: str


@dataclass(frozen=True, slots=True)
class IssuanceSourceLink:
    source_id: str
    url: str
    source_name: str
    report_date: str
    reference_period: str
