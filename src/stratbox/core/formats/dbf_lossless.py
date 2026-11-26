"""Strict source-local DBF decoding, independent of publisher semantics.

The initial profile accepts classic dBASE III headers (0x03/0x83) and fixed
textual C/N/F/D/L fields. Memo, binary and later dialects require their own
validated profiles. Exact DBF bytes remain a separate original; these records
preserve decoded lexemes after the declared fixed-width padding removal.
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from struct import unpack_from
from typing import BinaryIO, Callable, Iterator

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.values import DBFField, DBFRecord
from stratbox.shared.data.dbf import DBFHeaderEvidence

PROFILE = "dbf.classic-text.v1"
VERSIONS = frozenset({0x03, 0x83})
FIELD_TYPES = frozenset({"C", "N", "F", "D", "L"})


class DBFDecodeError(ValueError):
    """A stable format diagnostic; unsupported input never becomes guessed data."""






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

    @property
    def header(self) -> DBFHeaderEvidence:
        return DBFHeaderEvidence(self.source_identity, self.version, self.header_date,
            self.header_length, self.record_length, len(self.records), self.language_driver,
            self.encoding, self.encoding_basis, self.eof_marker)


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


def _validate_fields(fields: tuple[DBFField, ...], record_length: int) -> None:
    names, offset = set(), 1
    for field in fields:
        if (not field.name or not field.name.isascii() or len(field.name) > 11
                or field.name.casefold() in names
                or any(ord(char) < 33 or ord(char) > 126 for char in field.name)
                or not 1 <= field.length <= 255 or field.offset != offset):
            raise DBFDecodeError("dbf.field_invalid")
        if (field.field_type == "D" and field.length != 8
                or field.field_type == "L" and field.length != 1):
            raise DBFDecodeError("dbf.field_width_invalid")
        names.add(field.name.casefold())
        offset += field.length
    if record_length != offset:
        raise DBFDecodeError("dbf.record_geometry_invalid")


class DBFReader:
    """One strict header and bounded record iterator over a complete original.

    Exhaust the iterator before accepting its header as verified evidence.
    Every consumed byte participates in the expected original identity check.
    No record collection or deletion ledger is allocated by this reader.
    """

    def __init__(self, stream: BinaryIO, source_identity: ByteIdentity, *,
                 encoding: str = "cp866", encoding_basis: str = "caller",
                 max_records: int = 5_000_000, max_cells: int = 50_000_000,
                 budget=None, checkpoint: Callable[[], None] | None = None):
        if not isinstance(source_identity, ByteIdentity):
            raise DBFDecodeError("dbf.source_identity_required")
        if any(type(value) is not int or value < 0 for value in (max_records, max_cells)):
            raise DBFDecodeError("dbf.limits_invalid")
        try:
            encoding = codecs.lookup(encoding).name
        except (TypeError, LookupError):
            raise DBFDecodeError("dbf.encoding_invalid") from None
        if not isinstance(encoding_basis, str) or not encoding_basis:
            raise DBFDecodeError("dbf.encoding_basis_required")
        self.stream, self.budget, self.checkpoint = stream, budget, checkpoint
        self.source_identity = source_identity
        self._digest, self._consumed, self._started, self.verified = sha256(), 0, False, False
        self.stream.seek(0)
        prefix = self._read_exact(32, "dbf.header_truncated")
        if prefix[0] not in VERSIONS:
            raise DBFDecodeError("dbf.dialect_unsupported")
        if prefix[14] or prefix[15]:
            raise DBFDecodeError("dbf.transaction_or_encryption_unsupported")
        count, header_length, record_length = unpack_from("<IHH", prefix, 4)
        if (header_length < 65 or header_length > source_identity.size
                or (header_length - 33) % 32):
            raise DBFDecodeError("dbf.header_geometry_invalid")
        fields_count = (header_length - 33) // 32
        if count > max_records or count * fields_count > max_cells:
            raise DBFDecodeError("dbf.cell_limit")
        if budget is not None:
            budget.check("cells", count * fields_count)
        expected = header_length + count * record_length
        if expected > source_identity.size:
            raise DBFDecodeError("dbf.records_truncated")
        if source_identity.size - expected not in (0, 1):
            raise DBFDecodeError("dbf.trailing_data")
        descriptors = self._read_exact(header_length - 32, "dbf.header_truncated")
        if descriptors[-1] != 0x0D:
            raise DBFDecodeError("dbf.header_geometry_invalid")
        fields, offset = [], 1
        for position in range(0, len(descriptors) - 1, 32):
            descriptor = descriptors[position:position + 32]
            try:
                name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="strict")
                kind = descriptor[11:12].decode("ascii", errors="strict")
            except UnicodeError:
                raise DBFDecodeError("dbf.field_encoding_invalid") from None
            if kind in {"M", "G", "P"}:
                raise DBFDecodeError("dbf.memo_companion_required")
            if kind in {"B", "I", "+", "Y", "O", "T", "@"}:
                raise DBFDecodeError("dbf.binary_dialect_unsupported")
            if kind not in FIELD_TYPES:
                raise DBFDecodeError("dbf.field_type_unsupported")
            fields.append(DBFField(name, kind, descriptor[16], descriptor[17], offset))
            offset += descriptor[16]
        self.fields = tuple(fields)
        _validate_fields(self.fields, record_length)
        self.header = DBFHeaderEvidence(source_identity, prefix[0], prefix[1:4],
            header_length, record_length, count, prefix[29], encoding, encoding_basis,
            source_identity.size == expected + 1)

    def _read_exact(self, size: int, diagnostic: str) -> bytes:
        chunks, remaining = [], size
        while remaining:
            if self.checkpoint is not None:
                self.checkpoint()
            if self.budget is not None:
                self.budget.checkpoint()
            chunk = self.stream.read(min(65536, remaining))
            if not isinstance(chunk, bytes) or not chunk:
                raise DBFDecodeError(diagnostic)
            if len(chunk) > remaining:
                raise DBFDecodeError("dbf.reader_contract_invalid")
            self._digest.update(chunk)
            self._consumed += len(chunk)
            if self.budget is not None:
                self.budget.charge("decoded_bytes", len(chunk))
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def records(self) -> Iterator[DBFRecord]:
        if self._started:
            raise DBFDecodeError("dbf.records_already_consumed")
        self._started = True
        for index in range(self.header.record_count):
            row = self._read_exact(self.header.record_length, "dbf.records_truncated")
            if row[0] not in (0x20, 0x2A):
                raise DBFDecodeError("dbf.deletion_flag_invalid")
            values = []
            for field in self.fields:
                raw = row[field.offset:field.offset + field.length]
                try:
                    token = raw.decode(self.header.encoding if field.field_type == "C" else "ascii", errors="strict")
                except UnicodeError:
                    raise DBFDecodeError("dbf.value_encoding_invalid") from None
                values.append(token.rstrip(" \x00") if field.field_type == "C" else token.strip(" \x00"))
            if self.budget is not None:
                self.budget.charge("cells", len(self.fields))
            yield DBFRecord(index + 1, row[0] == 0x2A, tuple(values))
        if self.header.eof_marker and self._read_exact(1, "dbf.records_truncated") != b"\x1a":
            raise DBFDecodeError("dbf.trailing_data")
        if self.stream.read(1):
            raise DBFDecodeError("dbf.trailing_data")
        if ByteIdentity(self._digest.hexdigest(), self._consumed) != self.source_identity:
            raise DBFDecodeError("dbf.source_identity_mismatch")
        self.verified = True


def decode_dbf_stream(stream: BinaryIO, source_identity: ByteIdentity, **options) -> DBFTable:
    reader = DBFReader(stream, source_identity, **options)
    records = tuple(reader.records())
    header = reader.header
    return DBFTable(header.source_identity, header.version, header.header_date,
        header.header_length, header.record_length, header.language_driver,
        header.encoding, header.encoding_basis, reader.fields, records, header.eof_marker)


def decode_dbf(data: bytes, *, encoding: str = "cp866", encoding_basis: str = "caller",
               max_records: int = 5_000_000, max_cells: int = 50_000_000,
               budget=None, checkpoint: Callable[[], None] | None = None) -> DBFTable:
    """Collect the shared strict reader under explicit row/cell limits."""
    if type(data) is not bytes or len(data) < 33:
        raise DBFDecodeError("dbf.header_truncated")
    return decode_dbf_stream(BytesIO(data), ByteIdentity.of(data), encoding=encoding,
        encoding_basis=encoding_basis, max_records=max_records, max_cells=max_cells,
        budget=budget, checkpoint=checkpoint)


__all__ = ("DBFDecodeError", "DBFField", "DBFRecord", "DBFTable", "DBFReader",
           "decode_dbf", "decode_dbf_stream", "validate_table", "PROFILE")
