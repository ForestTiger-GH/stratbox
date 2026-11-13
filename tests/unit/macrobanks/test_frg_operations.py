import pytest

from stratbox.base.filestore import LocalFileStore, MutationRejected
from stratbox.macrobanks import frg

LATEST = "2026-05-01_Экспресс выдачи.xlsx"
OLDER = "2026-04-01_Экспресс выдачи.xlsx"


def populate(tmp_path):
    (tmp_path / LATEST).write_bytes(b"latest workbook")
    (tmp_path / OLDER).write_bytes(b"older workbook")
    (tmp_path / "unrelated.txt").write_bytes(b"unrelated")
    return LocalFileStore(root=str(tmp_path))


def test_cleanup_rechecks_plan_and_limits_effect_to_the_reviewed_scope(tmp_path):
    store = populate(tmp_path)
    original = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=True), store=store
    )
    assert original.outcome == "succeeded", original.diagnostics
    assert [action.kind for action in original.value.actions] == ["keep", "remove"]
    assert (tmp_path / OLDER).exists()
    tampered = frg.apply_cleanup(
        frg.ApplyCleanupRequest(original.value, ".", "invalid"), store=store
    )
    assert tampered.diagnostics[0].code == "effect.plan_not_authorized"
    (tmp_path / OLDER).write_bytes(b"replacement")
    stale = frg.apply_cleanup(
        frg.ApplyCleanupRequest(original.value, ".", original.value.identity.sha256),
        store=store,
    )
    assert stale.diagnostics[0].code == "effect.plan_stale"
    assert (tmp_path / OLDER).read_bytes() == b"replacement"
    fresh = frg.plan_cleanup(original.value.request, store=store).value
    applied = frg.apply_cleanup(
        frg.ApplyCleanupRequest(fresh, ".", fresh.identity.sha256), store=store
    )
    assert applied.outcome == "succeeded", applied.diagnostics
    assert not (tmp_path / OLDER).exists()
    assert (tmp_path / LATEST).exists() and (tmp_path / "unrelated.txt").exists()


def test_symbolic_entry_blocks_cleanup_plan(tmp_path):
    store = populate(tmp_path)
    try:
        (tmp_path / "symbolic.xlsx").symlink_to(tmp_path / LATEST)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable")
    result = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=True), store=store
    )
    assert result.outcome == "failed"
    assert not result.effects


def test_failed_conditional_remove_does_not_claim_success(tmp_path):
    class RejectingStore(LocalFileStore):
        def remove_expected(self, expected):
            raise MutationRejected("refused")

    populate(tmp_path)
    store = RejectingStore(root=str(tmp_path))
    plan = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=True), store=store
    ).value
    result = frg.apply_cleanup(
        frg.ApplyCleanupRequest(plan, ".", plan.identity.sha256), store=store
    )
    assert result.outcome == "failed" and result.effects[0].state == "failed"
    assert (tmp_path / OLDER).exists()


def test_cleanup_preserves_confirmed_and_unattempted_actions_on_cancellation(tmp_path):
    from threading import Event

    from stratbox.execution import ExecutionContext

    cancelled = Event()

    class CancellingStore(LocalFileStore):
        def remove_expected(self, expected):
            assert super().remove_expected(expected)
            cancelled.set()
            return True

    populate(tmp_path)
    extra = "2026-03-01_Экспресс выдачи.xlsx"
    (tmp_path / extra).write_bytes(b"more history")
    store = CancellingStore(root=str(tmp_path))
    plan = frg.plan_cleanup(frg.PlanCleanupRequest(".", delete_others=True), store=store).value
    result = frg.apply_cleanup(
        frg.ApplyCleanupRequest(plan, ".", plan.identity.sha256), store=store,
        context=ExecutionContext(cancellation=cancelled),
    )
    assert result.outcome == "partial"
    assert [receipt.state for receipt in result.value] == ["confirmed", "confirmed", "not_attempted"]
    assert len(result.effects) == 1 and result.effects[0].state == "confirmed"
    assert not store.exists(result.value[1].action.source.path)
    assert store.exists(result.value[2].action.source.path)
