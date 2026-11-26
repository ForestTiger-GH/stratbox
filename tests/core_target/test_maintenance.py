"""Explicit maintenance preserves changed sources and conflicting destinations."""
from contextlib import contextmanager
from pathlib import Path

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.identity import ByteIdentity


def planned(box, actions):
    inventory = box.invoke("command.material.list", inputs={"location": "."})
    assert inventory.outcome == "succeeded", inventory.diagnostics
    result = box.invoke("command.material.maintenance_plan",
        inputs={"inventory": inventory.output("inventory")},
        parameters={"actions": tuple(actions), "scope": "."})
    assert result.outcome == "succeeded", result.diagnostics
    return result.output("plan")


def move(source, destination, data):
    return {"source": source, "operation": "move", "destination": destination,
        "expected_identity": ByteIdentity.of(data)}


def apply(box, plan):
    return box.invoke("command.material.maintenance_apply", inputs={"plan": plan},
        parameters={"scope": "."})


def test_conflicting_destination_is_preserved_and_source_is_not_removed(tmp_path):
    source, destination = tmp_path / "source.xlsx", tmp_path / "destination.xlsx"
    source.write_bytes(b"selected exact original")
    destination.write_bytes(b"different retained original")
    with StrategyBox(providers={"filestore": LocalFileStore(str(tmp_path))}) as box:
        plan = planned(box, (move(source.name, destination.name, source.read_bytes()),))
        result = apply(box, plan)
        assert result.outcome == "failed", result.diagnostics
        assert source.read_bytes() == b"selected exact original"
        assert destination.read_bytes() == b"different retained original"


def test_source_changed_after_planning_is_preserved_without_destination_write(tmp_path):
    source, destination = tmp_path / "source.xlsx", tmp_path / "destination.xlsx"
    source.write_bytes(b"observed during planning")
    with StrategyBox(providers={"filestore": LocalFileStore(str(tmp_path))}) as box:
        plan = planned(box, (move(source.name, destination.name, source.read_bytes()),))
        source.write_bytes(b"changed after planning")
        result = apply(box, plan)
        assert result.outcome == "failed", result.diagnostics
        assert source.read_bytes() == b"changed after planning"
        assert not destination.exists()


def test_conflicting_move_prevents_subsequent_cleanup_actions(tmp_path):
    source, destination, older = (tmp_path / name for name in ("selected.xlsx", "canonical.xlsx", "older.xlsx"))
    source.write_bytes(b"selected original")
    destination.write_bytes(b"existing canonical original")
    older.write_bytes(b"older retained original")
    with StrategyBox(providers={"filestore": LocalFileStore(str(tmp_path))}) as box:
        plan = planned(box, ({**move(source.name, destination.name, source.read_bytes()), "action_id": "canonical"},
            {"source": older.name, "operation": "delete", "expected_identity": ByteIdentity.of(older.read_bytes()),
             "depends_on": ("canonical",)}))
        result = apply(box, plan)
        assert result.outcome == "failed", result.diagnostics
        assert source.read_bytes() == b"selected original"
        assert destination.read_bytes() == b"existing canonical original"
        assert older.read_bytes() == b"older retained original"


def copy(source, destination, data, **options):
    return {"source": source, "operation": "copy", "destination": destination,
            "expected_identity": ByteIdentity.of(data), **options}


