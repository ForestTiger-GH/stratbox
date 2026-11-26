"""Recognize native distributions without extracting economic content."""

from __future__ import annotations
from io import BytesIO
from typing import BinaryIO
from zipfile import BadZipFile, LargeZipFile, ZipFile


_RAR4 = b"Rar!\x1a\x07\x00"
_RAR5 = b"Rar!\x1a\x07\x01\x00"


def detect_envelope(source: BinaryIO, *, expected: str, size: int) -> str:
    """Verify the ZIP directory or an RAR/PDF signature; preserve input cursor."""
    if expected not in {"pdf", "xlsx", "zip", "rar"}:
        raise ValueError("rosstat.format_unsupported")
    if not 0 < size <= 256 * 1024 * 1024:
        raise ValueError("rosstat.file_size_invalid")
    previous = source.tell()
    try:
        source.seek(0)
        first = source.read(16)
        if first.lstrip().startswith(b"<"):
            raise ValueError("rosstat.original_envelope_mismatch")
        if expected == "pdf":
            if not first.startswith(b"%PDF-") or size < 12:
                raise ValueError("rosstat.original_envelope_mismatch")
            source.seek(max(0, size - 8192))
            if b"%%EOF" not in source.read():
                raise ValueError("rosstat.original_envelope_mismatch")
            return "pdf"
        if expected == "rar":
            if not (first.startswith(_RAR4) or first.startswith(_RAR5)) or size < 16:
                raise ValueError("rosstat.original_envelope_mismatch")
            return "rar"
        if not first.startswith(b"PK"):
            raise ValueError("rosstat.original_envelope_mismatch")
        source.seek(0)
        try:
            with ZipFile(source, "r") as archive:
                names = archive.namelist()
                if not names or len(names) > 20000:
                    raise ValueError("rosstat.archive_members_invalid")
                if expected == "xlsx" and not {
                    "[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"
                } <= set(names):
                    raise ValueError("rosstat.original_envelope_mismatch")
        except (BadZipFile, LargeZipFile, OSError, EOFError):
            raise ValueError("rosstat.original_envelope_mismatch") from None
        return expected
    finally:
        source.seek(previous)


def detect_bytes(source: bytes, *, expected: str) -> str:
    return detect_envelope(BytesIO(source), expected=expected, size=len(source))


def identify(inputs, settings, context):
    from stratbox.shared.data.values import Assessment, IdentifiedMaterial, Material, SourceClaim
    material = inputs["material"]
    publication_id = getattr(settings, "publication_id", settings.source_id)
    if not isinstance(material, Material) or material.source_id not in {None, settings.source_id, publication_id}:
        raise ValueError("rosstat.material_source_conflict")
    expected = context.parameters.get("format", material.metadata.get("format"))
    allowed = getattr(settings, "formats", frozenset({"xlsx"}))
    if expected and expected not in allowed:
        raise ValueError("rosstat.original_envelope_mismatch")
    options = (expected,) if expected else tuple(sorted(allowed))
    detected = None
    for format in options:
        try:
            detected = detect_bytes(material.data, expected=format)
            break
        except ValueError:
            continue
    if detected is None:
        raise ValueError("rosstat.original_envelope_mismatch")
    claim = inputs.get("claim") or SourceClaim(settings.source_id, str(context.parameters.get("issue_id", material.metadata.get("issue_id", ""))),
        str(material.metadata.get("asset_id", "main")))
    if not isinstance(claim, SourceClaim) or claim.source_id != settings.source_id or not claim.issue_id:
        raise ValueError("rosstat.material_claim_conflict")
    if material.metadata.get("issue_id") not in {None, "", claim.issue_id}:
        raise ValueError("rosstat.material_issue_conflict")
    assessment = Assessment(qualifications=frozenset({"native_envelope_verified", "explicit_source_use"}))
    return {"material": IdentifiedMaterial(material, claim, assessment), "assessment": assessment}
