"""All projections follow one placement and real payload lifetime is measured."""
from dataclasses import dataclass
import gc
import tracemalloc
import weakref

import pytest

from stratbox.core.execution.contracts import OperationDefinition, OperationResult, ObservabilitySummary
from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.execution.retention import (
    AttemptMapping, ResultMapping, ResultOwnership, ResultSpillStore, ValueMapping, retained_size,
)
from stratbox.core.execution.values.placement import ManagedResult, ManagedCollection, ValueReadScope, resolve_managed, isolate_managed
from stratbox.shared.data.operations import OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract


@dataclass
class Payload:
    data: bytearray


@dataclass(frozen=True)
class Request:
    size: int


CONTRACT = DataContract("test.placement")
DEFINITION = OperationDefinition("test.placement", "test.placement", Request, Payload,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), outputs=(OutputPort("value", CONTRACT),), summary="Exercise accepted placement ownership."))


def accepted(size=1024):
    payload = Payload(bytearray(b"x" * size))
    result = OperationResult(DEFINITION, "placement-result", "succeeded", payload, (), (), (), ObservabilitySummary(0, 0))
    ledger = ResourceLedger({"retained_bytes": 8 * max(size, 1024), "temporary_bytes": 8 * max(size, 1024)})
    assert ledger.reserve("accepted-result", {"retained_bytes": retained_size(payload)})
    return ManagedResult(result, ledger=ledger, reservation_owner="accepted-result"), ledger, weakref.ref(payload)


def test_spill_drops_real_payload_with_scope_result_and_attempt_projections_alive():
    size = 4 * 1024 * 1024
    tracemalloc.start()
    try:
        owner, ledger, payload_ref = accepted(size)
        scope = ValueMapping({"payload": owner.project(unwrap=True)})
        results = ResultMapping({"task": owner})
        attempts = AttemptMapping({"task": (owner,)})
        before, _ = tracemalloc.get_traced_memory()
        spill = ResultSpillStore(ledger=ledger)
        assert owner.spill(spill)
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
        assert payload_ref() is None
        assert before - after > size * 3 // 4
        assert ledger.snapshot().occupied["retained_bytes"] == 0
        assert len(scope["payload"].data) == size
        assert len(results["task"].value.data) == size
        assert len(attempts["task"][0].value.data) == size
        assert owner.placement == "temporary"
        assert ledger.snapshot().occupied["retained_bytes"] == 0
        owner.close()
        spill.close()
    finally:
        tracemalloc.stop()


def test_spilled_read_is_accounted_for_complete_core_use_then_released():
    owner, ledger, payload_ref = accepted()
    spill = ResultSpillStore(ledger=ledger)
    owner.spill(spill)
    gc.collect()
    assert payload_ref() is None
    with ValueReadScope():
        result = resolve_managed(owner)
        projected = resolve_managed(owner.project(unwrap=True))
        assert result.value.data == projected.data
        assert ledger.snapshot().occupied["retained_bytes"] == 1024
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    owner.close()
    spill.close()


def test_scope_close_preserves_active_reader_and_pin_without_fictitious_release():
    owner, ledger, payload_ref = accepted()
    lease = owner.read()
    pin = owner.pin()
    spill = ResultSpillStore(ledger=ledger)
    owner.spill(spill)
    assert payload_ref() is not None
    assert ledger.snapshot().occupied["retained_bytes"] == 1024
    owner.close()
    spill.close()
    assert lease.value.value.data == bytearray(b"x" * 1024)
    lease.close()
    gc.collect()
    assert payload_ref() is None
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    with pin.read() as retained:
        assert retained.value.data[0] == ord("x")
        assert ledger.snapshot().occupied["retained_bytes"] == 1024
    pin.close()
    assert ledger.snapshot().occupied["temporary_bytes"] == 0


def test_public_result_lease_keeps_spilled_placement_alive_after_result_close():
    owner, ledger, _ = accepted()
    spill = ResultSpillStore(ledger=ledger)
    owner.spill(spill)
    released = []
    ownership = ResultOwnership(ledger, (), spill, managed=(owner,), on_close=lambda: released.append("closed"))
    lease = ownership.lease(owner.project(unwrap=True))
    lease.value.data[0] = ord("z")
    ownership.close()
    assert not released
    assert lease.value.data[0] == ord("z")
    assert ledger.snapshot().occupied["retained_bytes"] == 2048  # Materialization plus mutable reader copy.
    lease.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    assert ledger.snapshot().occupied["temporary_bytes"] == 0
    assert released == ["closed"]
    ownership.close()
    assert released == ["closed"]


def test_materialization_denied_before_read_when_other_live_result_owns_capacity():
    owner, ledger, _ = accepted()
    spill = ResultSpillStore(ledger=ledger)
    owner.spill(spill)
    assert ledger.reserve("other-result", {"retained_bytes": ledger.capacities["retained_bytes"]})
    with pytest.raises(ValueError, match="retained_bytes"):
        owner.read()
    assert ledger.snapshot().occupied["retained_bytes"] == ledger.capacities["retained_bytes"]
    ledger.release("other-result")
    owner.close()
    spill.close()


def test_worker_copy_keeps_mutable_buffers_accounted_and_shares_sealed_source_bytes():
    from stratbox.shared.evidence import SourcePayload
    source = SourcePayload(b"x" * 100_000)
    payload = Payload(bytearray(b"x" * 1024))
    ledger = ResourceLedger({"retained_bytes": 2048})
    with ValueReadScope():
        isolated = isolate_managed({"source": source, "payload": payload}, ledger)
        assert isolated["source"] is source
        assert isolated["payload"] is not payload
        assert ledger.snapshot().occupied["retained_bytes"] == 1024
        isolated["payload"].data[0] = ord("z")
        assert payload.data[0] == ord("x")
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_structural_collection_keeps_projections_and_one_materialization_per_owner():
    owner, ledger, payload_ref = accepted()
    collection = ManagedCollection((owner.project(), owner.project()), DataContract("test.placements"), CONTRACT)
    spill = ResultSpillStore(ledger=ledger)
    owner.spill(spill)
    gc.collect()
    assert payload_ref() is None
    with collection.read() as prepared:
        assert len(prepared.value) == 2
        assert prepared.value[0] is prepared.value[1]
        assert ledger.snapshot().occupied["retained_bytes"] == 1024
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    assert all(item.owner is owner for item in collection.items)
    owner.close()
    spill.close()
