"""Dynamic consumers retain accounted materializations for their actual life."""
from dataclasses import dataclass
import gc
import tracemalloc
import weakref

import pytest

from stratbox.core.execution.contracts import OperationDefinition, OperationResult, ObservabilitySummary
from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.execution.retention import ResultOwnership, ResultSpillStore, ValueMapping, retained_size
from stratbox.core.execution.values.placement import (
    LeasedIterator, ManagedResult, ValueReadScope, detach_managed, isolate_managed, resolve_managed,
    isolate_plan,
)
from stratbox.shared.data.operations import OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract


@dataclass
class Item:
    data: bytearray


@dataclass
class Batch:
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Request:
    size: int


CONTRACT = DataContract("test.dynamic-batch")
DEFINITION = OperationDefinition("test.dynamic-batch", "test.dynamic-batch", Request, Batch,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), outputs=(OutputPort("value", CONTRACT),),
        summary="Exercise owned dynamic source materializations."))


def spilled(size=1024):
    batch = Batch((Item(bytearray(b"x" * size)), Item(bytearray(b"y" * size))))
    result = OperationResult(DEFINITION, "dynamic-batch", "succeeded", batch, (), (), (), ObservabilitySummary(0, 0))
    ledger = ResourceLedger({"retained_bytes": size * 8, "temporary_bytes": size * 8, "staging_bytes": size * 8})
    assert ledger.reserve("original", {"retained_bytes": retained_size(batch)})
    owner = ManagedResult(result, ledger=ledger, reservation_owner="original")
    store = ResultSpillStore(ledger=ledger)
    owner.spill(store)
    return owner, store, ledger


def test_internal_resolution_and_isolation_require_an_accounted_read_scope():
    owner, store, ledger = spilled()
    projection = owner.project(unwrap=True)
    with pytest.raises(ValueError, match="read_scope_required"):
        resolve_managed(projection)
    with pytest.raises(ValueError, match="read_scope_required"):
        isolate_managed({"value": bytearray(32)}, ledger)
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    # The public transfer names its different ownership contract explicitly.
    caller = detach_managed(projection)
    assert len(caller.items) == 2
    assert len(ValueMapping({"value": projection})["value"].items) == 2
    owner.close()
    store.close()
    assert caller.items[0].data[0] == ord("x")


def test_map_iterator_and_pending_child_keep_the_same_real_materialization_owned():
    size = 1024 * 1024
    owner, store, ledger = spilled(size)
    tracemalloc.start()
    try:
        scope = ValueReadScope()
        with scope.activate():
            source = resolve_managed(owner.project(unwrap=True))
            materialized = weakref.ref(source)
            item = weakref.ref(source.items[0])
            iterator = LeasedIterator(enumerate(source.items), scope)
            del source
        loaded, _ = tracemalloc.get_traced_memory()
        child_scope = scope.fork()
        _, element = next(iterator)
        pending_plan = {"item": element}
        del element
        iterator.close()
        gc.collect()
        assert materialized() is not None
        assert item() is pending_plan["item"]
        assert ledger.snapshot().occupied["retained_bytes"] == 2 * size
        with child_scope.activate():
            # The child's owner cache reuses the iterator's existing decode.
            assert resolve_managed(owner).value is materialized()
        del pending_plan
        child_scope.close()
        gc.collect()
        released, _ = tracemalloc.get_traced_memory()
        assert materialized() is None and item() is None
        assert loaded - released > size * 3 // 2
        assert ledger.snapshot().occupied["retained_bytes"] == 0
    finally:
        tracemalloc.stop()
        owner.close()
        store.close()


def test_nested_dynamic_consumers_release_source_after_last_descendant():
    owner, store, ledger = spilled()
    parent = ValueReadScope()
    with parent.activate():
        resolve_managed(owner)
    child = parent.fork()
    grandchild = child.fork()
    parent.close()
    child.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 2048
    try:
        with grandchild.activate():
            assert len(resolve_managed(owner).value.items) == 2
            raise ValueError("test.expansion_failed")
    except ValueError:
        grandchild.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    grandchild.close()
    with pytest.raises(ValueError, match="read_scope_closed"):
        parent.fork()
    owner.close()
    store.close()


