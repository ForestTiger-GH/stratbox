"""Explicit portable office-release data and evidence, independent of storage."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from collections.abc import Mapping

from stratbox.core.storage.datasets.codec import loads
from stratbox.shared.data.datasets import DatasetVersion, build_dataset_version
from stratbox.shared.data.lineage import input_from, input_value
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.source_context import source_use_value, source_use_from
from stratbox.shared.data.releases import ParsedRelease, ReleaseQualification, build_release
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import AcquisitionReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

_T, _I, _D, _N, _B = ScalarType.TEXT, ScalarType.INTEGER, ScalarType.DATE, ScalarType.DECIMAL, ScalarType.BINARY
_META = TableSchema(DataContract("cbr.service_network.release.metadata", 2, DataRole.EXTRACTS), tuple(ColumnSchema(*spec) for spec in (
    ("as_of", _D), ("row_count", _I), ("profile", _T), ("profile_version", _I), ("media_type", _T),
    ("encoding", _T, True), ("representation", _B), ("dataset", _T), ("release", _T), ("method", _T),
    ("manifest_version", _I), ("manifest", _B), ("acquisition", _T, True), ("source_details", _T, True),
    ("qualification", _T, True), ("facts_sha256", _T, True), ("facts_size", _I, True),
    ("facts_method", _T, True), ("batch_dataset", _T, True), ("batch_version", _I, True),
    ("batch_release", _T, True), ("batch_inputs", _T, True),
    ("batch_source_uses", _T, True),
)))
_OBS = TableSchema(DataContract("cbr.service_network.release.observations", 1, DataRole.EXTRACTS), tuple(ColumnSchema(*spec) for spec in (
    ("ordinal", _I), ("subject_namespace", _T), ("subject_id", _T), ("metric", _T), ("unit", _T),
    ("quantity_kind", _T, True), ("definition_version", _T, True), ("scale", _N, True),
    ("period_kind", _T), ("period_as_of", _D, True), ("period_start", _D, True), ("period_end", _D, True),
    ("dimensions", _T), ("perimeter", _T), ("value_kind", _T), ("value_integer", _I, True),
    ("value_decimal", _N, True), ("value_text", _T, True), ("value_status", _T),
    ("evidence_ref", _T), ("raw_token", _T, True),
)), ("ordinal",))


def _json(value):
    return canonical_manifest_bytes(value).decode("utf-8")


def detail_value(value, *, depth=0):
    """The bounded metadata grammar used by office extraction evidence."""
    if depth > 30:
        raise ValueError("cbr.offices.details_depth")
    if value is None or type(value) in {str, bool, int}:
        return ["scalar", value]
    if type(value) is date:
        return ["date", value.isoformat()]
    if isinstance(value, tuple):
        return ["tuple", [detail_value(item, depth=depth + 1) for item in value]]
    if isinstance(value, list):
        return ["list", [detail_value(item, depth=depth + 1) for item in value]]
    if isinstance(value, Mapping) and all(type(key) is str for key in value):
        return ["mapping", {key: detail_value(item, depth=depth + 1) for key, item in value.items()}]
    raise ValueError("cbr.offices.details_type_unsupported")


def detail_from(value, *, depth=0):
    if depth > 30 or not isinstance(value, list) or len(value) != 2:
        raise ValueError("cbr.offices.details_invalid")
    kind, item = value
    if kind == "scalar" and (item is None or type(item) in {str, bool, int}):
        return item
    if kind == "date" and type(item) is str:
        return date.fromisoformat(item)
    if kind in {"list", "tuple"} and isinstance(item, list):
        result = [detail_from(x, depth=depth + 1) for x in item]
        return tuple(result) if kind == "tuple" else result
    if kind == "mapping" and isinstance(item, dict):
        return {key: detail_from(x, depth=depth + 1) for key, x in item.items()}
    raise ValueError("cbr.offices.details_invalid")


def acquisition_value(value):
    if value is None:
        return None
    if not isinstance(value, AcquisitionReceipt) or value.observed_at_utc.utcoffset() is None:
        raise ValueError("cbr.offices.acquisition_invalid")
    return _json(asdict(value))


def acquisition_from(data):
    if data is None:
        return None
    value = loads(data.encode("utf-8"))
    value["identity"] = ByteIdentity(**value["identity"])
    value["observed_at_utc"] = datetime.fromisoformat(value["observed_at_utc"])
    result = AcquisitionReceipt(**value)
    if acquisition_value(result) != data:
        raise ValueError("cbr.offices.acquisition_invalid")
    return result


def validate_release(value, dataset, profile):
    if (not isinstance(value, ParsedRelease) or type(value.as_of) is not date
            or value.dataset_version.dataset_id != dataset or value.representation.profile_id != profile
            or value.dataset_version.release_id != value.as_of.isoformat()
            or type(value.row_count) is not int or value.row_count < 0
            or value.representation.version != 1 or value.representation.media_type != "text/csv"
            or value.dataset_version.manifest_version != 1
            or ByteIdentity.of(value.dataset_version.manifest) != value.dataset_version.identity):
        raise ValueError("cbr.offices.release_invalid")
    manifest = loads(value.dataset_version.manifest)
    rebuilt = build_dataset_version(dataset, value.as_of.isoformat(), value.dataset_version.method_version,
        value.inputs, value.representation.identity, parameters=manifest["parameters"], resources=manifest["resources"])
    if rebuilt != value.dataset_version:
        raise ValueError("cbr.offices.version_mismatch")
    if value.qualification is not None:
        q = value.qualification
        if (q.provenance not in {"offline_bytes", "literal_replay", "provider_reported", "tls_host", "peer_bound"}
                or q.analysis not in {"qualified", "qualified_subset", "literal_only"}
                or q.row_count != value.row_count or not q.scope
                or not isinstance(q.excluded_fields, tuple) or any(type(x) is not str for x in q.excluded_fields)):
            raise ValueError("cbr.offices.qualification_invalid")
    else:
        raise ValueError("cbr.offices.qualification_missing")
    observations = value.batch.observations if value.batch is not None else None
    if value.batch is not None and (value.batch.dataset_id != dataset
            or value.batch.release_id != value.as_of.isoformat() or value.batch.schema_version != 1
            or value.batch.lineage != value.inputs):
        raise ValueError("cbr.offices.batch_invalid")
    rebuilt_release = build_release(dataset, profile, value.dataset_version.method_version,
        value.as_of, value.representation.data, value.row_count, value.inputs, observations=observations,
        acquisition=value.acquisition, excluded_fields=value.qualification.excluded_fields,
        scope=value.qualification.scope if value.qualification.scope != dataset else None)
    if rebuilt_release.facts_identity != value.facts_identity:
        raise ValueError("cbr.offices.facts_identity_mismatch")
    if rebuilt_release.qualification != value.qualification:
        raise ValueError("cbr.offices.qualification_invalid")
    if value.acquisition is not None and not any(item.identity == value.acquisition.identity for item in value.inputs):
        raise ValueError("cbr.offices.acquisition_input_missing")
    if value.source_details is not None:
        if not isinstance(value.source_details, Mapping):
            raise ValueError("cbr.offices.details_invalid")
        detail_value(value.source_details)
    acquisition_value(value.acquisition)


def release_snapshot(value, *, dataset, profile, dataset_id, version_id, checkpoint=None):
    if checkpoint is not None:
        checkpoint()
    validate_release(value, dataset, profile)
    batch, facts, version, representation = value.batch, value.facts_identity, value.dataset_version, value.representation
    metadata = TypedTable(_META, ((value.as_of, value.row_count, representation.profile_id,
        representation.version, representation.media_type, representation.encoding, representation.data,
        version.dataset_id, version.release_id, version.method_version, version.manifest_version, version.manifest,
        acquisition_value(value.acquisition), _json(detail_value(value.source_details)) if value.source_details is not None else None,
        _json(asdict(value.qualification)) if value.qualification is not None else None,
        facts.sha256 if facts else None, facts.size if facts else None, value.facts_method,
        batch.dataset_id if batch else None, batch.schema_version if batch else None, batch.release_id if batch else None,
        _json([input_value(item) for item in batch.lineage]) if batch else None,
        _json([source_use_value(use) for use in batch.source_uses]) if batch else None),))
    observations = []
    for index, item in enumerate(batch.observations if batch else ()):
        if checkpoint is not None and index % 256 == 0:
            checkpoint()
        kind = "none" if item.value is None else "integer" if type(item.value) is int else "decimal" if type(item.value) is Decimal else "text"
        observations.append((index, item.subject.namespace, item.subject.id, item.metric.id, item.metric.unit,
            item.metric.quantity_kind, item.metric.definition_version, item.metric.scale,
            item.period.kind, item.period.as_of, item.period.start, item.period.end,
            _json(item.dimensions), item.perimeter, kind,
            item.value if kind == "integer" else None, item.value if kind == "decimal" else None,
            item.value if kind == "text" else None, item.value_status, item.evidence_ref, item.raw_token))
    coverage = "unknown" if value.batch is None else "partial" if value.qualification and value.qualification.analysis == "qualified_subset" else "complete"
    return DatasetSnapshot.build(dataset_id, version_id, DataContract(dataset + ".snapshot", 1, DataRole.EXTRACTS),
        (("metadata", metadata), ("observations", TypedTable(_OBS, tuple(observations)))),
        coverage=SnapshotCoverage(coverage, value.qualification.scope if value.qualification else dataset), inputs=value.inputs)


def release_from_snapshot(snapshot, *, dataset, profile, checkpoint=None):
    if checkpoint is not None:
        checkpoint()
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != DataContract(dataset + ".snapshot", 1, DataRole.EXTRACTS)
            or tuple(name for name, _ in snapshot.tables) != ("metadata", "observations")):
        raise ValueError("cbr.offices.snapshot_invalid")
    meta, obs = snapshot.table("metadata"), snapshot.table("observations")
    if meta.schema != _META or len(meta.rows) != 1 or obs.schema != _OBS:
        raise ValueError("cbr.offices.snapshot_schema_invalid")
    (as_of, count, profile_id, profile_version, media, encoding, data, dataset_name, release, method,
     manifest_version, manifest, acquisition, details, qualification, fact_sha, fact_size, facts_method,
     batch_dataset, batch_version, batch_release, batch_inputs, batch_source_uses) = meta.rows[0]
    observations = []
    for index, row in enumerate(obs.rows):
        if checkpoint is not None and index % 256 == 0:
            checkpoint()
        (ordinal, namespace, subject, metric, unit, quantity, definition, scale, period_kind,
         period_as_of, period_start, period_end, dimensions, perimeter, kind, integer, decimal,
         text, status, evidence, token) = row
        if (ordinal != index or kind not in {"none", "integer", "decimal", "text"}
                or (integer is not None) != (kind == "integer")
                or (decimal is not None) != (kind == "decimal") or (text is not None) != (kind == "text")):
            raise ValueError("cbr.offices.observation_invalid")
        value = {"none": None, "integer": integer, "decimal": decimal, "text": text}[kind]
        dimensions = loads(dimensions.encode("utf-8"))
        if not isinstance(dimensions, list) or any(not isinstance(x, list) or len(x) != 2 or any(type(y) is not str for y in x) for x in dimensions):
            raise ValueError("cbr.offices.observation_invalid")
        observations.append(Observation(SubjectRef(namespace, subject), MetricRef(metric, unit, quantity, definition, scale),
            PeriodRef(period_kind, period_as_of, period_start, period_end), tuple(tuple(x) for x in dimensions),
            perimeter, value, status, evidence, token))
    if batch_dataset is None:
        if observations or any(x is not None for x in (batch_version, batch_release, batch_inputs, batch_source_uses)):
            raise ValueError("cbr.offices.batch_invalid")
        batch = None
    else:
        batch = ObservationBatch(batch_dataset, batch_version, batch_release, tuple(observations),
            tuple(input_from(item) for item in loads(batch_inputs.encode("utf-8"))),
            tuple(source_use_from(item) for item in loads(batch_source_uses.encode("utf-8"))))
    q = None
    if qualification is not None:
        q = loads(qualification.encode("utf-8"))
        q["excluded_fields"] = tuple(q["excluded_fields"])
        q = ReleaseQualification(**q)
    if (fact_sha is None) != (fact_size is None):
        raise ValueError("cbr.offices.facts_identity_mismatch")
    value = ParsedRelease(as_of, batch, Representation(profile_id, profile_version, media, data, encoding),
        DatasetVersion(dataset_name, release, method, manifest_version, ByteIdentity.of(manifest), manifest),
        count, acquisition_from(acquisition), detail_from(loads(details.encode("utf-8"))) if details is not None else None,
        q, ByteIdentity(fact_sha, fact_size) if fact_sha is not None else None, snapshot.manifest.inputs, facts_method)
    validate_release(value, dataset, profile)
    rebuilt = release_snapshot(value, dataset=dataset, profile=profile,
        dataset_id=snapshot.manifest.dataset_id, version_id=snapshot.manifest.version_id, checkpoint=checkpoint)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("cbr.offices.snapshot_identity_mismatch")
    return value


__all__ = ("release_snapshot", "release_from_snapshot", "validate_release", "detail_value", "detail_from",
           "acquisition_value", "acquisition_from")
