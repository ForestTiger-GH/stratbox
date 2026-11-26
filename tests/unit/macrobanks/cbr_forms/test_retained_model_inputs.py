"""Retained observations must satisfy numerical semantics again at calculation admission."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from stratbox.domains.cbr.common.contracts import MappingRules
from stratbox.domains.cbr.methods.actions.observations import align
from .support import DAY, calculate, change_row, context, dataset, render, reopen, series, view


def aligned_group():
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.2300"),))
    rules=MappingRules(series("802").id,subjects=(("cbr.banking_group.registration","1000","group-a"),))
    return align({"dataset":source},rules,context())["dataset"]


def test_retained_group_observations_calculate_and_render_without_source_projection(tmp_path):
    original=aligned_group();restored=reopen(tmp_path,original)
    calculated=calculate("802",restored)
    capital=next(row for row in calculated.rows if row["source_code"]=="14")
    assert capital["value"]==Decimal("1.2300")
    assert capital["source_subject"]=="1000" and capital["subject"]=="group-a"
    assert capital["subject_namespace"]=="canonical"
    assert capital["source_subject_namespace"]=="cbr.banking_group.registration"
    assert capital["period_kind"]=="as_of" and capital["period"]==DAY
    assert restored.identity in calculated.lineage
    opened=load_workbook(BytesIO(render(view(calculated)).data),data_only=True)
    assert "Данные" in opened.sheetnames
    opened.close()


def test_retained_income_observations_keep_explicit_interval_through_model_calculation(tmp_path):
    source=dataset("102",("REGN","CODE","SIM_ITOGO"),(("1000","27000","123.4500"),),
        period=("2026-01-01","2026-03-31"))
    calculated=calculate("102",reopen(tmp_path,source))
    row=next(row for row in calculated.rows if row["metric"]=="net_fee_income")
    assert row["value"]==Decimal("123.4500")
    assert row["period_kind"]=="interval" and row["period"]==("2026-01-01","2026-03-31")


@pytest.mark.parametrize("changes", (
    {"unit":"USD"},{"scale":Decimal(1)},{"period_kind":"capture"},
    {"reporting_date":None},{"perimeter":"credit_institution"},
    {"source_dataset":"unreviewed"},{"metric":"invented.metric"},
    {"subject_namespace":"cbr.bank.registration"},{"measure_kind":"flow"},
    {"period":"2026-03-31"},
))
def test_calculation_rejects_semantically_incompatible_retained_observations(changes):
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.2300"),))
    with pytest.raises(ValueError):
        calculate("802",change_row(source,**changes))


def test_calculation_rechecks_mandatory_channels_and_duplicate_semantic_variables():
    source=dataset("802",("REGN_GKO","STR","VSEGO","KORR_P"),(("1000","14","10","1"),))
    incomplete=replace(source,rows=tuple(row for row in source.rows if row["measure"]!="total"))
    with pytest.raises(ValueError,match="channels_incomplete"):
        calculate("802",incomplete)
    duplicate=replace(source,rows=(*source.rows,source.rows[0]))
    with pytest.raises(ValueError,match="duplicate_variable"):
        calculate("802",duplicate)


def test_account_plan_is_required_and_keeps_other_chapters_separate(tmp_path):
    source=dataset("101",("REGN","NUM_SC","IITG","PLAN","A_P"),
        (("1481","45.2","123.4","A","1"),("1481","45.2","999.9","B","1")))
    calculated=calculate("101",reopen(tmp_path,source))
    value=next(row["value"] for row in calculated.rows if row["metric"]=="loans_individuals")
    assert value==Decimal("123.4")
    missing=replace(source,rows=tuple({**row,"dimensions":tuple(pair for pair in row["dimensions"] if pair[0]!="PLAN")}
        for row in source.rows))
    with pytest.raises(ValueError,match="account.plan|account_plan"):
        calculate("101",missing)


def test_each_bank_keeps_its_own_subject_evidence_and_period_metadata():
    source=dataset("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1"),("2000","14","2")))
    result=calculate("802",source)
    rows=[row for row in result.rows if row["source_code"]=="14"]
    assert {(row["subject"],row["value"],row["subject_namespace"],row["period"])
        for row in rows}=={("1000",Decimal(1),"cbr.banking_group.registration",DAY),
                         ("2000",Decimal(2),"cbr.banking_group.registration",DAY)}
    assert all(row["reporting_date"]==DAY for row in rows)
