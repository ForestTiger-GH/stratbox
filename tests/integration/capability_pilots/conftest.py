from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from threading import Lock

import pytest

from stratbox.capabilities.catalog import CatalogContribution, ProfileDefinition
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


def workbook(sheets):
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    book.close()
    return SourcePayload(buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def row_profile(sheet="Debt", dataset="fixture.debt", **overrides):
    return {"sheet": sheet, "dataset_id": dataset, "release_id": "2026-10-01",
        "subject_column": 0, "value_column": 1, "header_rows": 1,
        "metric_id": dataset, "unit": "RUB", "quantity_kind": "stock",
        "period_kind": "as_of", "as_of": "2026-10-01", "perimeter": "banking",
        "expected_headers": {"0": "Region", "1": "Value"}, **overrides}


@pytest.fixture
def two_tables():
    return workbook({"Debt": (("Region", "Value"), ("Region-A", 10), ("Region-B", 20)),
        "Total": (("Region", "Value"), ("Region-A", 100), ("Region-B", 400))})


@pytest.fixture
def profiled_catalog():
    return catalog_snapshot().overlay(CatalogContribution(profiles=(
        ProfileDefinition("fixture.debt", row_profile(), method_id="extract.rows"),
        ProfileDefinition("fixture.total", row_profile("Total", "fixture.total"), method_id="extract.rows"),
        ProfileDefinition("fixture.budget", {"table_profile": "minfin.budget_table", "sheet": "Budget",
            "dataset_id": "minfin.fedbud.annex3.monthly", "release_id": "2026-02-28", "header_row": 0},
            method_id="extract.minfin_budget", group_id="minfin.budget.columns"),
    )))


class FixtureHttp:
    """A deterministic streaming provider; every URL owns separate bytes."""
    accounts_http_budget = True
    def __init__(self, content):
        self.content = content
        self.calls = Counter()
        self.lock = Lock()

    def exchange_into(self, request, sink, *, cancelled=None):
        with self.lock:
            self.calls[request.url] += 1
        payload = self.content[request.url]
        if not isinstance(payload, SourcePayload):
            payload = SourcePayload(payload, "text/html")
        request.budget.charge("requests", 1)
        request.budget.charge("wire_bytes", len(payload.data))
        request.budget.charge("decoded_bytes", len(payload.data))
        for start in range(0, len(payload.data), 97):
            assert cancelled is None or not cancelled()
            sink.write(payload.data[start:start + 97])
        response = HttpResponse(200, b"", {"content-type": payload.media_type},
            datetime.now(timezone.utc), "https://" + request.url.split("/")[2])
        return HttpStreamResponse(response, ByteIdentity.of(payload.data))
