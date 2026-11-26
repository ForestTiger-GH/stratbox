"""A retained representation preserves the qualification of selected facts."""
from datetime import datetime, timezone
import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.core.observability.projections.source_state import SourceStateIndex
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import (ProcessingGoal, ProcessingRequirement, ProcessingPolicy,
    ReferenceAvailability, retained_reference_identity)
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import Assessment, SourceDataset


def test_partial_product_retention_requires_explicit_partial_acceptance(tmp_path):
    journal = MemoryJournal()
    partial = Assessment("partial", ("source.expected_issue_missing",))
    dataset = SourceDataset("test", ({"period": "2026-01-01", "metric": "m", "value": 1},),
        issue_id="2026-01-01", assessment=partial,
        source_uses=(SourceUse(SourceCoordinate("test", issue_id="2026-01-01", asset_id="main")),))
    with SQLiteSourceState(tmp_path / "state.sqlite") as state:
        providers = {"filestore": LocalFileStore(str(tmp_path / "objects")), "source_state": state}
        with StrategyBox(domains=DomainCatalog({}), journal=journal, providers=providers) as box:
            result = box.invoke("operation.product.publish", inputs={"dataset": dataset, "destination": "products"},
                parameters={"format": "csv"})
            assert result.outcome == "succeeded", result.diagnostics
            assert not result.output("product").assessment.complete
            assert not result.output("reference").assessment.complete
            SourceStateIndex(state).advance(journal)
            lookup = box.invoke("command.source.state.read", inputs={"keys": ("test",), "stream_id": journal.stream_id})
            assert lookup.outcome == "succeeded", lookup.diagnostics
            snapshot = lookup.output("state")
            output = next(value for value in snapshot.outputs if value.stage == "representation"
                and value.capability_id == "command.product.render")
            assert output.persistent and not output.assessment.complete
            now = datetime.now(timezone.utc)
            policy = ProcessingPolicy(availability=(ReferenceAvailability(
                retained_reference_identity(output.retained_reference), now, "available"),))
            def assess(allow_partial):
                checked = box.invoke("command.processing.assess", inputs={
                    "goal": ProcessingGoal(output.key, (ProcessingRequirement("representation", output.basis_identity,
                        allow_partial=allow_partial),)), "state": snapshot, "policy": policy, "evaluation_time": now})
                assert checked.outcome == "succeeded", checked.diagnostics
                return checked.output("assessment")
            assert not assess(False).no_work
            assert assess(True).no_work


@pytest.mark.parametrize('parent_status',('complete','partial'))
def test_generic_view_filter_uses_the_same_selected_scope_contract(parent_status):
    dataset = SourceDataset('test',(
        {'period':'2026-01-01','metric':'m','value':1},
        {'period':'2026-01-01','metric':'other','value':2}),
        assessment=Assessment(parent_status))
    with StrategyBox(domains=DomainCatalog({})) as box:
        with box.invoke('command.view.prepare',inputs={'dataset':dataset},
                parameters={'filters':{'metric':'m'}}) as prepared:
            assert prepared.outcome == 'succeeded',prepared.diagnostics
            view = prepared.output('view')
            assert len(view.value.rows) == 1
            assert view.assessment.complete == (parent_status == 'complete')
            assert view.assessment.coverage is not None
            with box.invoke('command.product.render',inputs={'view':view}) as rendered:
                assert rendered.outcome == 'succeeded',rendered.diagnostics
                assert rendered.output('product').assessment == view.assessment
