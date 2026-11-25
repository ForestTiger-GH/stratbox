"""Aged claims retain acyclic priority while independent capacity stays useful."""
from stratbox.core.execution.resources import ResourceLedger


def test_two_aged_waiters_cannot_block_one_another_after_capacity_frees(monkeypatch):
    import stratbox.core.execution.resources as resources
    now = [0.0]
    monkeypatch.setattr(resources, "monotonic", lambda: now[0])
    ledger = ResourceLedger({"worker": 3, "cpu": 2, "network": 1}, starvation_seconds=1)
    assert ledger.reserve("running", {"worker": 1, "cpu": 1})
    assert not ledger.reserve("older-large", {"worker": 1, "cpu": 2})
    now[0] = 2
    assert not ledger.reserve("younger-small", {"worker": 1, "cpu": 1})
    now[0] = 4
    ledger.release("running")
    assert ledger.reserve("older-large", {"worker": 1, "cpu": 2})
    assert not ledger.reserve("younger-small", {"worker": 1, "cpu": 1})
    ledger.release("older-large")
    assert ledger.reserve("younger-small", {"worker": 1, "cpu": 1})


def test_waiter_priority_survives_retries_but_cancellation_releases_its_claim(monkeypatch):
    import stratbox.core.execution.resources as resources
    now = [0.0]
    monkeypatch.setattr(resources, "monotonic", lambda: now[0])
    ledger = ResourceLedger({"worker": 4, "cpu": 3, "network": 1}, starvation_seconds=1)
    assert ledger.reserve("running", {"worker": 1, "cpu": 2})
    assert not ledger.reserve("first", {"worker": 1, "cpu": 3})
    now[0] = 2
    assert not ledger.reserve("second", {"worker": 1, "cpu": 1})
    assert ledger.reserve("independent", {"worker": 1, "network": 1})
    now[0] = 4
    assert not ledger.reserve("first", {"worker": 1, "cpu": 3})
    ledger.release("first")
    assert ledger.reserve("second", {"worker": 1, "cpu": 1})


def test_aged_multi_worker_claim_keeps_its_last_needed_worker_free(monkeypatch):
    import stratbox.core.execution.resources as resources
    now = [0.0]
    monkeypatch.setattr(resources, "monotonic", lambda: now[0])
    ledger = ResourceLedger({"worker": 3, "cpu": 2, "network": 2}, starvation_seconds=1)
    assert ledger.reserve("running", {"worker": 2, "cpu": 1})
    assert not ledger.reserve("large", {"worker": 2, "cpu": 1})
    now[0] = 2
    assert not ledger.reserve("small", {"worker": 1, "network": 1})
    ledger.release("running")
    assert ledger.reserve("large", {"worker": 2, "cpu": 1})
    assert ledger.reserve("small", {"worker": 1, "network": 1})
