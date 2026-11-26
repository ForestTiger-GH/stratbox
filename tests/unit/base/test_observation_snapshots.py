"""Exact observation rows survive independent dataset adapters and scalar admission."""
from dataclasses import replace
from decimal import Decimal
import pytest

from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.shared.data.values import Assessment,SourceDataset,canonical_tree,restore_tree
from stratbox.shared.identity import ByteIdentity


def batch():
    rows=tuple({"subject_namespace":"source.legal_entity","subject":"00001","metric":"source.metric",
        "unit":"RUB","scale":Decimal("1000.00"),"measure_kind":"flow","period_kind":"interval",
        "period":("2026-01-01","2026-03-31"),"perimeter":"legal_entity",
        "dimensions":(("geography","001"),("scope","full")),"value":value,"value_status":status,
        "evidence_ref":"sheet:1/row:"+str(i),"raw_token":raw}
        for i,(value,status,raw) in enumerate(((Decimal("1.2300"),"reported","0001.2300"),(0,"reported","0"),
            (None,"blank",""),(None,"withheld",None),("publisher text","reported","publisher text"))))
    return SourceDataset("logical.observations",rows,{"source_definition":"reported_flow"},"2026-03-31",(ByteIdentity.of(b"source"),),Assessment("unknown"))


def test_typed_observations_cold_replay_preserves_every_coordinate_and_scalar(tmp_path):
    original=batch();store=FileDatasetStore(tmp_path)
    reference=store.ingest(original,destination="retained",identity=original.identity)
    restored=FileDatasetStore(tmp_path).query(reference,{})
    assert restored==original and not hasattr(restored,"schema_version")
    assert restored.rows[0]["value"].as_tuple()==Decimal("1.2300").as_tuple()
    assert restored.rows[0]["scale"].as_tuple()==Decimal("1000.00").as_tuple()
    assert type(restored.rows[1]["value"]) is int
    assert restored.rows[2]["raw_token"]=="" and restored.rows[3]["raw_token"] is None
    assert restored.rows[4]["value"]=="publisher text"


def test_retention_preserves_order_and_never_aggregates_duplicate_records():
    original=replace(batch(),rows=(batch().rows[0],)*2)
    assert restore_tree(canonical_tree(original))==original
    assert len(original.rows)==2


def test_retention_rejects_missing_required_components_and_hidden_scalar_channels():
    encoded=canonical_tree(batch())
    del encoded["fields"]["rows"]
    with pytest.raises((TypeError,ValueError)):restore_tree(encoded)
    encoded=canonical_tree(batch())
    first=encoded["fields"]["rows"]["tuple"][0]["mapping"]
    scalar=next(value for key,value in first if key=="value")
    scalar["hidden_integer"]=1
    with pytest.raises(ValueError,match="envelope_not_admitted"):restore_tree(encoded)


def test_empty_observations_keep_metadata_lineage_and_explicit_unknown_coverage():
    original=replace(batch(),rows=())
    restored=restore_tree(canonical_tree(original))
    assert restored==original and restored.assessment.status=="unknown"
    assert not restored.rows and restored.lineage
