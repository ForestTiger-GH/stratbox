"""The standard refresh purpose acquires delivered files through the filestore."""
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.frank_rg.domain import DOMAIN
from stratbox.domains.frank_rg.methods.tables import CellRule, TableRules
from stratbox.sdk import StrategyBox
from stratbox.shared.identity import ByteIdentity

from .names import SUPPLIER_NAMES


class DeliveredFiles(LocalFileStore):
    def __init__(self, root):
        super().__init__(root)
        self.reads = []

    def open(self, location, mode="rb"):
        self.reads.append(str(location))
        return super().open(location, mode)


class ForbiddenHTTP:
    def fetch(self, request):
        raise AssertionError("Delivered files must be read through the selected filestore")


def test_standard_refresh_lists_selects_reads_and_interprets_delivered_original(tmp_path):
    source = "frg.express.issuance"
    filename = next(name for identifier, name in SUPPLIER_NAMES if identifier == source)
    book = Workbook()
    book.active.title = "Synthetic supplied layout"
    book.active.append(("Subject", "Amount"))
    book.active.append(("Fixture bank", "10.1234567890123456789012345"))
    stream = BytesIO()
    book.save(stream)
    book.close()
    data = stream.getvalue()
    (tmp_path / filename).write_bytes(data)
    rules = TableRules(source, (CellRule("Synthetic supplied layout", 2, 2,
        "fixture.amount", "fixture-bank", "RUB", "stock", "2026-04-30", "monthly", "synthetic_fixture_only"),),
        original_identity=ByteIdentity.of(data))
    store = DeliveredFiles(str(tmp_path))
    with StrategyBox(domains=DomainCatalog({"frank_rg": DOMAIN}), providers={
            "filestore": store, "http": ForbiddenHTTP()}) as box:
        result = box.invoke("scenario.series.refresh", inputs={"location": "."},
            parameters={"table_rules": rules}, target=source, timeout=10)
        assert result.outcome == "succeeded", result.diagnostics
        dataset = result.output("dataset")
        row, = dataset.rows
        assert row["value"] == Decimal("10.1234567890123456789012345")
        assert row["period"] == "2026-04-30" and dataset.issue_id == "2026-05-01"
        assert dataset.source_uses[0].coordinate.material_identity == ByteIdentity.of(data)
        assert filename in store.reads
        assert (tmp_path / filename).read_bytes() == data
