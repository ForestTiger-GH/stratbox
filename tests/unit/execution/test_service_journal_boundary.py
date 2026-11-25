"""Notification service suppression follows real effect semantics and scope."""
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import CommandDefinition, PortContract, ReuseContract
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract


def handoff(request, invocation):
    invocation.effect(EffectReceipt("notification.handoff", "confirmed", effect_id="handoff"))
    return 1


def mixed(request, invocation):
    invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="saved"))
    invocation.effect(EffectReceipt("notification.handoff", "confirmed", effect_id="handoff"))
    return 1


def records(box, run_id):
    return [entry.record for entry in box.session.journal.facts_source._entries.values()
            if entry.record.correlation.run_id == run_id]


def test_custom_id_pure_notification_is_suppressed_but_mixed_saved_work_is_published():
    port = PortContract(DataContract("service.control"), int)
    pure_effects = frozenset({"notification.handoff"})
    mixed_effects = pure_effects | {"storage.write"}
    pure = CommandDefinition("custom.transfer", __name__ + ":handoff", outputs={"value": port}, effects=pure_effects,
        reuse=ReuseContract(shareable=False, effects=pure_effects))
    business = CommandDefinition("custom.business", __name__ + ":mixed", outputs={"value": port}, effects=mixed_effects,
        reuse=ReuseContract(shareable=False, effects=mixed_effects))
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(pure, business))) as box:
        service = box.invoke(pure.capability_id)
        assert service.outcome == "succeeded"
        assert records(box, service.run_id) == []
        terminal = next(record for record in box.session.journal.records
            if record.kind == "run.finished" and record.correlation.run_id == service.run_id)
        assert terminal.payload["service"] is True
        result = box.invoke(business.capability_id)
        assert result.outcome == "succeeded"
        facts = records(box, result.run_id)
        assert {record.kind for record in facts} == {"value.accepted", "capability.finished", "effect.confirmed"}
        assert all(record.payload["capability_id"] == business.capability_id for record in facts)
        assert all(record.payload["capability_kind"] == "command" for record in facts)
        assert all(record.payload["scope_id"] == business.capability_id for record in facts)
        assert [record.payload["effect_id"] for record in facts if record.kind == "effect.confirmed"] == ["saved"]
        service.close(); result.close()