def test_copy_uses_bounded_named_writer_and_keeps_the_original(tmp_path):
    class BoundedCopy(LocalFileStore):
        def read_bytes(self, path):
            raise AssertionError("A full-file read was used")

        @contextmanager
        def stage_write(self, path):
            with super().stage_write(path) as stage:
                class Writer:
                    def write(self, data):
                        assert len(data) <= 1024 * 1024
                        return stage.stream.write(data)
                class Output:
                    stream = Writer()
                    def commit(self, mode, revision):
                        return stage.commit(mode, revision)
                yield Output()

    data = b"selected exact original\n" * 100000
    (tmp_path / "source.bin").write_bytes(data)
    with StrategyBox(providers={"filestore": BoundedCopy(tmp_path)}) as box:
        plan = planned(box, (copy("source.bin", "exports/copy.bin", data, action_id="publish"),))
        assert plan[0]["policy"] == "create_only" and plan[0]["depends_on"] == ()
        assert plan[0]["expected_destination"] is None and plan[0]["scope"] == "."
        result = apply(box, plan)
        assert result.outcome == "succeeded", result.diagnostics
        receipt, = result.output("receipts")
        assert receipt.intent.operation == "copy" and receipt.intent.expected_source == ByteIdentity.of(data)
        assert receipt.intent.expected_source_revision and receipt.status == "confirmed"
        assert receipt.intent.source_provider_scope and receipt.value.guarantee == "atomic_create"
        assert result.output("outcomes")[0]["effect_id"] == receipt.effect_id
    assert (tmp_path / "source.bin").read_bytes() == data
    assert (tmp_path / "exports/copy.bin").read_bytes() == data


@pytest.mark.parametrize("policy,changed", [("create_only", False), ("replace_if_matches", False), ("replace_if_matches", True)])
def test_copy_destination_policy_and_exact_precondition_are_frozen(tmp_path, policy, changed):
    (tmp_path / "source.bin").write_bytes(b"new exact original")
    destination = tmp_path / "canonical.bin"
    destination.write_bytes(b"previous original")
    action = copy("source.bin", destination.name, b"new exact original", policy=policy,
        **({"expected_destination": ByteIdentity.of(b"previous original")} if policy == "replace_if_matches" else {}))
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        plan = planned(box, (action,))
        action["policy"] = "unrelated caller mutation"
        if changed:
            destination.write_bytes(b"intervening original")
        result = apply(box, plan)
        successful = policy == "replace_if_matches" and not changed
        assert result.outcome == ("succeeded" if successful else "failed"), result.diagnostics
        receipt, = result.output("receipts")
        assert receipt.status == ("confirmed" if successful else "rejected")
        assert plan[0]["policy"] == policy
        if successful:
            assert receipt.intent.expected_destination_revision
            assert destination.read_bytes() == b"new exact original"
        else:
            assert destination.read_bytes() == (b"intervening original" if changed else b"previous original")
        assert (tmp_path / "source.bin").read_bytes() == b"new exact original"


def test_changed_copy_source_is_rejected_before_destination_mutation(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"observed source")
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        plan = planned(box, (copy(source.name, "output.bin", b"observed source"),))
        source.write_bytes(b"later source")
        result = apply(box, plan)
        assert result.outcome == "failed", result.diagnostics
        assert result.output("outcomes")[0]["effect_state"] == "rejected"
        assert not (tmp_path / "output.bin").exists()
        assert source.read_bytes() == b"later source"


def test_rejected_action_blocks_only_explicit_dependants(tmp_path):
    for name, body in (("selected", b"selected"), ("canonical", b"conflict"), ("independent", b"independent")):
        (tmp_path / name).write_bytes(body)
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        plan = planned(box, (
            copy("selected", "canonical", b"selected", action_id="publish"),
            {"source": "selected", "operation": "delete", "expected_identity": ByteIdentity.of(b"selected"),
             "action_id": "cleanup", "depends_on": ("publish",)},
            copy("independent", "independent-copy", b"independent", action_id="other"),
        ))
        result = apply(box, plan)
        assert result.outcome == "partial", result.diagnostics
        outcomes = result.output("outcomes")
        assert [item["outcome"] for item in outcomes] == ["failed", "blocked", "succeeded"]
        assert outcomes[1]["blocked_by"] == ("publish",) and outcomes[1]["effect_id"] is None
        assert [item.status for item in result.output("receipts")] == ["rejected", "confirmed"]
        assert "storage.destination_conflict" in result.diagnostics
    assert (tmp_path / "selected").read_bytes() == b"selected"
    assert (tmp_path / "canonical").read_bytes() == b"conflict"
    assert (tmp_path / "independent-copy").read_bytes() == b"independent"


