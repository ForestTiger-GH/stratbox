"""Real-store and multi-effect regression tests for execution finalization."""
from stratbox.core.execution import ExecutionContext, InMemorySink
from stratbox.core.operations.source.originals import (
    OriginalDestination, SaveOriginalRequest, save_original,
)
from stratbox.core.storage.filestore import LocalFileStore, MutationRejected
from stratbox.domains.frank_rg import retail_banking as frg
from stratbox.shared.evidence import SourcePayload


def test_existing_immutable_file_reports_known_failed_effect_without_false_success(tmp_path):
    store = LocalFileStore(str(tmp_path))
    (tmp_path / "original.bin").write_bytes(b"prior-content")
    result = save_original(
        SaveOriginalRequest(SourcePayload(b"new-bytes"), OriginalDestination("original.bin")),
        store=store,
    )
    assert result.outcome == "failed"
    assert result.effects and result.effects[0].state == "failed"
    assert (tmp_path / "original.bin").read_bytes() == b"prior-content"


def test_real_store_confirms_receipt_and_terminal_event(tmp_path):
    store = LocalFileStore(str(tmp_path))
    sink = InMemorySink()
    result = save_original(
        SaveOriginalRequest(SourcePayload(b"new-bytes"), OriginalDestination("original.bin")),
        store=store, context=ExecutionContext(sink=sink),
    )
    assert result.outcome == "succeeded"
    assert result.value.material.identity == result.value.storage.identity
    assert result.effects[0].state == "confirmed"
    assert sink.events[-1].outcome == result.outcome


def _populate_cleanup(directory):
    for period in ("2026-05-01", "2026-04-01", "2026-03-01"):
        (directory / (period + "_Экспресс выдачи.xlsx")).write_bytes(period.encode())


def test_frank_cleanup_partial_after_known_second_mutation_failure(tmp_path):
    class RejectSecond(LocalFileStore):
        mutations = 0

        def remove_expected(self, expected):
            self.mutations += 1
            if self.mutations == 2:
                raise MutationRejected("rejected")
            return super().remove_expected(expected)

    _populate_cleanup(tmp_path)
    store = RejectSecond(str(tmp_path))
    plan = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=True), store=store,
    )
    assert plan.outcome == "succeeded"
    executed = frg.apply_cleanup(
        frg.ApplyCleanupRequest(plan.value, ".", plan.value.identity.sha256),
        store=store,
    )
    assert executed.outcome == "partial"
    assert [effect.state for effect in executed.effects] == ["confirmed", "failed"]
    assert sum(receipt.state == "confirmed" for receipt in executed.value) >= 2
    assert any(receipt.state == "failed" for receipt in executed.value)


def test_frank_cleanup_unknown_after_second_mutation_does_not_claim_partial(tmp_path):
    class UnknownSecond(LocalFileStore):
        mutations = 0

        def remove_expected(self, expected):
            self.mutations += 1
            if self.mutations == 2:
                raise OSError("acknowledgement lost")
            return super().remove_expected(expected)

    _populate_cleanup(tmp_path)
    store = UnknownSecond(str(tmp_path))
    plan = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=True), store=store,
    ).value
    result = frg.apply_cleanup(
        frg.ApplyCleanupRequest(plan, ".", plan.identity.sha256), store=store,
    )
    assert result.outcome == "unknown"
    assert [effect.state for effect in result.effects] == ["confirmed", "unknown"]
    assert any(d.code == "effect.outcome_unknown" for d in result.diagnostics)


def test_staged_store_output_budget_is_checked_before_commit(tmp_path):
    from stratbox.core.execution import ExecutionBudget, ExecutionContext
    payload = SourcePayload(b"published-content")
    destination = OriginalDestination("budgeted.bin")

    too_small = save_original(
        SaveOriginalRequest(payload, destination),
        store=LocalFileStore(str(tmp_path)),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=len(payload.data) - 1)),
    )
    assert too_small.outcome == "failed"
    assert any(d.code == "budget.output_bytes" for d in too_small.diagnostics)
    assert not (tmp_path / "budgeted.bin").exists()
    assert not too_small.effects

    exactly = save_original(
        SaveOriginalRequest(payload, destination),
        store=LocalFileStore(str(tmp_path)),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=len(payload.data))),
    )
    assert exactly.outcome == "succeeded"
    assert exactly.effects[0].state == "confirmed"
    assert dict(exactly.resources_used)["output_bytes"] == len(payload.data)
