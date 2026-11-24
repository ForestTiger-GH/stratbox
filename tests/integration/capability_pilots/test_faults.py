"""P11 faults across shared commands, semantic scopes and physical commits."""
from dataclasses import replace
from threading import Event

from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
from stratbox.capabilities.commands import MATERIAL_INPUT, OBSERVATIONS
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.representation import Representation
from stratbox.sdk import StrategyBox
from .conftest import row_profile


def test_shared_consumer_cancel_preserves_other_extraction(profiled_catalog, two_tables, monkeypatch):
    import stratbox.core.capabilities.workbooks as codec
    entered, release = Event(), Event()
    original, decodes = codec.read_workbook_cells, []
    def decode(*args, **options):
        decodes.append(1)
        entered.set()
        assert release.wait(5)
        return original(*args, **options)
    monkeypatch.setattr(codec, "read_workbook_cells", decode)
    definition = ScenarioDefinition("fixture.independent", GraphBody((
        Call("debt", "extract.observations", {"material": InputRef("material")}, profile_id="fixture.debt"),
        Call("total", "extract.observations", {"material": InputRef("material")}, profile_id="fixture.total"),
    ), {"debt": OutputRef("debt", "observations"), "total": OutputRef("total", "observations")}),
        inputs={"material": MATERIAL_INPUT}, outputs={"debt": OBSERVATIONS, "total": OBSERVATIONS})
    with StrategyBox(capabilities=profiled_catalog, settings=ExecutionSettings(max_workers=1)) as box:
        handle = box.submit(box.prepare(definition, inputs={"material": two_tables}))
        assert entered.wait(5)
        try:
            assert handle.cancel("fixture.independent/debt")
        finally:
            release.set()
        result = handle.result(10)
        assert result.scopes["fixture.independent/total"] == "succeeded", result.scopes
        assert [o.value for o in result.output("total").observations] == [100, 400]
        assert "debt" not in result.outputs
        assert decodes == [1]


def test_optional_observer_failure_preserves_business_and_control(profiled_catalog, two_tables):
    failed = Event()
    def observer(record):
        failed.set()
        raise RuntimeError("fixture collector unavailable")
    with StrategyBox(capabilities=profiled_catalog, observer=observer,
                     settings=ExecutionSettings(max_workers=1, event_capacity=1)) as box:
        result = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.debt", timeout=10)
        assert failed.wait(5)
        assert result.outcome == "succeeded"
        assert [row.value for row in result.output("observations").observations] == [10, 20]
        health = box.session.journal.health_snapshot()
        assert health.coverage == "incomplete"
        assert health.observer_failed >= 1
        assert not box.session.ledger.snapshot().occupied.get("workers", 0)


def test_lost_save_reply_reconciles_without_reextract(profiled_catalog, two_tables, tmp_path, monkeypatch):
    import stratbox.core.capabilities.workbooks as codec
    original, decodes = codec.read_workbook_cells, []
    def decode(*args, **options):
        decodes.append(1)
        return original(*args, **options)
    monkeypatch.setattr(codec, "read_workbook_cells", decode)
    class LostReplyStore(LocalFileStore):
        writes = 0
        def create_if_absent(self, path, data):
            self.writes += 1
            super().create_if_absent(path, data)
            raise TimeoutError("commit reply lost")
    store = LostReplyStore(str(tmp_path))
    with StrategyBox(capabilities=profiled_catalog, providers={"output_filestore": store}) as box:
        result = box.invoke("scenario.observation_ratio", inputs={"numerator": two_tables, "denominator": two_tables},
            parameters={"numerator_profile": row_profile(), "denominator_profile": row_profile("Total", "fixture.total"),
                        "destination": "ratio.csv"}, timeout=15)
        assert result.outcome == "unknown", result.scopes
        assert (tmp_path / "ratio.csv").exists()
        representation = result.output("representation")
        assert result.output("view").batch.observations[0].value_status == "derived"
        effects = box.session.effects.snapshot()
        record = next(record for record in effects if record.intent.kind == "storage.write")
        assert record.receipt.state == "unknown" and record.intent.effect_id
        blocked = box.invoke("save.product", inputs={"material": representation},
            parameters={"destination": "ratio.csv"}, timeout=10)
        assert blocked.outcome == "unknown"
        assert store.writes == 1
        confirmed = EffectReceipt("storage.write", "confirmed", reference="ratio.csv",
            effect_id=record.intent.effect_id, identity=representation.identity,
            guarantee="atomic_create", stage="verify", reconciliation_owner="output_filestore")
        box.session.effects.reconcile(record.intent.run_id, record.intent.scope_id,
            record.intent.effect_id, confirmed, expected_revision=record.revision)
        recovered = box.invoke("save.product", inputs={"material": representation},
            parameters={"destination": "ratio.csv"}, timeout=10)
        assert recovered.outcome == "succeeded", recovered.diagnostics
        assert recovered.output("receipt").status == "already_present"
        assert store.writes == 1 and decodes == [1]


def test_stale_save_completion_keeps_new_revision_current(profiled_catalog, tmp_path):
    entered, release = Event(), Event()
    class DelayedStore(LocalFileStore):
        def replace_if_revision(self, path, data, expected_revision):
            if data == b"old\n":
                entered.set()
                assert release.wait(5)
            return super().replace_if_revision(path, data, expected_revision)
    store = DelayedStore(str(tmp_path))
    store.create_if_absent("report.csv", b"baseline\n")
    revision = store.current_revision("report.csv")
    old = Representation("fixture.old", 1, "text/csv", b"old\n", "utf-8")
    new = Representation("fixture.new", 1, "text/csv", b"new\n", "utf-8")
    with StrategyBox(capabilities=profiled_catalog, providers={"output_filestore": store},
                     settings=ExecutionSettings(max_workers=2, active_runs=2)) as box:
        parameters = {"destination": "report.csv", "mode": "replace_expected_revision", "expected_revision": revision}
        earlier = box.submit(box.prepare("save.product", inputs={"material": old}, parameters={**parameters, "source_revision": "1"}))
        assert entered.wait(5)
        try:
            later = box.invoke("save.product", inputs={"material": new}, parameters={**parameters, "source_revision": "2"}, timeout=10)
            assert later.outcome == "succeeded"
        finally:
            release.set()
        stale = earlier.result(10)
        assert stale.outcome == "failed"
        assert store.read_bytes("report.csv") == b"new\n"
        records = box.session.effects.snapshot()
        assert next(r for r in records if r.intent.source_revision == "2").current
        assert not next(r for r in records if r.intent.source_revision == "1").current
