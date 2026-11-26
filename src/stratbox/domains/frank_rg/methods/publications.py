"""Pure recognition of caller-delivered files; no website acquisition."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from collections.abc import Mapping

from stratbox.shared.data.values import (Assessment, AssetSelection, IdentifiedMaterial,
    Material, PublicationAsset, PublicationListing, SourceClaim, UpdateAssessment, fingerprint)
from ..common.naming import (_canonical_period, _date_period, _matches, _supplier_name,
    _week_period, canonical_filename, normalize_file_name, normalize_label_text)
from ..common.recognition import RULES


@dataclass(frozen=True)
class DeliverySettings:
    source_id: str = ""
    formats: frozenset[str] = frozenset({"xlsx", "xlsm", "xls", "xlsb"})


def recognize(filename, rules=RULES):
    stem, dot, extension = filename.rpartition(".")
    format = extension.casefold() if dot else ""
    stem = stem if dot else filename
    canonical = _canonical_period(stem)
    if canonical:
        label, periodicity, period = canonical
        candidates = [rule for rule in rules if rule.periodicity == periodicity
            and normalize_label_text(rule.canonical_label) == normalize_label_text(label)]
    elif _supplier_name(stem):
        normalized = normalize_file_name(stem)
        candidates = [rule for rule in rules if _matches(normalized, rule)]
        if candidates:
            priority = min(rule.priority for rule in candidates)
            candidates = [rule for rule in candidates if rule.priority == priority]
            period = _week_period(normalized) if candidates[0].periodicity == "month_week" else _date_period(normalized)
        else:
            period = None
    else:
        candidates, period = [], None
    if len(candidates) != 1:
        return None, None, format, "identity_conflict" if candidates else "unclassified"
    rule = candidates[0]
    if period is None:
        return rule, None, format, "publication_period_unresolved"
    if format not in {"xlsx", "xlsm", "xls", "xlsb"}:
        return rule, period, format, "unsupported_format"
    if rule.min_period_date and period.snapshot_date < rule.min_period_date:
        return rule, period, format, "period_before_reviewed_name_scope"
    return rule, period, format, None


def scan(inputs, settings: DeliverySettings, context):
    inventory = inputs["index"]
    entries = inventory.entries if hasattr(inventory, "entries") else inventory.get("entries", ()) if isinstance(inventory, Mapping) else inventory
    if not isinstance(entries, (tuple, list)):
        raise TypeError("frg.material_inventory_required")
    limit = context.parameters.get("max_items", 10000)
    if type(limit) is not int or limit < 1 or len(entries) > limit:
        raise ValueError("frg.inventory_limit")
    assets, findings = [], []
    observed_inventory = []
    seen = set()
    for entry in entries:
        context.checkpoint()
        if isinstance(entry, Mapping):
            path = str(entry.get("path", entry.get("location", "")))
            name = str(entry.get("filename", PurePosixPath(path).name))
            size, mtime = entry.get("size", entry.get("size_bytes")), entry.get("mtime")
        elif isinstance(entry, str):
            path, name, size, mtime = entry, PurePosixPath(entry).name, None, None
        else:
            path = str(getattr(entry, "path", ""))
            name = str(getattr(entry, "filename", PurePosixPath(path).name))
            size, mtime = getattr(entry, "size", None), getattr(entry, "mtime", None)
        if not path or path in seen:
            raise ValueError("frg.inventory_path_invalid")
        seen.add(path)
        observed_inventory.append((path, name, size, mtime))
        rule, period, format, diagnostic = recognize(name)
        if diagnostic:
            findings.append(diagnostic + ":" + path)
            continue
        if settings.source_id and rule.source_id != settings.source_id:
            continue
        assets.append(PublicationAsset(rule.source_id, period.text, "main", path, format,
            {"filename": name, "size": size, "mtime": mtime, "delivery": "filestore",
             "canonical_filename": canonical_filename(period, rule, format),
             "filename_date": period.snapshot_date.isoformat() if period.week_no is None else None,
             "publication_period": period.text, "week_number": period.week_no,
             "issue_order": (period.snapshot_date.year, period.snapshot_date.month,
                 period.week_no or 0, period.snapshot_date.day),
             "economic_period": "requires_table_interpretation"}))
    assessment = Assessment("partial" if findings else "complete", tuple(findings),
        observed=tuple(entry.source_id + ":" + entry.issue_id for entry in assets),
        qualifications=frozenset({"delivered_inventory_scope", "filename_attribution"}))
    inventory_identity = fingerprint(tuple(observed_inventory))
    assets = tuple(replace(asset, metadata={**asset.metadata, "inventory_identity": inventory_identity}) for asset in assets)
    listing = PublicationListing("frank_rg", assets, assessment, (inventory_identity,))
    return {"listing": listing, "coverage": assessment}


def select(inputs, settings: DeliverySettings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "frank_rg":
        raise TypeError("frg.publication_listing_required")
    from stratbox.shared.data.selection import IssueQuery, issue_query, select_publication_assets
    keys = set(IssueQuery.__dataclass_fields__) | {"source_id", "asset_id", "issue_id", "issue", "as_of", "periods", "format", "locator", "url"}
    raw = inputs.get("query", {key: value for key, value in context.parameters.items() if key in keys})
    query = issue_query(raw)
    if not settings.source_id and not query.source_ids:
        raise ValueError("frg.source_selection_required")
    if query.mode == "latest" and query.date_axis == "issue_id":
        query = replace(query, date_axis="issue_order")
    selection, report = select_publication_assets(listing, query,
        source_ids=(settings.source_id,) if settings.source_id else query.source_ids)
    return {"selection": selection, "report": report}


def _native_format(material):
    from io import BytesIO
    from zipfile import BadZipFile, ZipFile
    if material.data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    try:
        with ZipFile(BytesIO(material.data)) as archive:
            if len(archive.infolist()) > 20000:
                raise ValueError("frg.workbook_member_limit")
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                raise ValueError("frg.workbook_envelope_required")
            if "xl/workbook.bin" in names:
                return "xlsb"
            if "xl/workbook.xml" not in names:
                raise ValueError("frg.workbook_envelope_required")
            content = archive.getinfo("[Content_Types].xml")
            if content.file_size > 1024 * 1024:
                raise ValueError("frg.workbook_envelope_limit")
            return "xlsm" if b"macroEnabled" in archive.read(content) else "xlsx"
    except BadZipFile as error:
        raise ValueError("frg.workbook_envelope_required") from error


def identify(inputs, settings: DeliverySettings, context):
    from stratbox.shared.data.materials import MaterialInspection, StagedMaterialRef
    from stratbox.shared.data.values import ImmutableMaterialRef, ReadEvidence
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
    supplied = inputs["material"]
    material = supplied.material if isinstance(supplied, IdentifiedMaterial) else supplied
    if not isinstance(material, (Material, ImmutableMaterialRef, StagedMaterialRef)):
        raise ValueError("frg.material_claim_required")
    asset = inputs.get("asset")
    metadata = material.metadata
    claim = inputs.get("claim") or SourceClaim(settings.source_id,
        asset.issue_id if asset is not None else str(context.parameters.get("issue_id", metadata.get("issue_id", ""))))
    if not isinstance(claim, SourceClaim) or claim.source_id != settings.source_id:
        raise ValueError("frg.material_claim_required")
    if material.source_id not in {None, claim.source_id} or asset is not None and asset.source_id != claim.source_id:
        raise ValueError("frg.material_source_conflict")
    if metadata.get("issue_id") not in {None, "", claim.issue_id} or asset is not None and asset.issue_id != claim.issue_id:
        raise ValueError("frg.material_issue_conflict")
    inspection = inputs.get("inspection")
    detected = None
    if inspection is not None:
        if not isinstance(inspection, MaterialInspection) or inspection.identity != material.identity:
            raise ValueError("frg.material_inspection_conflict")
        verify = getattr(context, "verify_material_inspection", None)
        if verify is not None and verify(inspection, material):
            detected = inspection.format
    if detected is None and isinstance(material, Material):
        detected = _native_format(material)
    if detected not in settings.formats or inspection is not None and inspection.format != detected:
        raise ValueError("frg.workbook_envelope_required")
    filename = metadata.get("filename") or (asset.metadata.get("filename") if asset is not None else None)
    qualifications = {"caller_asserted_source", "native_envelope_verified"}
    if filename:
        rule, period, format, diagnostic = recognize(str(filename))
        if rule is not None and rule.source_id != claim.source_id:
            raise ValueError("frg.filename_source_conflict")
        if format != detected:
            raise ValueError("frg.filename_format_conflict")
        if diagnostic is None:
            if claim.issue_id and claim.issue_id != period.text:
                raise ValueError("frg.filename_issue_conflict")
            claim = SourceClaim(claim.source_id, period.text, claim.asset_id, "recognized")
            qualifications = {"filename_attribution", "native_envelope_verified", "economic_meaning_requires_table_rules"}
    if not claim.issue_id:
        raise ValueError("frg.publication_issue_required")
    uses = tuple(getattr(supplied, "source_uses", ()))
    evidence = inputs.get("evidence")
    if isinstance(evidence, ReadEvidence):
        if evidence.material_identity != material.identity or asset is not None and evidence.location != asset.locator:
            raise ValueError("frg.delivered_material_changed")
        accepted = getattr(context, "accepted_input", None)
        record = accepted("evidence") if accepted is not None else None
        producer = record.get("produced_by") if isinstance(record, Mapping) else getattr(record, "produced_by", None)
        if producer == "command.material.read" and claim.attribution == "recognized":
            uses += (SourceUse(SourceCoordinate(source_id=claim.source_id, issue_id=claim.issue_id,
                asset_id=claim.asset_id, material_identity=material.identity), "delivered_material",
                "filename_attribution", "sha256:" + material.identity.sha256),)
    assessment = Assessment(qualifications=frozenset(qualifications))
    return {"material": IdentifiedMaterial(material, claim, assessment,
        source_uses=tuple(dict.fromkeys(uses))), "assessment": assessment}


def assess(inputs, settings, context):
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.values import ImmutableMaterialRef
    materials = (Material, IdentifiedMaterial, ImmutableMaterialRef, StagedMaterialRef)
    evidence, baseline = inputs["evidence"], inputs.get("baseline")
    for value in (evidence, baseline):
        if isinstance(value, materials) and settings.source_id and value.source_id not in {None, settings.source_id}:
            raise ValueError("frg.source_comparison_conflict")
    from stratbox.core.commands.publications import retained_validation_assessment
    retained = retained_validation_assessment(inputs, context)
    if retained is not None:
        return retained
    if isinstance(evidence, materials) and isinstance(baseline, materials):
        def coordinates(value):
            if isinstance(value, IdentifiedMaterial):
                return value.claim.source_id, value.claim.issue_id, value.claim.asset_id
            return value.source_id or settings.source_id, str(value.metadata.get("issue_id", "")), str(value.metadata.get("asset_id", "main"))
        before, after = coordinates(baseline), coordinates(evidence)
        if before != after:
            return {"assessment": UpdateAssessment("changed", "explicit_publication_coordinates",
                predecessor=fingerprint(before), candidate=fingerprint(after))}
    if isinstance(evidence, IdentifiedMaterial):
        evidence = evidence.material
    if isinstance(baseline, IdentifiedMaterial):
        baseline = baseline.material
    if isinstance(evidence, materials):
        candidate = evidence.identity.sha256
        previous = baseline.identity.sha256 if isinstance(baseline, materials) else None
        status = "first_seen" if baseline is None else "unknown" if previous is None else "unchanged" if previous == candidate else "changed"
        return {"assessment": UpdateAssessment(status, "exact_material_bytes", predecessor=previous, candidate=candidate)}
    if not isinstance(evidence, PublicationListing):
        raise TypeError("frg.source_evidence_required")
    if evidence.domain_id != "frank_rg" or isinstance(baseline, PublicationListing) and baseline.domain_id != "frank_rg":
        raise ValueError("frg.publication_listing_required")
    scope = context.parameters.get("comparison_scope", "selected" if settings.source_id else "feed")
    if scope not in {"selected", "feed"}:
        raise ValueError("frg.comparison_scope_invalid")
    def members(value):
        entries = value.entries
        assessment = value.assessment
        if scope == "selected":
            from stratbox.shared.data.selection import select_publication_assets
            selected, report = select_publication_assets(value, inputs.get("query"),
                source_ids=(settings.source_id,) if settings.source_id else ())
            entries = selected.entries
            assessment = report.assessment
        return tuple(sorted((item.source_id, item.issue_id, item.asset_id, item.locator,
            item.format, fingerprint({key: value for key, value in item.metadata.items()
                if key != "inventory_identity"})) for item in entries)), assessment
    selected, coverage = members(evidence)
    before, previous_coverage = members(baseline) if isinstance(baseline, PublicationListing) else (None, None)
    candidate = fingerprint((scope, selected))
    previous = fingerprint((scope, before)) if before is not None else None
    status = "indeterminate" if (previous is None or previous == candidate or not coverage.complete
        or previous_coverage is not None and not previous_coverage.complete) else "changed"
    return {"assessment": UpdateAssessment(status,
        "delivered_metadata_only", ("metadata_cannot_establish_exact_byte_identity",), predecessor=previous, candidate=candidate,
        evidence={"scope": scope, "selected_coverage": coverage, "previous_selected_coverage": previous_coverage})}
