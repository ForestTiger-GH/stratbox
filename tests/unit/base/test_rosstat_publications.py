"""Unverified publisher HTML is candidate evidence, never complete inventory."""

from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile

import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.core.network import HttpResponse
from stratbox.domains.rosstat.publications.catalog import list_rosstat_sources, get_rosstat_source
from stratbox.domains.rosstat.publications.contracts import DiscoverRosstatRequest
from stratbox.domains.rosstat.publications.discovery.selection import (
    compare_publication_indices, select_assets,
)
from stratbox.domains.rosstat.publications.discovery.coverage import (
    qualified_inventory_from_index, qualified_presence_from_index,
)
from stratbox.domains.rosstat.publications.operations import discover
from stratbox.domains.rosstat.publications.download.envelope import detect_bytes
from stratbox.domains.rosstat._source import allowed_file_url, file_request
from stratbox.core.execution import OperationFailure
from stratbox.domains.registry import operation_catalog


def _index(series, body):
    source = SourcePayload(body.encode("utf-8"), "text/html", series + ".index", charset="utf-8")
    result = discover(DiscoverRosstatRequest(series, source))
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


@pytest.mark.parametrize("series,href,issue,asset_id", [
    ("rosstat.socioeconomic_russia", "osn-08-2026.pdf", "2026-08", "report"),
    ("rosstat.socioeconomic_regions", "info-stat-06-2026.zip", "2026-06", "regional_archive"),
    ("rosstat.short_term_indicators", "2026-08.xlsx", "2026-08", "main_workbook"),
    ("rosstat.population_municipalities", "BUL_MO_2024.xlsx", "2024", "population_workbook"),
])
def test_four_family_rules_are_distinct_and_never_claim_complete(series, href, issue, asset_id):
    index = _index(series, f'<a href="/storage/mediabank/{href}">Publication</a>')
    item, = index.qualified_assets
    assert item.key.issue.issue_id == issue
    assert item.key.asset_id == asset_id
    assert item.key.source_id.startswith("rosstat.")
    assert index.coverage == "unknown"
    assert not index.live_profile_verified
    with pytest.raises(ValueError, match="rosstat.inventory_not_verified"):
        qualified_inventory_from_index(index, owner_evidence_ref="owner-revision")


def test_catalog_four_exact_urls():
    assert len(list_rosstat_sources()) == 4
    assert get_rosstat_source("rosstat.short_term_indicators").landing_url.endswith("/50802")


def test_unrecognized_link_does_not_create_false_latest_or_absence():
    series = "rosstat.short_term_indicators"
    a = _index(series,
        '<a href="/storage/mediabank/2026-07.xlsx">July</a>'
        '<a href="/storage/mediabank/2026-08.xlsx">August</a>')
    b = _index(series,
        '<a href="/storage/mediabank/2026-07.xlsx">July</a>'
        '<a href="/download?id=august">Download August</a>')
    assert b.coverage == "unknown"
    assert b.unclassified_count >= 1
    delta = compare_publication_indices(a, b)
    assert delta.state == "indeterminate"
    assert delta.missing_asset_ids == ()
    with pytest.raises(ValueError, match="rosstat.selection_index_unverified"):
        select_assets(b, policy="latest_qualified")
    assert len(select_assets(b, issue_ids=("2026-07",))) == 1


def test_explicit_multi_asset_keys_and_duplicate_ambiguity():
    series = "rosstat.short_term_indicators"
    html = (
        '<a href="/storage/mediabank/2026-08.xlsx">Основной выпуск 2026-08</a>'
        '<a href="/storage/mediabank/table_2026-08.xlsx">Таблицы 2026-08</a>'
        '<a href="/storage/mediabank/a_2026-08.xlsx">Приложение 1 2026-08</a>'
        '<a href="/storage/mediabank/b_2026-08.xlsx">Приложение 2 2026-08</a>'
    )
    index = _index(series, html)
    assert len(index.qualified_assets) == 4
    ids = {asset.key.asset_id for asset in index.qualified_assets}
    assert ids == {"main_workbook", "tables", "annex_1", "annex_2"}
    assert len({asset.source_id for asset in index.qualified_assets}) == 4
    collision = _index(series,
        '<a href="/storage/mediabank/2026-08.xlsx">A</a>'
        '<a href="/storage/mediabank/other_2026-08.xlsx">B</a>')
    assert not collision.qualified_assets and len(collision.ambiguous_assets) == 2


