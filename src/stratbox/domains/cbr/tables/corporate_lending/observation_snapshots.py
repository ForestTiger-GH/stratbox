"""Stable, data-only encodings of corporate source observations."""
from dataclasses import asdict
import json

from stratbox.core.formats.dataframes import frame_to_table, frame_from_table
from stratbox.shared.data.lineage import computation_value, computation_from, input_value, input_from
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.data.tables import TABLE_ENCODING, table_identity
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity
from .observations import CorporateSourceDataset, _PROFILES, _COLUMNS

CONTRACT = DataContract("cbr.corporate_lending.source_observations.snapshot", 1, DataRole.EXTRACTS)
FRAME_CONTRACT = DataContract("cbr.corporate_lending.source_observations.table", 1, DataRole.EXTRACTS)
_CONTEXT = TableSchema(DataContract("cbr.corporate_lending.source_observations.context", 1, DataRole.EXTRACTS),
                      (ColumnSchema("context", ScalarType.TEXT),))


def metadata(value):
    return {"series_id": value.series_id, "issue_id": value.issue_id, "asset_id": value.asset_id,
            "source_identity": asdict(value.source_identity),
            "profile_id": value.profile_id, "profile_version": value.profile_version,
            "available_periods": value.available_periods, "selected_periods": value.selected_periods,
            "diagnostics": value.diagnostics, "coverage": asdict(value.coverage),
            "lineage": [input_value(item) for item in value.lineage]}


def identity(value):
    table = table_identity((("observations", value.observations),))
    return ByteIdentity.of(canonical_manifest_bytes({"encoding": TABLE_ENCODING,
        "tables": [table.sha256, table.size], "metadata": metadata(value)}))


def validate(value, *, require_seal=False):
    if (not isinstance(value, CorporateSourceDataset) or value.series_id not in _PROFILES
            or tuple(value.observations.columns) != _COLUMNS or value.observations.empty
            or value.profile_version != 1 or not set(value.selected_periods) <= set(value.available_periods)
            or set(value.observations["series_id"]) != {value.series_id}
            or set(value.observations["issue_id"]) != {value.issue_id}
            or set(value.observations["period"]) != set(value.selected_periods)
            or value.observations.duplicated(["sheet", "row", "column"]).any()):
        raise ValueError("cbr.corporate.observation_contract_invalid")
    try:
        SourceAssetIdentity(value.series_id, value.issue_id, value.asset_id)
    except ValueError:
        raise ValueError("cbr.corporate.observation_asset_invalid") from None
    profile = _PROFILES[value.series_id]
    if value.profile_id != "cbr.corporate.observations." + profile.publisher_code.lower():
        raise ValueError("cbr.corporate.observation_profile_invalid")
    if require_seal and value.evidence is None:
        raise ValueError("cbr.corporate.observation_seal_required")
    if value.evidence is not None and value.evidence.output != identity(value):
        raise ValueError("cbr.corporate.observation_identity_mismatch")


def snapshot(value, *, dataset_id="cbr.corporate_lending.source_observations", version_id=None, checkpoint=None):
    validate(value, require_seal=True)
    table, descriptor = frame_to_table(value.observations, contract=FRAME_CONTRACT, checkpoint=checkpoint)
    body = canonical_manifest_bytes({**metadata(value), "descriptor": descriptor,
        "lineage": [input_value(item) for item in value.lineage], "evidence": computation_value(value.evidence)})
    if len(body) > 16 * 1024 * 1024:
        raise ValueError("cbr.corporate.observation_metadata_limit")
    return DatasetSnapshot.build(dataset_id, version_id or value.evidence.output.sha256, CONTRACT,
        (("context", TypedTable(_CONTEXT, ((body.decode("utf-8"),),))), ("observations", table)),
        coverage=value.coverage, inputs=value.evidence.inputs)


def from_snapshot(value, *, checkpoint=None):
    if (not isinstance(value, DatasetSnapshot) or value.manifest.contract != CONTRACT or not value.complete
            or tuple(name for name, _ in value.tables) != ("context", "observations")):
        raise ValueError("cbr.corporate.observation_snapshot_invalid")
    context, table = value.table("context"), value.table("observations")
    if context.schema != _CONTEXT or len(context.rows) != 1 or table.schema.contract != FRAME_CONTRACT:
        raise ValueError("cbr.corporate.observation_snapshot_invalid")
    raw = context.rows[0][0].encode("utf-8")
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("cbr.corporate.observation_metadata_limit")
    data = json.loads(raw)
    if canonical_manifest_bytes(data) != raw or set(data) != {
            "series_id", "issue_id", "asset_id", "source_identity", "profile_id", "profile_version", "available_periods",
            "selected_periods", "diagnostics", "coverage", "descriptor", "lineage", "evidence"}:
        raise ValueError("cbr.corporate.observation_snapshot_invalid")
    result = CorporateSourceDataset(data["series_id"], data["issue_id"], ByteIdentity(**data["source_identity"]),
        data["profile_id"], data["profile_version"], frame_from_table(table, data["descriptor"], checkpoint=checkpoint),
        tuple(data["available_periods"]), tuple(data["selected_periods"]), tuple(tuple(item) for item in data["diagnostics"]),
        SnapshotCoverage(**data["coverage"]), tuple(input_from(item) for item in data["lineage"]),
        computation_from(data["evidence"]), asset_id=data["asset_id"])
    validate(result, require_seal=True)
    return result
