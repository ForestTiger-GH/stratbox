"""An additional publication family supplies methods without central dispatch edits."""
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
import pytest
from stratbox.core.execution import OperationFailure
from stratbox.core.limits import BudgetMeter, ExecutionBudget
from stratbox.domains.fns.operations.pipeline import FamilyMethods, FamilyOperations
from stratbox.domains.fns.publications.contracts import ReleaseContext
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


@dataclass(frozen=True)
class FutureFlake:
    context: ReleaseContext
    lineage: tuple[UsedInputReceipt, ...]


class Invocation:
    def __init__(self):
        self.budget = BudgetMeter(ExecutionBudget())
        self.context = SimpleNamespace(profile="local")
        self.receipts = []
    def check_cancelled(self):
        self.budget.checkpoint()
    def use(self, receipt):
        self.receipts.append(receipt)


def test_family_methods_extend_the_source_boundary_without_a_series_dispatch_table():
    calls = []
    def extract(payload, release, *, invocation, rar_reader=None):
        calls.append(release)
        return FutureFlake(release, (UsedInputReceipt.for_payload(payload, "future_original"),))
    def unused(*args, **kwargs):
        raise AssertionError("Independent extraction cannot run a later stage")
    methods = FamilyMethods("fns.fixture", FutureFlake, 1024, extract, unused, unused,
        unused, unused, unused, unused, unused, lambda value: 0)
    operations = FamilyOperations(methods)
    context = ReleaseContext("fns.fixture", "issue-1", date(2026,11,23))
    invocation = Invocation()
    result = operations.extract(SimpleNamespace(payload=SourcePayload(b"original"), release=context), invocation)
    assert result.context == context and calls == [context]
    assert invocation.budget.used("input_bytes") == len(b"original")
    with pytest.raises(OperationFailure, match="source_family_mismatch"):
        operations.extract(SimpleNamespace(payload=SourcePayload(b"other"),
            release=ReleaseContext("fns.other", "issue-1", date(2026,11,23))), invocation)
    assert calls == [context]
