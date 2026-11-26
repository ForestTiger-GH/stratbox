"""Prepare requests, acquire and inspect supplied materials through explicit providers."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, FetchEvidence, IdentifiedMaterial, ImmutableMaterialRef, Material, PublicationAsset, ReadEvidence, RequestSpec, SourceClaim, fingerprint, request_identity
from ._settings import _get, _option
from ._values import _material, _carrier
from ._storage import _provider_scope, _read


def request_prepare(inputs, settings, context):
    locator = inputs.get("locator") or _option(context, settings, "url")
    if hasattr(locator, "locator"):
        locator = locator.locator
    if isinstance(locator, Mapping):
        locator = locator.get("url", locator.get("locator"))
    if not isinstance(locator, str):
        raise ExecutionFailure("request.locator_required")
    return {"request": RequestSpec(locator, _option(context, settings, "method", "GET"),
        _get(settings, "headers", {}), _get(settings, "body"), _get(settings, "form"),
        _option(context, settings, "max_bytes", 16 * 1024 * 1024), _option(context, settings, "timeout", 60),
        source_id=_get(settings, "source_id"), observation_id=context.run_id)}


from .acquisition_http import material_fetch, material_receive


def _request_identity(request):
    return request_identity(request)


def material_read(inputs, settings, context):
    location = inputs["location"]
    expected = getattr(location, "identity", None)
    path = getattr(location, "location", getattr(location, "locator", getattr(location, "path", location)))
    if isinstance(location, Mapping):
        path = location.get("location", location.get("path", location.get("locator")))
        expected = location.get("identity")
    metadata = {**dict(getattr(location, "metadata", {})), "location": str(path)}
    expected = expected or metadata.get("identity") or _option(context, settings, "expected_identity")
    placement = _option(context, settings, "placement", "buffered")
    if placement not in {"buffered", "staged"}:
        raise ExecutionFailure("material.placement_invalid")
    store = context.provider("filestore")
    if isinstance(location, ImmutableMaterialRef) and location.provider_scope != _provider_scope(store, path):
        raise ExecutionFailure("storage.provider_scope_conflict")
    if expected is None and placement == "staged" and callable(getattr(store, "inspect_file", None)):
        expected = store.inspect_file(str(path)).identity
    if placement == "staged":
        from stratbox.core.storage.readable import open_provider, copy_stream
        limit = _option(context, settings, "max_bytes", 16 * 1024**3)
        metadata.setdefault("filename", Path(str(path)).name)
        source_id = getattr(location, "source_id", None) or _get(settings, "source_id", metadata.get("source_id"))
        if isinstance(location, PublicationAsset):
            metadata.update(dict(location.metadata), issue_id=location.issue_id, asset_id=location.asset_id, format=location.format)
        with context.stage(source_id=source_id, metadata=metadata,
                media_type=_get(settings, "media_type", metadata.get("media_type", "application/octet-stream")),
                lineage=tuple(getattr(location, "lineage", ())),
                source_uses=tuple(getattr(location, "source_uses", ()))) as stage:
            with open_provider(store, path) as stream:
                identity = copy_stream(stream, stage.stream, limit=limit, expected=expected,
                    checkpoint=context.checkpoint, budget=context.budget, resource="input_bytes")
            evidence = ReadEvidence(str(path), identity, datetime.now(timezone.utc), _provider_scope(store, path),
                                    "identity_checked" if expected is not None else "observed_copy")
            material = stage.seal(lineage=(*tuple(getattr(location, "lineage", ())), evidence))
        return {"material": material, "evidence": evidence}
    data = _read(context.provider("filestore"), path, _option(context, settings, "max_bytes", 128 * 1024 * 1024))
    if getattr(context, "budget", None): context.budget.charge("input_bytes", len(data))
    source_id = getattr(location, "source_id", _get(settings, "source_id", getattr(location, "metadata", {}).get("source_id")))
    metadata.setdefault("filename", Path(str(path)).name)
    if isinstance(location, PublicationAsset):
        metadata.update(dict(location.metadata), issue_id=location.issue_id, asset_id=location.asset_id, format=location.format)
    value = Material(data, _get(settings, "media_type", metadata.get("media_type", "application/octet-stream")), source_id, metadata=metadata,
        lineage=tuple(getattr(location, "lineage", ())))
    if expected is not None and expected != value.identity:
        raise ExecutionFailure("storage.identity_mismatch")
    evidence = ReadEvidence(str(path), value.identity, datetime.now(timezone.utc), _provider_scope(store, path),
                            "identity_checked" if expected is not None else "observed_copy")
    from dataclasses import replace
    return {"material": replace(value, lineage=(*value.lineage, evidence)), "evidence": evidence}


def material_list(inputs, settings, context):
    store, location = context.provider("filestore"), inputs["location"]
    limit = _option(context, settings, "max_items", 10000)
    listing = getattr(store, "list", None) or getattr(store, "listdir", None)
    if listing is None:
        raise ExecutionFailure("storage.list_protocol")
    result = []
    for item in listing(str(location)):
        context.checkpoint()
        if len(result) == limit:
            raise ExecutionFailure("storage.inventory_limit")
        if isinstance(item, Mapping):
            result.append(dict(item))
        else:
            candidate = str(item)
            path = candidate if Path(candidate).is_absolute() or str(location) in Path(candidate).parents else str(Path(str(location)) / candidate)
            metadata = {"path": path, "filename": Path(candidate).name}
            stat = getattr(store, "stat", None)
            if stat:
                state = stat(path)
                metadata.update(size=state.st_size, mtime=state.st_mtime_ns)
            result.append(metadata)
    return {"inventory": tuple(sorted(result, key=lambda item: item["path"]))}


def material_identify(inputs, settings, context):
    original, claim = inputs["material"], inputs.get("claim") or _get(settings, "claim")
    if isinstance(original, IdentifiedMaterial):
        if claim and original.claim.source_id != claim.source_id:
            raise ExecutionFailure("source.context_conflict")
        return {"material": original, "assessment": original.assessment}
    original = _carrier(original)
    if claim is None and inputs.get("request") is not None:
        request, evidence, asset = inputs["request"], inputs.get("evidence"), inputs.get("asset")
        if (not isinstance(request, RequestSpec) or not isinstance(evidence, FetchEvidence)
                or evidence.material_identity != original.identity or evidence.request_identity != _request_identity(request)):
            raise ExecutionFailure("source.acquisition_evidence_conflict")
        if isinstance(asset, PublicationAsset):
            if asset.locator != request.url or request.source_id not in {None, asset.source_id}:
                raise ExecutionFailure("source.selected_asset_conflict")
            claim = SourceClaim(asset.source_id, asset.issue_id, asset.asset_id, "recognized")
        elif request.source_id:
            claim = SourceClaim(request.source_id, str(request.metadata.get("issue_id", "")), str(request.metadata.get("asset_id", "main")), "recognized")
    if claim is None and isinstance(inputs.get("evidence"), ReadEvidence) and isinstance(inputs.get("asset"), PublicationAsset):
        evidence, asset = inputs["evidence"], inputs["asset"]
        if evidence.location != asset.locator or evidence.material_identity != original.identity or original.source_id not in {None, asset.source_id}:
            raise ExecutionFailure("source.selected_asset_conflict")
        claim = SourceClaim(asset.source_id, asset.issue_id, asset.asset_id, "recognized")
    if claim is None:
        raise ExecutionFailure("source.claim_required")
    if original.source_id is not None and original.source_id != claim.source_id:
        raise ExecutionFailure("source.context_conflict")
    assessment = Assessment(qualifications=frozenset({"source." + claim.attribution}))
    if inputs.get("evidence") is not None:
        from dataclasses import replace
        if isinstance(original, Material):
            original = replace(original, lineage=(*original.lineage, inputs["evidence"]))
    return {"material": IdentifiedMaterial(original, claim, assessment), "assessment": assessment}


def material_select(inputs, settings, context):
    formats = frozenset(_option(context, settings, "formats", ()))
    names = frozenset(_option(context, settings, "names", ()))
    accepted, findings, observed, expected = [], [], [], []
    for index, value in enumerate(inputs["materials"]):
        material = _carrier(value)
        name = str(material.metadata.get("member", material.metadata.get("filename", index)))
        expected.append(name)
        suffix = name.rsplit(".", 1)[-1].lower()
        if names and name not in names or formats and suffix not in formats:
            findings.append("material.excluded:" + name)
        else:
            accepted.append(value); observed.append(name)
    return {"materials": tuple(accepted), "assessment": Assessment("complete",
        tuple(findings), tuple(observed), tuple(observed),
        qualifications=frozenset({"selected_scope", "parent_membership_recorded"}))}


def material_inspect(inputs, settings, context):
    """Recognize a physical envelope without materializing a complete file."""
    from stratbox.shared.data.materials import MaterialInspection
    from zipfile import ZipFile
    import struct
    original = _carrier(inputs["material"])
    identity = original.identity
    metadata_limit = _option(context, settings, "max_inspection_bytes", 16 * 1024 * 1024)
    max_entries = _option(context, settings, "max_entries", 100000)
    name = str(original.metadata.get("member", original.metadata.get("filename", "")))
    suffix = name.rsplit(".", 1)[-1].lower()
    details, qualifications = {}, {"complete_identity", "signature"}
    with context.open_material(original) as stream:
        head = stream.read(4096)
        if head.startswith(b"PK"):
            from stratbox.core.formats.archives.members import ArchiveLimits, admit_zip_directory
            limits = ArchiveLimits(members=max_entries, packed_bytes=max(identity.size, 1),
                metadata_bytes=metadata_limit)
            admit_zip_directory(stream, identity.size, limits)
            with ZipFile(stream) as archive:
                names = {item.filename for item in archive.infolist()}
                fmt = "xlsx" if "xl/workbook.xml" in names else "xlsb" if "xl/workbook.bin" in names else "docx" if "word/document.xml" in names else "zip"
                if fmt == "xlsx" and "[Content_Types].xml" in names:
                    part = archive.getinfo("[Content_Types].xml")
                    if part.file_size > min(metadata_limit, 1024 * 1024):
                        raise ExecutionFailure("inspection.content_types_limit")
                    with archive.open(part) as content:
                        types = content.read(min(metadata_limit, 1024 * 1024) + 1)
                    if len(types) != part.file_size:
                        raise ExecutionFailure("inspection.content_types_size_mismatch")
                    if getattr(context, "budget", None):
                        context.budget.charge("decoded_bytes",len(types))
                    if b"macroEnabled" in types:
                        fmt = "xlsm"
                details = {"entries": len(names)}
                qualifications.add("envelope")
        elif head.startswith(b"Rar!\x1a\x07"):
            fmt = "rar"
        elif head.startswith(b"%PDF-"):
            fmt = "pdf"
        elif head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            fmt = "doc" if suffix == "doc" else "xls"
        elif head.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
            fmt = "html"
        elif len(head) >= 32 and head[0] in {0x03, 0x83, 0x30, 0x31, 0x32, 0x43, 0x63, 0x8B, 0xCB, 0xF5}:
            header_length, record_length = struct.unpack_from("<HH", head, 8)
            fmt = "dbf" if 32 <= header_length <= identity.size and record_length > 0 else "unknown"
        elif head.lstrip().startswith((b"{", b"[")):
            fmt = "json"
        elif suffix in {"csv", "tsv", "txt"}:
            fmt = suffix
        else:
            fmt = "unknown"
    return {"inspection": MaterialInspection(identity, fmt, original.media_type,
        getattr(original, "provider_scope", None), frozenset(qualifications),
        () if fmt != "unknown" else ("inspection.format_unknown",), details)}
