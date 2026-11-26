"""Selected publications retain exact physical origin and domain membership."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.catalog.selection import resolve_sources
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.domains.cbr.methods.actions import publications
from stratbox.domains.cbr.series.reporting_forms import PUBLICATIONS, PUBLICATIONS_SETTINGS, F101
from stratbox.shared.data.materials import MaterialInspection
from stratbox.shared.data.selection import IssueQuery, SourceQuery
from stratbox.shared.data.values import (Assessment, FetchEvidence, ImmutableMaterialRef, Material,
    PublicationAsset, PublicationListing, RequestSpec, SourceClaim, request_identity)

FEED = PUBLICATIONS.id
ISSUE = "2026-04-01"
URL = "https://www.cbr.ru/vfs/credit/forms/101-20260401.zip"


def context(*, trusted=False, inspection=False, **parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None,
        accepted_input=lambda name: {"produced_by": "command.material.fetch"} if trusted and name == "evidence" else None,
        verify_material_inspection=lambda descriptor, carrier: inspection and descriptor.identity == carrier.identity,
        verify_source_use=lambda use: False)


def zip_data(files):
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def fetch_for(request, material, **changes):
    evidence = FetchEvidence(request_identity(request), datetime.now(timezone.utc), 200,
        material.identity, effective_locator="https://www.cbr.ru/",
        actual_target_identity=sha256(request.url.encode()).hexdigest())
    return replace(evidence, **changes)


def test_caller_selects_rolling_workbooks_using_intrinsic_facets():
    catalog = DomainCatalog({"cbr": DOMAIN})
    selection = resolve_sources(catalog, SourceQuery(mode="predicate", facets={
        "publisher_id": ("cbr",), "issue_model": ("rolling",), "artifact_category": ("workbook",)}))
    assert len(selection.source_ids) == 42
    assert FEED not in selection.source_ids
    chosen = selection.source_ids[-1], selection.source_ids[0]
    assert resolve_sources(catalog, SourceQuery(includes=chosen)).source_ids == chosen
    assert resolve_sources(catalog, SourceQuery()).source_ids == ()


def test_forms_feed_discovers_unknown_numeric_form_without_semantic_declaration():
    original = Material(b'<a href="/vfs/credit/forms/101-20260401.zip">Known</a>'
        b'<a href="/vfs/credit/forms/999-20260401.rar">Physical only</a>', "text/html", FEED + ".index")
    listing = publications.scan({"index": original}, PUBLICATIONS_SETTINGS, context())["listing"]
    unknown = next(asset for asset in listing.entries if asset.asset_id == "form-0409999")
    assert "known_series_id" not in unknown.metadata
    assert unknown.metadata["discovery"] == "observed_index"
    assert listing.lineage == (original.identity,)
    result = publications.select({"listing": listing,
        "query": IssueQuery(asset_ids=(unknown.asset_id,), issues=(ISSUE,), mode="exact")}, PUBLICATIONS_SETTINGS, context())
    assert result["selection"].entries == (unknown,)
    assert "cbr.reporting_forms.f999" not in DOMAIN.series
    with pytest.raises(ValueError, match="explicit_form_selection"):
        publications.select({"listing": listing}, PUBLICATIONS_SETTINGS, context())


def test_index_role_ignores_asset_date_and_direct_request_remains_unobserved():
    request = publications.prepare_request({"query": {"issue_id": ISSUE, "form_code": "999"}},
        PUBLICATIONS_SETTINGS, context(role="index"))["request"]
    assert request.url == PUBLICATIONS_SETTINGS.locator and request.metadata["role"] == "index"
    direct = publications.prepare_request({"query": {"issue_id": ISSUE, "form_code": "999", "role": "asset"}},
        PUBLICATIONS_SETTINGS, context())["request"]
    assert direct.url.endswith("999-20260401.rar")
    assert direct.metadata["discovery"] == "explicit_locator"
    with pytest.raises(ValueError, match="explicit_form_code"):
        publications.prepare_request({"query": {"issue_id": ISSUE}}, PUBLICATIONS_SETTINGS, context())


def test_ambiguity_is_per_form_and_issue_across_multidate_selection():
    one = PublicationAsset(FEED, ISSUE, "form-0409101", URL, "zip")
    conflict = replace(one, locator=URL + "?alternative=1")
    later = replace(one, issue_id="2026-05-01", locator=URL.replace("0401", "0501"))
    listing = PublicationListing("cbr", (one, conflict, later))
    with pytest.raises(ValueError, match="ambiguous_asset"):
        publications.select({"listing": listing, "query": IssueQuery()}, PUBLICATIONS_SETTINGS, context())
    result = publications.select({"listing": listing,
        "query": IssueQuery(ambiguity="report")}, PUBLICATIONS_SETTINGS, context())
    assert result["selection"].entries == (later,)
    assert result["report"].ambiguous
    resolved = publications.select({"listing": listing,
        "query": IssueQuery(locators=(URL,))}, PUBLICATIONS_SETTINGS, context())
    assert resolved["selection"].entries == (one,)


@pytest.mark.parametrize("body", (b"<html>unavailable</html>", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + bytes(64), b"\x03" + bytes(31)))
def test_wrong_real_format_never_becomes_a_fixed_xlsx_original(body):
    series = DOMAIN.series["cbr.funding.funds_all"]
    settings = series.commands["command.material.identify"].settings
    with pytest.raises(ValueError, match="format_unavailable"):
        publications.identify({"material": Material(body, source_id=series.id)}, settings, context())


def test_forged_inspection_does_not_override_buffered_bytes_or_retained_authority():
    settings = DOMAIN.series["cbr.funding.funds_all"].commands["command.material.identify"].settings
    material = Material(b"<html>error</html>", source_id=settings.series_id)
    descriptor = MaterialInspection(material.identity, "xlsx")
    with pytest.raises(ValueError, match="inspection_mismatch"):
        publications.identify({"material": material, "inspection": descriptor}, settings, context())
    retained = ImmutableMaterialRef("objects/body", material.identity,
        metadata={"source_id": settings.series_id})
    with pytest.raises(ValueError, match="accepted_material_inspection_required"):
        publications.identify({"material": retained, "inspection": descriptor}, settings, context())


def test_macro_enabled_envelope_is_distinct_even_without_a_vba_project():
    settings = DOMAIN.series["cbr.funding.funds_all"].commands["command.material.identify"].settings
    body = zip_data({"[Content_Types].xml": b'<Types ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>',
        "xl/workbook.xml": b"<workbook/>"})
    with pytest.raises(ValueError, match="format_unavailable"):
        publications.identify({"material": Material(body, source_id=settings.series_id)}, settings, context())


def test_verified_feed_origin_adds_exact_form_use_without_relabeling_original():
    material = Material(zip_data({"data.dbf": b"physical payload"}), "application/zip", FEED,
        metadata={"issue_id": ISSUE, "asset_id": "form-0409101"})
    asset = PublicationAsset(FEED, ISSUE, "form-0409101", URL, "zip")
    request = RequestSpec(URL, source_id=FEED)
    settings = F101.commands["command.material.identify"].settings
    result = publications.identify({"material": material, "asset": asset, "request": request,
        "evidence": fetch_for(request, material)}, settings, context(trusted=True))["material"]
    assert result.claim.source_id == FEED and result.material is material
    assert {use.coordinate.source_id for use in result.source_uses} == {FEED, F101.id}
    assert all(use.coordinate.material_identity == material.identity for use in result.source_uses)
    bad_settings = DOMAIN.series["cbr.reporting_forms.f802"].commands["command.material.identify"].settings
    with pytest.raises(ValueError, match="asset_mismatch"):
        publications.identify({"material": material, "asset": asset}, bad_settings, context())
    with pytest.raises(ValueError, match="verified_origin_required"):
        publications.identify({"material": material, "asset": asset, "request": request,
            "evidence": fetch_for(request, material)}, settings, context())


def test_retained_validation_reuses_identity_with_qualified_core_evidence():
    source = DOMAIN.series["cbr.funding.funds_all"]
    body = zip_data({"[Content_Types].xml": b"<Types/>", "xl/workbook.xml": b"<workbook/>"})
    reference = ImmutableMaterialRef("objects/retained", Material(body).identity, effect_id="retention",
        provider_scope="fixture", metadata={"source_id": source.id})
    request = RequestSpec(source.publication.locator, source_id=source.id)
    evidence = fetch_for(request, reference, status_code=304, validation_kind="retained_validation",
        retained_effect_id="retention", representation_identity="core-verified-request-basis")
    descriptor = MaterialInspection(reference.identity, "xlsx", provider_scope="fixture")
    result = publications.identify({"material": reference, "inspection": descriptor,
        "request": request, "evidence": evidence}, source.commands["command.material.identify"].settings,
        context(trusted=True, inspection=True))["material"]
    assert result.material is reference and result.claim.attribution == "verified"
    wrong = replace(evidence, actual_target_identity="0" * 64)
    with pytest.raises(ValueError, match="verified_attribution_requires_evidence"):
        publications.identify({"material": reference, "inspection": descriptor,
            "request": request, "evidence": wrong, "claim": SourceClaim(source.id, attribution="verified")},
            source.commands["command.material.identify"].settings, context(trusted=True, inspection=True))