@pytest.mark.parametrize("invalid", [
    {"action_id": "first"},
    {"action_id": "second", "depends_on": ("later",)},
    {"action_id": "second", "depends_on": ("second",)},
    {"action_id": "second", "destination": "../outside"},
])
def test_invalid_plan_is_rejected_before_any_effect(tmp_path, invalid):
    (tmp_path / "source").write_bytes(b"original")
    actions = (copy("source", "first-copy", b"original", action_id="first"),
        {**copy("source", "second-copy", b"original"), **invalid})
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        result = apply(box, actions)
        assert result.outcome == "failed" and not result.effects
    assert not (tmp_path / "first-copy").exists() and not (tmp_path / "second-copy").exists()
    assert (tmp_path / "source").read_bytes() == b"original"


def test_unknown_copy_preserves_reports_and_resumes_dependencies_after_cold_reconciliation(tmp_path):
    class LostAcknowledgement(LocalFileStore):
        @contextmanager
        def stage_write(self, path):
            with super().stage_write(path) as stage:
                if Path(path).name != "published":
                    yield stage
                    return
                class Output:
                    stream = stage.stream
                    def commit(self, mode, revision):
                        stage.commit(mode, revision)
                        raise OSError("Named copy committed; acknowledgement lost")
                yield Output()

    files, effects = tmp_path / "files", tmp_path / "effects"
    files.mkdir()
    (files / "selected").write_bytes(b"selected")
    (files / "independent").write_bytes(b"independent")
    with StrategyBox(providers={"filestore": LostAcknowledgement(files), "effect_state": FileEffectState(effects)}) as box:
        plan = planned(box, (
            copy("selected", "published", b"selected", action_id="publish"),
            {"source": "selected", "operation": "delete", "expected_identity": ByteIdentity.of(b"selected"),
             "action_id": "cleanup", "depends_on": ("publish",)},
            copy("independent", "other-copy", b"independent", action_id="other"),
        ))
        result = apply(box, plan)
        assert result.outcome == "unknown", result.diagnostics
        outcomes = result.output("outcomes")
        assert [item["outcome"] for item in outcomes] == ["unknown", "blocked", "succeeded"]
        assert len(result.output("receipts")) == 2 and len(result.effects) == 2
        effect_id = outcomes[0]["effect_id"]
        assert (files / "selected").read_bytes() == b"selected"
        assert (files / "published").read_bytes() == b"selected"

    class NoRecopy(LocalFileStore):
        def stage_write(self, path):
            if Path(path).name in {"published", "other-copy"}:
                raise AssertionError("Confirmed copies must not be replayed")
            return super().stage_write(path)

    with StrategyBox(providers={"filestore": NoRecopy(files), "effect_state": FileEffectState(effects)}) as box:
        previous = box.session.lookup_effect(effect_id)
        assert previous.status == "unknown" and previous.intent.source == "selected"
        assert previous.intent.expected_source_revision and previous.intent.expected_destination is None
        reconciled = box.invoke("command.artifact.reconcile", inputs={"effect": previous})
        assert reconciled.outcome == "succeeded" and reconciled.output("assessment").complete
        resumed = apply(box, plan)
        assert resumed.outcome == "succeeded", resumed.diagnostics
        assert [item["outcome"] for item in resumed.output("outcomes")] == ["succeeded"] * 3
        assert resumed.output("outcomes")[0]["effect_id"] == effect_id
    assert not (files / "selected").exists()
    assert (files / "published").read_bytes() == b"selected"
    assert (files / "independent").read_bytes() == b"independent"
    assert (files / "other-copy").read_bytes() == b"independent"
