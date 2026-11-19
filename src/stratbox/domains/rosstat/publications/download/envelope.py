"""Recognize native distributions without extracting economic content."""

from __future__ import annotations
from io import BytesIO
from typing import BinaryIO
from zipfile import BadZipFile, LargeZipFile, ZipFile
from stratbox.core.execution import OperationFailure

_RAR4 = b"Rar!\x1a\x07\x00"
_RAR5 = b"Rar!\x1a\x07\x01\x00"


def detect_envelope(source: BinaryIO, *, expected: str, size: int) -> str:
    """Verify the ZIP directory or an RAR/PDF signature; preserve input cursor."""
    if expected not in {"pdf", "xlsx", "zip", "rar"}:
        raise OperationFailure("rosstat.format_unsupported")
    if not 0 < size <= 256 * 1024 * 1024:
        raise OperationFailure("rosstat.file_size_invalid")
    previous = source.tell()
    try:
        source.seek(0)
        first = source.read(16)
        if first.lstrip().startswith(b"<"):
            raise OperationFailure("rosstat.original_envelope_mismatch")
        if expected == "pdf":
            if not first.startswith(b"%PDF-") or size < 12:
                raise OperationFailure("rosstat.original_envelope_mismatch")
            source.seek(max(0, size - 8192))
            if b"%%EOF" not in source.read():
                raise OperationFailure("rosstat.original_envelope_mismatch")
            return "pdf"
        if expected == "rar":
            if not (first.startswith(_RAR4) or first.startswith(_RAR5)) or size < 16:
                raise OperationFailure("rosstat.original_envelope_mismatch")
            return "rar"
        if not first.startswith(b"PK"):
            raise OperationFailure("rosstat.original_envelope_mismatch")
        source.seek(0)
        try:
            with ZipFile(source, "r") as archive:
                names = archive.namelist()
                if not names or len(names) > 20000:
                    raise OperationFailure("rosstat.archive_members_invalid")
                if expected == "xlsx" and not {
                    "[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"
                } <= set(names):
                    raise OperationFailure("rosstat.original_envelope_mismatch")
        except (BadZipFile, LargeZipFile, OSError, EOFError):
            raise OperationFailure("rosstat.original_envelope_mismatch") from None
        return expected
    finally:
        source.seek(previous)


def detect_bytes(source: bytes, *, expected: str) -> str:
    return detect_envelope(BytesIO(source), expected=expected, size=len(source))
