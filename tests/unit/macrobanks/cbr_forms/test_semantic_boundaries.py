"""Physical source facts, semantic observations and numerical purposes stay separate."""
from dataclasses import replace
from decimal import Decimal

import pytest

from stratbox.shared.data.values import Material
from .support import DAY, calculate, command, dataset, reopen, series, view


def test_default_model_selects_all_admitted_banks_and_preserves_an_explicit_subset():
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.23"),("2000","14","9")))
    result=calculate("802",source)
    assert {row["subject"] for row in result.rows}=={"1000","2000"}
    selected=view(result,subjects=("1000",))
    from io import BytesIO
    from openpyxl import load_workbook
    from .support import render
    workbook=load_workbook(BytesIO(render(selected).data),data_only=True)
    values=list(workbook["Данные"].values);ordinal=list(values[0]).index("REGN")
    assert {str(row[ordinal]) for row in values[1:]}=={"1000"}
    workbook.close()


def test_alignment_keeps_banks_groups_exact_number_and_physical_record_evidence():
    group=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","000001.2300"),))
    bank=dataset("101",("REGN","NUM_SC","IITG","PLAN","A_P"),(("1000","47422","5","A","2"),))
    g=command("802","observations.align",{"dataset":group})["dataset"]
    b=command("101","observations.align",{"dataset":bank})["dataset"]
    assert g.rows[0]["subject_namespace"]=="cbr.banking_group.registration"
    assert b.rows[0]["subject_namespace"]=="cbr.bank.registration"
    assert g.rows[0]["value"]==Decimal("1.2300") and g.rows[0]["value"].as_tuple().exponent==-4
    assert g.rows[0]["unit"]=="RUB" and g.rows[0]["scale"]==1000
    assert "record=1&field=VSEGO" in g.rows[0]["evidence_ref"]
    assert g.rows[0]["raw_token"]=="000001.2300"
    assert b.rows[0]["perimeter"]=="credit_institution"
    assert g.source_id==series("802").id and b.source_id==series("101").id
    assert g.issue_id==b.issue_id==DAY and group.lineage[0] in g.lineage
    assert g.source_uses==group.source_uses and b.source_uses==bank.source_uses


def test_flow_interpretation_requires_explicit_interval():
    with pytest.raises(ValueError,match="flow_period_required"):
        dataset("102",("REGN","CODE","SIM_ITOGO"),(("1000","11101","100"),))
    source=dataset("102",("REGN","CODE","SIM_ITOGO"),(("1000","11101","100"),),period=("2026-01-01","2026-03-31"))
    assert source.rows[0]["period"]==("2026-01-01","2026-03-31")
    assert source.rows[0]["measure_kind"]=="flow"


def test_interpretation_distinguishes_blank_zero_and_absent_optional_measure():
    source=dataset("802",("REGN_GKO","STR","VSEGO","KORR_P"),(("1000","14","0",""),))
    channels={row["measure"]:row for row in source.rows}
    assert channels["total"]["value"]==0 and channels["total"]["value_status"]=="reported"
    assert channels["consolidation_plus"]["value_status"]=="blank"
    assert "consolidation_minus" not in channels


def test_source_comparison_accepts_raw_material_without_a_financial_model():
    before=Material(b"source-raw-before");after=Material(b"source-raw-after")
    changed=command("803","source.assess",{"evidence":after,"baseline":before})["assessment"]
    assert changed.status=="changed" and changed.basis=="exact_material_bytes"
    initial=command("803","source.assess",{"evidence":before})["assessment"]
    assert initial.status=="first_seen" and initial.basis=="no_baseline"


def test_unknown_form_links_cannot_be_silently_admitted_to_a_known_series():
    index=Material(b'<a href="/vfs/credit/forms/999-20260401.rar">source</a>',"text/html")
    listing=command("803","publication.scan",{"index":index})["listing"]
    assert listing.entries==() and listing.assessment.status=="partial"
    assert "cbr.index_no_qualified_assets" in listing.assessment.findings
    with pytest.raises(KeyError):
        series("999")


def test_integrated_values_and_prepared_views_continue_after_their_own_encoding(tmp_path):
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.2300"),))
    integrated=command("802","observations.align",{"dataset":source})["dataset"]
    assert reopen(tmp_path,integrated)==integrated
    calculated=calculate("802",reopen(tmp_path,integrated))
    prepared=view(calculated)
    for value in (source,integrated,calculated,prepared):
        restored=reopen(tmp_path,value)
        assert restored==value and restored.lineage==value.lineage
    assert source.lineage[0] in calculated.lineage and calculated.identity in prepared.lineage
