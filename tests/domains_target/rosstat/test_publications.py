"""Publication evidence and supplied document semantics use bounded explicit scopes."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from stratbox.domains.rosstat.domain import DOMAIN
from stratbox.domains.rosstat.methods import publications, materials, documents
from stratbox.domains.rosstat.common.publication_rules import parse_issue
from stratbox.shared.data.values import DocumentBlock, DocumentEvidence, DocumentStructure, Material, SourceClaim


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def index(source_id, text):
    settings = DOMAIN.common["publications"][source_id].settings
    material = Material(text.encode(), "text/html", source_id + ".index", "utf-8")
    return publications.scan({"index": material}, settings, context())["listing"]


@pytest.mark.parametrize("source_id,filename,issue,asset", (
    ("rosstat.socioeconomic_russia", "osn-08-2026.pdf", "2026-08", "report"),
    ("rosstat.socioeconomic_regions", "info-stat-06-2026.zip", "2026-06", "regional_archive"),
    ("rosstat.short_term_indicators.publications", "2026-08.xlsx", "2026-08", "main_workbook"),
    ("rosstat.population_municipalities.publications", "BUL_MO_2024.xlsx", "2024", "population_workbook"),
))
def test_four_publication_channels_preserve_distinct_issue_and_asset_rules(source_id, filename, issue, asset):
    listing = index(source_id, f'<a href="/storage/mediabank/{filename}">Publication</a>')
    entry, = listing.entries
    assert (entry.source_id, entry.issue_id, entry.asset_id) == (source_id, issue, asset)
    assert listing.assessment.status == "unknown"
    assert "publisher_inventory_not_certified" in listing.assessment.qualifications


def test_partial_listing_never_proves_absence_unchanged_bytes_or_latest_publisher_issue():
    sid = "rosstat.short_term_indicators.publications"
    settings = DOMAIN.common["publications"][sid].settings
    first = index(sid, '<a href="/storage/mediabank/2026-08.xlsx">August</a><a href="/storage/mediabank/2026-07.xlsx">July</a>')
    changed = index(sid, '<a href="/storage/mediabank/2026-07.xlsx">July</a><a href="/download?id=august">Download</a>')
    assessment = publications.assess({"evidence": changed, "baseline": first}, settings, context())["assessment"]
    assert assessment.status == "indeterminate"
    selected = publications.select({"listing": first, "query": {"mode": "latest", "asset_ids": ("main_workbook",)}}, settings, context())["selection"]
    assert selected.entries[0].issue_id == "2026-08"
    assert "latest_observed_only" in selected.assessment.qualifications
    assert publications.assess({"evidence": first, "baseline": first}, settings, context())["assessment"].status == "indeterminate"


def test_multiasset_labels_and_same_asset_ambiguity_are_explicit():
    sid = "rosstat.short_term_indicators.publications"
    listing = index(sid, '<a href="/storage/mediabank/2026-08.xlsx">2026-08</a>'
        '<a href="/storage/mediabank/tables_2026-08.xlsx">Таблицы 2026-08</a>'
        '<a href="/storage/mediabank/annex_2026-08.xlsx">Приложение 1, 2026-08</a>')
    assert {entry.asset_id for entry in listing.entries} == {"main_workbook", "tables", "annex_1"}
    collision = replace(listing, entries=(listing.entries[0], replace(listing.entries[0], locator="https://rosstat.gov.ru/upload/2026-08.xlsx")))
    with pytest.raises(ValueError, match="ambiguous_asset"):
        publications.select({"listing": collision}, DOMAIN.common["publications"][sid].settings, context())
    assert not index(sid, '<a href="/storage/mediabank/2026-08.xlsx">Выпуск 2025-08</a>').entries


def test_official_request_and_asset_context_reject_contradictions_before_fetch():
    sid = "rosstat.short_term_indicators.publications"
    spec = DOMAIN.common["publications"][sid]
    asset, = index(sid, '<a href="/storage/mediabank/2026-08.xlsx">2026-08</a>').entries
    request = publications.request({"locator": asset}, spec.settings, context())["request"]
    assert request.url == asset.locator and request.metadata["issue_id"] == "2026-08"
    with pytest.raises(ValueError, match="identity_conflict"):
        publications.request({"locator": replace(asset, issue_id="2025-08")}, spec.settings, context())
    with pytest.raises(ValueError, match="official_url_required"):
        publications.request({"locator": replace(asset, locator="https://evil.example/storage/mediabank/2026-08.xlsx")}, spec.settings, context())
    with pytest.raises(ValueError, match="official_url_required"):
        publications.request({"locator": replace(asset, locator="https://rosstat.gov.ru/admin/2026-08.xlsx")}, spec.settings, context())
    with pytest.raises(ValueError, match="base_forbidden"):
        index(sid, '<base href="https://evil.example/"><a href="2026-08.xlsx">X</a>')


def test_native_envelope_and_source_claim_are_checked_without_decoding_numerical_tables():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        for name in ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"):
            archive.writestr(name, "<fixture/>")
    body = stream.getvalue()
    assert materials.detect_bytes(body, expected="xlsx") == "xlsx"
    assert materials.detect_bytes(b"%PDF-1.7\nfixture\n%%EOF", expected="pdf") == "pdf"
    with pytest.raises(ValueError, match="envelope_mismatch"):
        materials.detect_bytes(b"<html>temporarily unavailable</html>", expected="xlsx")
    rules = DOMAIN.series["rosstat.short_term_indicators"].commands["command.material.identify"].settings
    original = Material(body, source_id=rules.source_id, metadata={"issue_id": "2026-08", "format": "xlsx"})
    result = materials.identify({"material": original}, rules, context())["material"]
    assert result.material.identity == original.identity and result.claim.issue_id == "2026-08"
    with pytest.raises(ValueError, match="source_conflict"):
        materials.identify({"material": replace(original, source_id="rosstat.population_municipalities")}, rules, context())


def test_named_periods_and_historical_issue_years_do_not_infer_observation_dates():
    monthly = DOMAIN.common["publications"]["rosstat.short_term_indicators.publications"].settings.issue_rule
    annual = DOMAIN.common["publications"]["rosstat.population_municipalities.publications"].settings.issue_rule
    assert parse_issue(monthly, "source.xlsx", "Январь-август 2026")[0] == "2026-08"
    assert parse_issue(annual, "BUL_MO_2024.xlsx", "")[0] == "2024"
    assert parse_issue(annual, "BUL_MO_2024_2025.xlsx", "2024")[0] is None


def test_accepted_http_bytes_do_not_certify_opaque_publication_membership():
    from datetime import datetime, timezone
    from hashlib import sha256
    from stratbox.shared.data.values import FetchEvidence, request_identity
    sid = "rosstat.short_term_indicators.publications"
    settings = DOMAIN.common["publications"][sid].settings
    asset, = index(sid, '<a href="/storage/mediabank/2026-08.xlsx">August</a>').entries
    request = publications.request({"locator": asset}, settings, context())["request"]
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name in ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"):
            archive.writestr(name, "<fixture/>")
    original = Material(output.getvalue(), source_id=sid, metadata={"issue_id": asset.issue_id, "asset_id": asset.asset_id})
    evidence = FetchEvidence(request_identity(request), datetime.now(timezone.utc), 200,
        original.identity, effective_locator="https://rosstat.gov.ru/",
        actual_target_identity=sha256(request.url.encode()).hexdigest())
    accepted = SimpleNamespace(parameters={}, checkpoint=lambda: None,
        accepted_input=lambda name: {"produced_by": "command.material.fetch"} if name == "evidence" else None)
    result = materials.identify({"material": original, "asset": asset, "request": request,
        "evidence": evidence}, settings, accepted)["material"]
    assert result.claim.attribution == "recognized"
    assert {"verified_transport", "explicit_selected_asset"} <= result.assessment.qualifications
    assert "verified_source" not in result.assessment.qualifications
    assert all(use.qualification != "verified" for use in result.source_uses)
    with pytest.raises(ValueError, match="source_attribution_not_established"):
        materials.identify({"material": original, "asset": asset, "request": request, "evidence": evidence,
            "claim": SourceClaim(sid, asset.issue_id, asset.asset_id, "verified")}, settings, accepted)


def test_explicit_document_regions_are_required_before_cell_interpretation():
    material = Material(b"explicit synthetic document", source_id="rosstat.socioeconomic_russia", metadata={"issue_id": "2026-08"})
    structure = DocumentStructure("pdf", (DocumentBlock(0, "page", "Region;Amount\nExample;12,5", page=1),), material.identity)
    physical = DocumentEvidence(material, structure)
    rules = documents.DocumentRules(material.source_id, material.identity, "Synthetic selected text only",
        (documents.TextRegion(0, "amount", 1, 2, 2, separator=";"),),
        (documents.DocumentCell("amount", 2, 2, "fixture.amount", "example", "publisher.region", ("2026-08-01", "2026-08-31"),
            "monthly", "RUB", "flow", "fixture_population"),))
    with pytest.raises(ValueError, match="geometry_required"):
        documents.TextRegion(0, "amount", 1, 2, 2)
    extracted = documents.extract({"physical": physical}, rules, context())["tables"]
    dataset = documents.interpret({"tables": extracted}, rules, context())["dataset"]
    assert dataset.rows[0]["value"] == Decimal("12.5")
    assert dataset.rows[0]["period"] == ("2026-08-01", "2026-08-31")
    assert "explicit_supplied_document_semantics" in dataset.assessment.qualifications
    with pytest.raises(ValueError, match="review_evidence_required"):
        documents.extract({"physical": physical}, replace(rules, material_identity=Material(b"different").identity), context())
