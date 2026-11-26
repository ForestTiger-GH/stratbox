"""Standard technical action handlers; source knowledge arrives as narrow settings."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlencode
import ast
import csv
import json
import os
import tempfile
import zipfile

from stratbox.shared.data.values import *
from stratbox.core.execution.service import ExecutionFailure


def _get(settings, name, default=None):
    return settings.get(name, default) if isinstance(settings, Mapping) else getattr(settings, name, default)


def _option(context, settings, name, default=None):
    return context.parameters.get(name, _get(settings, name, default))


def _material(value):
    if isinstance(value, IdentifiedMaterial):
        original, claim = value.material, value.claim
        for key, expected in (("issue_id", claim.issue_id), ("asset_id", claim.asset_id)):
            if expected and original.metadata.get(key) not in {None, "", expected}:
                raise ExecutionFailure("source.context_conflict")
        if original.source_id not in {None, claim.source_id}:
            raise ExecutionFailure("source.context_conflict")
        from dataclasses import replace
        return replace(original, source_id=claim.source_id,
            metadata={**dict(original.metadata), "issue_id": claim.issue_id, "asset_id": claim.asset_id})
    if isinstance(value, ConvertedMaterial):
        return value.material
    if isinstance(value, bytes):
        return Material(value)
    if not isinstance(value, Material):
        raise ExecutionFailure("material.required")
    return value


def _rows(dataset):
    if not isinstance(dataset, SourceDataset):
        raise ExecutionFailure("dataset.required")
    return dataset.rows


def _grain_key(row,names):
    values = []
    for name in names:
        value = row.get(name)
        try: hash(value)
        except TypeError: value = fingerprint(value)
        values.append(value)
    return tuple(values)


def _derived(dataset, rows, *, sources=(), semantics=None):
    assessment = Assessment(dataset.assessment.status, dataset.assessment.findings,
        qualifications=dataset.assessment.qualifications | frozenset({"derived_coordinates"}))
    return DerivedDataset(dataset.source_id, tuple(rows), semantics or dataset.semantics,
        dataset.issue_id, (*dataset.lineage, dataset.identity, *sources), assessment, source_uses=dataset.source_uses)


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


def material_fetch(inputs, settings, context):
    request = inputs["request"]
    if request.method not in {"GET", "POST"} or request.method == "POST" and not request.read_only:
        raise ExecutionFailure("http.read_only_request_required")
    provider = context.provider("http")
    context.checkpoint()
    budget = getattr(context, "budget", None)
    before = dict(budget.usage()) if budget else {}
    metered = bool(getattr(provider, "accounts_http_budget", False))
    if budget and not metered: budget.charge("requests", 1)
    if hasattr(provider, "fetch"):
        response = provider.fetch(request)
    elif callable(provider):
        response = provider(request)
    else:
        # Adapt a neutral provider's HTTP contract; no publisher dispatch occurs.
        from stratbox.core.network.contracts import HttpRequest, HttpsEndpoint
        from urllib.parse import urlsplit
        parts = urlsplit(request.url)
        exchange = HttpRequest(request.method, request.url,
            (HttpsEndpoint(parts.hostname, parts.path or "/", allow_query=True),), headers=request.headers,
            body=request.body, form_fields=request.form, deadline_seconds=request.timeout,
            max_response_bytes=request.max_bytes, read_only_post=request.method == "POST" and request.read_only,
            budget=budget)
        send = getattr(provider, "exchange", None) or getattr(provider, "request", None) or getattr(provider, "send", None)
        if send is None:
            raise ExecutionFailure("http.provider_protocol")
        response = send(exchange)
    if isinstance(response, Material):
        material, status, headers = response, 200, {}
    else:
        body = response if isinstance(response, bytes) else getattr(response, "body", getattr(response, "content", None))
        status, headers = getattr(response, "status_code", 200), getattr(response, "headers", {})
        if status == 304:
            retained = _option(context, settings, "retained_material")
            if retained is None:
                raise ExecutionFailure("http.retained_body_required")
            material = _material(retained)
        elif not 200 <= status < 300 or not isinstance(body, bytes):
            raise ExecutionFailure("http.response_failed:" + str(status))
        else:
            material = Material(body, headers.get("content-type", "application/octet-stream").split(";")[0],
                request.source_id, metadata={"url": request.url, **dict(request.metadata)})
    if len(material.data) > request.max_bytes:
        raise ExecutionFailure("http.response_limit")
    if budget:
        for resource, amount in (("wire_bytes", getattr(response, "wire_size", None) or len(material.data)),
                                  ("decoded_bytes", len(material.data))):
            already = budget.used(resource) - before.get(resource, 0)
            if amount > already: budget.charge(resource, amount - already)
    evidence = FetchEvidence(_request_identity(request), getattr(response, "observed_at_utc", datetime.now(timezone.utc)), status,
        material.identity, headers, request.observation_id or context.run_id,
        getattr(response, "effective_locator_safe", request.url), getattr(response, "origin_assurance", "provider_reported"),
        getattr(response, "transport_assurance", None), getattr(response, "route_id", None),
        getattr(response, "target_sha256", None), getattr(response, "logical_target_sha256", None))
    from dataclasses import replace
    material = replace(material, lineage=(*material.lineage, evidence))
    return {"material": material, "evidence": evidence}


def _request_identity(request):
    return request_identity(request)


def material_receive(inputs, settings, context):
    """Receive an original into bounded staging without materializing its body."""
    from stratbox.core.network.contracts import HttpRequest, HttpsEndpoint, HttpStreamResponse
    from urllib.parse import urlsplit
    request, destination = inputs["request"], inputs["destination"]
    if request.method not in {"GET", "POST"} or request.method == "POST" and not request.read_only:
        raise ExecutionFailure("http.read_only_request_required")
    if not isinstance(destination, str) or not destination: raise ExecutionFailure("storage.destination_required")
    transport, store = context.provider("http"), context.provider("filestore")
    if not callable(getattr(transport, "exchange_into", None)) or not callable(getattr(store, "stage_content", None)) or not getattr(store, "immutable_content", False):
        raise ExecutionFailure("streaming.provider_capability_required")
    parts = urlsplit(request.url)
    exchange = HttpRequest(request.method, request.url,
        (HttpsEndpoint(parts.hostname, parts.path or "/", allow_query=True),), headers=request.headers,
        form_fields=request.form, body=request.body, deadline_seconds=min(request.timeout, context.remaining_seconds()),
        max_response_bytes=request.max_bytes, read_only_post=request.method == "POST", budget=context.budget)
    scope = _provider_scope(store, destination)
    effect_id = fingerprint(("material.receive", scope, destination, request_identity(request), request.observation_id or context.run_id))
    accepted = context.accepted_input("request")
    def action():
        before = dict(context.budget.usage())
        if not getattr(transport, "accounts_http_budget", False): context.budget.charge("requests", 1)
        with store.stage_content(destination) as stage:
            class BoundedSink:
                def __init__(self): self.size = 0
                def write(self, data):
                    context.checkpoint()
                    if self.size + len(data) > request.max_bytes: raise ExecutionFailure("http.response_limit")
                    context.budget.charge("temporary_bytes", len(data))
                    result = stage.stream.write(data); self.size += len(data); return result
                def seek(self, *args): return stage.stream.seek(*args)
                def tell(self): return stage.stream.tell()
                def truncate(self, *args): return stage.stream.truncate(*args)
                def flush(self): return stage.stream.flush()
            response = transport.exchange_into(exchange, BoundedSink(), cancelled=lambda: bool(context.run.cancel.is_set() and not context.service._producer_needed(context.task)))
            if not isinstance(response, HttpStreamResponse) or not 200 <= response.response.status_code < 300:
                from stratbox.core.storage.filestore import MutationRejected
                raise MutationRejected("No accepted streamed response", code="http.streaming_response_failed")
            identity, observed = response.identity, response.response
            for resource, amount in (("wire_bytes", observed.wire_size or identity.size), ("decoded_bytes", identity.size)):
                spent = context.budget.used(resource) - before.get(resource, 0)
                if amount > spent: context.budget.charge(resource, amount - spent)
            evidence = FetchEvidence(request_identity(request), observed.observed_at_utc, observed.status_code, identity,
                observed.headers, request.observation_id or context.run_id, observed.effective_locator_safe,
                observed.origin_assurance, observed.transport_assurance, observed.route_id, observed.target_sha256, observed.logical_target_sha256)
            context.budget.account_output(effect_id, identity)
            if not callable(getattr(stage, "location", None)):
                raise ExecutionFailure("streaming.exact_stage_location_required")
            location = stage.location(identity)
            uses = ()
            if request.source_id:
                from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
                uses = (SourceUse(SourceCoordinate(request.source_id, issue_id=request.metadata.get("issue_id"),
                    asset_id=request.metadata.get("asset_id"), material_identity=identity), "material", "identified"),)
            reference = ImmutableMaterialRef(location, identity, str(getattr(store, "provider_id", "filestore")),
                (*(accepted["basis"] if accepted else ()), request_identity(request), evidence),
                accepted_value_id=accepted["id"] if accepted else None, effect_id=effect_id,
                provider_scope=_provider_scope(store, location), source_uses=uses,
                metadata={**dict(request.metadata), "url":request.url, "filename":Path(parts.path).name,
                    "media_type":observed.headers.get("content-type","application/octet-stream").split(";")[0], "source_id":request.source_id})
            context.update_effect_intent(effect_id, reference)
            if stage.commit(identity, checkpoint=context.checkpoint) != location:
                raise ExecutionFailure("streaming.retained_location_conflict")
            return reference
    receipt = context.effect("storage.write", effect_id, action, resource=str(destination),
        intent={"request_identity":request_identity(request),"provider_scope":scope,"destination":destination})
    if receipt.status != "confirmed": raise ExecutionFailure("streaming."+receipt.status, outcome="unknown" if receipt.status == "unknown" else "failed")
    evidence = next(item for item in reversed(receipt.value.lineage) if isinstance(item, FetchEvidence))
    return {"reference": receipt.value, "evidence": evidence, "receipt": receipt}


def _read(store, location, limit):
    if hasattr(store, "open"):
        with store.open(str(location), "rb") as stream:
            data = stream.read(limit + 1)
    elif hasattr(store, "read_bytes"):
        data = store.read_bytes(str(location))
    else:
        raise ExecutionFailure("storage.read_protocol")
    if len(data) > limit:
        raise ExecutionFailure("storage.read_limit")
    return data


def material_read(inputs, settings, context):
    location = inputs["location"]
    expected = getattr(location, "identity", None)
    path = getattr(location, "location", getattr(location, "locator", location))
    data = _read(context.provider("filestore"), path, _option(context, settings, "max_bytes", 128 * 1024 * 1024))
    if getattr(context, "budget", None): context.budget.charge("input_bytes", len(data))
    source_id = getattr(location, "source_id", _get(settings, "source_id", getattr(location, "metadata", {}).get("source_id")))
    metadata = {**dict(getattr(location, "metadata", {})), "location": str(path)}
    metadata.setdefault("filename", Path(str(path)).name)
    if isinstance(location, PublicationAsset):
        metadata.update(dict(location.metadata), issue_id=location.issue_id, asset_id=location.asset_id, format=location.format)
    value = Material(data, _get(settings, "media_type", metadata.get("media_type", "application/octet-stream")), source_id, metadata=metadata,
        lineage=tuple(getattr(location, "lineage", ())))
    if expected is not None and expected != value.identity:
        raise ExecutionFailure("storage.identity_mismatch")
    evidence = ReadEvidence(str(path), value.identity, datetime.now(timezone.utc), _provider_scope(context.provider("filestore"), path))
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
    original = _material(original)
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
        original = replace(original, lineage=(*original.lineage, inputs["evidence"]))
    return {"material": IdentifiedMaterial(original, claim, assessment), "assessment": assessment}


def material_select(inputs, settings, context):
    formats = frozenset(_option(context, settings, "formats", ()))
    names = frozenset(_option(context, settings, "names", ()))
    accepted, findings, observed, expected = [], [], [], []
    for index, value in enumerate(inputs["materials"]):
        material = _material(value)
        name = str(material.metadata.get("member", material.metadata.get("filename", index)))
        expected.append(name)
        suffix = name.rsplit(".", 1)[-1].lower()
        if names and name not in names or formats and suffix not in formats:
            findings.append("material.excluded:" + name)
        else:
            accepted.append(value); observed.append(name)
    return {"materials": tuple(accepted), "assessment": Assessment("complete" if len(accepted) == len(expected) else "partial",
        tuple(findings), tuple(expected), tuple(observed))}


def publication_scan(inputs, settings, context):
    raise ExecutionFailure("publication.source_specification_required")


def issue_select(inputs, settings, context):
    listing, query = inputs["listing"], inputs.get("query") or context.parameters
    expected = _get(query, "source_id", _get(settings, "source_id"))
    issue = _get(query, "issue_id", _get(settings, "issue_id"))
    selected = tuple(a for a in listing.entries if (not expected or a.source_id == expected) and (not issue or a.issue_id == issue))
    if not selected:
        raise ExecutionFailure("publication.issue_not_found")
    keys = [(a.source_id, a.issue_id, a.asset_id) for a in selected]
    if len(keys) != len(set(keys)):
        raise ExecutionFailure("publication.ambiguous_asset")
    return {"selection": AssetSelection(selected, listing.assessment)}


def source_assess(inputs, settings, context):
    candidate, previous = inputs["evidence"], inputs.get("baseline")
    incomplete = any(not getattr(value.assessment, "complete", False) for value in (candidate, previous)
                     if value is not None and hasattr(value, "assessment"))
    if incomplete or isinstance(candidate, PublicationListing):
        return {"assessment": UpdateAssessment("unknown", _get(settings, "basis", "provided_evidence"),
            ("Evidence is incomplete or establishes only a publication listing, not actual asset content.",), evidence=(candidate, previous))}
    current = fingerprint(candidate)
    baseline = fingerprint(previous) if previous is not None else None
    return {"assessment": UpdateAssessment("first_seen" if previous is None else "unchanged" if current == baseline else "changed",
        _get(settings, "basis", "provided_evidence"), predecessor=baseline, candidate=current)}


def workbook_decode(inputs, settings, context):
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    from stratbox.core.formats.spreadsheets.workbook_input import workbook_profile
    from stratbox.shared.data.workbook_cells import WorkbookCells
    material = _material(inputs["material"])
    budget = getattr(context, "budget", None)
    admission = workbook_profile(material.data, budget=budget)
    assessment = Assessment()
    if admission.kind in {"xlsx", "xlsm"}:
        value = read_workbook_cells(material.data, budget=budget, checkpoint=context.checkpoint, _profile=admission)
    else:
        from stratbox.core.formats.spreadsheets.binary_cells import _xls, _xlsb
        sheets = (_xls if admission.kind == "xls" else _xlsb)(material.data, budget, context.checkpoint)
        value = WorkbookCells(sheets, material.identity)
        assessment = Assessment("partial", ("Binary decoded values retained; source numeric text and formula expressions are unavailable.",), qualifications=frozenset({"decoded_binary"}))
    max_cells = _option(context, settings, "max_cells", 5_000_000)
    if sum(len(sheet.cells) for sheet in value.sheets) > max_cells:
        raise ExecutionFailure("workbook.cell_limit")
    neutral = material
    return {"physical": WorkbookEvidence(neutral, value, assessment)}


def json_decode(inputs, settings, context):
    material, tokens = _material(inputs["material"]), {}
    class Token(str):
        pass
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExecutionFailure("json.duplicate_key")
            result[key] = value
        return result
    def number(token):
        return Token(token)
    def convert(value, path=()):
        if getattr(context, "budget", None):
            context.budget.charge("objects" if isinstance(value, (dict, list)) else "cells", 1)
        if isinstance(value, Token):
            tokens[path] = str(value)
            return Decimal(value) if any(c in value for c in ".eE") else int(value)
        if isinstance(value, dict):
            return {key: convert(item, (*path, key)) for key, item in value.items()}
        if isinstance(value, list):
            return tuple(convert(item, (*path, index)) for index, item in enumerate(value))
        return value
    if len(material.data) > _option(context, settings, "max_bytes", 128 * 1024 * 1024):
        raise ExecutionFailure("json.input_limit")
    parsed = json.loads(material.data.decode(material.charset or "utf-8-sig"), parse_float=number, parse_int=number,
        parse_constant=lambda _: (_ for _ in ()).throw(ExecutionFailure("json.nonfinite")), object_pairs_hook=pairs)
    neutral = material
    return {"physical": JsonEvidence(neutral, convert(parsed), tokens=tokens)}


def csv_decode(inputs, settings, context):
    material = _material(inputs["material"])
    reader = csv.reader(StringIO(material.data.decode(_option(context, settings, "encoding", material.charset or "utf-8-sig"))),
                        delimiter=_option(context, settings, "delimiter", ","))
    rows, limit = [], _option(context, settings, "max_rows", 1000000)
    for row in reader:
        context.checkpoint()
        if len(rows) == limit:
            raise ExecutionFailure("csv.row_limit")
        if getattr(context, "budget", None): context.budget.charge("cells", len(row))
        rows.append(tuple(row))
    return {"physical": TableEvidenceSet((tuple(rows),), material)}


def dbf_decode(inputs, settings, context):
    from stratbox.core.formats.dbf_lossless import decode_dbf
    material = _material(inputs["material"])
    encoding = _option(context, settings, "encoding", "cp866")
    value = decode_dbf(material.data, encoding=encoding, checkpoint=context.checkpoint)
    if getattr(context, "budget", None): context.budget.charge("cells", len(value.fields) * len(value.records))
    neutral = material
    return {"physical": DbfEvidence(neutral, value.fields, value.records,
        decoded_identity=fingerprint((material.identity, value.fields, value.records, encoding)), encoding=encoding)}


def archive_unpack(inputs, settings, context):
    material = _material(inputs["material"])
    max_members, max_bytes = _option(context, settings, "max_members", 1000), _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024)
    selected = _option(context, settings, "names", ())
    if not zipfile.is_zipfile(BytesIO(material.data)):
        provider = context.provider("archive_reader")
        return {"members": tuple(provider.unpack(material, max_members=max_members, max_bytes=max_bytes, checkpoint=context.checkpoint))}
    result, total = [], 0
    with zipfile.ZipFile(BytesIO(material.data)) as archive:
        entries = archive.infolist()
        from stratbox.core.formats.archives.members import validate_members, zip_members, ArchiveLimits
        validate_members(zip_members(archive), ArchiveLimits(max_members, max_bytes,
            _option(context, settings, "max_member_bytes", max_bytes), max(1, len(material.data))))
        if len(entries) > max_members or sum(x.file_size for x in entries) > max_bytes:
            raise ExecutionFailure("archive.expansion_limit")
        if len({x.filename for x in entries}) != len(entries):
            raise ExecutionFailure("archive.duplicate_member")
        for entry in entries:
            context.checkpoint()
            if entry.is_dir() or selected and entry.filename not in selected:
                continue
            if "\\" in entry.filename or Path(entry.filename).is_absolute() or ".." in Path(entry.filename).parts:
                raise ExecutionFailure("archive.member_path")
            data = archive.read(entry)
            total += len(data)
            if total > max_bytes:
                raise ExecutionFailure("archive.expansion_limit")
            result.append(Material(data, source_id=material.source_id,
                metadata={**dict(material.metadata), "member": entry.filename, "parent": material.identity.sha256,
                    "container_asset_id": material.metadata.get("asset_id"), "asset_id": entry.filename,
                    "archive_depth": int(material.metadata.get("archive_depth", 0)) + 1},
                lineage=(*material.lineage, material.identity)))
    return {"members": tuple(result)}


def archive_pack(inputs, settings, context):
    limit = _option(context, settings, "max_bytes", 128 * 1024 * 1024)
    class BoundedBuffer(BytesIO):
        def write(self, data):
            if self.tell() + len(data) > limit: raise ExecutionFailure("archive.output_limit")
            return super().write(data)
    stream, names, manifest = BoundedBuffer(), set(), []
    members = inputs["members"]
    if len(members) > _option(context, settings, "max_members", 1000): raise ExecutionFailure("archive.member_limit")
    if sum(len(_material(value).data) for value in members) > _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024): raise ExecutionFailure("archive.input_limit")
    from stratbox.core.formats.archives.members import validate_members, ArchiveMember, ArchiveLimits
    validate_members(tuple(ArchiveMember(str(_material(value).metadata.get("member", index)), len(_material(value).data))
        for index, value in enumerate(members)), ArchiveLimits(_option(context, settings, "max_members", 1000),
        _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024),
        _option(context, settings, "max_member_bytes", 256 * 1024 * 1024), limit))
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, value in enumerate(members):
            context.checkpoint()
            material = _material(value)
            name = material.metadata.get("member", str(index))
            if "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
                raise ExecutionFailure("archive.member_path")
            if name in names: raise ExecutionFailure("archive.duplicate_member")
            names.add(name)
            archive.writestr(name, material.data)
            manifest.append({"name": name, "identity": material.identity})
    data = stream.getvalue()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for record in manifest:
            if ByteIdentity.of(archive.read(record["name"])) != record["identity"]:
                raise ExecutionFailure("archive.verification_failed")
    return {"material": Material(data, "application/zip", metadata={"members": tuple(manifest)}, lineage=tuple(record["identity"] for record in manifest))}


def document_decode(inputs, settings, context):
    material = _material(inputs["material"])
    blocks = []
    if material.data.startswith(b"PK"):
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        from stratbox.core.formats.archives.members import open_zip
        from stratbox.core.formats.xml import parse_xml
        with open_zip(material.data) as package:
            if "word/document.xml" not in package.namelist():
                raise ExecutionFailure("document.docx_required")
            parse_xml(package.read("word/document.xml"))
        doc = Document(BytesIO(material.data))
        for index, node in enumerate(doc.element.body):
            context.checkpoint()
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "p":
                blocks.append(DocumentBlock(len(blocks), "paragraph", Paragraph(node, doc).text, locator=f"body:{index}"))
            elif tag == "tbl":
                rows = tuple(tuple(cell.text for cell in row.cells) for row in Table(node, doc).rows)
                blocks.append(DocumentBlock(len(blocks), "table", rows=rows, locator=f"body:{index}"))
        fmt, findings = "docx", ("Main body paragraphs and table grids only; merged cells may repeat.",)
    elif material.data.startswith(b"%PDF-"):
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(material.data), strict=True)
        if reader.is_encrypted or len(reader.pages) > _option(context, settings, "max_pages", 10000):
            raise ExecutionFailure("document.pdf_limits")
        for index, page in enumerate(reader.pages):
            context.checkpoint()
            try:
                blocks.append(DocumentBlock(index, "page", page.extract_text() or "", index + 1, locator=f"page:{index+1}"))
            except Exception as error:
                blocks.append(DocumentBlock(index, "error", "page_text_extraction_failed:" + type(error).__name__, index + 1, locator=f"page:{index+1}"))
        fmt, findings = "pdf", ("Text extraction only; table geometry and OCR are not established.",)
    else:
        raise ExecutionFailure("document.format_unsupported")
    findings = (*findings, *(block.text for block in blocks if block.kind == "error"))
    assessment = Assessment("partial", findings)
    if getattr(context, "budget", None):
        context.budget.charge("cells", sum(sum(map(len, block.rows)) for block in blocks))
    neutral = material
    return {"physical": DocumentEvidence(neutral, DocumentStructure(fmt, tuple(blocks), material.identity, assessment), assessment)}


def document_convert(inputs, settings, context):
    material, converter = _material(inputs["material"]), context.provider("document_converter")
    limit = _option(context, settings, "max_bytes", 128 * 1024 * 1024)
    converted = converter.convert(material, target_format="docx", max_bytes=limit, checkpoint=context.checkpoint)
    converted = _material(converted)
    if converted.source_id not in {None, material.source_id} or len(converted.data) > limit or not converted.data.startswith(b"PK"):
        raise ExecutionFailure("document.conversion_invalid")
    from stratbox.core.formats.xml import parse_xml
    with zipfile.ZipFile(BytesIO(converted.data)) as archive:
        parse_xml(archive.read("word/document.xml"))
    converted = Material(converted.data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", material.source_id,
        metadata={"converted_from": material.identity.sha256}, lineage=(*material.lineage, material.identity))
    return {"material": converted, "evidence": ConvertedMaterial(converted, material.identity, str(getattr(converter, "provider_id", type(converter).__name__)))}


def publication_transcribe(inputs, settings, context):
    return {"publication": inputs["physical"]}


def table_extract(inputs, settings, context):
    physical = inputs["physical"]
    if isinstance(physical, TableEvidenceSet):
        return {"tables": physical, "coverage": physical.assessment}
    raise ExecutionFailure("table.source_specification_required")


def table_interpret(inputs, settings, context):
    raise ExecutionFailure("table.semantic_specification_required")


def observations_validate(inputs, settings, context):
    dataset = inputs["dataset"]
    keys, grain = set(), _get(settings, "grain", ("metric", "subject_namespace", "subject", "period", "unit", "scale", "perimeter", "measure_kind", "dimensions"))
    for row in _rows(dataset):
        key = _grain_key(row,grain)
        if key in keys:
            raise ExecutionFailure("observations.duplicate_grain")
        keys.add(key)
    return {"dataset": dataset, "assessment": dataset.assessment}


def observations_align(inputs, settings, context):
    dataset, rows = inputs["dataset"], []
    mappings = _get(settings, "mappings", {})
    for row in _rows(dataset):
        converted = dict(row)
        for axis, mapping in mappings.items():
            if converted.get(axis) not in mapping:
                raise ExecutionFailure("mapping.unresolved:" + axis)
            converted[axis] = mapping[converted[axis]]
        rows.append(converted)
    result = IntegratedDataset(dataset.source_id, tuple(rows), dataset.semantics, dataset.issue_id,
                               (*dataset.lineage, dataset.identity), dataset.assessment, source_uses=dataset.source_uses)
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}


def observations_compare(inputs, settings, context):
    before, after = inputs["before"], inputs["after"]
    grain = _get(settings, "grain", ("metric", "subject_namespace", "subject", "period", "unit", "scale", "perimeter", "measure_kind", "frequency", "period_kind", "basis", "dimensions", "legal_kind", "currency"))
    sides = []
    for dataset in (before, after):
        values = {}
        for row in _rows(dataset):
            key = _grain_key(row,grain)
            if key in values:
                raise ExecutionFailure("comparison.duplicate_grain")
            values[key] = row
        sides.append(values)
    left, right = sides
    changes = []
    def semantic(row):
        return None if row is None else (row.get("value"), row.get("value_status"), row.get("raw_token"))
    for key in dict.fromkeys((*left, *right)):
        a, b = left.get(key), right.get(key)
        if semantic(a) == semantic(b): continue
        delta = None
        if a is not None and b is not None and a.get("value") is not None and b.get("value") is not None:
            delta = _number(b) - _number(a)
        changes.append({"key": key, "before": a, "after": b, "delta": delta,
                        "kind": "added" if a is None else "removed" if b is None else "changed"})
    return {"changes": tuple(changes), "assessment": Assessment()}


def timeseries_prepare(inputs, settings, context):
    dataset = inputs["observations"]
    selected = dict(_option(context, settings, "selection", {}))
    rows = [row for row in _rows(dataset) if all(row.get(k) == v for k, v in selected.items())]
    grain = _get(settings, "group_by", ("metric", "subject_namespace", "subject", "unit", "scale", "perimeter", "measure_kind", "frequency", "period_kind", "basis", "dimensions", "legal_kind", "currency"))
    coordinates = {_grain_key(row,grain) for row in rows}
    if len(coordinates) != 1:
        raise ExecutionFailure("timeseries.unique_grain_required")
    rows.sort(key=lambda row: str(row["period"]))
    sample = rows[0]
    dataset = select_dataset(dataset,rows)
    series = TimeSeries({key:sample.get(key) for key in grain}, tuple(row["period"] for row in rows), tuple(row.get("value") for row in rows),
        sample.get("unit", ""), sample.get("frequency", ""), sample.get("measure_kind", ""), (*dataset.lineage, dataset.identity), dataset.assessment, source_uses=dataset.source_uses)
    return {"series": series, "assessment": series.assessment}


def timeseries_partition(inputs, settings, context):
    dataset = inputs.get("dataset", inputs.get("observations"))
    group = _get(settings, "group_by", ("metric", "subject_namespace", "subject", "unit", "scale", "perimeter", "measure_kind", "frequency", "period_kind", "basis", "dimensions", "legal_kind", "currency"))
    groups = defaultdict(list)
    for row in _rows(dataset):
        groups[_grain_key(row,group)].append(row)
    results = []
    for key in sorted(groups, key=str):
        selected = select_dataset(dataset, groups[key])
        results.append(timeseries_prepare({"observations": selected}, settings, context)["series"])
    return {"items": tuple(results)}


def observations_merge(inputs, settings, context):
    datasets = inputs["datasets"]
    if not datasets or any(not isinstance(item, SourceDataset) for item in datasets):
        raise ExecutionFailure("observations.datasets_required")
    if len(datasets) == 1:
        return {"dataset": datasets[0], "assessment": datasets[0].assessment}
    source_ids = {item.source_id for item in datasets}
    if len(source_ids) != 1 and not _get(settings, "allow_cross_source", False):
        raise ExecutionFailure("observations.source_mismatch")
    if any(item.semantics != datasets[0].semantics for item in datasets):
        raise ExecutionFailure("observations.semantic_mismatch")
    issues = tuple(dict.fromkeys(item.issue_id for item in datasets))
    semantics = dict(datasets[0].semantics)
    if len(issues) > 1: semantics["source_issues"] = issues
    assessments = tuple(item.assessment for item in datasets)
    assessment = Assessment("complete" if all(item.complete for item in assessments) else "partial",
        tuple(dict.fromkeys(f for item in assessments for f in item.findings)),
        qualifications=frozenset(q for item in assessments for q in item.qualifications) | frozenset({"partitioned_input_coverage"}))
    result = SourceDataset(datasets[0].source_id, tuple(row for item in datasets for row in item.rows),
        semantics, issue_id=issues[0] if len(issues) == 1 else "multi_issue_history", lineage=tuple(item.identity for item in datasets),
        assessment=assessment,
        source_uses=tuple(dict.fromkeys(use for item in datasets for use in item.source_uses)))
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}


def timeseries_validate(inputs, settings, context):
    series = inputs["series"]
    if not series.unit or not series.frequency or not series.measure_kind:
        raise ExecutionFailure("timeseries.semantics_required")
    if len(series.values) < _option(context, settings, "minimum_periods", 1):
        raise ExecutionFailure("timeseries.insufficient_history")
    if any(value is None for value in series.values) and _get(settings, "missingness", "reject") == "reject":
        raise ExecutionFailure("timeseries.missing_values")
    return {"assessment": Assessment()}


def timeseries_adjust(inputs, settings, context):
    timeseries_validate(inputs, settings, context)
    provider = context.provider("seasonal_adjustment")
    original = inputs["series"]
    result = provider.adjust(original, settings=settings, checkpoint=context.checkpoint)
    _validate_adjustment(result, settings)
    if result.input_identity != fingerprint(original): raise ExecutionFailure("timeseries.adjustment_input_mismatch")
    return {"adjustment": result}


def _validate_adjustment(adjustment, settings):
    if not isinstance(adjustment, TimeSeriesAdjustment) or not isinstance(adjustment.diagnostics, AdjustmentDiagnostics):
        raise ExecutionFailure("timeseries.typed_adjustment_required")
    original, adjusted = adjustment.original, adjustment.adjusted
    if not adjustment.method or adjustment.input_identity != fingerprint(original) or adjustment.diagnostics.input_identity != adjustment.input_identity:
        raise ExecutionFailure("timeseries.adjustment_input_mismatch")
    if (original.periods != adjusted.periods or original.frequency != adjusted.frequency or original.coordinates != adjusted.coordinates
            or original.unit != adjusted.unit or original.measure_kind != adjusted.measure_kind):
        raise ExecutionFailure("timeseries.adjustment_semantic_mismatch")
    if len(adjusted.values) != len(original.values) or any(value is None or not Decimal(value).is_finite() for value in adjusted.values):
        raise ExecutionFailure("timeseries.adjustment_invalid_values")
    required = set(_get(settings, "required_diagnostics", ("residual_seasonality", "outlier_policy")))
    if not required or not required <= adjustment.diagnostics.checks.keys() or not all(adjustment.diagnostics.checks[key] for key in required):
        raise ExecutionFailure("timeseries.diagnostics_not_admitted")
    if not adjustment.assessment.complete or not adjustment.diagnostics.assessment.complete:
        raise ExecutionFailure("timeseries.adjustment_not_admitted")


def timeseries_diagnose(inputs, settings, context):
    adjustment = inputs["adjustment"]
    _validate_adjustment(adjustment, settings)
    return {"diagnostics": adjustment.diagnostics}


def _number(row):
    value = row.get("value")
    if value is None or row.get("value_status") in {"missing", "dash", "suppressed", "withheld"}:
        raise ExecutionFailure("calculation.numeric_value_required")
    number = Decimal(value)
    if not number.is_finite():
        raise ExecutionFailure("calculation.nonfinite")
    return number


def calculate_change(inputs, settings, context):
    dataset = inputs["observations"]
    required_kind = _get(settings, "required_measure_kind")
    if required_kind and any(row.get("measure_kind") != required_kind for row in dataset.rows):
        raise ExecutionFailure("calculation.measure_kind_mismatch")
    grain = _get(settings, "group_by", ("metric", "subject", "subject_namespace", "unit", "scale", "perimeter",
        "measure_kind", "frequency", "period_kind", "basis", "value_basis", "dimensions", "legal_kind", "currency", "portfolio", "activity", "bank", "sex", "age"))
    groups, result = defaultdict(list), []
    for row in _rows(dataset):
        groups[_grain_key(row,grain)].append(row)
    before, after, mode = _option(context, settings, "before"), _option(context, settings, "after"), _get(settings, "mode", "absolute")
    if (before is None) != (after is None) or before is not None and str(before) >= str(after):
        raise ExecutionFailure("calculation.change_selection_invalid")
    for rows in groups.values():
        rows.sort(key=lambda row: str(row["period"]))
        periods = [row["period"] for row in rows]
        if len(periods) != len(set(periods)):
            raise ExecutionFailure("calculation.duplicate_period")
        pairs = [(next(r for r in rows if r["period"] == before), next(r for r in rows if r["period"] == after))] if before is not None and after is not None else list(zip(rows, rows[1:]))
        for first, last in pairs:
            if _get(settings, "same_window", _get(settings, "same_accumulation_window", False)):
                def window(row):
                    period = row["period"]
                    if isinstance(period, tuple): return tuple(str(part)[4:] for part in period)
                    return str(period)[4:]
                if window(first) != window(last):
                    raise ExecutionFailure("calculation.accumulation_window_mismatch")
            a, b = _number(first), _number(last)
            if mode not in {"absolute", "percent"}: raise ExecutionFailure("calculation.invalid_change_mode")
            status = "prior_zero" if a == 0 else "sign_change" if a < 0 < b or b < 0 < a else "comparable"
            value = b - a if mode == "absolute" else None if status != "comparable" else (b / a - 1) * 100
            row = {**dict(last), "value": value, "value_status": "derived" if value is not None else "undefined",
                           "comparison_period": first["period"], "calculation": mode, "comparison_status": status,
                           "baseline_evidence_ref": first.get("evidence_ref"), "baseline_value": first.get("value"),
                           "baseline_annotations": first.get("annotations", ()),
                           "metric": _get(settings, "output_metric", str(last.get("metric")) + (".change" if mode == "absolute" else ".growth"))}
            if mode == "percent":
                row.update(measure_kind="rate", unit="percent", scale=1)
            elif last.get("measure_kind") == "stock":
                row.update(measure_kind="net_change", period_kind="interval", period=(first["period"], last["period"]),
                    period_start=first["period"], period_end=last["period"], source_measure_kind="stock")
            else:
                row["measure_kind"] = "difference"
            result.append(row)
    if not result: raise ExecutionFailure("calculation.no_comparable_pair")
    return {"dataset": _derived(dataset, result)}


def calculate_index(inputs, settings, context):
    dataset, rows = inputs["observations"], []
    for row in _rows(dataset):
        if row.get("measure_kind") != "index":
            raise ExecutionFailure("calculation.index_required")
        rows.append({**dict(row), "metric": _get(settings, "output_metric", str(row.get("metric")) + ".growth"),
                     "value": _number(row) - Decimal(_get(settings, "base", 100)), "value_status": "derived", "measure_kind": "rate"})
    return {"dataset": _derived(dataset, rows)}


def calculate_flow(inputs, settings, context):
    dataset = inputs["observations"]
    if any(row.get("measure_kind") != "flow" or row.get("basis", row.get("value_basis")) not in {"ytd", "cumulative"} for row in dataset.rows):
        raise ExecutionFailure("calculation.cumulative_flow_required")
    groups, result = defaultdict(list), []
    for row in dataset.rows:
        groups[tuple(row.get(k) for k in ("metric", "subject", "unit", "scale", "perimeter"))].append(row)
    def end(row):
        period = row.get("period_end", row["period"])
        period = period[-1] if isinstance(period, tuple) else period
        raw = str(period)
        if "Q" in raw:
            return int(raw[:4]), int(raw[-1]) * 3
        if len(raw) < 7: raise ExecutionFailure("calculation.explicit_flow_period_required")
        return int(raw[:4]), int(raw[5:7])
    for rows in groups.values():
        rows.sort(key=lambda row: str(row["period"]))
        previous = None
        for row in rows:
            year, month = end(row)
            frequency = row.get("frequency", _get(settings, "frequency", "monthly"))
            step = 3 if frequency == "quarterly" else 1 if frequency == "monthly" else None
            if step is None: raise ExecutionFailure("calculation.flow_frequency_unsupported")
            first = month == step
            if previous is None or end(previous)[0] != year:
                if not first:
                    raise ExecutionFailure("calculation.preceding_ytd_required")
                value = _number(row)
            else:
                if end(previous)[1] + step != month:
                    raise ExecutionFailure("calculation.ytd_period_gap")
                value = _number(row) - _number(previous)
            from datetime import timedelta
            import calendar
            end_day = date(year, month, calendar.monthrange(year, month)[1])
            start_day = date(year, month - step + 1, 1)
            result.append({**dict(row), "value": value, "value_status": "derived", "basis": "period_flow",
                "value_basis": "period_flow", "period_kind": "interval", "period": (start_day.isoformat(), end_day.isoformat()),
                "period_start": start_day.isoformat(), "period_end": end_day.isoformat(),
                "cumulative_evidence_ref": row.get("evidence_ref"),
                "preceding_cumulative_evidence_ref": previous.get("evidence_ref") if previous is not None and end(previous)[0] == year else None})
            previous = row
    return {"dataset": _derived(dataset, result)}


def calculate_ratio(inputs, settings, context):
    numerator, denominator = inputs["numerator"], inputs["denominator"]
    group = _get(settings, "group_by", ("period", "subject_namespace", "subject", "perimeter", "period_kind", "frequency", "measure_kind"))
    required_kind = _get(settings, "required_measure_kind")
    if required_kind and any(row.get("measure_kind") != required_kind for item in (numerator, denominator) for row in item.rows):
        raise ExecutionFailure("ratio.measure_kind_mismatch")
    right = {}
    for row in _rows(denominator):
        key = _grain_key(row,group)
        if key in right:
            raise ExecutionFailure("ratio.ambiguous_denominator")
        right[key] = row
    result = []
    for row in _rows(numerator):
        matching = right.get(_grain_key(row,group))
        if matching is None or row.get("unit") != matching.get("unit") or row.get("scale", 1) != matching.get("scale", 1):
            raise ExecutionFailure("ratio.incompatible_inputs")
        if any(row.get(key) != matching.get(key) for key in ("subject_namespace", "measure_kind", "period_kind", "frequency")):
            raise ExecutionFailure("ratio.semantic_mismatch")
        den = _number(matching)
        value = _number(row) / den * Decimal(_get(settings, "multiplier", 1)) if den else None
        result.append({**dict(row), "metric": _get(settings, "output_metric", "ratio"), "unit": "ratio", "scale": 1,
            "value": value, "value_status": "derived" if value is not None else "undefined", "measure_kind": "ratio",
            "denominator_evidence_ref": matching.get("evidence_ref"), "denominator_metric": matching.get("metric"),
            "denominator_annotations": matching.get("annotations", ()), "denominator_value": matching.get("value")})
    from dataclasses import replace
    result = _derived(numerator,result,sources=(denominator.identity,))
    return {"dataset":replace(result,source_uses=tuple(dict.fromkeys((*numerator.source_uses,*denominator.source_uses))))}


def calculate_formula(inputs, settings, context):
    dataset = inputs["dataset"]
    operands, group = _get(settings, "operands", {}), _get(settings, "group_by", ("period", "subject", "perimeter"))
    expression = ast.parse(_get(settings, "expression", ""), mode="eval")
    def evaluate(node, numbers):
        if isinstance(node, ast.Expression): return evaluate(node.body, numbers)
        if isinstance(node, ast.Name) and node.id in numbers: return numbers[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}: return Decimal(str(node.value)), {}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value, unit = evaluate(node.operand, numbers)
            return (-value if isinstance(node.op, ast.USub) else value), unit
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            (a, au), (b, bu) = evaluate(node.left, numbers), evaluate(node.right, numbers)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if au != bu: raise ExecutionFailure("formula.dimension_mismatch")
                return (a + b if isinstance(node.op, ast.Add) else a - b), au
            unit = dict(au)
            sign = -1 if isinstance(node.op, ast.Div) else 1
            for key, exponent in bu.items(): unit[key] = unit.get(key, 0) + sign * exponent
            unit = {key: exponent for key, exponent in unit.items() if exponent}
            if isinstance(node.op, ast.Mult): return a * b, unit
            if b == 0: raise ExecutionFailure("formula.zero_denominator")
            return a / b, unit
        raise ExecutionFailure("formula.expression_not_admitted")
    groups, result = defaultdict(dict), []
    for row in _rows(dataset):
        names = [name for name, metric in operands.items() if row.get("metric") == metric]
        for name in names:
            bucket = groups[_grain_key(row,group)]
            if name in bucket: raise ExecutionFailure("formula.duplicate_operand")
            bucket[name] = row
    for rows in groups.values():
        if set(rows) != set(operands): raise ExecutionFailure("formula.operand_missing")
        units = {(row.get("unit"), row.get("scale", 1)) for row in rows.values()}
        if len(units) != 1 or next(iter(units))[0] != _get(settings, "unit"):
            raise ExecutionFailure("formula.incompatible_unit")
        value, dimensions = evaluate(expression, {name: (_number(row), {row["unit"]: 1}) for name, row in rows.items()})
        expected = {} if _get(settings, "unit") in {"ratio", "percent", "1"} else {_get(settings, "unit"): 1}
        if dimensions != expected: raise ExecutionFailure("formula.output_dimension_mismatch")
        result.append({**dict(next(iter(rows.values()))), "metric": _get(settings, "output_metric"),
                       "value": value, "value_status": "derived", "formula_inputs": tuple(operands.values())})
    if not result: raise ExecutionFailure("formula.no_eligible_group")
    return {"dataset": _derived(dataset, result)}


def view_prepare(inputs, settings, context):
    dataset, filters = inputs["dataset"], _option(context, settings, "filters", {})
    rows = tuple(row for row in dataset.rows if all(row.get(k) in v if isinstance(v, (tuple, list, set, frozenset)) else row.get(k) == v for k, v in filters.items()))
    return {"view": View(select_dataset(dataset, rows),
                         {} if settings is None else settings, (*dataset.lineage, dataset.identity), dataset.source_uses)}


def product_render(inputs, settings, context):
    view = inputs["view"]
    rows = view.value.rows if isinstance(view.value, SourceDataset) else view.value
    fmt = _option(context, settings, "format", "csv")
    if fmt == "csv":
        columns = tuple(_get(settings, "columns", ())) or tuple(dict.fromkeys(k for row in rows for k in row))
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
        data, media = stream.getvalue().encode("utf-8"), "text/csv"
    elif fmt in {"json", "jsonl"}:
        encode = lambda value: json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
        data = ("\n".join(encode(dict(row)) for row in rows) if fmt == "jsonl" else encode([dict(row) for row in rows])).encode()
        media = "application/x-ndjson" if fmt == "jsonl" else "application/json"
    else:
        renderer = context.provider("renderer")
        data, media = renderer.render(view, format=fmt, checkpoint=context.checkpoint)
    return {"product": EncodedProduct(data, media, view.lineage, source_uses=view.source_uses)}


def value_encode(inputs, settings, context):
    return {"representation": encode_value(inputs["value"],context=context,
        max_bytes=_option(context,settings,"max_bytes",256*1024*1024))}


def encode_value(value, *, context, admitted_types=None, max_bytes=256 * 1024 * 1024):
    """Bounded shared serializer with an explicit trusted scientific vocabulary."""
    limit = max_bytes
    budget = getattr(context, "budget", None)
    if budget and budget.remaining("output_bytes") is not None: limit = min(limit, budget.remaining("output_bytes"))
    data = bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":")).iterencode(validate_portable_tree(canonical_tree(value),admitted_types=admitted_types)):
        context.checkpoint()
        raw = chunk.encode()
        if len(data) + len(raw) > limit:
            if budget and budget.remaining("output_bytes") is not None: budget.check("output_bytes", len(data) + len(raw))
            raise ExecutionFailure("codec.output_limit")
        data.extend(raw)
    data = bytes(data)
    identity = fingerprint(value)
    return EncodedProduct(data, "application/json", (identity,),
        descriptor={"encoding": "canonical_tree", "value_identity": identity},
        source_uses=getattr(value, "source_uses", ()))


def value_decode(inputs, settings, context):
    encoded = inputs["representation"]
    data = encoded if isinstance(encoded, bytes) else encoded.data
    value = restore_tree(json.loads(data))
    expected = getattr(encoded, "descriptor", {}).get("value_identity")
    if expected is not None and fingerprint(value) != expected: raise ExecutionFailure("codec.value_identity_mismatch")
    return {"value": value}


def artifact_commit(inputs, settings, context):
    value = inputs["material"]
    data = value if isinstance(value, bytes) else value.data
    identity, store = ByteIdentity.of(data), context.provider("filestore")
    destination = inputs.get("destination") or _option(context, settings, "destination")
    if destination is None: raise ExecutionFailure("storage.destination_required")
    if getattr(context, "budget", None):
        context.budget.account_output(fingerprint(("artifact", str(destination))), identity)
    # Content members always receive digest addressing. A mutable publication pointer is separate.
    path = str(Path(str(destination)) / identity.sha256)
    scope = _provider_scope(store, path)
    accepted = context.accepted_input("material")
    effect_id = fingerprint(("storage.write", scope, path, identity))
    reference = ImmutableMaterialRef(path, identity, str(getattr(store, "provider_id", "filestore")),
        accepted["basis"] if accepted else (), accepted_value_id=accepted["id"] if accepted else None,
        effect_id=effect_id, provider_scope=scope, source_uses=accepted["source_uses"] if accepted else ())
    def action():
        if getattr(store, "immutable_content", False) and hasattr(store, "create_immutable"):
            store.create_immutable(path, data)
        else:
            raise ExecutionFailure("storage.immutable_provider_required")
        actual = _read(store, path, identity.size)
        if ByteIdentity.of(actual) != identity: raise ExecutionFailure("storage.identity_mismatch")
        return reference
    receipt = context.effect("storage.write", effect_id, action, resource=path, intent=reference)
    if receipt.status != "confirmed": raise ExecutionFailure("storage.unknown", outcome="unknown")
    return {"reference": receipt.value, "receipt": receipt}


def artifact_reconcile(inputs, settings, context):
    receipt = inputs["effect"]
    provider = context.provider("filestore")
    def lookup(effect_id):
        known = context.service.lookup_effect(effect_id)
        expected = known.intent if known is not None else None
        if not isinstance(expected, ImmutableMaterialRef) or not getattr(provider, "immutable_content", False): return None
        if expected.provider_scope != _provider_scope(provider, expected.location): return None
        try:
            actual = ByteIdentity.of(_read(provider, expected.location, expected.identity.size))
        except (OSError, ExecutionFailure):
            return None
        return expected if actual == expected.identity else None
    recovered = context.service.reconcile_effect(receipt.effect_id, lookup, context=context)
    return {"assessment": Assessment("complete" if recovered.status == "confirmed" else "indeterminate",
        qualifications=frozenset({"exact_immutable_readback"}) if recovered.status == "confirmed" else frozenset())}


def dataset_ingest(inputs, settings, context):
    dataset, writer = inputs["dataset"], context.provider("dataset_writer")
    _rows(dataset)
    destination = inputs.get("destination") or _option(context, settings, "destination", dataset.source_id)
    identity = fingerprint(dataset)
    def action():
        result = writer.ingest(dataset, destination=destination, identity=identity)
        return result if isinstance(result, SnapshotRef) else SnapshotRef(str(result), str(getattr(writer, "provider_id", "dataset_writer")), identity)
    receipt = context.effect("dataset.write", fingerprint(("dataset.write", _provider_scope(writer, destination), destination, identity)), action, resource=str(destination))
    if receipt.status != "confirmed": raise ExecutionFailure("dataset.unknown", outcome="unknown")
    return {"reference": receipt.value, "receipt": receipt}


def dataset_query(inputs, settings, context):
    reader = context.provider("dataset_reader")
    result = reader.query(inputs["reference"], inputs.get("query") or _get(settings, "query", {}))
    _rows(result)
    return {"observations": result}


def _provider_scope(provider, destination):
    scope = getattr(provider, "storage_scope", None)
    location = scope(str(destination)) if callable(scope) else getattr(provider, "scope_id", None)
    if location is None:
        root = getattr(provider, "directory", getattr(provider, "_root", None))
        location = str(root) if root is not None else str(getattr(provider, "provider_id", type(provider).__module__ + ":" + type(provider).__qualname__))
    return fingerprint((str(getattr(provider, "provider_id", type(provider).__qualname__)), str(location)))


def _verify_member(reference, context):
    if not isinstance(reference, ImmutableMaterialRef) or not reference.accepted_value_id or not reference.effect_id:
        raise ExecutionFailure("release.accepted_lineage_required")
    receipt = context.service.lookup_effect(reference.effect_id)
    if receipt is None or receipt.status != "confirmed" or receipt.value != reference:
        raise ExecutionFailure("release.confirmed_retention_required")
    store = context.provider("filestore")
    if not getattr(store, "immutable_content", False) or reference.provider_scope != _provider_scope(store, reference.location):
        raise ExecutionFailure("release.immutable_provider_required")
    if ByteIdentity.of(_read(store, reference.location, reference.identity.size)) != reference.identity:
        raise ExecutionFailure("release.member_identity_mismatch")


def release_assemble(inputs, settings, context):
    members = inputs["members"]
    if not members: raise ExecutionFailure("release.empty_members")
    basis = _option(context, settings, "basis")
    records = []
    for member in members:
        reference = _get(member, "reference", member if isinstance(member, ImmutableMaterialRef) else None)
        derivation = _get(member, "derivation", getattr(reference, "lineage", ()))
        _verify_member(reference, context)
        if tuple(derivation) != reference.lineage:
            raise ExecutionFailure("release.caller_derivation_conflict")
        requested = set(basis.values()) if isinstance(basis, Mapping) else set(basis) if isinstance(basis, (tuple, list, set, frozenset)) else {basis} if basis is not None else set()
        if requested and not {fingerprint(item) for item in requested} <= {fingerprint(item) for item in reference.lineage}:
            raise ExecutionFailure("release.member_basis_mismatch")
        records.append({"reference": reference, "derivation": derivation})
    return {"manifest": {"members": tuple(records), "basis": basis, "identity": fingerprint(records)}}


def release_publish(inputs, settings, context):
    store, manifest = context.provider("filestore"), inputs["manifest"]
    publish = getattr(store, "compare_and_set", None)
    if publish is None: raise ExecutionFailure("publication.conditional_provider_required")
    destination = _option(context, settings, "destination")
    if not isinstance(destination, str) or not destination:
        raise ExecutionFailure("publication.destination_required")
    for member in manifest["members"]:
        _verify_member(member["reference"], context)
    data = json.dumps(canonical_tree(manifest), sort_keys=True, separators=(",", ":")).encode()
    expected = inputs.get("expected_token")
    receipt = context.effect("publication.write", fingerprint((destination, expected, data)),
        lambda: publish(destination, expected, data), resource=str(destination))
    if receipt.status != "confirmed": raise ExecutionFailure("publication.unknown", outcome="unknown")
    return {"receipt": receipt}


def material_maintenance_plan(inputs, settings, context):
    actions = _option(context, settings, "actions", ())
    if not actions: return {"plan": ()}
    available = {str(item.get("path")) if isinstance(item, Mapping) else str(item) for item in inputs["inventory"]}
    if any(str(_get(action, "source")) not in available for action in actions):
        raise ExecutionFailure("maintenance.inventory_mismatch")
    return {"plan": tuple(actions)}


def material_maintenance_apply(inputs, settings, context):
    store, receipts = context.provider("filestore"), []
    for action in inputs["plan"]:
        context.checkpoint()
        source, operation = _get(action, "source"), _get(action, "operation")
        scope = _option(context, settings, "scope")
        if scope is None or not Path(str(source)).is_relative_to(Path(str(scope))):
            raise ExecutionFailure("maintenance.explicit_scope_required")
        expected = _get(action, "expected_identity")
        if expected is None: raise ExecutionFailure("maintenance.expected_identity_required")
        methods = ("guard_directory", "inspect_file", "rename_expected" if operation == "move" else "remove_expected")
        if operation not in {"move", "delete"} or not all(callable(getattr(store, name, None)) for name in methods):
            raise ExecutionFailure("maintenance.conditional_provider_required")
        destination = _get(action, "destination")
        if destination is not None and not Path(str(destination)).is_relative_to(Path(str(scope))):
            raise ExecutionFailure("maintenance.destination_outside_scope")
        if destination is not None and Path(str(source)).parent != Path(str(destination)).parent:
            raise ExecutionFailure("maintenance.same_directory_required")
        def perform(source=source, destination=destination, expected=expected, operation=operation):
            from stratbox.core.storage.filestore import MutationRejected
            with store.guard_directory(str(Path(str(source)).parent)):
                observed = store.inspect_file(source)
                if observed.identity != expected:
                    raise MutationRejected("Source changed", code="maintenance.state_conflict")
                success = store.rename_expected(observed, destination) if operation == "move" else store.remove_expected(observed)
                if not success: raise MutationRejected("Conditional mutation rejected", code="maintenance.state_conflict")
                return {"source": source, "destination": destination, "identity": expected, "operation": operation}
        receipt = context.effect("storage.write", fingerprint(("maintenance", _provider_scope(store, source), operation, source, destination, expected)), perform, resource=str(source))
        if receipt.status != "confirmed": raise ExecutionFailure("maintenance." + receipt.status, outcome="unknown" if receipt.status == "unknown" else "failed")
        receipts.append(receipt)
    return {"receipts": tuple(receipts)}


def notification_prepare(inputs, settings, context):
    facts = tuple(inputs["facts"])
    state = context.provider("notification_state")
    selector, route = _option(context, settings, "selector", {}), _option(context, settings, "route")
    subscription = _option(context, settings, "subscription_id", "default")
    effect_id = fingerprint(("notification.state", _provider_scope(state, subscription), subscription, selector, route,
        tuple((f.stream_id, f.run_id, f.sequence) for f in facts)))
    def prepare_state():
        # This transaction is idempotent: the cursor and deterministic intent
        # keys are committed together. Replay can safely resolve a lost reply.
        prepared = state.prepare(facts, subscription_id=subscription, selector=selector, route=route)
        return {"status": "confirmed", "effect_id": effect_id, "prepared": len(prepared)}
    receipt = context.effect("notification.state", effect_id,
        prepare_state, reconcile=lambda previous: prepare_state(), resource=subscription)
    if receipt.status != "confirmed": raise ExecutionFailure("notification.state_unknown", outcome="unknown")
    # A repeated preparation confirms the input transaction, then reads the
    # current pending page; its old effect receipt is not a current queue view.
    return {"intents": state.pending(subscription, after_sequence=_option(context, settings, "after_sequence", 0),
        limit=_option(context, settings, "limit", 1000))}


def notification_deliver(inputs, settings, context):
    provider, intent = context.provider("notification"), inputs["intent"]
    subscription = intent.get("subscription_id")
    state = context.service.providers.get("notification_state") if subscription is not None else None
    if subscription is not None and not callable(getattr(state, "acknowledge", None)):
        raise ExecutionFailure("notification.acknowledgement_state_required")
    def deliver():
        acknowledgement = provider.deliver(intent)
        status = acknowledgement.get("status", acknowledgement.get("confirmation")) if isinstance(acknowledgement, Mapping) else getattr(acknowledgement, "status", getattr(acknowledgement, "confirmation", None))
        if status in {"rejected", "failed"}:
            from stratbox.core.storage.filestore import MutationRejected
            raise MutationRejected("The channel rejected the notification", code="notification.delivery_rejected")
        if status not in {"confirmed", "accepted", "delivered"}:
            raise ExecutionFailure("notification.acknowledgement_missing", outcome="unknown")
        return acknowledgement
    receipt = context.effect("notification.deliver", intent["id"], deliver,
        reconcile=lambda previous: provider.lookup(previous.effect_id) if hasattr(provider, "lookup") else None,
        resource=str(intent.get("route")))
    if receipt.status != "confirmed":
        raise ExecutionFailure("notification.delivery_" + receipt.status,
            outcome="unknown" if receipt.status == "unknown" else "failed")
    if subscription is not None:
        acknowledgement_id = fingerprint(("notification.acknowledge", _provider_scope(state, subscription),
            subscription, intent["id"]))
        def acknowledge():
            result = state.acknowledge(subscription, intent["id"], receipt)
            return {"status": "confirmed", "effect_id": acknowledgement_id, **result}
        acknowledged = context.effect("notification.state", acknowledgement_id, acknowledge,
            reconcile=lambda previous: acknowledge(), resource=subscription)
        if acknowledged.status != "confirmed":
            raise ExecutionFailure("notification.state_unknown", outcome="unknown")
    return {"receipt": receipt}


def notification_reconcile(inputs, settings, context):
    provider, receipt = context.provider("notification"), inputs["receipt"]
    return {"assessment": context.service.reconcile_effect(receipt.effect_id, provider.lookup, context=context) if hasattr(provider, "lookup") else Assessment("indeterminate")}


def _model_method(inputs, settings, context):
    raise ExecutionFailure("calculation.model_specification_required")


model_inputs = constraints_build = bounds_propagate = facts_inherit = facts_reconcile = model_compile = model_feasibility = bounds_optimize = values_certify = observations_assemble = _model_method


def _exact_calculation(method):
    """Deterministic precision independent of the caller's Decimal context."""
    from functools import wraps
    @wraps(method)
    def execute(inputs, settings, context):
        numbers = [row.get("value") for dataset in inputs.values() if isinstance(dataset, SourceDataset) for row in dataset.rows if row.get("value") is not None]
        precision = 80
        for value in numbers:
            try:
                item = Decimal(value)
                precision = max(precision, 3 * (len(item.as_tuple().digits) + abs(item.as_tuple().exponent)) + 40)
            except (TypeError, ValueError):
                pass
        if precision > 100000: raise ExecutionFailure("calculation.precision_limit")
        with localcontext() as decimal_context:
            decimal_context.prec = precision
            return method(inputs, settings, context)
    return execute


calculate_change = _exact_calculation(calculate_change)
calculate_ratio = _exact_calculation(calculate_ratio)
calculate_formula = _exact_calculation(calculate_formula)
calculate_flow = _exact_calculation(calculate_flow)
calculate_index = _exact_calculation(calculate_index)
observations_compare = _exact_calculation(observations_compare)
