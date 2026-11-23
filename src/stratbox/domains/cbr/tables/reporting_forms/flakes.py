"""All-member reporting-form extraction and explicit portable flake tables."""

from __future__ import annotations

from datetime import date
import re

from stratbox.core.formats.archives.members import ArchiveLimits, extract_members, safe_member_name
from stratbox.core.formats.dbf_lossless import DBFDecodeError, DBFField, DBFRecord, DBFTable, decode_dbf, validate_table
from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from stratbox.domains.cbr.tables.reporting_forms.contracts import FormFlakes, FormKey, FormMember

from stratbox.domains.cbr.publications.catalog import FORM_CODES

SOURCE_FORM_CODES = frozenset(FORM_CODES)
LIMITS = ArchiveLimits(1000, 256 * 1024 * 1024, 128 * 1024 * 1024, 64 * 1024 * 1024)
FLAKES = DataContract("cbr.forms.flakes", 1, DataRole.EXTRACTS)
FLAKE_SNAPSHOT = DataContract("cbr.forms.flakes.snapshot", 1, DataRole.EXTRACTS)
_T, _I, _B, _BIN, _D = ScalarType.TEXT, ScalarType.INTEGER, ScalarType.BOOLEAN, ScalarType.BINARY, ScalarType.DATE


def _schema(name, columns, key=()):
    return TableSchema(DataContract("cbr.forms.flakes." + name, 1, DataRole.EXTRACTS),
                       tuple(ColumnSchema(*column) for column in columns), key)


_META = _schema("metadata", (("form", _T), ("as_of", _D), ("original_sha256", _T),
    ("original_size", _I), ("source_id", _T, True), ("media_type", _T), ("archived", _B), ("method", _T)))
_INVENTORY = _schema("inventory", (("ordinal", _I), ("name", _T), ("sha256", _T),
    ("size", _I), ("status", _T), ("diagnostic", _T, True)), ("ordinal",))
_ORIGINAL = _schema("member_original", (("data", _BIN),))
_HEADER = _schema("header", (("version", _I), ("header_date", _BIN), ("header_length", _I),
    ("record_length", _I), ("language_driver", _I), ("encoding", _T), ("encoding_basis", _T),
    ("eof_marker", _B), ("profile", _T)))
_FIELDS = _schema("fields", (("ordinal", _I), ("name", _T), ("type", _T),
    ("width", _I), ("decimals", _I), ("offset", _I)), ("ordinal",))


def _records_schema(width):
    return _schema("records", (("source_record", _I), ("deleted", _B),
        *((f"value_{index}", _T) for index in range(width))), ("source_record",))


def validate_key(key):
    if (not isinstance(key, FormKey) or type(key.code) is not str
            or re.fullmatch(r"[0-9]{3}", key.code) is None or type(key.as_of) is not date):
        raise ValueError("request.form_key_invalid")
    if key.code not in SOURCE_FORM_CODES:
        raise ValueError("source.form_profile_unsupported")


