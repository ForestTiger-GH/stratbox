"""Offline source profile, original envelope, and registered-owner tests."""

from io import BytesIO
from zipfile import ZipFile
import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.rosstat.publications.catalog import list_rosstat_sources, get_rosstat_source
from stratbox.domains.rosstat.publications.contracts import DiscoverRosstatRequest
from stratbox.domains.rosstat.publications.discovery.selection import compare_publication_indices, select_assets
from stratbox.domains.rosstat.publications.operations import discover
from stratbox.domains.rosstat.publications.download.envelope import detect_bytes
from stratbox.domains.rosstat._source import allowed_file_url
from stratbox.core.execution import OperationFailure
from stratbox.domains.registry import operation_catalog


def _index(series, body):
    source = SourcePayload(body.encode("utf-8"), "text/html", series + ".index", charset="utf-8")
    result = discover(DiscoverRosstatRequest(series, source))
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


@pytest.mark.parametrize("series,href,issue", [
    ("rosstat.socioeconomic_russia", "osn-08-2026.pdf", "2026-08"),
    ("rosstat.socioeconomic_regions", "info-stat-06-2026.zip", "2026-06"),
    ("rosstat.short_term_indicators", "2026-08.xlsx", "2026-08"),
    ("rosstat.population_municipalities", "BUL_MO_2024.xlsx", "2024"),
])
def test_four_sources_recognize_offline_native_originals(series, href, issue):
    html = '<a href="/storage/mediabank/' + href + '">Publication</a>'
    index = _index(series, html)
    assert index.qualified_assets[0].key.issue.issue_id == issue
    assert index.qualified_assets[0].key.source_id.startswith("rosstat.")
    assert index.live_profile_verified is False


def test_catalog_exact_urls():
    sources = list_rosstat_sources()
    assert len(sources) == len({source.series_id for source in sources}) == 4
    assert get_rosstat_source("rosstat.short_term_indicators").landing_url == (
        "https://rosstat.gov.ru/compendium/document/50802"
    )


def test_ambiguity_prevents_selection():
    series = "rosstat.short_term_indicators"
    html = (
        '<a href="/storage/mediabank/2026-08.xlsx">one</a>'
        '<a href="/storage/mediabank/other_2026-08.xlsx">two</a>'
    )
    index = _index(series, html)
    assert index.qualified_assets == ()
    assert len(index.ambiguous_assets) == 2
    assert index.coverage == "partial"


def test_link_reordering_not_change_and_locator_move_is_index_only():
    series = "rosstat.short_term_indicators"
    html = '<a href="/storage/mediabank/2026-08.xlsx">Aug</a><a href="/storage/mediabank/2026-07.xlsx">Jul</a>'
    a = _index(series, html)
    b = _index(series, html.replace("Aug", "August").replace("Jul", "July"))
    assert compare_publication_indices(a, b).state == "unchanged"
    moved = _index(series, html.replace("/2026-08.xlsx", "/another_2026-08.xlsx"))
    assert compare_publication_indices(a, moved).relocated_asset_ids


def test_selection_limits_and_latest():
    series = "rosstat.short_term_indicators"
    index = _index(series,
        '<a href="/storage/mediabank/2026-07.xlsx">July</a>'
        '<a href="/storage/mediabank/2026-08.xlsx">August</a>')
    assert len(select_assets(index, policy="latest_qualified")) == 1
    assert select_assets(index, issue_ids=("2026-07",))[0].key.issue.issue_id == "2026-07"
    with pytest.raises(ValueError):
        select_assets(index, policy="all_qualified", max_assets=1)


def test_untrusted_urls_html_base_and_missing_attachments_fail_closed():
    for url in ("http://rosstat.gov.ru/storage/mediabank/a.xlsx",
                "https://example.org/storage/mediabank/a.xlsx",
                "https://rosstat.gov.ru/compendium/document/50802"):
        assert not allowed_file_url(url)
    series = "rosstat.short_term_indicators"
    bad = discover(DiscoverRosstatRequest(series, SourcePayload(
        b'<base href="https://evil.example/"><a href="2026-08.xlsx">X</a>',
        "text/html", series + ".index",
    )))
    assert bad.outcome == "failed"
    empty = discover(DiscoverRosstatRequest(series, SourcePayload(
        b"<html><title>Temporarily unavailable</title></html>",
        "text/html", series + ".index",
    )))
    assert empty.outcome == "failed"


def test_native_envelopes():
    assert detect_bytes(b"%PDF-1.7\nfoo\n%%EOF", expected="pdf") == "pdf"
    with BytesIO() as sink:
        with ZipFile(sink, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("_rels/.rels", "<Relationships/>")
            z.writestr("xl/workbook.xml", "<workbook/>")
        data = sink.getvalue()
    assert detect_bytes(data, expected="xlsx") == "xlsx"
    with pytest.raises(OperationFailure):
        detect_bytes(b"<html>error</html>", expected="xlsx")
    assert detect_bytes(b"Rar!\x1a\x07\x01\x00" + b"test-archive!", expected="rar") == "rar"


def test_registered_operations_resolve():
    catalog = operation_catalog()
    assert all(catalog.get(name, 1) for name in (
        "rosstat.publications.discover",
        "rosstat.publications.acquire",
        "rosstat.publications.acquire_to_store",
    ))


def test_wrong_series_payload_is_rejected_offline():
    series = "rosstat.short_term_indicators"
    payload = SourcePayload(
        b'<a href="/storage/mediabank/2026-08.xlsx">X</a>',
        "text/html", "rosstat.socioeconomic_russia.index",
    )
    result = discover(DiscoverRosstatRequest(series, payload))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "rosstat.index_source_mismatch"


def test_official_file_redirects_stay_within_source_roots():
    from stratbox.domains.rosstat._source import file_request
    request = file_request(
        "https://rosstat.gov.ru/storage/mediabank/2026-08.xlsx",
        1024 * 1024, 30,
    )
    assert request.permits("https://www.rosstat.gov.ru/storage/mediabank/renamed.xlsx")
    assert request.permits("https://rosstat.gov.ru/upload/other.xlsx")
    assert not request.permits("https://rosstat.gov.ru/admin/private.xlsx")
    assert not request.permits("https://evil.example/storage/mediabank/2026-08.xlsx")


def test_official_html_base_root_and_source_text_are_preserved():
    series = "rosstat.short_term_indicators"
    html = '<base href="/"><a href="storage/mediabank/2026-08.xlsx"> Aug  2026 </a>'
    index = _index(series, html)
    assert len(index.qualified_assets) == 1
    item = index.qualified_assets[0]
    assert item.url == "https://rosstat.gov.ru/storage/mediabank/2026-08.xlsx"
    assert item.label_literal == " Aug  2026 "
    assert item.raw_href == "storage/mediabank/2026-08.xlsx"
