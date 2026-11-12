from io import BytesIO

from openpyxl import Workbook, load_workbook

from stratbox.data import SourcePayload
from stratbox.macrobanks import escrow
from stratbox.macrobanks.escrow.columns import ESCROW_INDICATOR_SPECS


def workbook_bytes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Регионы"
    titles = [
        item.canonical_name for item in ESCROW_INDICATOR_SPECS if item.is_required
    ]
    sheet.append(["№", "Субъект Российской Федерации (федеральный округ)", *titles])
    sheet.append(["Центральный ФО", None, *[1] * len(titles)])
    sheet.append([1, "Белгородская область", 0, None, *[2] * (len(titles) - 2)])
    sheet.append(["Итого", None, *[3] * len(titles)])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_escrow_history_is_offline_and_renders_views_to_exact_bytes():
    payload = SourcePayload(workbook_bytes())
    request = escrow.ParseEscrowRequest(payload, "escrow_01062026.xlsx")
    history = escrow.build_history(escrow.EscrowHistoryBuildRequest((request,)))
    assert history.outcome == "succeeded", history.diagnostics
    assert history.used_inputs[0].identity == payload.identity
    assert history.value.dates == ("2026-06-01",)
    region = history.value.df_long[
        history.value.df_long["Регион"].eq("Белгородская область")
    ]
    assert 0 in region["Значение"].values
    assert (
        "active_credit_contracts_amount_mln_rub" not in region["indicator_code"].values
    )
    views = escrow.build_views(escrow.BuildEscrowViewsRequest(history.value))
    assert views.outcome == "succeeded", views.diagnostics
    workbook = escrow.render_workbook(views.value)
    assert workbook.outcome == "succeeded", workbook.diagnostics
    assert workbook.value == escrow.render_workbook(views.value).value
    verified = load_workbook(BytesIO(workbook.value.data), read_only=True)
    assert "КДКД" in verified.sheetnames


def test_escrow_discovery_recognizes_actual_cbr_collection_paths():
    """CBR's official month links live under /Collection/Collection/File/."""
    html = b"""
      <a href="/Collection/Collection/File/62244/01072026.xlsx">01.07.2026</a>
      <a href="/Collection/Collection/File/62109/01062026.xlsx">01.06.2026</a>
      <a href="/vfs/statistics/escrow_01052026.xlsx">01.05.2026</a>
      <a href="https://other.example/Collection/Collection/File/123/01042026.xlsx">bad host</a>
      <a href="/unrelated/01032026.xlsx">bad path</a>
    """
    found = escrow.discover(escrow.DiscoverEscrowRequest(
        SourcePayload(html, "text/html", "cbr.escrow.index")
    ))
    assert found.outcome == "succeeded", found.diagnostics
    assert [link.source_name for link in found.value] == [
        "01072026.xlsx", "01062026.xlsx", "escrow_01052026.xlsx"
    ]
    assert [link.file_date_hint for link in found.value] == [
        "2026-07-01", "2026-06-01", "2026-05-01"
    ]


def test_escrow_acquire_accepts_official_collection_workbook():
    """Use an offline transport to verify actual URL admission and source bytes."""
    from datetime import datetime, timezone
    from stratbox.base.net import HttpResponse

    source = escrow.discover(escrow.DiscoverEscrowRequest(
        SourcePayload(
            b'<a href="/Collection/Collection/File/62244/01072026.xlsx">file</a>',
            "text/html",
        )
    ))
    assert source.outcome == "succeeded", source.diagnostics
    link = source.value[0]
    content = workbook_bytes()

    class StubTransport:
        def exchange(self, request, *, cancelled=None):
            assert request.method == "GET"
            assert request.url == link.url
            assert request.permits(request.url)
            assert request.max_response_bytes >= len(content)
            return HttpResponse(
                200, content,
                {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                datetime.now(timezone.utc),
                "https://www.cbr.ru",
            )

    result = escrow.acquire(link, transport=StubTransport())
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.payload.data == content
    assert result.value.payload.source_id == link.source_id