def validate_flakes(value):
    if not isinstance(value, FormFlakes) or value.method_version != "cbr.forms.flakes.v1":
        raise ValueError("cbr.forms.flakes_invalid")
    validate_key(value.key)
    if (not isinstance(value.original_identity, ByteIdentity) or type(value.archived) is not bool
            or not isinstance(value.members, tuple) or not value.members or len(value.members) > LIMITS.members):
        raise ValueError("cbr.forms.flakes_invalid")
    seen = set()
    dbfs = 0
    for member in value.members:
        if (not isinstance(member, FormMember) or not safe_member_name(member.name)
                or member.name.casefold() in seen or type(member.data) is not bytes
                or ByteIdentity.of(member.data) != member.identity):
            raise ValueError("cbr.forms.member_invalid")
        seen.add(member.name.casefold())
        is_dbf = member.name.lower().endswith(".dbf")
        dbfs += is_dbf
        if member.status == "decoded":
            if not is_dbf or member.table is None or member.diagnostic is not None:
                raise ValueError("cbr.forms.member_status_invalid")
            validate_table(member.table)
            if member.table.source_identity != member.identity:
                raise ValueError("cbr.forms.member_identity_mismatch")
        elif member.status == "auxiliary":
            if is_dbf or member.table is not None or member.diagnostic is not None:
                raise ValueError("cbr.forms.member_status_invalid")
        elif member.status in {"unsupported", "failed"}:
            if not is_dbf or member.table is not None or not member.diagnostic:
                raise ValueError("cbr.forms.member_status_invalid")
        else:
            raise ValueError("cbr.forms.member_status_invalid")
    if not dbfs:
        raise ValueError("source.dbf_missing")
    if not value.archived and (len(value.members) != 1 or value.members[0].identity != value.original_identity):
        raise ValueError("cbr.forms.original_identity_mismatch")


def extract_value(req, invocation, *, rar_reader=None):
    validate_key(req.key)
    if type(req.strict) is not bool:
        raise ValueError("request.strict_invalid")
    overrides = dict(req.encoding_overrides)
    if len(overrides) != len(req.encoding_overrides):
        raise ValueError("request.encoding_overrides_invalid")
    use_payload(req.payload, invocation, role="source_form", limit=LIMITS.packed_bytes)
    archived = req.payload.data.startswith((b"Rar!", b"PK"))
    if req.payload.data.startswith(b"Rar!") and invocation.context.profile == "managed":
        invocation.require_provider("archive_decoder", rar_reader)
    invocation.stage("inventory")
    if archived:
        members = extract_members(req.payload.data, select=lambda names: names,
            limits=LIMITS, rar_reader=rar_reader, budget=invocation.budget,
            checkpoint=invocation.check_cancelled)
    else:
        if not safe_member_name(req.member_name) or not req.member_name.lower().endswith(".dbf"):
            raise ValueError("request.member_name_invalid")
        members = {req.member_name: req.payload.data}
    if set(overrides) - set(members):
        raise ValueError("request.encoding_override_member_missing")
    output = []
    invocation.stage("extract_all_dbf")
    for name, data in members.items():
        invocation.check_cancelled()
        identity = ByteIdentity.of(data)
        table = None
        status, diagnostic = "auxiliary", None
        if name.lower().endswith(".dbf"):
            try:
                table = decode_dbf(data, encoding=overrides.get(name, req.text_encoding),
                    encoding_basis="member_override" if name in overrides else "cbr_default_or_caller",
                    budget=invocation.budget, checkpoint=invocation.check_cancelled)
                status = "decoded"
            except DBFDecodeError as error:
                if req.strict:
                    raise
                diagnostic = str(error)
                status = "unsupported" if any(token in diagnostic for token in ("unsupported", "required")) else "failed"
        if archived:
            payload = SourcePayload(data, "application/x-dbf" if name.lower().endswith(".dbf") else "application/octet-stream",
                                    req.payload.source_id)
            invocation.use(UsedInputReceipt.for_payload(payload,
                "dbf_member" if name.lower().endswith(".dbf") else "auxiliary_member",
                container=req.payload.identity, member=name))
        output.append(FormMember(name, data, identity, status, table, diagnostic))
    result = FormFlakes(req.key, req.payload.identity, req.payload.source_id,
        req.payload.media_type, tuple(output), tuple(invocation.used_inputs), archived)
    validate_flakes(result)
    return result


