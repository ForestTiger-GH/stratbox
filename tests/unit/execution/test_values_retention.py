"""Process-private spill remains bounded, counted and protected from tampering."""
from dataclasses import dataclass
from pathlib import Path

import pytest

from stratbox.core.execution.contracts import OperationDefinition, OperationResult, ObservabilitySummary
from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.execution.retention import ResultOwnership, ResultSpillStore


@dataclass(frozen=True)
class Request:
    value: bytes


DEFINITION = OperationDefinition("test.spill", "test.spill", Request, bytes)


def result(value):
    return OperationResult(DEFINITION, "test-invocation", "succeeded", value, (), (), (), ObservabilitySummary(0, 0))


def test_private_spill_writes_under_capacity_and_lease_preserves_it_after_close():
    ledger = ResourceLedger({"temporary_bytes": 100_000, "retained_bytes": 100_000})
    spill = ResultSpillStore(max_bytes=100_000, ledger=ledger)
    original = result(b"bounded" * 100)
    reference = spill.put(original)
    assert ledger.snapshot().occupied["temporary_bytes"] > len(original.value)
    assert reference.resolve() == original
    owner = ResultOwnership(ledger, spill=spill)
    lease = owner.lease(reference)
    owner.close()
    assert lease.value.resolve() == original
    lease.close()
    assert ledger.snapshot().occupied["temporary_bytes"] == 0
    with pytest.raises(ValueError, match="retention_closed"):
        reference.resolve()


def test_oversized_private_spill_leaves_no_file_or_reservation():
    ledger = ResourceLedger({"temporary_bytes": 128})
    spill = ResultSpillStore(max_bytes=128, ledger=ledger)
    with pytest.raises(ValueError, match="temporary_bytes"):
        spill.put(result(b"a" * 100_000))
    assert not tuple(Path(spill._directory.name).iterdir())
    assert ledger.snapshot().occupied.get("temporary_bytes", 0) == 0
    spill.close()


def test_external_file_growth_is_rejected_before_loading_payload():
    spill = ResultSpillStore()
    reference = spill.put(result(b"expected"))
    Path(spill._directory.name, reference.key).write_bytes(b"unexpected" * 10_000)
    with pytest.raises(ValueError, match="retained_content_changed"):
        reference.resolve()
    spill.close()


def test_shared_invocation_spills_have_distinct_physical_owners_per_store():
    ledger = ResourceLedger({"temporary_bytes": 100_000})
    left = ResultSpillStore(ledger=ledger)
    right = ResultSpillStore(ledger=ledger)
    original = result(b"shared invocation, independent retained copies")
    left.put(original)
    one = ledger.snapshot().occupied["temporary_bytes"]
    right_reference = right.put(original)
    assert ledger.snapshot().occupied["temporary_bytes"] == 2 * one
    left.close()
    assert ledger.snapshot().occupied["temporary_bytes"] == one
    assert right_reference.resolve() == original
    right.close()
