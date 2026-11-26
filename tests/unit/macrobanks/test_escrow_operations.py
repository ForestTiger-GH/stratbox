"""Offline standard escrow routes retain exact source bytes and prepared content."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import runpy
import pytest
from openpyxl import Workbook, load_workbook

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.domains.cbr.common.escrow import required_indicators
from stratbox.domains.cbr.methods.actions.publications import scan
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material
from stratbox.shared.evidence import SourcePayload

SERIES="cbr.project_finance.escrow"
_HELPERS=runpy.run_path(str(Path(__file__).resolve().parents[1]/"cbr_escrow/test_replay.py"))

def workbook_bytes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Регионы"
    titles = [
        item.canonical_name for item in required_indicators()
    ]
    sheet.append(["№", "Субъект Российской Федерации (федеральный округ)", *titles])
    sheet.append(["Центральный ФО", None, *[1] * len(titles)])
    sheet.append([1, "Белгородская область", 0, None, *[2] * (len(titles) - 2)])
    sheet.append(["Итого", None, *[3] * len(titles)])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_escrow_history_is_offline_and_renders_views_to_exact_bytes():
    content = workbook_bytes()
    request = SimpleNamespace(payload=SourcePayload(content), source_name="escrow_01062026.xlsx")
    physical, table, dataset = _HELPERS["source"](request)
    assert dataset.source_uses[0].coordinate.material_identity == physical.material.identity
    assert {row["period"] for row in dataset.rows} == {"2026-06-01"}
    region = [row for row in dataset.rows if row["subject"] == "Белгородская область"]
    assert any(row["value"] == 0 for row in region)
    assert next(row for row in region if row["metric"] == "active_credit_contracts_amount_mln_rub")["value_status"] == "blank"
    view = _HELPERS["prepared"](dataset)
    output = _HELPERS["rendered"](view)
    assert output == _HELPERS["rendered"](view)
    verified = load_workbook(BytesIO(output.data), read_only=True)
    assert "КДКД" in verified.sheetnames
    verified.close()


def test_escrow_discovery_recognizes_actual_cbr_collection_paths():
    html=b'''
<a href="/Collection/Collection/File/62244/01072026.xlsx">01.07.2026</a>
<a href="/Collection/Collection/File/62109/01062026.xlsx">01.06.2026</a>
<a href="/vfs/statistics/escrow_01052026.xlsx">01.05.2026</a>
<a href="https://other.example/Collection/Collection/File/123/01042026.xlsx">bad host</a>
<a href="/unrelated/01032026.xlsx">bad path</a>'''
    settings=DOMAIN.series[SERIES].commands["command.publication.scan"].settings
    result=scan({"index":Material(html,"text/html")},settings,SimpleNamespace(parameters={},checkpoint=lambda:None))["listing"]
    assert [item.locator.rsplit("/",1)[1] for item in result.entries] == ["01072026.xlsx","01062026.xlsx","escrow_01052026.xlsx"]
    assert [item.issue_id for item in result.entries] == ["2026-07-01","2026-06-01","2026-05-01"]


def test_escrow_acquire_accepts_official_collection_workbook():
    content=workbook_bytes()
    html=Material(b'<a href="/Collection/Collection/File/62244/01072026.xlsx">file</a>',"text/html")
    settings=DOMAIN.series[SERIES].commands["command.publication.scan"].settings
    asset=scan({"index":html},settings,SimpleNamespace(parameters={},checkpoint=lambda:None))["listing"].entries[0]
    class Publisher:
        def fetch(self,request):
            assert request.method=="GET" and request.url==asset.locator
            assert request.max_bytes>=len(content)
            return Material(content,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",SERIES)
    with StrategyBox(providers={"http":Publisher()}) as box:
        acquired=box.invoke("operation.material.acquire",inputs={"locator":asset},target=SeriesTarget(SERIES))
        assert acquired.outcome=="succeeded",acquired.diagnostics
        material=acquired.output("material")
        assert material.material.data==content
        assert material.claim.source_id==SERIES and material.claim.issue_id=="2026-07-01"


def test_prepared_escrow_data_freezes_source_geography_and_preserves_identity():
    request=SimpleNamespace(payload=SourcePayload(workbook_bytes()),source_name="escrow_01062026.xlsx")
    dataset=_HELPERS["source"](request)[2]
    identity=dataset.identity
    with pytest.raises(TypeError):
        dataset.rows[0]["subject"]="forged geography"
    assert dataset.identity==identity