def test_conflicting_publisher_date_candidates_are_unresolved():
    series = "rosstat.short_term_indicators"
    index = _index(series,
        '<a href="/storage/mediabank/2026-08.xlsx">Выпуск 2025-08</a>')
    item, = index.ambiguous_assets
    assert item.key is None
    assert "issue_evidence_conflict" in item.diagnostic_codes
    annual = _index("rosstat.population_municipalities",
        '<a href="/storage/mediabank/BUL_MO_2024_2025.xlsx">2024</a>')
    assert annual.qualified_assets == ()


def test_reordered_links_and_relocated_urls_do_not_prove_change():
    series = "rosstat.short_term_indicators"
    first = _index(series,
        '<a href="/storage/mediabank/2026-08.xlsx">August</a>'
        '<a href="/storage/mediabank/2026-07.xlsx">July</a>')
    reordered = _index(series,
        '<a href="/storage/mediabank/2026-07.xlsx">July</a>'
        '<a href="/storage/mediabank/2026-08.xlsx">August</a>')
    assert compare_publication_indices(first, reordered).state == "indeterminate"
    assert compare_publication_indices(first, reordered).observed_candidate_ids == ()
    relocated = _index(series, '<a href="/storage/mediabank/another_2026-08.xlsx">August</a>')
    assert compare_publication_indices(first, relocated).missing_asset_ids == ()


def test_offline_wrong_media_and_source_mixup_rejected():
    series = "rosstat.short_term_indicators"
    html = b'<a href="/storage/mediabank/2026-08.xlsx">X</a>'
    pdf = discover(DiscoverRosstatRequest(series, SourcePayload(html, "application/pdf", series + ".index")))
    assert pdf.outcome == "failed"
    wrong = discover(DiscoverRosstatRequest(series, SourcePayload(html, "text/html", "rosstat.other.index")))
    assert wrong.outcome == "failed"
    assert wrong.diagnostics[0].code == "rosstat.index_source_mismatch"


class _PagePublisher:
    def exchange(self, request, *, cancelled=None):
        return HttpResponse(
            200, b'<a href="/storage/mediabank/2026-08.xlsx">August</a>',
            {"content-type": "text/html; charset=utf-8"},
            datetime(2026, 11, 19, tzinfo=timezone.utc), "https://rosstat.gov.ru",
        )


def test_http_discovery_retains_acquisition_receipt():
    result = discover(DiscoverRosstatRequest("rosstat.short_term_indicators"), transport=_PagePublisher())
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.acquisition is not None
    assert result.value.source_kind == "publisher_http"
    assert result.value.acquisition.identity == result.value.index_identity


def test_html_bounds_and_unrecognized_index_fail():
    series = "rosstat.short_term_indicators"
    bad = discover(DiscoverRosstatRequest(series, SourcePayload(
        b"<html><title>Temporarily unavailable</title></html>",
        "text/html", series + ".index",
    )))
    assert bad.outcome == "failed"
    huge = ('<a href="/storage/mediabank/2026-08.xlsx">' + "z"*9000 + "</a>")
    result = discover(DiscoverRosstatRequest(series, SourcePayload(
        huge.encode(), "text/html", series + ".index",
    )))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "rosstat.html_label_limit"


def test_untrusted_html_base_and_urls_rejected_before_download():
    series = "rosstat.short_term_indicators"
    result = discover(DiscoverRosstatRequest(series, SourcePayload(
        b'<base href="https://evil.example/"><a href="2026-08.xlsx">X</a>',
        "text/html", series + ".index",
    )))
    assert result.outcome == "failed"
    assert not allowed_file_url("http://rosstat.gov.ru/storage/mediabank/2026-08.xlsx")
    assert not allowed_file_url("https://evil.example/storage/mediabank/2026-08.xlsx")


