"""Complete durable headline results, independent of rerunning a calculator."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt
from ..publications.context import context_document, context_from_document
from .contracts import HeadlineMetric, HeadlineSummary

SUMMARY_SNAPSHOT = DataContract("minfin.headlines.snapshot", 1, DataRole.PRODUCTS)
_T, _I = ScalarType.TEXT, ScalarType.INT64
_META = TableSchema(DataContract("minfin.headlines.metadata", 1, DataRole.PRODUCTS), (
    *(ColumnSchema(x, _T) for x in ("family_id", "source_id", "period_id", "frequency", "value_basis", "original_sha256")),
    ColumnSchema("original_size", _I), ColumnSchema("flake_method", _T), ColumnSchema("calculation_profile", _T),
    ColumnSchema("calculation_version", _I), ColumnSchema("flake_sha256", _T), ColumnSchema("flake_size", _I),
    ColumnSchema("publication", _T, nullable=True),
))
_VALUES = TableSchema(DataContract("minfin.headlines.metrics", 1, DataRole.PRODUCTS), (
    ColumnSchema("metric_id", _T), ColumnSchema("label", _T), ColumnSchema("value", _T),
    ColumnSchema("previous_year_value", _T, nullable=True), ColumnSchema("yoy_pct", _T, nullable=True),
    ColumnSchema("comparison", _T), ColumnSchema("unit", _T),
), ("metric_id",))


def validate_summary(value: HeadlineSummary):
    if (not isinstance(value, HeadlineSummary) or not value.source_id.startswith(value.family_id + ".")
            or not value.calculation_profile or type(value.calculation_version) is not int or value.calculation_version < 1
            or not isinstance(value.flake_identity, ByteIdentity) or not value.metrics
            or len({x.metric_id for x in value.metrics}) != len(value.metrics)):
        raise ValueError("minfin.summary.snapshot_invalid")
    if value.publication is not None and value.publication.series_id != value.source_id:
        raise ValueError("minfin.summary.snapshot_invalid")
    from ..integration.observations import economic_period
    economic_period(value.period_id, value.frequency, value.value_basis)
    for item in value.metrics:
        if item.unit != "billion_rub" or item.comparison not in {"comparable", "prior_missing", "prior_zero", "sign_change"}:
            raise ValueError("minfin.summary.snapshot_invalid")
        for number in (item.value, item.previous_year_value, item.yoy_pct):
            try:
                if number is not None and (type(number) is not str or not Decimal(number).is_finite()):
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise ValueError("minfin.summary.snapshot_invalid") from None
        if (item.comparison == "comparable") != (item.yoy_pct is not None):
            raise ValueError("minfin.summary.snapshot_invalid")


def summary_snapshot(value: HeadlineSummary, *, dataset_id: str, version_id: str) -> DatasetSnapshot:
    validate_summary(value)
    publication = context_document(value.publication)
    metadata = ((value.family_id, value.source_id, value.period_id, value.frequency, value.value_basis,
                 value.original_identity.sha256, value.original_identity.size, value.flake_method_version,
                 value.calculation_profile, value.calculation_version, value.flake_identity.sha256,
                 value.flake_identity.size, canonical_manifest_bytes(publication).decode() if publication else None),)
    rows = tuple((x.metric_id, x.label, x.value, x.previous_year_value, x.yoy_pct, x.comparison, x.unit) for x in value.metrics)
    return DatasetSnapshot.build(dataset_id, version_id, SUMMARY_SNAPSHOT,
        (("metadata", TypedTable(_META, metadata)), ("metrics", TypedTable(_VALUES, rows))),
        coverage=SnapshotCoverage("complete", "All metrics of the identified headline calculation result."),
        inputs=(UsedInputReceipt("flake", value.flake_identity, "application/json", "reference_only", value.source_id),
                UsedInputReceipt("original", value.original_identity, "application/octet-stream", "reference_only", value.source_id)))


def summary_from_snapshot(snapshot: DatasetSnapshot) -> HeadlineSummary:
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != SUMMARY_SNAPSHOT
            or tuple(name for name, _ in snapshot.tables) != ("metadata", "metrics")
            or snapshot.table("metadata").schema != _META or snapshot.table("metrics").schema != _VALUES
            or len(snapshot.table("metadata").rows) != 1):
        raise ValueError("minfin.summary.snapshot_invalid")
    family, source, period, frequency, basis, sha, size, method, profile, version, flake_sha, flake_size, publication = snapshot.table("metadata").rows[0]
    value = HeadlineSummary(family, source, period, frequency, basis, ByteIdentity(sha, size), method,
        tuple(HeadlineMetric(*row) for row in snapshot.table("metrics").rows), profile, version,
        ByteIdentity(flake_sha, flake_size), context_from_document(json.loads(publication)) if publication else None)
    validate_summary(value)
    return value
