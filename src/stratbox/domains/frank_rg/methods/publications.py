"""Pure recognition of caller-delivered files; no website acquisition."""
from __future__ import annotations

from dataclasses import dataclass
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
    assets, findings = [], []
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
        rule, period, format, diagnostic = recognize(name)
        if diagnostic:
            findings.append(diagnostic + ":" + path)
            continue
        if settings.source_id and rule.source_id != settings.source_id:
            continue
        assets.append(PublicationAsset(rule.source_id, period.text, "main", path, format,
            {"filename": name, "size": size, "mtime": mtime,
             "canonical_filename": canonical_filename(period, rule, format),
             "publication_date": period.snapshot_date, "week_number": period.week_no,
             "economic_period": "requires_table_interpretation"}))
    assessment = Assessment("partial" if findings else "complete", tuple(findings),
        observed=tuple(entry.source_id + ":" + entry.issue_id for entry in assets),
        qualifications=frozenset({"delivered_inventory_scope", "filename_attribution"}))
    listing = PublicationListing("frank_rg", tuple(assets), assessment)
    return {"listing": listing, "coverage": assessment}


def select(inputs, settings: DeliverySettings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "frank_rg":
        raise TypeError("frg.publication_listing_required")
    query = inputs.get("query", context.parameters)
    query = query if isinstance(query, Mapping) else {}
    source_id = settings.source_id or query.get("source_id")
    if not source_id:
        raise ValueError("frg.source_selection_required")
    candidates = tuple(entry for entry in listing.entries if entry.source_id == source_id)
    issue = query.get("issue_id", query.get("issue"))
    if issue is None and candidates:
        latest = max((entry.metadata["publication_date"], entry.metadata.get("week_number") or 0) for entry in candidates)
        candidates = tuple(entry for entry in candidates if (entry.metadata["publication_date"], entry.metadata.get("week_number") or 0) == latest)
    elif issue is not None:
        candidates = tuple(entry for entry in candidates if entry.issue_id == issue)
    assessment = Assessment("complete" if len(candidates) == 1 else "unknown",
        () if len(candidates) == 1 else ("ambiguous_same_issue_materials" if candidates else "requested_issue_not_observed",),
        observed=tuple(entry.locator for entry in candidates))
    return {"selection": AssetSelection(candidates, assessment)}


def identify(inputs, settings: DeliverySettings, context):
    material = inputs["material"]
    claim = inputs.get("claim") or SourceClaim(settings.source_id, str(context.parameters.get("issue_id", material.metadata.get("issue_id", ""))))
    if not isinstance(material, Material) or not isinstance(claim, SourceClaim) or claim.source_id != settings.source_id:
        raise ValueError("frg.material_claim_required")
    if material.source_id not in {None, claim.source_id}:
        raise ValueError("frg.material_source_conflict")
    if material.metadata.get("issue_id") not in {None, "", claim.issue_id}:
        raise ValueError("frg.material_issue_conflict")
    filename = material.metadata.get("filename")
    qualifications = {"caller_asserted_source"}
    if filename:
        rule, period, format, diagnostic = recognize(str(filename))
        if rule is not None and rule.source_id != claim.source_id:
            raise ValueError("frg.filename_source_conflict")
        if diagnostic is None:
            if claim.issue_id and claim.issue_id != period.text:
                raise ValueError("frg.filename_issue_conflict")
            claim = SourceClaim(claim.source_id, period.text, claim.asset_id, "filename")
            qualifications = {"filename_attribution", "economic_meaning_requires_table_rules"}
    if not claim.issue_id:
        raise ValueError("frg.publication_issue_required")
    assessment = Assessment(qualifications=frozenset(qualifications))
    return {"material": IdentifiedMaterial(material, claim, assessment), "assessment": assessment}


def assess(inputs, settings, context):
    evidence, baseline = inputs["evidence"], inputs.get("baseline")
    if isinstance(evidence, IdentifiedMaterial):
        evidence = evidence.material
    if isinstance(baseline, IdentifiedMaterial):
        baseline = baseline.material
    if isinstance(evidence, Material):
        candidate = evidence.identity.sha256
        previous = baseline.identity.sha256 if isinstance(baseline, Material) else baseline if isinstance(baseline, str) else None
        status = "first_seen" if previous is None else "unchanged" if previous == candidate else "changed"
        return {"assessment": UpdateAssessment(status, "exact_material_bytes", predecessor=previous, candidate=candidate)}
    if not isinstance(evidence, PublicationListing):
        raise TypeError("frg.source_evidence_required")
    candidate = fingerprint(evidence.entries)
    previous = fingerprint(baseline.entries) if isinstance(baseline, PublicationListing) else None
    return {"assessment": UpdateAssessment("indeterminate" if previous is None or previous == candidate else "changed",
        "delivered_metadata_only", ("metadata_cannot_establish_exact_byte_identity",), predecessor=previous, candidate=candidate)}
