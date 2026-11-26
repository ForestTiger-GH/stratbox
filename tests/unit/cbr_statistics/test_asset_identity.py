"""Logical assets remain distinct when their original bytes are shared."""
from dataclasses import replace

import pytest

from stratbox.shared.data.values import fingerprint
from stratbox.domains.cbr.methods.actions.workbook_comparison import compare_workbooks
from .test_workbook_replay import action, flake, interpret, prepare, replay, workbook


@pytest.fixture
def originals():
    data=workbook(exact="123")
    return tuple(flake(data,asset=asset) for asset in ("main","appendix"))


def test_same_bytes_under_two_assets_have_distinct_source_evidence_and_exact_input_vectors(originals):
    first,second=originals
    assert first.material.identity==second.material.identity
    assert first.tables==second.tables
    assert [value.metadata["asset_id"] for value in originals]==["main","appendix"]
    assert fingerprint(first)!=fingerprint(second)
    datasets=tuple(interpret(replay(value)) for value in originals)
    for source,dataset in zip(originals,datasets):
        assert replay(dataset)==dataset
        assert dataset.source_uses[0].coordinate.asset_id==source.metadata["asset_id"]
        assert dataset.source_uses[0].coordinate.material_identity==source.material.identity
        assert replay(prepare(dataset)).lineage[-1]==dataset.identity
    assert {dict(row["dimensions"])["source_asset_id"] for dataset in datasets for row in dataset.rows}=={"main","appendix"}
    assert len({row["subject"] for dataset in datasets for row in dataset.rows if dict(row["dimensions"])["source_hierarchy"]=="M2"})==2
    assert len({row["metric"] for dataset in datasets for row in dataset.rows if dict(row["dimensions"])["source_hierarchy"]=="M2"})==2
    with pytest.raises(ValueError,match="comparison_asset_mismatch"):
        compare_workbooks(*originals)


def test_asset_scoped_original_lineage_is_retained(originals):
    value=originals[1];data=interpret(value)
    assert data.lineage[0]==value.material.identity
    assert replay(data).source_uses==data.source_uses


@pytest.mark.parametrize("asset_id",["","invalid/asset","invalid asset"])
def test_retained_source_evidence_validates_logical_asset_tokens(originals,asset_id):
    source=replace(originals[0],metadata={"asset_id":asset_id})
    with pytest.raises(ValueError,match="source.identity_token_invalid"):
        action("value.encode",{"value":source})
