"""Complete byte paths and recoverable named effects use one effect authority."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt, StagedMaterialRef
from stratbox.shared.data.values import Assessment, Material, SourceDataset
from stratbox.shared.identity import ByteIdentity


def output(result, name):
    assert result.outcome == "succeeded", result.diagnostics
    return result.output(name)


def test_existing_exact_named_postcondition_needs_no_new_temporary_copy(tmp_path):
    from stratbox.core.limits import ExecutionBudget
    body = b'existing exact output'
    (tmp_path/'named.csv').write_bytes(body)
    class ReadOnlyExistingDestination(LocalFileStore):
        def stage_write(self, path):
            raise AssertionError('An existing exact named output must not be recopied')
    with StrategyBox(providers={'filestore':ReadOnlyExistingDestination(str(tmp_path))},
            settings=ExecutionSettings(run_limits=ExecutionBudget(temporary_bytes=0))) as box:
        with box.invoke('command.artifact.materialize',inputs={
                'material':Material(body),'destination':'named.csv'}) as delivered:
            receipt = output(delivered,'receipt')
            assert receipt.status == 'confirmed'
            assert receipt.value.guarantee == 'verified_existing_postcondition'
            assert delivered.resources.get('temporary_bytes',0) == 0


class BoundedFile:
    def __init__(self, stream):
        self.stream = stream

    def read(self, size=-1):
        if size < 0:
            position = self.stream.tell()
            size = self.stream.seek(0, 2) - position
            self.stream.seek(position)
        assert 0 <= size <= 1024 * 1024, "Whole-file read crossed the provider boundary"
        return self.stream.read(size)

    def write(self, data):
        assert len(data) <= 1024 * 1024, "Whole-file write crossed the provider boundary"
        return self.stream.write(data)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()


class StreamingOnlyStore(LocalFileStore):
    def open_read(self, path):
        return BoundedFile(super().open_read(path))

    def read_bytes(self, path):
        raise AssertionError("A buffered storage path was used")

    def create_immutable(self, path, data):
        raise AssertionError("A buffered storage path was used")

    @contextmanager
    def stage_content(self, directory):
        with super().stage_content(directory) as stage:
            class Bounded:
                stream = BoundedFile(stage.stream)
                def location(self, identity):
                    return stage.location(identity)
                def commit(self, identity, **kwargs):
                    return stage.commit(identity, **kwargs)
            yield Bounded()


def test_read_pack_commit_release_and_reconcile_remain_bounded(tmp_path):
    # The payload exceeds the entire service's retained-RAM allowance.
    data = b"complete source\n" * 200000
    path = tmp_path / "original.bin"
    path.write_bytes(data)
    store = StreamingOnlyStore(tmp_path)
    with StrategyBox(providers={"filestore": store}, settings=ExecutionSettings(max_retained_bytes=256 * 1024)) as box:
        acquired = box.invoke("command.material.read", inputs={"location": {
            "path": "original.bin", "identity": ByteIdentity.of(data)}}, parameters={"placement": "staged"})
        source = output(acquired, "material")
        assert isinstance(source, StagedMaterialRef)
        packed = box.invoke("command.archive.pack", inputs={"members": (source,)},
            parameters={"placement": "staged", "compression": "stored", "names": ("original.bin",)})
        archive = output(packed, "material")
        retained = box.invoke("command.artifact.commit", inputs={"material": archive, "destination": "objects"})
        reference = output(retained, "reference")
        assert reference.identity.size > len(data)
        assembled = box.invoke("command.release.assemble", inputs={"members": (reference,)})
        output(assembled, "manifest")
        reconciled = box.invoke("command.artifact.reconcile", inputs={"effect": retained.output("receipt")})
        assert output(reconciled, "assessment").complete
        compact = replace(reference, lineage=(), source_uses=(), metadata={})
        inspected = box.invoke("command.archive.inspect", inputs={"material": compact})
        assert output(inspected, "inventory").parent_identity == reference.identity
        forged = replace(reference, lineage=(*reference.lineage, "invented-derivation"))
        rejected = box.invoke("command.release.assemble", inputs={"members": (forged,)})
        assert rejected.outcome == "failed" and "release.logical_lineage_conflict" in rejected.diagnostics


def test_named_create_and_compare_replace_preserve_conflicting_destinations(tmp_path):
    store = LocalFileStore(tmp_path)
    target = tmp_path / "report.csv"
    target.write_bytes(b"old original")
    with StrategyBox(providers={"filestore": store}) as box:
        rejected = box.invoke("command.artifact.materialize", inputs={"material": Material(b"new"), "destination": target.name})
        assert rejected.outcome == "failed" and target.read_bytes() == b"old original"
        delivered = box.invoke("command.artifact.materialize", inputs={"material": Material(b"new"),
            "destination": target.name, "expected_destination": ByteIdentity.of(b"old original")},
            parameters={"policy": "replace_if_matches", "delivery_id": "report-one"})
        receipt = output(delivered, "receipt")
        assert isinstance(receipt.value, NamedMaterialReceipt)
        assert receipt.value.guarantee == "compare_and_replace_under_directory_guard"
        assert receipt.intent.expected_destination_revision
        assert target.read_bytes() == b"new"
        stale = box.invoke("command.artifact.materialize", inputs={"material": Material(b"other"),
            "destination": target.name, "expected_destination": ByteIdentity.of(b"old original")},
            parameters={"policy": "replace_if_matches"})
        assert stale.outcome == "failed" and target.read_bytes() == b"new"


class LostNamedAcknowledgement(LocalFileStore):
    @contextmanager
    def stage_write(self, path):
        with super().stage_write(path) as stage:
            if Path(path).name != "report.zip":
                yield stage
                return
            class Lost:
                stream = stage.stream
                def commit(self, mode, revision):
                    stage.commit(mode, revision)
                    raise OSError("Named delivery completed; acknowledgement lost")
            yield Lost()


def lost_named_write(tmp_path, *, ancestor=True):
    files, state = tmp_path / "files", tmp_path / "effects"
    with StrategyBox(providers={"filestore": LostNamedAcknowledgement(files), "effect_state": FileEffectState(state)}) as box:
        encoded = box.invoke("command.archive.pack", inputs={"members": (Material(b"exact"),)},
            parameters={"placement": "staged", "names": ("data",)})
        material = output(encoded, "material")
        inputs = {"material": material, "destination": "report.zip"}
        if ancestor:
            kept = box.invoke("command.artifact.commit", inputs={"material": material, "destination": "objects"})
            inputs["retained_ancestor"] = output(kept, "reference")
        delivered = box.invoke("command.artifact.materialize", inputs=inputs,
            parameters={"delivery_id": "frozen-delivery"})
        assert delivered.outcome == "unknown", delivered.diagnostics
        receipt, = delivered.effects.values()
        assert isinstance(receipt.intent, NamedEffectIntent)
        assert not isinstance(receipt.intent.retained_ancestor, StagedMaterialRef)
        encoded.close()
        return receipt


@pytest.mark.parametrize("change", ["unchanged", "conflict", "missing"])
def test_unknown_named_write_reconciles_after_stage_lifetime_ends(tmp_path, change):
    receipt = lost_named_write(tmp_path)
    target = tmp_path / "files" / "report.zip"
    expected = target.read_bytes()
    if change == "conflict":
        target.write_bytes(b"intervening bytes")
    elif change == "missing":
        target.unlink()
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path / "files"),
                                "effect_state": FileEffectState(tmp_path / "effects")}) as box:
        assessed = box.invoke("command.artifact.reconcile", inputs={"effect": receipt})
        assert output(assessed, "assessment").complete == (change == "unchanged")
        if change == "missing":
            recovered = box.invoke("command.artifact.materialize", inputs={
                'material': receipt.intent.retained_ancestor, 'destination': receipt.intent.destination},
                parameters={'delivery_id': 'explicit-repair-occurrence'})
            repaired = output(recovered, 'receipt')
            assert repaired.effect_id != receipt.effect_id
            assert box.session.lookup_effect(receipt.effect_id).status == 'unknown'
            assert target.read_bytes() == expected
        elif change == "conflict":
            blocked = box.invoke("command.artifact.reconcile", inputs={"effect": receipt})
            assert not output(blocked, "assessment").complete
            assert target.read_bytes() == b"intervening bytes"


def test_missing_named_output_without_surviving_source_stays_unresolved(tmp_path):
    receipt = lost_named_write(tmp_path, ancestor=False)
    (tmp_path / "files" / "report.zip").unlink()
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path / "files"),
                                "effect_state": FileEffectState(tmp_path / "effects")}) as box:
        assessed = box.invoke("command.artifact.reconcile", inputs={"effect": receipt})
        assert not output(assessed, "assessment").complete
        assert not (tmp_path / "files" / "report.zip").exists()


def archive_prerequisite(box, material):
    packed = box.invoke("command.archive.pack", inputs={"members": (material,)})
    archive = output(packed, "material")
    retained = box.invoke("command.artifact.commit", inputs={"material": archive, "destination": "objects"})
    reference = output(retained, "reference")
    return {"reference": reference, "archive_members": packed.output("manifest")}


@pytest.mark.parametrize("mode", ["latest_only", "every_removed", "missing", "wrong_members", "corrupt_archive"])
def test_cleanup_requires_the_exact_requested_preservation_policy(tmp_path, mode):
    (tmp_path / "latest.dat").write_bytes(b"latest")
    older = tmp_path / "older.dat"
    older.write_bytes(b"older")
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        prerequisite = archive_prerequisite(box, Material(b"latest", metadata={"member": "latest.dat"}))
        if mode == "wrong_members":
            prerequisite = {**prerequisite, "archive_members": ({"name": "different.dat", "identity": ByteIdentity.of(b"latest")},)}
        elif mode == "corrupt_archive":
            (tmp_path / prerequisite["reference"].location).write_bytes(b"corrupt")
        plan = ({"operation": "delete", "source": "older.dat", "expected_identity": ByteIdentity.of(b"older")},)
        result = box.invoke("command.material.maintenance_apply", inputs={"plan": plan,
            "prerequisites": () if mode == "missing" else (prerequisite,)},
            parameters={"scope": ".", "require_preservation": True, "preserve_sources": mode == "every_removed"})
        if mode == "latest_only":
            receipt, = output(result, "receipts")
            assert receipt.value.operation == "delete" and not older.exists()
            assert receipt.intent.expected_source_revision
        else:
            assert result.outcome == "failed", result.diagnostics
            assert older.read_bytes() == b"older" and not result.effects
        assert (tmp_path / "latest.dat").read_bytes() == b"latest"


@pytest.mark.parametrize("operation", ["move", "delete"])
@pytest.mark.parametrize("proof_survives", [True, False])
def test_mutation_reconciliation_requires_transition_evidence_not_path_absence(tmp_path, operation, proof_survives):
    class LostTransition(LocalFileStore):
        def apply_named_mutation(self, effect_id, intent, **kwargs):
            super().apply_named_mutation(effect_id, intent, **kwargs)
            if not proof_survives:
                self._named_transition_path(effect_id, intent).unlink()
            raise OSError("Mutation complete; acknowledgement lost")
    files, state = tmp_path / "files", tmp_path / "effects"
    files.mkdir()
    source = files / "source.dat"
    source.write_bytes(b"selected original")
    action = {"source": source.name, "operation": operation, "expected_identity": ByteIdentity.of(b"selected original")}
    if operation == "move":
        action["destination"] = "moved.dat"
    with StrategyBox(providers={"filestore": LostTransition(files), "effect_state": FileEffectState(state)}) as box:
        result = box.invoke("command.material.maintenance_apply", inputs={"plan": (action,)}, parameters={"scope": "."})
        assert result.outcome == "unknown", result.diagnostics
        effect, = result.effects.values()
        assert not source.exists()
    with StrategyBox(providers={"filestore": LocalFileStore(files), "effect_state": FileEffectState(state)}) as box:
        assessed = box.invoke("command.artifact.reconcile", inputs={"effect": effect})
        assert output(assessed, "assessment").complete == proof_survives
        assert box.session.lookup_effect(effect.effect_id).status == ("confirmed" if proof_survives else "unknown")
        assert not source.exists()


def test_confirmed_named_delivery_does_not_claim_a_later_missing_path(tmp_path):
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        delivered = box.invoke("command.artifact.materialize", inputs={"material": Material(b"bytes"), "destination": "named"})
        receipt = output(delivered, "receipt")
        (tmp_path / "named").unlink()
        assessed = box.invoke("command.artifact.reconcile", inputs={"effect": receipt})
        assert not output(assessed, "assessment").complete
        assert not (tmp_path / "named").exists()


def test_retained_representation_preserves_partial_assessment_without_relabeling_physical_receipt(tmp_path):
    partial = Assessment("partial", findings=("Unresolved requested coverage",),
                         expected=("a", "b"), observed=("a",))
    dataset = SourceDataset("test.dataset", ({"value": 1},), assessment=partial)
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        with box.invoke("command.value.encode", inputs={"value": dataset}) as encoded:
            product = output(encoded, "representation")
            assert product.assessment == partial
            with box.invoke("command.artifact.commit", inputs={"material": product, "destination": "objects"}) as retained:
                reference = output(retained, "reference")
                receipt = retained.output("receipt")
                assert reference.assessment == partial and not reference.assessment.complete
                alias = replace(reference, assessment=Assessment())
                with box.invoke("command.value.decode", inputs={"representation": alias}) as decoded:
                    restored = output(decoded, "value")
                    assert restored.assessment == partial
                with box.invoke("command.release.assemble", inputs={"members": (alias,)}) as rejected:
                    assert rejected.outcome == "failed" and "release.assessment_conflict" in rejected.diagnostics
                changed = replace(product, assessment=Assessment())
                with box.invoke("command.artifact.commit", inputs={"material": changed, "destination": "objects"}) as reused:
                    assert output(reused, "reference") == reference
                    assert reused.output("receipt") == receipt
