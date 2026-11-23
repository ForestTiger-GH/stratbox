from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook

from stratbox.core.network import HttpResponse
import stratbox.domains.cbr.operations.collection as collector
from stratbox.shared.material_collections import decode_collection
from stratbox.shared.data.processing import DataRole


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
        assert len(set(packed.namelist())) == 3
        manifest = decode_collection(packed.read("manifest.json"))
        assert manifest.complete and manifest.coverage.status == "unknown"
        assert all(member.contract.role is DataRole.ORIGINALS for member in manifest.members)
        assert all(packed.read(member.name) == bytes_received for member in manifest.members)


def test_failure_continuation_controls_the_retained_partial_scope_and_identity():
    workbook = Workbook()
    workbook.active["A1"] = "Source"
    buffer = BytesIO()
    workbook.save(buffer)
    body = buffer.getvalue()
    sources = tuple(entry.source_id for entry in collector.discover(collector.DiscoverFilesRequest()).value[:3])
    stopped = collector.collect_raw(collector.CollectFilesRequest(sources,
        continue_on_error=False, try_case_variants=False), transport=ArchiveTransport(body))
    continued = collector.collect_raw(collector.CollectFilesRequest(sources,
        continue_on_error=True, try_case_variants=False), transport=ArchiveTransport(body))
    assert stopped.outcome == continued.outcome == "partial"
    assert tuple(item.source.payload.identity for item in stopped.value.completed) == \
        tuple(item.source.payload.identity for item in continued.value.completed)
    assert len(stopped.value.failed) == 1 and len(continued.value.failed) == 2
    assert stopped.value.not_attempted == sources[2:]
    assert continued.value.not_attempted == ()
    assert stopped.computation.computation_id != continued.computation.computation_id


def test_batch_byte_scope_changes_partitions_even_for_byte_identical_materials():
    from stratbox.domains.cbr.operations.collection.materials import (
        CollectMaterial, CollectMaterialsRequest, collect_materials,
    )
    from stratbox.shared.evidence import SourcePayload
    payload = SourcePayload(b"<html>same original</html>", "text/html", "cbr.service_network.bank_offices")
    items = tuple(CollectMaterial(key, "cbr.service_network.bank_offices", issue, "html", payload=payload)
                  for key, issue in (("first", "2026-11-01"), ("second", "2026-11-02")))
    limited = collect_materials(CollectMaterialsRequest(items, max_batch_bytes=payload.identity.size))
    full = collect_materials(CollectMaterialsRequest(items, max_batch_bytes=2 * payload.identity.size))
    assert limited.outcome == "partial", limited.diagnostics
    assert full.outcome == "succeeded", full.diagnostics
    assert len(limited.value.manifest.members) == 1
    assert len(full.value.manifest.members) == 2
    assert limited.computation.computation_id != full.computation.computation_id
