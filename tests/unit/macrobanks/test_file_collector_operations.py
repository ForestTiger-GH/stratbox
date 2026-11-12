from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook

from stratbox.base.net import HttpResponse
from stratbox.macrobanks import cbr_file_collector as collector


class ArchiveTransport:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def exchange(self, request, *, cancelled=None):
        self.calls.append(request.url)
        successful = len(self.calls) == 1
        return HttpResponse(
            200 if successful else 404,
            self.content if successful else b"not found",
            {"Content-Type": "application/octet-stream"},
            datetime(2026, 11, 11, tzinfo=timezone.utc),
            "https://www.cbr.ru",
        )


def test_collection_partial_receipt_and_repeatable_archive():
    catalog = collector.discover(collector.DiscoverFilesRequest())
    assert catalog.outcome == "succeeded" and len(catalog.value) == 41
    workbook = Workbook()
    workbook.active["A1"] = "Source"
    buffer = BytesIO()
    workbook.save(buffer)
    bytes_received = buffer.getvalue()
    transport = ArchiveTransport(bytes_received)
    selected = tuple(entry.source_id for entry in catalog.value[:3])
    result = collector.collect_raw(
        collector.CollectFilesRequest(
            selected,
            continue_on_error=False,
            try_case_variants=False,
        ),
        transport=transport,
    )
    assert result.outcome == "partial", result.diagnostics
    collection = result.value
    assert collection.attempted == selected[:2]
    assert collection.not_attempted == selected[2:]
    assert collection.failed[0].code == "http.status_404"
    original = collection.completed[0]
    assert original.source.payload.data == bytes_received
    assert original.source.receipt.identity == original.source.payload.identity
    request = collector.PrepareArchiveRequest((original, original))
    archive = collector.prepare_archive(request)
    assert archive.outcome == "succeeded"
    assert archive.value == collector.prepare_archive(request).value
    with ZipFile(BytesIO(archive.value.data)) as packed:
        assert len(set(packed.namelist())) == 2
        assert all(packed.read(name) == bytes_received for name in packed.namelist())
