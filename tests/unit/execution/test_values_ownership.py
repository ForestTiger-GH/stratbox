"""Acceptance is coherent, readers are isolated, and real owners keep capacity."""
from dataclasses import dataclass

import pytest

from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.execution.retention import ResultOwnership, retained_size
from stratbox.core.execution.values.ownership import AcceptedValueStore, accept_owned_value
from stratbox.shared.data.processing import DataContract

C = DataContract("test.accepted")


def accepted(store, value, *, obligations=()):
    candidate = store.begin({"value": C}, obligations=obligations)
    candidate.write("value", value)
    candidate.close_writer()
    candidate.validate()
    return candidate.accept()["value"]


def test_named_outputs_are_unavailable_until_complete_validated_group_acceptance():
    store = AcceptedValueStore(max_resident_bytes=100, max_staging_bytes=100)
    with store.begin({"left": C, "right": C}) as candidate:
        candidate.write("left", 1)
        with pytest.raises(ValueError, match="not_validated"):
            candidate.accept()
        with pytest.raises(ValueError, match="not_closed"):
            candidate.validate()
        candidate.close_writer()
        with pytest.raises(ValueError, match="set_incomplete"):
            candidate.validate()
        assert store.resident_bytes == 0
    assert store.staging_bytes == 0


def test_semantic_failure_releases_staging_without_exposing_one_successful_member():
    store = AcceptedValueStore()
    with store.begin({"left": C, "right": C}) as candidate:
        candidate.write("left", 1)
        candidate.write("right", -1)
        candidate.close_writer()
        with pytest.raises(ValueError, match="semantic_check_failed"):
            candidate.validate((lambda values: values["right"] >= 0,))
        assert store.resident_bytes == 0
    assert store.staging_bytes == 0


def test_caller_and_consumer_mutation_do_not_change_another_reader():
    original = {"rows": [1, 2]}
    store = AcceptedValueStore()
    handle = accepted(store, original)
    original["rows"].append(3)
    with handle.read() as first:
        first["rows"].append(4)
        with handle.read() as second:
            assert second == {"rows": [1, 2]}
    handle.close()
    assert store.resident_bytes == 0


def test_scope_close_keeps_reader_and_demand_pin_then_releases_actual_bytes():
    ledger = ResourceLedger({"retained_bytes": 1000, "staging_bytes": 1000})
    store = AcceptedValueStore(ledger=ledger)
    handle = accepted(store, [1, 2])
    pin, lease = handle.pin(), handle.read()
    handle.close()
    store.close()
    assert lease.value == [1, 2]
    assert ledger.snapshot().occupied["retained_bytes"] > 0
    lease.close()
    assert store.resident_bytes == 16
    pin.close()
    assert store.resident_bytes == 0
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_unresolved_recovery_obligation_preserves_value_without_live_handle():
    store = AcceptedValueStore()
    handle = accepted(store, 7, obligations=("commit.unknown",))
    key = handle.key
    handle.close()
    assert store.resident_bytes == 8
    store.resolve_obligation(key, "commit.unknown")
    assert store.resident_bytes == 0


def test_resident_and_staging_limits_are_independent_and_acceptance_is_atomic():
    store = AcceptedValueStore(max_resident_bytes=8, max_staging_bytes=16)
    with store.begin({"a": C, "b": C}) as candidate:
        candidate.write("a", 1)
        candidate.write("b", 2)
        candidate.close_writer()
        candidate.validate()
        with pytest.raises(ValueError, match="retained_bytes"):
            candidate.accept()
        assert store.resident_bytes == 0
        assert store.staging_bytes == 16
    assert store.staging_bytes == 0


def test_reader_copy_capacity_is_counted_until_lease_close():
    store = AcceptedValueStore(max_resident_bytes=32)
    handle = accepted(store, [1, 2])
    lease = handle.read()
    assert store.resident_bytes == 32
    with pytest.raises(ValueError, match="retained_bytes"):
        handle.read()
    lease.close()
    assert store.resident_bytes == 16
    handle.close()


def test_live_result_capacity_survives_run_and_close_until_final_reader():
    ledger = ResourceLedger({"retained_bytes": 100})
    assert ledger.reserve("completed-run", {"retained_bytes": 80})
    owner = ResultOwnership(ledger, ("completed-run",))
    lease = owner.lease(b"selected output")
    owner.close()
    assert owner.closed
    assert ledger.snapshot().occupied["retained_bytes"] == 80
    assert lease.value == b"selected output"
    with pytest.raises(ValueError, match="retention_closed"):
        owner.lease()
    lease.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_clone_is_independent_demand_without_payload_duplication():
    store = AcceptedValueStore()
    first = accepted(store, b"abc")
    second = first.clone()
    first.close()
    assert store.resident_bytes == 3
    with second.read() as value:
        assert value == b"abc"
    second.close()
    assert store.resident_bytes == 0


def test_command_acceptance_transfers_reservation_without_releasing_owned_payload():
    ledger = ResourceLedger({"retained_bytes": 1000, "staging_bytes": 1000})
    original = {"left": [1], "right": [2]}
    transfer = accept_owned_value(original, C, ledger=ledger, max_resident_bytes=1000,
        max_staging_bytes=1000, checks=(lambda outputs: set(outputs) == {"left", "right"},))
    assert transfer.value == original
    original["left"].append(3)
    assert transfer.value["left"] == [1]
    assert ledger.snapshot().occupied["staging_bytes"] == 0
    assert ledger.requirements(transfer.owner) == {"retained_bytes": transfer.descriptor.resident_bytes}
    owner = ResultOwnership(ledger, (transfer.owner,))
    lease = owner.lease(transfer.value)
    owner.close()
    assert lease.value["right"] == [2]
    assert ledger.snapshot().occupied["retained_bytes"] > 0
    lease.close()
    assert ledger.snapshot().occupied["retained_bytes"] == 0


def test_rejected_command_envelope_never_acquires_accepted_reservation():
    ledger = ResourceLedger({"retained_bytes": 1000, "staging_bytes": 1000})
    with pytest.raises(ValueError, match="semantic_check_failed"):
        accept_owned_value({"left": 1}, C, ledger=ledger, max_resident_bytes=1000,
            max_staging_bytes=1000, checks=(lambda outputs: "right" in outputs,))
    assert ledger.snapshot().occupied.get("retained_bytes", 0) == 0
    assert ledger.snapshot().occupied.get("staging_bytes", 0) == 0
