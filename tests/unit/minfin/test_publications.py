"""Observed fiscal link semantics through direct standard-command methods."""
from types import SimpleNamespace
import pytest

from stratbox.domains.minfin.domain import DOMAIN
from stratbox.domains.minfin.common.access import allowed_url
from stratbox.domains.minfin.methods import publications
from stratbox.shared.data.values import Material
from .page_fixtures import official_pages


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def rules(family):
    return next(record.commands["command.publication.scan"].settings for record in DOMAIN.series.values()
                if record.commands["command.publication.scan"].settings.family_id == family)


@pytest.mark.parametrize("family,expected", [
    ("minfin.fedbud", {"annex3_monthly", "annex3_quarterly", "annex3_annual"}),
    ("minfin.conbud", {"annex8_monthly", "annex8_quarterly", "annex8_annual"}),
    ("minfin.subbud", {"annex6_monthly", "annex6_quarterly", "annex6_annual"}),
    ("minfin.nwf", {"movement_workbook", "volume_report", "preferred_shares", "veb_deposits"}),
])
def test_observed_filenames_and_title_labels_keep_all_known_series(family, expected):
    links = official_pages()[family]
    html = "".join(f'<a title="{title}" href="/common/upload/library/{path}">Document</a>' for title, path in links)
    listing = publications.scan({"index": Material(html.encode(), "text/html", family + ".index")}, rules(family), context())["listing"]
    assert {item.asset_id for item in listing.entries} == expected
    assert all(item.source_id in DOMAIN.series for item in listing.entries)
    assert all(item.metadata["label"] != "Document" for item in listing.entries)
    assert "source.observed_index_page_only" in listing.assessment.qualifications


def test_empty_observed_scope_never_proves_removed_publication():
    html = b'<a href="https://other.example/data.xlsx">Other</a>'
    listing = publications.scan({"index": Material(html, "text/html")}, rules("minfin.fedbud"), context())["listing"]
    assert listing.entries == () and not listing.assessment.complete
    result = publications.assess({"evidence": listing}, rules("minfin.fedbud"), context())["assessment"]
    assert result.status == "unknown" and not result.evidence["selected_coverage"].complete


def test_saved_index_errors_never_trigger_network_fallback():
    ctx = context()
    ctx.provider = lambda _: pytest.fail("Pure index scan must not use any provider")
    with pytest.raises(ValueError, match="no_links"):
        publications.scan({"index": Material(b"bad saved index", "text/html")}, rules("minfin.fedbud"), ctx)
    with pytest.raises(ValueError, match="untrusted"):
        publications.scan({"index": Material(b'<base href="https://other.example"><a href="x.xlsx">x</a>')}, rules("minfin.fedbud"), ctx)


@pytest.mark.parametrize("url", ["https://other.example/common/upload/library/data.xlsx",
    "https://minfin.gov.ru/ru/account/admin.xlsx", "https://minfin.gov.ru/common/upload/library/../admin.xlsx",
    "http://minfin.gov.ru/common/upload/library/data.xlsx"])
def test_unrelated_or_conflicting_asset_locations_are_not_admitted(url):
    assert not allowed_url(url, asset=True)


def test_index_source_context_cannot_be_relabelled():
    with pytest.raises(ValueError, match="source_mismatch"):
        publications.scan({"index": Material(b'<a href="x">x</a>', source_id="minfin.subbud.index")}, rules("minfin.fedbud"), context())
