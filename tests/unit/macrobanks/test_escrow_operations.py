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
