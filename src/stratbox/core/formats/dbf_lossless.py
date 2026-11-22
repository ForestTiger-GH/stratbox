"""Strict source-local DBF decoding, independent of publisher semantics.

The initial profile accepts classic dBASE III headers (0x03/0x83) and fixed
textual C/N/F/D/L fields. Memo, binary and later dialects require their own
validated profiles. Exact DBF bytes remain a separate original; these records
preserve decoded lexemes after the declared fixed-width padding removal.
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from struct import unpack_from
from typing import Callable

from stratbox.shared.identity import ByteIdentity

PROFILE = "dbf.classic-text.v1"
VERSIONS = frozenset({0x03, 0x83})
FIELD_TYPES = frozenset({"C", "N", "F", "D", "L"})


class DBFDecodeError(ValueError):
    """A stable format diagnostic; unsupported input never becomes guessed data."""


@dataclass(frozen=True, slots=True)
class DBFField:
    name: str
    field_type: str
    length: int
    decimals: int
    offset: int


@dataclass(frozen=True, slots=True)
class DBFRecord:
    ordinal: int
    deleted: bool
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DBFTable:
    source_identity: ByteIdentity
    version: int
    header_date: bytes
    header_length: int
    record_length: int
    language_driver: int
    encoding: str
    encoding_basis: str
    fields: tuple[DBFField, ...]
    records: tuple[DBFRecord, ...]
    eof_marker: bool
    profile: str = PROFILE


def validate_table(table: DBFTable) -> None:
    """Validate a persisted decoded table without reading its original again."""
    if (not isinstance(table, DBFTable) or table.profile != PROFILE
            or table.version not in VERSIONS or type(table.header_date) is not bytes
            or len(table.header_date) != 3 or not isinstance(table.source_identity, ByteIdentity)
            or type(table.language_driver) is not int or not 0 <= table.language_driver <= 255
            or type(table.eof_marker) is not bool or not table.encoding_basis):
        raise DBFDecodeError("dbf.table_invalid")
    try:
        codecs.lookup(table.encoding)
    except (TypeError, LookupError):
        raise DBFDecodeError("dbf.encoding_invalid") from None
    if (not isinstance(table.fields, tuple) or not table.fields
            or not isinstance(table.records, tuple)
            or table.header_length != 33 + 32 * len(table.fields)):
        raise DBFDecodeError("dbf.header_geometry_invalid")
    offset = 1
    names = set()
    for field in table.fields:
        if (not isinstance(field, DBFField) or not field.name or not field.name.isascii()
                or len(field.name) > 11 or field.name.casefold() in names
                or any(ord(c) < 33 or ord(c) > 126 for c in field.name)
                or field.field_type not in FIELD_TYPES or type(field.length) is not int
                or not 1 <= field.length <= 255 or type(field.decimals) is not int
                or not 0 <= field.decimals <= 255 or field.offset != offset):
            raise DBFDecodeError("dbf.field_invalid")
        if (field.field_type == "D" and field.length != 8
                or field.field_type == "L" and field.length != 1):
            raise DBFDecodeError("dbf.field_width_invalid")
        names.add(field.name.casefold())
        offset += field.length
    if table.record_length != offset:
        raise DBFDecodeError("dbf.record_geometry_invalid")
    expected = table.header_length + table.record_length * len(table.records) + int(table.eof_marker)
    if expected != table.source_identity.size:
        raise DBFDecodeError("dbf.file_geometry_invalid")
    for ordinal, record in enumerate(table.records, 1):
        if (not isinstance(record, DBFRecord) or type(record.ordinal) is not int
                or record.ordinal != ordinal or type(record.deleted) is not bool
                or not isinstance(record.values, tuple) or len(record.values) != len(table.fields)
                or any(type(value) is not str for value in record.values)):
            raise DBFDecodeError("dbf.record_invalid")


def decode_dbf(data: bytes, *, encoding: str = "cp866", encoding_basis: str = "caller",
               max_records: int = 5_000_000, max_cells: int = 50_000_000,
               budget=None, checkpoint: Callable[[], None] | None = None) -> DBFTable:
    """Keep row order, deletion flags, code zeros and unparsed date/number tokens."""
    if type(data) is not bytes or len(data) < 33:
        raise DBFDecodeError("dbf.header_truncated")
    if data[0] not in VERSIONS:
        raise DBFDecodeError("dbf.dialect_unsupported")
    if data[14] or data[15]:
        raise DBFDecodeError("dbf.transaction_or_encryption_unsupported")
    try:
        encoding = codecs.lookup(encoding).name
    except (TypeError, LookupError):
        raise DBFDecodeError("dbf.encoding_invalid") from None
    count, header_length, record_length = unpack_from("<IHH", data, 4)
    if (header_length < 65 or header_length > len(data)
            or (header_length - 33) % 32 or data[header_length - 1] != 0x0D):
        raise DBFDecodeError("dbf.header_geometry_invalid")
    fields_count = (header_length - 33) // 32
    if count > max_records or count * fields_count > max_cells:
        raise DBFDecodeError("dbf.cell_limit")
    if budget is not None:
        budget.check("cells", count * fields_count)
    expected = header_length + count * record_length
    if expected > len(data):
        raise DBFDecodeError("dbf.records_truncated")
    tail = data[expected:]
    if tail not in {b"", b"\x1a"}:
        raise DBFDecodeError("dbf.trailing_data")
    fields = []
    offset = 1
    for position in range(32, header_length - 1, 32):
        descriptor = data[position:position + 32]
        raw_name = descriptor[:11].split(b"\x00", 1)[0]
        try:
            name = raw_name.decode("ascii", errors="strict")
            kind = descriptor[11:12].decode("ascii", errors="strict")
        except UnicodeError:
            raise DBFDecodeError("dbf.field_encoding_invalid") from None
        if kind in {"M", "G", "P", "B"}:
            raise DBFDecodeError("dbf.companion_or_binary_profile_required")
        if kind not in FIELD_TYPES:
            raise DBFDecodeError("dbf.field_type_unsupported")
        field = DBFField(name, kind, descriptor[16], descriptor[17], offset)
        fields.append(field)
        offset += field.length
    if record_length != offset:
        raise DBFDecodeError("dbf.record_geometry_invalid")
    records = []
    for index in range(count):
        if index % 4096 == 0:
            if checkpoint is not None:
                checkpoint()
            if budget is not None:
                budget.checkpoint()
        start = header_length + index * record_length
        flag = data[start]
        if flag not in {0x20, 0x2A}:
            raise DBFDecodeError("dbf.deletion_flag_invalid")
        values = []
        for field in fields:
            raw = data[start + field.offset:start + field.offset + field.length]
            try:
                token = raw.decode(encoding if field.field_type == "C" else "ascii", errors="strict")
            except UnicodeError:
                raise DBFDecodeError("dbf.value_encoding_invalid") from None
            values.append(token.rstrip(" \x00") if field.field_type == "C" else token.strip(" \x00"))
        records.append(DBFRecord(index + 1, flag == 0x2A, tuple(values)))
    result = DBFTable(ByteIdentity.of(data), data[0], data[1:4], header_length,
                      record_length, data[29], encoding, encoding_basis,
                      tuple(fields), tuple(records), tail == b"\x1a")
    validate_table(result)
    if budget is not None:
        budget.charge("cells", count * fields_count)
    return result


__all__ = ("DBFDecodeError", "DBFField", "DBFRecord", "DBFTable", "decode_dbf", "validate_table", "PROFILE")
