"""Real target methods use common scopes, retained facts and separate delivery."""
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.domains.rosstat.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, WorkbookEvidence
from .fixtures import synthetic_kep2_bytes


class Delivery:
    scope_id="fixture.rosstat.notifications"
    def __init__(self):
        self.calls = 0
        self.recovered = None

    def deliver(self, intent):
        self.calls += 1
        raise OSError("Acknowledgement was lost")

    def lookup(self, effect_id):
        return self.recovered


def test_source_dataset_acceptance_precedes_notification_and_unknown_delivery_never_reparses():
    original = Material(synthetic_kep2_bytes(), source_id="rosstat.short_term_indicators", metadata={"issue_id": "2025-01"})
    physical = WorkbookEvidence(original, read_workbook_cells(original.data))
    delivery = Delivery()
    with StrategyBox(domains=DomainCatalog({"rosstat": DOMAIN}), providers={"notification": delivery}) as box:
        prepared = box.prepare("operation.series.extract_workbook", inputs={"physical": physical},
            target=SeriesTarget("rosstat.short_term_indicators"))
        assert not any(task.command.id == "command.workbook.decode" for task in prepared.tasks if getattr(task, "command", None))
        result = box.run(prepared, timeout=10)
        assert result.outcome == "succeeded", result.diagnostics
        dataset = result.output("dataset")
        facts = box.session.journal.read(run_id=result.run_id)
        accepted = tuple(fact for fact in facts if fact.kind == "output.accepted" and fact.output_name == "dataset")
        assert accepted and any(fact.kind == "scope.completed" for fact in facts)
        notification = box.invoke("command.notification.prepare",
            inputs={"page": box.session.journal.read_page(run_id=result.run_id)},
            parameters={"selector": {"run_id": result.run_id, "kind": "output.accepted",
                "output_name": "dataset", "scope_id": accepted[0].scope_id}}, timeout=10)
        intent, = notification.output("intents")
        assert intent["payload"]["run_id"] == result.run_id
        first = box.invoke("command.notification.deliver", inputs={"intent": intent}, timeout=10)
        assert first.effects[intent["id"]].status == "unknown"
        assert "receipt" not in first.outputs
        second = box.invoke("command.notification.deliver", inputs={"intent": intent}, timeout=10)
        assert second.effects[intent["id"]].status == "unknown" and delivery.calls == 1
        delivery.recovered = {"channel": "fixture", "status": "confirmed"}
        third = box.invoke("command.notification.deliver", inputs={"intent": intent}, timeout=10)
        assert third.output("receipt").status == "confirmed" and delivery.calls == 1
        assert dataset.rows == result.output("dataset").rows
        assert any(fact.kind == "effect.unknown" for fact in box.session.journal.read())
