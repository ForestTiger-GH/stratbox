"""Portable observation batches with exact scalar, period and evidence semantics.

This codec imposes no source, subject, geography or metric interpretation. The
outer dataset location/version can differ from the batch's logical identifiers.
Observation order and duplicate records are retained rather than aggregated.
"""
from __future__ import annotations

from decimal import Decimal
import json

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.assessment import assessment_value, evidence_from
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.source_context import source_use_value, source_use_from
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import canonical_manifest_bytes

OBSERVATION_SNAPSHOT = DataContract("observations.batch.snapshot", 1)
_T, _I, _D, _N = ScalarType.TEXT, ScalarType.INTEGER, ScalarType.DATE, ScalarType.DECIMAL
_METADATA = TableSchema(DataContract("observations.batch.metadata", 3), (
    ColumnSchema("dataset_id", _T), ColumnSchema("schema_version", _I), ColumnSchema("release_id", _T),
    ColumnSchema("source_uses", _T),
    ColumnSchema("evidence", _T),
))
_OBSERVATIONS = TableSchema(DataContract("observations.batch.rows", 1), tuple(ColumnSchema(*spec) for spec in (
    ("ordinal", _I), ("subject_namespace", _T), ("subject_id", _T), ("metric_id", _T), ("unit", _T),
    ("quantity_kind", _T, True), ("definition_version", _T, True), ("scale", _N, True),
    ("period_kind", _T), ("as_of", _D, True), ("start", _D, True), ("end", _D, True),
    ("dimensions", _T), ("perimeter", _T), ("value_kind", _T), ("integer_value", _I, True),
    ("decimal_value", _N, True), ("text_value", _T, True), ("value_status", _T),
    ("evidence_ref", _T), ("raw_token", _T, True),
)), ("ordinal",))
_COVERAGE = SnapshotCoverage("unknown", "Exactly the supplied observation batch; source-wide coverage is not inferred.")


def _validate_batch(batch):
    if (not isinstance(batch, ObservationBatch) or type(batch.dataset_id) is not str or not batch.dataset_id
            or type(batch.release_id) is not str or not batch.release_id
            or type(batch.schema_version) is not int or batch.schema_version < 1
            or not isinstance(batch.observations, tuple) or not isinstance(batch.lineage, tuple)
            or any(not isinstance(item, UsedInputReceipt) for item in batch.lineage)):
        raise ValueError("observations.batch_invalid")
    for item in batch.observations:
        if (not isinstance(item, Observation) or not isinstance(item.subject, SubjectRef)
                or not isinstance(item.metric, MetricRef) or not isinstance(item.period, PeriodRef)
                or type(item.subject.namespace) is not str or not item.subject.namespace
                or type(item.subject.id) is not str or not item.subject.id
                or not isinstance(item.dimensions, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 or any(type(value) is not str for value in pair)
                       for pair in item.dimensions)
                or type(item.perimeter) is not str or not item.perimeter
                or type(item.evidence_ref) is not str):
            raise ValueError("observations.record_invalid")
        # Reconstruct the immutable public contract to recheck exact scalar/status rules.
        Observation(item.subject, item.metric, item.period, item.dimensions, item.perimeter,
                    item.value, item.value_status, item.evidence_ref, item.raw_token)


def observation_snapshot(batch: ObservationBatch, *, dataset_id=None, version_id=None) -> DatasetSnapshot:
    """Encode every admitted observation property without lossy numeric casts."""
    _validate_batch(batch)
    rows=[]
    for ordinal, item in enumerate(batch.observations):
        kind = "none" if item.value is None else "integer" if type(item.value) is int else "decimal" if type(item.value) is Decimal else "text"
        dimensions=canonical_manifest_bytes({"dimensions": item.dimensions}).decode("utf-8")
        rows.append((ordinal, item.subject.namespace, item.subject.id, item.metric.id, item.metric.unit,
            item.metric.quantity_kind, item.metric.definition_version, item.metric.scale,
            item.period.kind, item.period.as_of, item.period.start, item.period.end,
            dimensions, item.perimeter, kind, item.value if kind == "integer" else None,
            item.value if kind == "decimal" else None, item.value if kind == "text" else None,
            item.value_status, item.evidence_ref, item.raw_token))
    return DatasetSnapshot.build(dataset_id if dataset_id is not None else batch.dataset_id,
        version_id if version_id is not None else batch.release_id, OBSERVATION_SNAPSHOT,
        (("metadata", TypedTable(_METADATA, ((batch.dataset_id, batch.schema_version, batch.release_id,
            canonical_manifest_bytes({"uses": [source_use_value(use) for use in batch.source_uses]}).decode("utf-8"),
            canonical_manifest_bytes({"evidence": assessment_value(batch.evidence)}).decode("utf-8")),))),
         ("observations", TypedTable(_OBSERVATIONS, tuple(rows)))),
        coverage=_COVERAGE, inputs=batch.lineage)


