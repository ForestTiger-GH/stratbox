"""SME flake snapshots preserve all levels, field order, JSON kinds and literal tokens."""
from dataclasses import replace
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, TableSchema, TypedTable

from ..contracts import JsonField, JsonFlake, JsonRecord
from ..snapshots import context_table, read_context
from .extraction import _DECODER, _kind

FLAKE = DataContract("fns.sme.full_json.snapshot", 1, DataRole.EXTRACTS)
_I, _T = ScalarType.INTEGER, ScalarType.TEXT
_RECORDS = TableSchema(DataContract("fns.sme.json.records", 1), (ColumnSchema("ordinal", _I),), ("ordinal",))
_FIELDS = TableSchema(DataContract("fns.sme.json.fields", 1), (
    ColumnSchema("record", _I), ColumnSchema("ordinal", _I), ColumnSchema("name", _T),
    ColumnSchema("kind", _T), ColumnSchema("raw_token", _T),
), ("record", "ordinal"))


def flake_snapshot(value, *, dataset_id=None, version_id=None):
    if not isinstance(value, JsonFlake) or value.context.series_id != "fns.sme":
        raise ValueError("fns.sme.flake_invalid")
    if value.profile_id != "fns.sme.full-json.v1":
        raise ValueError("fns.sme.flake_profile_unknown")
    fields = []
    for ordinal, record in enumerate(value.records):
        if record.ordinal != ordinal or len({item.name for item in record.fields}) != len(record.fields):
            raise ValueError("fns.sme.flake_records_invalid")
        for index, item in enumerate(record.fields):
            decoded, end = _DECODER.raw_decode(item.raw_token)
            if end != len(item.raw_token) or _kind(decoded) != item.kind:
                raise ValueError("fns.sme.flake_field_invalid")
            fields.append((ordinal, index, item.name, item.kind, item.raw_token))
    if not value.records or not any(item.identity == value.source_identity for item in value.lineage):
        raise ValueError("fns.sme.flake_lineage_invalid")
    result = DatasetSnapshot.build(dataset_id or "fns.sme.flake",
        version_id or "content", FLAKE,
        (("context", context_table(value.context, value.source_identity, value.profile_id)),
         ("records", TypedTable(_RECORDS, tuple((item.ordinal,) for item in value.records))),
         ("fields", TypedTable(_FIELDS, tuple(fields)))),
        coverage=value.coverage, inputs=value.lineage)
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def flake_from_snapshot(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != FLAKE
            or tuple(name for name, _ in snapshot.tables) != ("context", "records", "fields")
            or snapshot.table("records").schema != _RECORDS or snapshot.table("fields").schema != _FIELDS):
        raise ValueError("fns.sme.flake_snapshot_invalid")
    context, identity, profile, qualifications, dispositions, details = read_context(snapshot.table("context"))
    if qualifications or dispositions or details != "{}":
        raise ValueError("fns.sme.flake_snapshot_context_invalid")
    groups = {row[0]: [] for row in snapshot.table("records").rows}
    for record, ordinal, name, kind, token in snapshot.table("fields").rows:
        if record not in groups or ordinal != len(groups[record]):
            raise ValueError("fns.sme.flake_snapshot_field_order_invalid")
        groups[record].append(JsonField(name, kind, token))
    result = JsonFlake(context, identity, tuple(JsonRecord(key, tuple(items)) for key, items in groups.items()),
                       snapshot.manifest.inputs, profile, snapshot.manifest.coverage)
    if flake_snapshot(result, dataset_id=snapshot.manifest.dataset_id,
                      version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.sme.flake_snapshot_identity_mismatch")
    return result
