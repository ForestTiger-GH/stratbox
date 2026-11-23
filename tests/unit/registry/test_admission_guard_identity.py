"""Strict admission ceilings preserve successful meaning and never truncate it."""
from io import BytesIO

import pytest

from stratbox.shared.evidence import SourcePayload


def _key(result):
    assert result.outcome in {"succeeded", "partial"}, result.diagnostics
    assert result.computation is not None
    return result.computation.computation_id


def test_cbr_link_ceiling_rejects_the_whole_index_without_changing_admitted_identity():
    from stratbox.domains.cbr.publications.contracts import DiscoverRequest
    from stratbox.domains.cbr.operations.publications.handlers import discover
    html = SourcePayload(b'<a href="/statistics/x.xlsx">One</a><a href="/statistics/y.xlsx">Two</a>',
                         "text/html", "cbr.service_network.bank_offices")
    first = discover(DiscoverRequest("cbr.service_network.bank_offices", html, max_links=2))
    second = discover(DiscoverRequest("cbr.service_network.bank_offices", html, max_links=3))
    assert first.value == second.value
    assert _key(first) == _key(second)
    refused = discover(DiscoverRequest("cbr.service_network.bank_offices", html, max_links=1))
    assert refused.outcome == "failed" and refused.value is None
    assert refused.diagnostics[0].code == "cbr.inventory.link_limit"


def test_minfin_link_ceiling_overflow_never_publishes_a_prefix():
    from stratbox.domains.minfin import DiscoverRequest, discover
    html = SourcePayload(b'<html><a href="/common/upload/library/2026/11/main/one.xlsx">One</a>'
                         b'<a href="/common/upload/library/2026/11/main/two.xlsx">Two</a></html>',
                         "text/html", "minfin.fedbud.index", charset="utf-8")
    first = discover(DiscoverRequest("minfin.fedbud", html, max_links=2))
    second = discover(DiscoverRequest("minfin.fedbud", html, max_links=3))
    assert len(first.value.assets) == len(second.value.assets) == 2
    assert _key(first) == _key(second)
    refused = discover(DiscoverRequest("minfin.fedbud", html, max_links=1))
    assert refused.outcome == "failed" and refused.value is None
    assert refused.diagnostics[0].code == "minfin.index_untrusted_or_oversized"


def test_rosstat_asset_ceiling_refuses_oversize_selection_instead_of_selecting_a_prefix():
    from stratbox.domains.rosstat.publications.contracts import DiscoverRosstatRequest
    from stratbox.domains.rosstat.operations.publications import discover
    from stratbox.domains.rosstat.operations.contracts import SelectRequest
    from stratbox.domains.rosstat.operations.handlers import select
    series = "rosstat.short_term_indicators"
    html = SourcePayload(b'<a href="/storage/mediabank/2026-07.xlsx">July</a>'
                         b'<a href="/storage/mediabank/2026-08.xlsx">August</a>',
                         "text/html", series + ".index", charset="utf-8")
    index = discover(DiscoverRosstatRequest(series, html))
    _key(index)
    first = select(SelectRequest(index.value, policy="all_qualified", max_assets=2))
    second = select(SelectRequest(index.value, policy="all_qualified", max_assets=3))
    assert len(first.value) == len(second.value) == 2
    assert _key(first) == _key(second)
    refused = select(SelectRequest(index.value, policy="all_qualified", max_assets=1))
    assert refused.outcome == "failed" and refused.value is None
    assert refused.diagnostics[0].code == "rosstat.selection_limit_exceeded"


def test_minfin_pdf_page_ceiling_does_not_change_accepted_text_or_return_partial_pages():
    pypdf = pytest.importorskip("pypdf")
    from stratbox.domains.minfin import ReadableRequest, readable_document
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    stream = BytesIO()
    writer.write(stream)
    payload = SourcePayload(stream.getvalue(), "application/pdf", "minfin.nwf.volume")
    first = readable_document(ReadableRequest("minfin.nwf", payload, max_pages=2))
    second = readable_document(ReadableRequest("minfin.nwf", payload, max_pages=3))
    assert first.value.pages == second.value.pages
    assert len(first.value.pages) == 2
    assert _key(first) == _key(second)
    refused = readable_document(ReadableRequest("minfin.nwf", payload, max_pages=1))
    assert refused.outcome == "failed" and refused.value is None