def _dimensions(value):
    if type(value) is not str or len(value.encode("utf-8")) > 8 * 1024 * 1024:
        raise ValueError("observations.dimensions_invalid")
    try:
        data=json.loads(value)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("observations.dimensions_invalid") from None
    if (not isinstance(data, dict) or set(data) != {"dimensions"}
            or not isinstance(data["dimensions"], list)
            or any(not isinstance(pair, list) or len(pair) != 2 or any(type(part) is not str for part in pair)
                   for pair in data["dimensions"])):
        raise ValueError("observations.dimensions_invalid")
    result=tuple(tuple(pair) for pair in data["dimensions"])
    if canonical_manifest_bytes({"dimensions": result}).decode("utf-8") != value:
        raise ValueError("observations.dimensions_noncanonical")
    return result


def observations_from_snapshot(snapshot: DatasetSnapshot) -> ObservationBatch:
    """Validate and restore a complete batch, preserving logical IDs and lineage."""
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != OBSERVATION_SNAPSHOT
            or tuple(name for name, _ in snapshot.tables) != ("metadata", "observations")
            or snapshot.table("metadata").schema != _METADATA
            or snapshot.table("observations").schema != _OBSERVATIONS
            or len(snapshot.table("metadata").rows) != 1):
        raise ValueError("observations.snapshot_invalid")
    records=[]
    for ordinal, row in enumerate(snapshot.table("observations").rows):
        (position, namespace, subject_id, metric_id, unit, quantity, definition, scale,
         period_kind, as_of, start, end, dimensions, perimeter, kind, integer, decimal,
         text, status, evidence, raw)=row
        if position != ordinal:
            raise ValueError("observations.record_order_invalid")
        choices={"integer": integer, "decimal": decimal, "text": text, "none": None}
        if kind not in choices or any(value is not None for name, value in (
                ("integer", integer), ("decimal", decimal), ("text", text)) if name != kind):
            raise ValueError("observations.value_encoding_invalid")
        value=choices[kind]
        if (kind == "none") != (value is None):
            raise ValueError("observations.value_encoding_invalid")
        records.append(Observation(SubjectRef(namespace,subject_id),
            MetricRef(metric_id,unit,quantity,definition,scale), PeriodRef(period_kind,as_of,start,end),
            _dimensions(dimensions),perimeter,value,status,evidence,raw))
    dataset, schema_version, release, context, assessment=snapshot.table("metadata").rows[0]
    try:
        source_uses=json.loads(context)
        if not isinstance(source_uses, dict) or set(source_uses) != {"uses"} or not isinstance(source_uses["uses"], list):
            raise ValueError
        uses=tuple(source_use_from(use) for use in source_uses["uses"])
    except (ValueError, TypeError, KeyError):
        raise ValueError("observations.source_uses_invalid") from None
    try:
        assessment = json.loads(assessment)
        if not isinstance(assessment, dict) or set(assessment) != {"evidence"}:
            raise ValueError
        evidence = evidence_from(assessment["evidence"]) if assessment["evidence"] is not None else None
    except (ValueError, TypeError, KeyError):
        raise ValueError("observations.evidence_invalid") from None
    batch=ObservationBatch(dataset,schema_version,release,tuple(records),snapshot.manifest.inputs,uses,evidence)
    rebuilt=observation_snapshot(batch,dataset_id=snapshot.manifest.dataset_id,version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("observations.snapshot_identity_mismatch")
    return batch


__all__ = ("OBSERVATION_SNAPSHOT", "observation_snapshot", "observations_from_snapshot")
