"""Explicit maintenance preserves changed sources and conflicting destinations."""
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
        plan = planned(box, (move(source.name, destination.name, source.read_bytes()),
            {"source": older.name, "operation": "delete", "expected_identity": ByteIdentity.of(older.read_bytes())}))
        result = apply(box, plan)
        assert result.outcome == "failed", result.diagnostics
        assert source.read_bytes() == b"selected original"
        assert destination.read_bytes() == b"existing canonical original"
        assert older.read_bytes() == b"older retained original"
