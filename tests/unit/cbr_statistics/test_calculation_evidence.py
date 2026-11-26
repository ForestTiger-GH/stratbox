"""Derived measures retain annotations and deterministic exact arithmetic."""
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from stratbox.core.commands import standard
from stratbox.core.execution.service import ExecutionFailure
from .test_workbook_replay import context, selected


def test_period_annotations_are_evidence_and_both_inputs_remain_attached():
    dataset,(left,right)=selected()
    left={**left,"annotations":{"source_period_label":"01.01.2026**","source_value_qualification":"annotated"},"raw_token":"123**"}
    dataset=replace(dataset,rows=(left,right))
    expected=standard.calculate_change({"observations":dataset},{"mode":"percent"},context())["dataset"]
    with localcontext() as ambient:
        ambient.prec=3
        result=standard.calculate_change({"observations":dataset},{"mode":"percent"},context())["dataset"]
    row,=result.rows
    assert row["value"]==expected.rows[0]["value"] and Decimal(270)<row["value"]<Decimal(271)
    assert row["baseline_annotations"]==left["annotations"]
    assert row["baseline_evidence_ref"]==left["evidence_ref"] and right["evidence_ref"] in row["evidence_ref"]
    assert dataset.identity in result.lineage


def test_share_retains_denominator_annotations_and_explicit_relationship():
    dataset,(left,_)=selected()
    numerator={**left,"metric":"selected.part","value":Decimal(1)}
    denominator={**left,"metric":"selected.whole","value":Decimal(3),
        "annotations":{"source_value_qualification":"annotated"}}
    top=replace(dataset,rows=(numerator,));bottom=replace(dataset,rows=(denominator,))
    inputs={"numerator":top,"denominator":bottom};settings={"multiplier":100}
    expected=standard.calculate_ratio(inputs,settings,context())["dataset"]
    with localcontext() as ambient:
        ambient.prec=4
        result=standard.calculate_ratio(inputs,settings,context())["dataset"]
    row,=result.rows
    assert row["value"]==expected.rows[0]["value"] and Decimal(33)<row["value"]<Decimal(34)
    assert row["denominator_annotations"]==denominator["annotations"]
    assert row["denominator_metric"]=="selected.whole"
    assert bottom.identity in result.lineage


def test_absolute_difference_preserves_digits_beyond_ambient_decimal_precision():
    dataset,(left,right)=selected()
    left={**left,"value":Decimal("1234567890123456789012345678901234567890.0001")}
    right={**right,"value":Decimal("1234567890123456789012345678901234567890.0003")}
    dataset=replace(dataset,rows=(left,right))
    with localcontext() as ambient:
        ambient.prec=3
        result=standard.calculate_change({"observations":dataset},{"mode":"absolute"},context())["dataset"]
    assert result.rows[0]["value"]==Decimal("0.0002")
    with pytest.raises((ExecutionFailure,ValueError),match="selection_invalid|period_order|change_order"):
        standard.calculate_change({"observations":dataset},{"mode":"absolute"},
            context(before=right["period"],after=left["period"]))
