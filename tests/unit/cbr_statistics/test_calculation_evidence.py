"""Derived measures keep annotations and deterministic arithmetic policies."""
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from stratbox.domains.cbr.analytics.statistics.changes import calculate_change, calculate_share
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from test_workbook_replay import flake, workbook


def selected():
    dataset = align_statistics((flake(workbook(exact="123")),))
    batch = dataset.batches[0]
    rows = tuple(item for item in batch.observations if dict(item.dimensions)["source_hierarchy"] == "M2")
    return replace(dataset, batches=(replace(batch, observations=rows),)), rows


def test_period_annotations_are_evidence_and_both_inputs_remain_attached():
    dataset, (left, right) = selected()
    left = replace(left, dimensions=tuple(sorted((*left.dimensions,
        ("source_period_label", "01.01.2026**"), ("source_value_qualification", "annotated")))), raw_token="123**")
    dataset = replace(dataset, batches=(replace(dataset.batches[0], observations=(left, right)),))
    expected = (Decimal(456) / 123 - 1) * 100
    with localcontext() as context:
        context.prec = 3
        result = calculate_change(dataset, left.period, right.period, method="growth_percent")
    row, = result.batches[0].observations
    assert row.value == expected
    assert dict(row.dimensions)["baseline_source_period_label"] == "01.01.2026**"
    assert dict(row.dimensions)["baseline_source_value_qualification"] == "annotated"
    assert left.evidence_ref in row.evidence_ref and right.evidence_ref in row.evidence_ref
    assert result.inputs == dataset.inputs


def test_share_retains_denominator_annotations_and_explicit_relationship():
    dataset, (left, _) = selected()
    numerator = replace(left, metric=replace(left.metric, id="selected.part"), value=Decimal(1))
    denominator = replace(left, metric=replace(left.metric, id="selected.whole"), value=Decimal(3),
        dimensions=tuple(sorted((*left.dimensions, ("source_value_qualification", "annotated")))))
    dataset = replace(dataset, batches=(replace(dataset.batches[0], observations=(numerator, denominator)),))
    expected = Decimal(1) / 3 * 100
    with localcontext() as context:
        context.prec = 4
        result = calculate_share(dataset, "selected.part", "selected.whole")
    row, = result.batches[0].observations
    assert row.value == expected
    assert dict(row.dimensions)["denominator_source_value_qualification"] == "annotated"
    assert dict(row.dimensions)["denominator_metric"] == "selected.whole"


def test_absolute_difference_preserves_digits_beyond_ambient_decimal_precision():
    dataset, (left, right) = selected()
    left = replace(left, value=Decimal("1234567890123456789012345678901234567890.0001"))
    right = replace(right, value=Decimal("1234567890123456789012345678901234567890.0003"))
    dataset = replace(dataset, batches=(replace(dataset.batches[0], observations=(left, right)),))
    with localcontext() as context:
        context.prec = 3
        result = calculate_change(dataset, left.period, right.period)
    assert result.batches[0].observations[0].value == Decimal("0.0002")
    with pytest.raises(ValueError, match="change_selection_invalid"):
        calculate_change(dataset, right.period, left.period)
