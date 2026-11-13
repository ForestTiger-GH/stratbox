"""Streaming FRG archive tests: size, integrity, safe retry and exact plan."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks import frg

LATEST = "2026-05-01_Экспресс выдачи.xlsx"
OLDER = "2026-04-01_Экспресс выдачи.xlsx"


def _setup(tmp_path, large=False):
    source = tmp_path / "inputs"
    source.mkdir()
    latest = source / LATEST
    if large:
        with latest.open("wb") as stream:
            stream.truncate(105 * 1024 * 1024)  # > old 100 MiB aggregate / 32 MiB member ceilings
    else:
        latest.write_bytes(b"latest")
    (source / OLDER).write_bytes(b"older")
    output = tmp_path / "outputs"
    output.mkdir()
    input_store = LocalFileStore(root=str(source))
    output_store = LocalFileStore(root=str(output))
    plan_result = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=False), store=input_store
    )
    assert plan_result.outcome == "succeeded", plan_result.diagnostics
    return input_store, output_store, plan_result.value, latest, output


def test_large_frg_archive_streams_to_disk_with_report(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path, large=True)
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "frg-latest.zip", b'{"status":"complete"}'),
        store=inp,
        output_store=out,
    )
    assert result.outcome == "succeeded", result.diagnostics
    receipt = result.value
    assert receipt.identity.size > 100 * 1024 * 1024
    data = destination_dir / "frg-latest.zip"
    assert data.exists()
    expected = next(action.destination.split("/")[-1] for action in plan.actions if action.kind != "remove")
    with ZipFile(data) as package:
        assert set(package.namelist()) == {expected, "selection_report.json"}
        assert package.getinfo(expected).file_size == 105 * 1024 * 1024
        assert package.read("selection_report.json") == b'{"status":"complete"}'
    digest = sha256()
    with data.open("rb") as raw:
        while chunk := raw.read(1024 * 1024):
            digest.update(chunk)
    assert digest.hexdigest() == receipt.identity.sha256
    assert latest.stat().st_size == 105 * 1024 * 1024


def test_changed_source_blocks_archive_and_preserves_existing_output(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path)
    target = destination_dir / "frg-latest.zip"
    target.write_bytes(b"previous-safe-artifact")
    latest.write_bytes(b"changed-after-plan")
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "frg-latest.zip"),
        store=inp, output_store=out,
    )
    assert result.outcome == "failed"
    assert target.read_bytes() == b"previous-safe-artifact"


def test_report_written_as_separate_archive_member(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path)
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "bad.zip", b'{"hello":"world"}'),
        store=inp, output_store=out,
    )
    assert result.outcome == "succeeded", result.diagnostics
    assert (destination_dir / "bad.zip").exists()


def test_commit_ack_loss_cas_conflict_and_quota_leave_verifiable_state(tmp_path):
    from contextlib import contextmanager
    from dataclasses import replace

    from stratbox.base.limits import ExecutionBudget
    from stratbox.execution import ExecutionContext

    inp, _, plan, _, outputs = _setup(tmp_path)

    class LostAckStore(LocalFileStore):
        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                class CommitThenLoseAck:
                    stream = stage.stream

                    def commit(self, mode, revision):
                        assert stage.commit(mode, revision) is True
                        raise TimeoutError("lost after actual storage commit")

                yield CommitThenLoseAck()

    request = frg.StreamArchiveRequest(plan, "result.zip")
    ordinary = LocalFileStore(root=str(outputs))
    lost = frg.prepare_archive_to_store(request, store=inp, output_store=LostAckStore(str(outputs)))
    assert lost.outcome == "unknown" and lost.value.storage.stage == "commit"
    observed = ordinary.inspect_file("result.zip")
    assert observed.identity == lost.value.identity
    reconciled = frg.prepare_archive_to_store(request, store=inp, output_store=ordinary)
    assert reconciled.value.storage.status == "already_present"
    assert reconciled.value.effect_id == lost.value.effect_id
    changed = replace(request, report_json=b"{}", mode="replace_expected_revision", expected_revision="stale")
    rejected = frg.prepare_archive_to_store(changed, store=inp, output_store=ordinary)
    assert rejected.diagnostics[0].code == "effect.conflict"
    assert ordinary.inspect_file("result.zip") == observed
    quota = ExecutionContext(budget=ExecutionBudget(temporary_bytes=20))
    exhausted = frg.prepare_archive_to_store(
        replace(changed, expected_revision=observed.revision), store=inp,
        output_store=ordinary, context=quota,
    )
    assert exhausted.diagnostics[0].code == "budget.temporary_bytes"
    assert not exhausted.effects and ordinary.inspect_file("result.zip") == observed
    assert [file.name for file in outputs.iterdir()] == ["result.zip"]
    replaced = frg.prepare_archive_to_store(
        replace(changed, expected_revision=observed.revision), store=inp, output_store=ordinary,
    )
    assert replaced.outcome == "succeeded" and replaced.value.identity != observed.identity


def test_managed_archive_and_cleanup_recheck_scope_at_store(tmp_path):
    from contextlib import contextmanager

    from stratbox.base.capabilities import ProviderBinding
    from stratbox.base.filestore import MutationRejected
    from stratbox.execution import ExecutionContext
    from stratbox.macrobanks.frg.api import APPLY, STREAM_ARCHIVE

    inp, _, plan, _, outputs = _setup(tmp_path)

    class Owner(LocalFileStore):
        allowed_plan = None
        calls = []

        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                class Scoped:
                    stream = stage.stream

                    def commit_admitted(self, intent):
                        Owner.calls.append(intent)
                        if intent.plan_identity != Owner.allowed_plan or intent.destination != "admitted.zip":
                            raise MutationRejected("Current grant excludes this effect")
                        self.stream.seek(0)
                        assert sha256(self.stream.read()).hexdigest() == intent.content.sha256
                        return stage.commit(intent.mode, intent.expected_revision)

                yield Scoped()

        def commit_mutation(self, intent, data):
            self.calls.append(intent)
            if intent.plan_identity != self.allowed_plan or intent.kind != "remove":
                raise MutationRejected("Current grant excludes this effect")
            assert data is None
            return self.remove_expected(intent.source)

    output = Owner(str(outputs))
    context = ExecutionContext(profile="managed", bindings=(
        ProviderBinding("input", STREAM_ARCHIVE.capability("filestore", managed=True), "ready", inp, "input"),
        ProviderBinding("output", STREAM_ARCHIVE.capability("output_filestore", managed=True), "ready", output, "output"),
    ))
    request = frg.StreamArchiveRequest(plan, "admitted.zip")
    denied = frg.prepare_archive_to_store(request, store=inp, output_store=output, context=context)
    assert denied.diagnostics[0].code == "effect.rejected" and not list(outputs.iterdir())
    Owner.allowed_plan = plan.identity
    accepted = frg.prepare_archive_to_store(request, store=inp, output_store=output, context=context)
    assert accepted.outcome == "succeeded" and accepted.value.storage.observed_identity == accepted.value.identity
    assert [call.effect_id for call in output.calls] == [accepted.value.effect_id] * 2

    owner = Owner(str(tmp_path / "inputs"))
    deletion = frg.plan_cleanup(frg.PlanCleanupRequest(".", delete_others=True), store=owner).value
    removed = next(action for action in deletion.actions if action.kind == "remove")
    Owner.allowed_plan = None
    context = ExecutionContext(profile="managed", bindings=(
        ProviderBinding("input", APPLY.capability("filestore", managed=True), "ready", owner, "input"),
    ))
    attempt = frg.apply_cleanup(frg.ApplyCleanupRequest(deletion, ".", deletion.identity.sha256),
                                store=owner, context=context)
    assert attempt.diagnostics[0].code == "effect.rejected"
    assert inp.exists(removed.source.path)
    assert owner.calls[-1].plan_identity == deletion.identity
    assert owner.calls[-1].source == removed.source
    Owner.allowed_plan = deletion.identity
    accepted = frg.apply_cleanup(frg.ApplyCleanupRequest(deletion, ".", deletion.identity.sha256),
                                 store=owner, context=context)
    assert accepted.outcome == "succeeded" and not inp.exists(removed.source.path)


def test_directory_and_planning_budget_stop_before_archive_stage(tmp_path):
    from stratbox.base.limits import ExecutionBudget
    from stratbox.execution import ExecutionContext

    inp, out, plan, _, outputs = _setup(tmp_path)
    request = frg.StreamArchiveRequest(plan, "result.zip")
    for cap, reason in (
        (ExecutionBudget(objects=1), "budget.objects"),
        (ExecutionBudget(input_bytes=1), "budget.input_bytes"),
    ):
        result = frg.prepare_archive_to_store(request, store=inp, output_store=out,
                                              context=ExecutionContext(budget=cap))
        assert result.diagnostics[0].code == reason
        assert not result.effects and not list(outputs.iterdir())
