"""Publisher facts and source attribution use direct standard-command methods."""
from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, SourceClaim


FIXED = "cbr.corporate_lending.corp_debt_a"
FORM = "cbr.reporting_forms.f101"
ESCROW = "cbr.project_finance.escrow"


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def call(source, command, inputs, **parameters):
    spec = DOMAIN.series[source].commands[command]
    return spec.method.resolve()(inputs, spec.settings, context(**parameters))


def workbook():
    book = Workbook()
    book.active.append(["Published table", 1])
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def scan(source, html, **parameters):
    return call(source, "command.publication.scan",
        {"index": Material(html, "text/html", source + ".index")}, **parameters)["listing"]


def test_catalog_has_57_distinct_publications_with_shared_methods_and_explicit_source_constraints():
    assert len(DOMAIN.series) == 57
    assert len({item.publication.family_id for item in DOMAIN.series.values()}) == 12
    for source, declaration in DOMAIN.series.items():
        assert declaration.id == declaration.publication.series_id == source
        for command in ("command.request.prepare", "command.publication.scan", "command.issue.select",
                        "command.material.identify", "command.table.extract", "command.table.interpret"):
            assert callable(declaration.commands[command].method.resolve())
            assert declaration.commands[command].applicability.source_ids == {source}
    assert DOMAIN.series["cbr.funding.escrow_accounts"].publication.family_id != DOMAIN.series[ESCROW].publication.family_id


@pytest.mark.parametrize("code", ("101", "102", "123", "134", "135", "802", "803", "805"))
def test_dated_form_discovery_preserves_only_real_calendar_dates_and_official_urls(code):
    source = "cbr.reporting_forms.f" + code
    html = f'''<a href="/vfs/credit/forms/{code}-20261001.rar">one</a>
      <a href="/vfs/credit/forms/{code}-20260231.rar">invalid date</a>
      <a href="https://other.example/{code}-20260901.rar">external</a>'''.encode()
    listing = scan(source, html)
    assert len(listing.entries) == 1
    assert listing.entries[0].issue_id == "2026-10-01"
    assert listing.entries[0].format == "rar"
    assert "observed_index_only" in listing.assessment.qualifications


def test_explicit_broken_offline_index_never_falls_back_to_network():
    class ForbiddenHTTP:
        def fetch(self, request):
            pytest.fail("A supplied index must not trigger network fallback")

    with StrategyBox(providers={"http": ForbiddenHTTP()}) as box:
        result = box.invoke("operation.source.check", inputs={"index": Material(b"broken", "text/html", FORM + ".index")},
            target=SeriesTarget(FORM))
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("assessment").status in {"unknown", "indeterminate"}
        assert result.output("selection").entries == ()


def test_historical_escrow_html_remains_original_only_until_geometry_is_reviewed():
    listing = scan(ESCROW, b'<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">2019</a>')
    asset, = listing.entries
    assert asset.issue_id == "2019-08-26" and asset.format == "html"
    original = Material(b"<html>original</html>", "text/html", ESCROW)
    identified = call(ESCROW, "command.material.identify",
        {"material": original, "claim": SourceClaim(ESCROW, asset.issue_id)})["material"]
    assert identified.material.data == original.data
    with pytest.raises(ValueError, match="physical_evidence_required"):
        call(ESCROW, "command.table.extract", {"physical": original})


def test_neutral_filestore_read_gets_explicit_source_and_issue_context(tmp_path):
    data = workbook()
    store = LocalFileStore(str(tmp_path))
    store.write_bytes("renamed.xlsx", data)
    with StrategyBox(providers={"filestore": store}) as box:
        read = box.invoke("command.material.read", inputs={"location": "renamed.xlsx"})
        assert read.outcome == "succeeded", read.diagnostics
        admitted = box.invoke("command.material.identify",
            inputs={"material": read.output("material"), "claim": SourceClaim(FIXED, "2026-11-23")},
            target=SeriesTarget(FIXED))
        assert admitted.outcome == "succeeded", admitted.diagnostics
        assert admitted.output("material").material.data == data
        assert admitted.output("material").claim.issue_id == "2026-11-23"