def test_handler_parameter_copies_are_admitted_before_allocation_and_released():
    ledger = ResourceLedger({"retained_bytes": 3000})
    source = Item(bytearray(b"x" * 2000))
    with ValueReadScope():
        parameters = isolate_managed({"parameter": source}, ledger)
        copied = weakref.ref(parameters["parameter"])
        assert ledger.snapshot().occupied["retained_bytes"] == 2000
        parameters["parameter"].data[0] = ord("z")
        assert source.data[0] == ord("x")
        with pytest.raises(ValueError, match="retained_bytes"):
            isolate_managed({"parameter": source}, ledger)
        del parameters
    gc.collect()
    assert copied() is None
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_iterator_close_releases_owned_source_when_generator_cleanup_fails():
    owner, store, ledger = spilled()
    scope = ValueReadScope()
    with scope.activate():
        source = resolve_managed(owner.project(unwrap=True))

    def values():
        try:
            yield source.items[0]
        finally:
            raise ValueError("test.generator_close_failed")

    iterator = LeasedIterator(values(), scope)
    next(iterator)
    del source
    with pytest.raises(ValueError, match="generator_close_failed"):
        iterator.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    owner.close()
    store.close()


def test_returned_literal_keeps_its_input_reader_until_last_public_read_finishes():
    ledger = ResourceLedger({"retained_bytes": 8192})
    input_reader = ValueReadScope()
    with input_reader.activate():
        value = isolate_managed({"literal": Item(bytearray(b"x" * 1024))}, ledger)["literal"]
    ownership = ResultOwnership(ledger, readers=(input_reader,))
    reader = ownership.lease(value)
    del value
    ownership.close()
    assert len(reader.value.data) == 1024
    assert ledger.snapshot().occupied["retained_bytes"] == 2048
    reader.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_plan_isolation_reuses_graph_metadata_and_owns_one_shared_material_copy():
    from stratbox.composition.plan import CompiledTask, ExecutionPlan, PlanScope
    source = Item(bytearray(b"x" * 1024))
    plan = ExecutionPlan("test-plan", "test-definition", (
        CompiledTask("test-definition/task", "test.command", {"data": source}, {"parameter": source}, (), "test-definition"),
    ), {"literal": source}, (PlanScope("test-definition", "test-definition", outputs={"literal": source}),),
        selected_bindings={"test-definition": {"metadata": "large control declaration" * 10_000}})
    ledger = ResourceLedger({"retained_bytes": 1024})
    with ValueReadScope():
        copied = isolate_plan(plan, ledger)
        assert ledger.snapshot().occupied["retained_bytes"] == 1024
        material = copied.tasks[0].inputs["data"]
        assert material is not source
        assert material is copied.tasks[0].parameters["parameter"]
        assert material is copied.outputs["literal"]
        assert material is copied.scopes[0].outputs["literal"]
        material.data[0] = ord("z")
        assert source.data[0] == ord("x")
    assert ledger.snapshot().occupied["retained_bytes"] == 0
    with ValueReadScope(), pytest.raises(ValueError, match="retained_bytes"):
        isolate_plan(plan, ResourceLedger({"retained_bytes": 1023}))


def test_metadata_only_plan_fits_tiny_material_quota():
    from stratbox.composition.plan import CompiledTask, ExecutionPlan, PlanScope
    from stratbox.composition.models import PlanOutputRef
    reference = PlanOutputRef("test-definition/task")
    plan = ExecutionPlan("test-plan", "test-definition", (
        CompiledTask("test-definition/task", "test.command", {}, {"count": 1}, (), "test-definition"),
    ), {"value": reference}, (PlanScope("test-definition", "test-definition", outputs={"value": reference}),))
    ledger = ResourceLedger({"retained_bytes": 1})
    with ValueReadScope():
        copied = isolate_plan(plan, ledger)
        assert copied == plan
        assert isolate_managed({"count": 1}, ledger) == {"count": 1}
        assert ledger.snapshot().occupied.get("retained_bytes", 0) == 0
        assert ledger.snapshot().reservations == 0