def flakes_snapshot(value, *, dataset_id, version_id):
    validate_flakes(value)
    tables = [
        ("metadata", TypedTable(_META, ((value.key.code, value.key.as_of,
            value.original_identity.sha256, value.original_identity.size,
            value.source_id, value.media_type, value.archived, value.method_version),))),
        ("inventory", TypedTable(_INVENTORY, tuple((i, member.name, member.identity.sha256,
            member.identity.size, member.status, member.diagnostic) for i, member in enumerate(value.members)))),
    ]
    for index, member in enumerate(value.members):
        prefix = f"member_{index}"
        tables.append((prefix + "_original", TypedTable(_ORIGINAL, ((member.data,),))))
        dbf = member.table
        if dbf is None:
            continue
        tables.extend((
            (prefix + "_header", TypedTable(_HEADER, ((dbf.version, dbf.header_date,
                dbf.header_length, dbf.record_length, dbf.language_driver, dbf.encoding,
                dbf.encoding_basis, dbf.eof_marker, dbf.profile),))),
            (prefix + "_fields", TypedTable(_FIELDS, tuple((i, field.name,
                field.field_type, field.length, field.decimals, field.offset)
                for i, field in enumerate(dbf.fields)))),
            (prefix + "_records", TypedTable(_records_schema(len(dbf.fields)),
                tuple((record.ordinal, record.deleted, *record.values) for record in dbf.records))),
        ))
    return DatasetSnapshot.build(dataset_id, version_id, FLAKE_SNAPSHOT, tuple(tables),
        coverage=SnapshotCoverage("complete" if value.complete else "partial",
            "All regular members of this supplied release; no assertion of publisher historical coverage."),
        inputs=value.lineage)


def flakes_from_snapshot(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != FLAKE_SNAPSHOT):
        raise ValueError("cbr.forms.flake_snapshot_invalid")
    def table(name, schema, single=False):
        try:
            item = snapshot.table(name)
        except KeyError:
            raise ValueError("cbr.forms.flake_snapshot_invalid") from None
        if item.schema != schema or single and len(item.rows) != 1:
            raise ValueError("cbr.forms.flake_snapshot_invalid")
        return item.rows[0] if single else item.rows
    meta = table("metadata", _META, True)
    code, as_of, sha, size, source_id, media_type, archived, method = meta
    inventory = table("inventory", _INVENTORY)
    members, names = [], ["metadata", "inventory"]
    for index, row in enumerate(inventory):
        ordinal, name, sha256, length, status, diagnostic = row
        if ordinal != index:
            raise ValueError("cbr.forms.member_order_invalid")
        prefix = f"member_{index}"
        names.append(prefix + "_original")
        data, = table(prefix + "_original", _ORIGINAL, True)
        identity = ByteIdentity(sha256, length)
        dbf = None
        if status == "decoded":
            names.extend((prefix + "_header", prefix + "_fields", prefix + "_records"))
            header = table(prefix + "_header", _HEADER, True)
            fields = table(prefix + "_fields", _FIELDS)
            if any(row[0] != i for i, row in enumerate(fields)):
                raise ValueError("cbr.forms.field_order_invalid")
            records = table(prefix + "_records", _records_schema(len(fields)))
            dbf = DBFTable(identity, *header[:7],
                tuple(DBFField(*row[1:]) for row in fields),
                tuple(DBFRecord(row[0], row[1], tuple(row[2:])) for row in records),
                header[7], header[8])
        members.append(FormMember(name, data, identity, status, dbf, diagnostic))
    if tuple(name for name, _ in snapshot.tables) != tuple(names):
        raise ValueError("cbr.forms.flake_components_invalid")
    value = FormFlakes(FormKey(code, as_of), ByteIdentity(sha, size), source_id,
        media_type, tuple(members), snapshot.manifest.inputs, archived, method)
    validate_flakes(value)
    if snapshot.manifest.coverage.status != ("complete" if value.complete else "partial"):
        raise ValueError("cbr.forms.flake_coverage_invalid")
    return value


__all__ = ("SOURCE_FORM_CODES", "FLAKES", "FLAKE_SNAPSHOT", "LIMITS", "extract_value",
           "flakes_snapshot", "flakes_from_snapshot", "validate_key", "validate_flakes")
