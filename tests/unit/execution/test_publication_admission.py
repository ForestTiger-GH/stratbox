"""Publication capacity is acquired before variable-size physical effects."""
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import CommandDefinition, PortContract, ReuseContract
from stratbox.core.execution.contracts import Correlation, EffectReceipt
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.observability.journal.sources import JournalReadLimits
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract
from stratbox.shared.identity import ByteIdentity

CALLS = []


def write(request, invocation):
    for position in range(request["count"]):
        effect_id = "write." + str(position)
        def action(effect_id=effect_id):
            CALLS.append(effect_id)
            return EffectReceipt("storage.write", "confirmed", effect_id=effect_id,
                                 reference="fixture.csv", guarantee="fixture.confirmed")
        invocation.commit_effect("storage.write", effect_id, action, resource="fixture.store")
    return len(CALLS)


def snapshot():
    return CatalogSnapshot(definitions=(CommandDefinition("publication.write", __name__ + ":write",
        parameters={"count": 1}, outputs={"value": PortContract(DataContract("publication.number"), int)},
        effects=frozenset({"storage.write"}), reuse=ReuseContract(shareable=False)),))


def test_excess_receipt_is_rejected_before_second_physical_write():
    CALLS.clear()
    with StrategyBox(capabilities=snapshot(), settings=ExecutionSettings(publication_capacity=1)) as box:
        result = box.invoke("publication.write", parameters={"count": 2}, timeout=5)
        assert result.outcome == "failed"
        assert CALLS == ["write.0"]
        assert len(result.effects) == 1 and result.effects[0].state == "confirmed"
        assert any(d.code == "orchestration.publication_capacity" for value in result.results.values() for d in value.diagnostics)
        assert box.session.journal.facts_source.pending == 1
        assert box.session.ledger.snapshot().occupied["worker"] == 0
        result.close()


def test_full_fact_journal_retains_real_confirmed_write_obligation_after_result_close():
    CALLS.clear()
    with StrategyBox(capabilities=snapshot(), settings=ExecutionSettings(publication_capacity=1, event_capacity=1)) as box:
        journal = box.session.journal
        journal.accepted_value(Correlation(session_id=box.session.session_id, run_id="prior"),
            value_id="prior", stage="extract", role="extracts", identity=ByteIdentity.of(b"prior"))
        result = box.invoke("publication.write", timeout=5)
        assert result.outcome == "succeeded" and CALLS == ["write.0"]
        assert journal.health_snapshot().unpublished_transitions == 1
        result.close()
        assert journal.health_snapshot().unpublished_transitions == 1
        journal.facts_source.acknowledge(1)
        assert journal.flush_transitions() == 1
        head = journal.facts_source.head(journal.facts_stream)
        page = journal.facts_source.read_page(head.cursor(1), head=head, limits=JournalReadLimits())
        entry, = page.entries
        assert entry.record.kind == "effect.confirmed"
        assert entry.record.payload["effect_id"] == "write.0"
        assert journal.health_snapshot().unpublished_transitions == 0


def test_dynamic_slice_larger_than_total_publication_capacity_fails_without_waiting():
    from stratbox.capabilities.model import (
        AcceptanceContract, Call, GraphBody, InputRef, MapCall, OperationDefinition, OutputRef, ScenarioDefinition,
    )
    from stratbox.shared.data.processing import DataRole
    number = PortContract(DataContract("publication.extract", role=DataRole.EXTRACTS), int)
    pair = OperationDefinition("publication.pair", GraphBody((),
        {"left": InputRef("item"), "right": InputRef("item")}),
        inputs={"item": number}, outputs={"left": number, "right": number},
        acceptance=AcceptanceContract(coherent_outputs=("left", "right")))
    item = ScenarioDefinition("publication.item", GraphBody((
        Call("pair", pair.capability_id, {"item": InputRef("item")}),
    ), {"value": OutputRef("pair", "left")}), inputs={"item": number}, outputs={"value": number})
    scenario = ScenarioDefinition("publication.map", GraphBody((
        MapCall("items", item.capability_id, (1,), window=1),
    ), {"values": OutputRef("items")}),
        outputs={"values": PortContract(number.schema, collection=True)})
    catalog = CatalogSnapshot(definitions=(pair, item, scenario))
    with StrategyBox(capabilities=catalog, settings=ExecutionSettings(publication_capacity=1)) as box:
        result = box.invoke(scenario.capability_id, timeout=5)
        assert result.outcome == "failed"
        assert "orchestration.publication_unsatisfiable" in result.diagnostics
        result.close()
