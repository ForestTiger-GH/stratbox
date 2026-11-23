"""Explicit period-qualified mappings into the shared observation contract.

Source geography remains the default identity. Cross-publication geography is
admitted only through caller-supplied, versioned mappings for the reporting date.
Cumulative releases with no reviewed start date retain that qualification.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .snapshots import dataset_snapshot, _release_input


@dataclass(frozen=True, slots=True)
class EscrowGeographyRule:
    source_name: str
    row_kind: str
    target_namespace: str
    target_id: str
    edition: str
    valid_from: date | None = None
    valid_through: date | None = None

    def __post_init__(self):
        if (not all(type(item) is str and item for item in
                    (self.source_name, self.row_kind, self.target_namespace, self.target_id, self.edition))
                or self.row_kind not in {"region", "federal_district", "rf_total"}
                or any(value is not None and type(value) is not date for value in (self.valid_from, self.valid_through))
                or self.valid_from and self.valid_through and self.valid_from > self.valid_through):
            raise ValueError("escrow.geography_rule_invalid")

    def applies(self, name, kind, period):
        return (self.source_name == name and self.row_kind == kind
                and (self.valid_from is None or self.valid_from <= period)
                and (self.valid_through is None or period <= self.valid_through))


def mapping_identity(rules):
    return ByteIdentity.of(canonical_manifest_bytes([
        {key: value.isoformat() if isinstance(value, date) else value for key, value in asdict(rule).items()}
        for rule in rules
    ]))


def align_values(dataset, rules=()):
    """Translate admitted source measures without inventing unavailable mappings."""
    snapshot = dataset_snapshot(dataset)
    mapping_input = UsedInputReceipt("geography_mapping", mapping_identity(rules), "application/json", "inline")
    definitions = {item.code: item for item in dataset.indicator_specs}
    releases = {item.period: item for item in dataset.releases}
    observations = []
    for period, region, kind, code, value, token, status, source_name, sheet, row, column in dataset.observations.itertuples(index=False, name=None):
        day = date.fromisoformat(period)
        matching = tuple(rule for rule in rules if rule.applies(region, kind, day))
        if len(matching) > 1:
            raise ValueError("escrow.geography_mapping_ambiguous")
        rule = matching[0] if matching else None
        subject = (SubjectRef(rule.target_namespace, rule.target_id) if rule else
                   SubjectRef("cbr.project_finance.source_geography", f"{kind}:{region}"))
        spec = definitions[code]
        value_status = "reported" if status == "numeric" else "blank" if status == "blank" else (
            "dash" if status == "marker" and token.strip() in {"-", "–", "—"} else "missing"
        )
        dimensions = (
            ("row_kind", kind), ("source_geography", region),
            ("geography_mapping", rule.edition if rule else "source-only"),
            ("geography_status", "mapped" if rule else "source_identity"),
            ("source_period_basis", "cumulative_start_unspecified" if code.startswith("revealed_") else "reporting_date"),
            ("source_status", status),
        )
        observations.append(Observation(
            subject,
            MetricRef(f"cbr.project_finance.{code}", spec.unit, spec.quantity_kind,
                      spec.definition_version, Decimal(spec.scale)),
            PeriodRef("as_of", as_of=day), dimensions, "cbr.project_finance.published_geography",
            value, value_status, f"{releases[period].original_identity.sha256}:{sheet}!R{row}C{column}", token,
        ))
    return ObservationBatch("cbr.project_finance.observations", 1, snapshot.manifest.version_id,
        tuple(observations), tuple(_release_input(item) for item in dataset.releases) + (
            UsedInputReceipt("integrated_dataset", snapshot.identity, "application/json", "reference_only"), mapping_input,
        ))
