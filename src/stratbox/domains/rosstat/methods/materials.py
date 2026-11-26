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
                actual = "zip"
                if {"[Content_Types].xml", "xl/workbook.xml"} <= set(names):
                    content_types = archive.getinfo("[Content_Types].xml")
                    if content_types.file_size > 1_000_000:
                        raise ValueError("rosstat.archive_members_invalid")
                    actual = ("xlsm" if "xl/vbaProject.bin" in names or b"macroenabled" in archive.read(content_types).lower()
                        else "xlsx")
                elif {"[Content_Types].xml", "xl/workbook.bin"} <= set(names):
                    actual = "xlsb"
                if actual != expected:
                    raise ValueError("rosstat.original_envelope_mismatch")
        except (BadZipFile, LargeZipFile, OSError, EOFError):
            raise ValueError("rosstat.original_envelope_mismatch") from None
        return expected
    finally:
        source.seek(previous)


def detect_bytes(source: bytes, *, expected: str) -> str:
    return detect_envelope(BytesIO(source), expected=expected, size=len(source))


def identify(inputs, settings, context):
    from collections.abc import Mapping
    from stratbox.shared.data.materials import MaterialInspection, StagedMaterialRef
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
    from stratbox.shared.data.values import (Assessment, FetchEvidence, IdentifiedMaterial, ImmutableMaterialRef,
        Material, PublicationAsset, RequestSpec, SourceClaim, request_identity)
    supplied = inputs["material"]
    material = supplied.material if isinstance(supplied, IdentifiedMaterial) else supplied
    publication_id = getattr(settings, "publication_id", settings.source_id)
    if not isinstance(material, (Material, ImmutableMaterialRef, StagedMaterialRef)) or material.source_id not in {None, settings.source_id, publication_id}:
        raise ValueError("rosstat.material_source_conflict")
    asset = inputs.get("asset")
    if asset is not None and (not isinstance(asset, PublicationAsset) or asset.source_id not in {settings.source_id, publication_id}):
        raise ValueError("rosstat.material_source_conflict")
    expected = asset.format if asset is not None else context.parameters.get("format", material.metadata.get("format"))
    allowed = getattr(settings, "formats", frozenset({"xlsx"}))
    if expected and expected not in allowed:
        raise ValueError("rosstat.original_envelope_mismatch")
    inspection = inputs.get("inspection")
    detected = None
    if inspection is not None:
        if not isinstance(inspection, MaterialInspection) or inspection.identity != material.identity:
            raise ValueError("rosstat.material_inspection_mismatch")
        verify = getattr(context, "verify_material_inspection", None)
        if verify is not None and verify(inspection, material):
            detected = inspection.format
    if detected is None and isinstance(material, Material):
        for format in (expected,) if expected else tuple(sorted(allowed)):
            try:
                detected = detect_bytes(material.data, expected=format)
                break
            except ValueError:
                continue
    if detected not in allowed or expected is not None and detected != expected:
        raise ValueError("rosstat.original_envelope_mismatch")
    if inspection is not None and inspection.format != detected:
        raise ValueError("rosstat.material_inspection_mismatch")
    source = material.source_id or settings.source_id
    issue = asset.issue_id if asset is not None else str(context.parameters.get("issue_id", material.metadata.get("issue_id", "")))
    asset_id = asset.asset_id if asset is not None else str(material.metadata.get("asset_id", "main"))
    request, fetch = inputs.get("request"), inputs.get("evidence")
    verified = (isinstance(request, RequestSpec) and isinstance(fetch, FetchEvidence)
        and request.source_id == source and fetch.request_identity == request_identity(request)
        and fetch.material_identity == material.identity
        and (200 <= fetch.status_code < 300 or fetch.status_code == 304
            and getattr(fetch, "validation_kind", "body") == "retained_validation"
            and bool(getattr(fetch, "retained_effect_id", None))
            and bool(getattr(fetch, "representation_identity", None))))
    if request is not None:
        from .publications import _file_url
        if not isinstance(request, RequestSpec) or not _file_url(request.url) or request.source_id != source:
            raise ValueError("rosstat.material_request_mismatch")
        if asset is not None and request.url != asset.locator:
            raise ValueError("rosstat.material_asset_mismatch")
        if isinstance(fetch, FetchEvidence):
            from hashlib import sha256
            from urllib.parse import urlsplit
            expected_target = sha256(request.url.encode()).hexdigest()
            if fetch.route_id is not None:
                verified = verified and fetch.logical_target_identity == expected_target
            elif fetch.effective_locator is not None and urlsplit(fetch.effective_locator).path not in {"", "/"}:
                if not _file_url(fetch.effective_locator):
                    raise ValueError("rosstat.material_request_mismatch")
                verified = verified and fetch.effective_locator == request.url
            else:
                verified = verified and fetch.actual_target_identity == expected_target
    if verified:
        accepted = getattr(context, "accepted_input", None)
        record = accepted("evidence") if accepted is not None else None
        producer = record.get("produced_by") if isinstance(record, Mapping) else getattr(record, "produced_by", None)
        verified = producer in {"command.material.fetch", "command.material.receive"}
    # Opaque media-bank addresses attest transport independently of the
    # publisher-label relationship supplied with the selected asset.
    claim = inputs.get("claim") or SourceClaim(source, issue, asset_id, "recognized" if asset is not None else "asserted")
    if (not isinstance(claim, SourceClaim) or claim.source_id != source or not claim.issue_id
            or claim.issue_id != issue or claim.asset_id != asset_id):
        raise ValueError("rosstat.material_claim_conflict")
    if material.metadata.get("issue_id") not in {None, "", claim.issue_id}:
        raise ValueError("rosstat.material_issue_conflict")
    if claim.attribution == "verified":
        raise ValueError("rosstat.source_attribution_not_established")
    uses = tuple(getattr(supplied, "source_uses", ()))
    if asset is not None:
        uses += (SourceUse(SourceCoordinate(source_id=source, issue_id=issue,
            asset_id=asset_id, material_identity=material.identity), "publication_acquisition", "explicit_selected_asset",
            "sha256:" + material.identity.sha256),)
    assessment = Assessment(qualifications=frozenset({"native_envelope_verified",
        "verified_transport" if verified else "unverified_transport",
        "explicit_selected_asset" if asset is not None else "explicit_source_use"}))
    return {"material": IdentifiedMaterial(material, claim, assessment,
        source_uses=tuple(dict.fromkeys(uses))), "assessment": assessment}
