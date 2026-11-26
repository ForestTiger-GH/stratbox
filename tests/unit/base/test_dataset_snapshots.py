"""Versionless retained datasets preserve exact content, scope and effect outcomes."""
from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
import json
import struct

import pytest

from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.core.storage.datasets import FileDatasetStore,MemoryDatasetStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Assessment,SourceDataset,canonical_tree,restore_tree,fingerprint
from stratbox.shared.identity import ByteIdentity


def dataset(value=Decimal("10.50")):
    return SourceDataset("example.series",({"key":"a","value":value},{"key":"b","value":None}),
        {"unit":"USD","grain":("key",)},"2026-11",(ByteIdentity.of(b"original"),),Assessment("partial",("One observed issue",)))


def checked(result,port):
    assert result.outcome=="succeeded",result.diagnostics
    return result.output(port)


def test_exact_scalar_roundtrip_preserves_types_nulls_float_bits_and_decimal_scale():
    values=(True,-(2**63),2**100,-0.0,Decimal("1.2300"),"Text",b"\x00\xff",date(2026,11,23),
        datetime(2026,11,23,11,22,33,123456,timezone(timedelta(hours=3))),
        datetime(2026,11,23,11,22,33,123456),timedelta(days=-4,microseconds=7),None)
    restored=restore_tree(canonical_tree(values))
    assert restored==values and all(type(a) is type(b) for a,b in zip(restored,values))
    assert struct.pack(">d",restored[3])==struct.pack(">d",-0.0)
    assert restored[4].as_tuple()==Decimal("1.2300").as_tuple()
    assert fingerprint(values)==fingerprint(restored)


def test_ieee_special_values_preserve_all_bits():
    values=(struct.unpack(">d",bytes.fromhex("7ff8000000000007"))[0],float("inf"),float("-inf"))
    restored=restore_tree(canonical_tree(values))
    assert [struct.pack(">d",x) for x in restored]==[struct.pack(">d",x) for x in values]
    assert fingerprint(values)==fingerprint(restored)


def test_explicit_scalar_tags_do_not_collapse_boolean_integer_text_and_decimal():
    values=(True,1,1.0,"1",Decimal("1"),b"1")
    assert len({fingerprint(value) for value in values})==len(values)
    assert tuple(type(restore_tree(canonical_tree(value))) for value in values)==tuple(type(value) for value in values)


@pytest.mark.parametrize("bad",({"decimal":"not-decimal"},{"type":"untrusted.module:Code","fields":{}},{"hidden_scalar":1},{"bytes":"nothex"}))
def test_unknown_types_and_malformed_scalar_envelopes_are_rejected(bad):
    with pytest.raises((TypeError,ValueError,ArithmeticError)):restore_tree(bad)


@pytest.mark.parametrize("adapter",("memory","files"))
def test_immutable_retention_keeps_multiple_observed_contents_and_queries_are_independent(tmp_path,adapter):
    store=MemoryDatasetStore(scope_id="test") if adapter=="memory" else FileDatasetStore(tmp_path)
    first,later=dataset(),dataset(Decimal("30.00"))
    a=store.ingest(first,destination="source",identity=first.identity)
    b=store.ingest(later,destination="source",identity=later.identity)
    assert a!=b
    assert store.query(a,{})==first and store.query(b,{})==later
    assert store.ingest(first,destination="source",identity=first.identity)==a
    selected=store.query(a,{"filters":{"key":"a"},"limit":1})
    assert selected.rows==(first.rows[0],) and selected.assessment.status=="partial"
    assert store.query(a,{})==first
    with pytest.raises(ValueError):store.query(replace(a,identity="f"*64),{})
    with pytest.raises((KeyError,ValueError)):store.query(replace(a,provider_id="other"),{})


def test_provider_scope_is_part_of_a_retained_reference(tmp_path):
    value=dataset()
    for left,right in ((MemoryDatasetStore(scope_id="left"),MemoryDatasetStore(scope_id="right")),
                       (FileDatasetStore(tmp_path/"left"),FileDatasetStore(tmp_path/"right"))):
        a=left.ingest(value,destination="same",identity=value.identity)
        right.ingest(value,destination="same",identity=value.identity)
        with pytest.raises((KeyError,ValueError),match="scope|provider|reference|conflict"):
            right.query(a,{})


def test_file_tampering_and_missing_snapshots_fail_before_return(tmp_path):
    store=FileDatasetStore(tmp_path);value=dataset()
    reference=store.ingest(value,destination="source",identity=value.identity)
    physical=tmp_path/reference.snapshot_id
    physical.write_bytes(b"corrupt")
    with pytest.raises((ValueError,KeyError)):store.query(reference,{})
    physical.unlink()
    with pytest.raises((ValueError,KeyError,OSError)):store.query(reference,{})


def test_dataset_sdk_storage_and_cold_replay_keep_exact_identity_and_source_lineage(tmp_path):
    store=FileDatasetStore(tmp_path);value=dataset()
    with StrategyBox(providers={"dataset_writer":store}) as box:
        result=box.invoke("command.dataset.ingest",inputs={"dataset":value,"destination":"observations"})
        reference=checked(result,"reference")
        assert all(effect.status=="confirmed" for effect in result.effects.values())
    with StrategyBox(providers={"dataset_reader":FileDatasetStore(tmp_path)}) as box:
        restored=checked(box.invoke("command.dataset.query",inputs={"reference":reference}),"observations")
        assert restored==value and restored.identity==value.identity


def test_content_identity_changes_with_meaning_coverage_lineage_or_decimal_precision():
    original=dataset()
    changed=(dataset(Decimal("10.500")),replace(original,issue_id="2026-12"),
        replace(original,assessment=Assessment("complete")),replace(original,lineage=()),
        replace(original,semantics={"unit":"RUB","grain":("key",)}))
    assert all(value.identity!=original.identity for value in changed)


def test_unknown_acknowledgement_never_exposes_confirmed_reference_or_blind_retry():
    underlying=MemoryDatasetStore(scope_id="actual")
    class Lost:
        scope_id="lost";provider_id="lost"
        def __init__(self):self.calls=0
        def ingest(self,*args,**kwargs):
            self.calls+=1;underlying.ingest(*args,**kwargs)
            raise ConnectionError("Acknowledgement lost")
    writer=Lost()
    with StrategyBox(providers={"dataset_writer":writer}) as box:
        for _ in range(2):
            result=box.invoke("command.dataset.ingest",inputs={"dataset":dataset(),"destination":"source"})
            assert result.outcome=="unknown"
            with pytest.raises((ValueError,KeyError)):result.output("reference")
            assert any(effect.status=="unknown" for effect in result.effects.values())
        assert writer.calls==1


def test_size_and_output_budget_reject_before_a_confirmed_storage_effect(tmp_path):
    value=dataset()
    with pytest.raises(ValueError,match="size_limit"):
        FileDatasetStore(tmp_path/"small",max_bytes=10).ingest(value,destination="source",identity=value.identity)
    assert not list((tmp_path/"small").glob("*/*"))
    with StrategyBox(providers={"filestore":__import__("stratbox.core.storage.filestore",fromlist=["LocalFileStore"]).LocalFileStore(tmp_path/"artifacts")},settings=ExecutionSettings(run_limits=ExecutionBudget(output_bytes=1))) as box:
        result=box.invoke("command.artifact.commit",inputs={"material":b"too large","destination":"source"})
        assert result.outcome=="failed" and not result.effects
