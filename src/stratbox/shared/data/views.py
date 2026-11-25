"""Prepared observation views keep source evidence and never aggregate implicitly."""
from __future__ import annotations

from dataclasses import dataclass, replace
import csv
from io import StringIO
import json

from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.data.assessment import selected_evidence, value_evidence

OBSERVATION_VIEW = DataContract("observations.prepared_view", 1, DataRole.PRODUCTS)
OBSERVATION_VIEW_SNAPSHOT = DataContract("observations.prepared_view.snapshot", 1, DataRole.PRODUCTS)
_SCHEMA = TableSchema(DataContract("observations.view.metadata", 1), (
    ColumnSchema("view_id", ScalarType.TEXT), ColumnSchema("source_sha256", ScalarType.TEXT),
    ColumnSchema("source_size", ScalarType.INTEGER), ColumnSchema("qualifications", ScalarType.TEXT)))


@dataclass(frozen=True, slots=True)
class ObservationView:
    view_id: str
    batch: ObservationBatch
    source_identity: ByteIdentity
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...] = ()

    def __post_init__(self):
        if (type(self.view_id) is not str or not self.view_id
                or not isinstance(self.batch, ObservationBatch) or not isinstance(self.source_identity, ByteIdentity)
                or not isinstance(self.coverage, SnapshotCoverage) or not isinstance(self.qualifications, tuple)
                or any(type(q) is not str or not q for q in self.qualifications)):
            raise ValueError("view.invalid")

    @property
    def identity(self):
        return view_snapshot(self).identity


def prepare_observation_view(batch: ObservationBatch, *, view_id, metric_ids=(), period_kinds=(),
                             subject_ids=(), coverage=None, qualifications=()):
    source = observation_snapshot(batch)
    for selection in (metric_ids, period_kinds, subject_ids):
        if not isinstance(selection, tuple) or any(type(v) is not str or not v for v in selection):
            raise ValueError("view.selection_invalid")
    if set(period_kinds) - {"as_of", "capture", "interval"}:
        raise ValueError("view.period_kind_invalid")
    selected = tuple(o for o in batch.observations if
        (not metric_ids or o.metric.id in metric_ids) and
        (not period_kinds or o.period.kind in period_kinds) and
        (not subject_ids or o.subject.id in subject_ids))
    scope = coverage or SnapshotCoverage("unknown", "Caller-supplied observation batch; publisher-wide coverage is unspecified.")
    if len(selected) != len(batch.observations):
        scope = replace(scope, status="partial", description="Explicitly selected observations from the supplied batch.")
        batch = replace(batch, evidence=selected_evidence(value_evidence(batch), selected))
    return ObservationView(view_id, replace(batch, observations=selected), source.identity, scope, tuple(qualifications))


def view_snapshot(view: ObservationView, *, dataset_id=None, version_id=None):
    view.__post_init__()
    batch = observation_snapshot(view.batch)
    meta = TypedTable(_SCHEMA, ((view.view_id, view.source_identity.sha256, view.source_identity.size,
        canonical_manifest_bytes(view.qualifications).decode("utf-8")),))
    result = DatasetSnapshot.build(dataset_id or view.batch.dataset_id, version_id or "content", OBSERVATION_VIEW,
        (("view", meta), *batch.tables), coverage=view.coverage, inputs=view.batch.lineage,
        parents=(view.source_identity,))
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def view_from_snapshot(snapshot: DatasetSnapshot):
    if (not snapshot.complete or snapshot.manifest.contract != OBSERVATION_VIEW
            or tuple(n for n, _ in snapshot.tables) != ("view", "metadata", "observations")
            or snapshot.table("view").schema != _SCHEMA or len(snapshot.table("view").rows) != 1):
        raise ValueError("view.snapshot_invalid")
    from stratbox.shared.data.observation_snapshots import OBSERVATION_SNAPSHOT, _COVERAGE
    dataset, _, release = snapshot.table("metadata").rows[0][:3]
    raw = DatasetSnapshot.build(dataset, release, OBSERVATION_SNAPSHOT, snapshot.tables[1:],
        coverage=_COVERAGE, inputs=snapshot.manifest.inputs)
    batch = observations_from_snapshot(raw)
    name, sha, size, quals = snapshot.table("view").rows[0]
    result = ObservationView(name, batch, ByteIdentity(sha, size), snapshot.manifest.coverage, tuple(json.loads(quals)))
    if view_snapshot(result, dataset_id=snapshot.manifest.dataset_id,
                     version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("view.snapshot_identity_mismatch")
    return result


def _records(view):
    for o in view.batch.observations:
        yield {"subject_namespace": o.subject.namespace, "subject_id": o.subject.id,
            "metric_id": o.metric.id, "unit": o.metric.unit, "scale": str(o.metric.scale) if o.metric.scale is not None else None,
            "quantity_kind": o.metric.quantity_kind, "definition_version": o.metric.definition_version,
            "period_kind": o.period.kind, "as_of": o.period.as_of.isoformat() if o.period.as_of else None,
            "start": o.period.start.isoformat() if o.period.start else None,
            "end": o.period.end.isoformat() if o.period.end else None, "dimensions": o.dimensions,
            "perimeter": o.perimeter, "value_type": "null" if o.value is None else type(o.value).__name__,
            "value": str(o.value) if o.value is not None else None,
            "value_status": o.value_status, "evidence_ref": o.evidence_ref, "raw_token": o.raw_token}


def render_observation_view(view: ObservationView, *, format="csv") -> Representation:
    view.__post_init__()
    records = tuple(_records(view))
    if format == "csv":
        fields = ("subject_namespace", "subject_id", "metric_id", "unit", "scale", "quantity_kind", "definition_version",
            "period_kind", "as_of", "start", "end", "dimensions", "perimeter", "value_type", "value",
            "value_status", "evidence_ref", "raw_token")
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({**record, "dimensions": canonical_manifest_bytes(record["dimensions"]).decode("utf-8")})
        return Representation("observations.view.csv", 1, "text/csv", stream.getvalue().encode("utf-8"), "utf-8")
    if format == "jsonl":
        return Representation("observations.view.jsonl", 1, "application/x-ndjson",
            b"\n".join(canonical_manifest_bytes(r) for r in records) + (b"\n" if records else b""), "utf-8")
    if format == "json":
        return Representation("observations.view.json", 1, "application/json", canonical_manifest_bytes({
            "view_id": view.view_id, "source_sha256": view.source_identity.sha256,
            "coverage": view.coverage.status, "qualifications": view.qualifications, "observations": records}), "utf-8")
    raise ValueError("view.render_format_unsupported")