def test_alternative_urls_and_format_variants_are_preserved_without_silent_preference():
    first = "/vfs/credit/forms/101-20261001.rar"
    alternate = "/Collection/Collection/File/12345/101-20261001.rar"
    html = f'''<a href="{first}">one</a><a href="{alternate}">alternative</a>
       <a href="{first}">duplicate</a><a href="/vfs/credit/forms/101-20261001.zip">format variant</a>
       <a href="https://[broken]/101-20261001.rar">broken</a>'''.encode()
    listing = scan(FORM, html)
    assert len(listing.entries) == 3
    selection = call(FORM, "command.issue.select",
        {"listing": listing, "query": {"issue_id": "2026-10-01"}})["selection"]
    assert selection.assessment.status == "conflicted"
    assert len(selection.entries) == 3
    chosen = call(FORM, "command.issue.select",
        {"listing": listing, "query": {"issue_id": "2026-10-01", "locator": "https://www.cbr.ru" + alternate}})["selection"]
    assert len(chosen.entries) == 1 and chosen.entries[0].locator.endswith(alternate)


def test_fixed_sources_keep_the_declared_locator_without_inventing_issue_dates():
    listing = scan(FIXED, b"<html>Caller retained index evidence</html>")
    asset, = listing.entries
    assert asset.locator == DOMAIN.series[FIXED].publication.locator
    assert asset.issue_id == "" and asset.format == "xlsx"
    with pytest.raises(ValueError, match="source_url_invalid"):
        call(FIXED, "command.request.prepare", {"locator": ""})


@pytest.mark.parametrize("issue", ("20261001", "2026-W40-4", "2026-02-31", ""))
def test_dated_identification_requires_one_canonical_calendar_issue(issue):
    with pytest.raises(ValueError, match="issue"):
        call(FORM, "command.material.identify",
            {"material": Material(b"Rar!\x1a\x07\x00synthetic", "application/x-rar-compressed"),
             "claim": SourceClaim(FORM, issue)})


def test_claim_cannot_overwrite_another_known_source_or_forge_verified_attribution():
    original = Material(workbook(), source_id=FIXED)
    with pytest.raises(ValueError, match="source_mismatch"):
        call("cbr.funding.funds_all", "command.material.identify",
            {"material": original, "claim": SourceClaim("cbr.funding.funds_all", "2026-11-01")})
    with pytest.raises(ValueError, match="verified_attribution_requires_evidence"):
        call(FIXED, "command.material.identify",
            {"material": replace(original, source_id=None), "claim": SourceClaim(FIXED, "2026-11-01", attribution="verified")})


def test_wrong_native_media_and_truncated_xlsx_are_rejected_at_attribution():
    for material in (Material(b"not a workbook"), Material(b"<html>failure</html>", "application/zip"),
                     Material(b"PK\x03\x04truncated")):
        with pytest.raises(ValueError, match="signature|format|envelope"):
            call(FIXED, "command.material.identify",
                {"material": material, "claim": SourceClaim(FIXED, "2026-11-01")})


def test_bounded_index_interpretation_rejects_unbounded_anchor_sets():
    html = b'<a href="/vfs/credit/forms/101-20261001.rar">one</a>' * 3
    with pytest.raises(ValueError, match="index_link_limit"):
        scan(FORM, html, max_links=2)


def test_request_uses_shared_publisher_limits_and_explicit_dated_format():
    request = call(FORM, "command.request.prepare", {"query": {"issue_id": "2026-10-01", "format": "dbf"}})["request"]
    assert request.url == "https://www.cbr.ru/vfs/credit/forms/101-20261001.dbf"
    assert request.max_bytes == DOMAIN.common["access"].max_response_bytes
    assert request.timeout == DOMAIN.common["access"].deadline_seconds
    assert request.source_id == FORM
    with pytest.raises(ValueError, match="format_unavailable"):
        call(FORM, "command.request.prepare", {"query": {"issue_id": "2026-10-01", "format": "xlsx"}})