def test_redirect_paths_within_official_roots_only():
    request = file_request("https://rosstat.gov.ru/storage/mediabank/2026-08.xlsx", 1024, 30)
    assert request.permits("https://www.rosstat.gov.ru/storage/mediabank/other.xlsx")
    assert request.permits("https://rosstat.gov.ru/upload/other.xlsx")
    assert not request.permits("https://evil.example/storage/mediabank/2026-08.xlsx")
    assert not request.permits("https://rosstat.gov.ru/admin/private.xlsx")


def test_base_root_preserves_source_anchor():
    index = _index("rosstat.short_term_indicators",
        '<base href="/"><a href="storage/mediabank/2026-08.xlsx"> Aug  2026 </a>')
    a, = index.qualified_assets
    assert a.label_literal == " Aug  2026 "
    assert a.raw_href == "storage/mediabank/2026-08.xlsx"


def test_native_envelope_stays_outer_only():
    assert detect_bytes(b"%PDF-1.7\nfoo\n%%EOF", expected="pdf") == "pdf"
    with BytesIO() as buf:
        with ZipFile(buf, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("_rels/.rels", "<Relationships/>")
            z.writestr("xl/workbook.xml", "<workbook/>")
        b = buf.getvalue()
    assert detect_bytes(b, expected="xlsx") == "xlsx"
    with pytest.raises(OperationFailure):
        detect_bytes(b"<html>error</html>", expected="xlsx")


def test_registered_discovery_and_acquisition_handlers():
    catalog = operation_catalog()
    for name in ("rosstat.publications.discover",
                 "rosstat.publications.acquire",
                 "rosstat.publications.acquire_to_store"):
        assert catalog.get(name, 1).operation_id == name


def test_owner_review_of_exact_http_page_can_create_scoped_inventory():
    from stratbox.domains.rosstat.publications.discovery.approval import (
        ReviewedIndexScope, approve_index,
    )
    series = "rosstat.short_term_indicators"
    source = discover(DiscoverRosstatRequest(series), transport=_PagePublisher()).value
    ref, = source.qualified_assets
    evidence = ReviewedIndexScope(
        series, source.assessment.profile_id, source.profile_version,
        source.index_identity, "recent_listing", ("official_current_issues",),
        (ref.key.source_id,), "human-reviewed-publisher-page-2026-11",
        issue_lower_bound="2026-01",
    )
    approved = approve_index(source, evidence)
    assert approved.coverage == "complete"
    inventory = qualified_inventory_from_index(
        approved, owner_evidence_ref="verified-owner-state",
    )
    assert inventory.assets == (ref.key.identity,)
    assert inventory.covers_issue("2026-09")
    presence = qualified_presence_from_index(
        approved, ref.key.source_id, owner_evidence_ref="verified-current-index",
    )
    assert presence.asset == ref.key.identity
    with pytest.raises(ValueError):
        qualified_presence_from_index(source, ref.key.source_id, owner_evidence_ref="unreviewed")
    with pytest.raises(ValueError):
        qualified_inventory_from_index(source, owner_evidence_ref="unapproved")


def test_manual_review_must_bind_current_byte_version_and_all_assets():
    from stratbox.domains.rosstat.publications.discovery.approval import (
        ReviewedIndexScope, approve_index,
    )
    series = "rosstat.short_term_indicators"
    source = discover(DiscoverRosstatRequest(series), transport=_PagePublisher()).value
    key, = (item.key.source_id for item in source.qualified_assets)
    wrong = ReviewedIndexScope(
        series, source.assessment.profile_id, source.profile_version,
        ByteIdentity.of(b"other-page"), "recent_listing", ("current",),
        (key,), "reviewer", issue_lower_bound="2026-01",
    )
    with pytest.raises(ValueError, match="rosstat.review_evidence_mismatch"):
        approve_index(source, wrong)
    wrong_members = ReviewedIndexScope(
        series, source.assessment.profile_id, source.profile_version,
        source.index_identity, "recent_listing", ("current",),
        (), "reviewer", issue_lower_bound="2026-01",
    )
    with pytest.raises(ValueError, match="rosstat.review_evidence_mismatch"):
        approve_index(source, wrong_members)
