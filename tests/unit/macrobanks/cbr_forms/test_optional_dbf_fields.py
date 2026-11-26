"""Absent optional channels, explicit blanks and exact zero remain distinct."""
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from stratbox.core.commands import archives as technical_archives
from stratbox.core.formats.archives.members import zip_bytes
from stratbox.shared.data.values import Material
from .support import DAY, calculate, character_dbf, command, context, dataset, physical, series, view


def test_historical_form802_keeps_absent_adjustment_distinct_from_empty_and_proves_archive_member():
    data=character_dbf(("REGN_GKO","STR","KORR_P","KORR_M","VSEGO"),(("1000","14","","","0"),))
    unrelated=character_dbf(("FSORT","FRAZD"),(("1","2"),))
    material=Material(zip_bytes({"PK8022512.dbf":data,"F802META.dbf":unrelated}),source_id=series("802").id)
    members=technical_archives.archive_unpack({"material":material},None,context())["members"]
    assert members[0].metadata["member"]=="PK8022512.dbf"
    assert members[0].metadata["parent"]==material.identity.sha256
    decoded=tuple(physical("802",member.data,**member.metadata) for member in members)
    extracted=command("802","table.extract",{"physical":decoded},issue_id=DAY)["tables"]
    normalized=command("802","table.interpret",{"tables":extracted},issue_id=DAY)["dataset"]
    by_measure={row["measure"]:row for row in normalized.rows}
    assert by_measure["total"]["value"]==Decimal(0)
    assert by_measure["consolidation_plus"]["value_status"]=="blank"
    assert "intragroup_adjustment" not in by_measure
    assert extracted.tables[0].material.identity==members[0].identity
    assert len(extracted.metadata["all_members"])==2


def test_current_form802_can_read_present_adjustment_from_standalone_dbf():
    source=dataset("802",("REGN_GKO","STR","VSEGO","KORR_GR"),(("1000","14","10","1"),))
    adjustment=next(row for row in source.rows if row["measure"]=="intragroup_adjustment")
    assert adjustment["value"]==1 and "field=KORR_GR" in adjustment["evidence_ref"]
    calculated=calculate("802",source)
    values={row["source_code"]:row["value"] for row in calculated.rows}
    assert values["14"]==10 and values["15.4"] is None


def test_formula_source_absence_is_not_coerced_to_zero():
    source=dataset("123",("REGN","C1","C3"),(("1000","000","0"),("1000","102","10")))
    values={row["metric"]:row["value"] for row in calculate("123",source).rows}
    assert values["capital_total"]==0 and values["base_capital"]==10
    assert values["main_capital"] is None


def test_calculated_and_prepared_values_are_immutable_and_keep_model_identity():
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","10"),))
    calculated=calculate("802",source)
    prepared=view(calculated)
    assert calculated.lineage and calculated.identity in prepared.lineage
    with pytest.raises(TypeError):
        calculated.rows[0]["value"]=90
    with pytest.raises(FrozenInstanceError):
        calculated.rows=()


def test_financial_model_and_workbook_execute_through_standard_named_ports():
    from stratbox.sdk import StrategyBox
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","10"),))
    with StrategyBox() as box:
        result=box.invoke("command.calculate.formula",target="cbr.forms.f802.model",inputs={"dataset":source})
        assert result.outcome=="succeeded",result.diagnostics
        calculated=result.output("dataset")
        assert len(calculated.rows)==86 and calculated.source_uses==source.source_uses
        prepared=box.invoke("command.view.prepare",target="cbr.forms.workbook",inputs={"dataset":calculated})
        assert prepared.outcome=="succeeded",prepared.diagnostics
        rendered=box.invoke("command.product.render",target="cbr.forms.workbook",inputs={"view":prepared.output("view")})
        assert rendered.outcome=="succeeded",rendered.diagnostics
        assert rendered.output("product").data.startswith(b"PK")
