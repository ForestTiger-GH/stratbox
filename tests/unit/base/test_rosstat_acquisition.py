"""Offline fake publisher and local staged storage; never contacts Rosstat."""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from stratbox.core.network import HttpResponse, HttpStreamResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.operations.source.originals import OriginalDestination
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.rosstat.publications.contracts import (
    AcquireRosstatRequest, AcquireRosstatToStoreRequest, DiscoverRosstatRequest,
)
from stratbox.domains.rosstat.operations.publications import acquire, acquire_to_store, discover


def workbook():
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr("xl/workbook.xml", "<workbook/>")
    return buf.getvalue()


class Publisher:
    def __init__(self, body, *, status=200, mime="application/octet-stream"):
        self.body = body
        self.status = status
        self.mime = mime
        self.requests = []

    def _response(self, body):
        return HttpResponse(
            self.status, body, {"content-type": self.mime},
            datetime(2026, 11, 19, tzinfo=timezone.utc), "https://rosstat.gov.ru",
        )

    def exchange(self, request, *, cancelled=None):
        self.requests.append(request)
        return self._response(self.body)

    def exchange_into(self, request, sink, *, cancelled=None):
        self.requests.append(request)
        sink.write(self.body)
        return HttpStreamResponse(self._response(b""), ByteIdentity.of(self.body))


def asset():
    series = "rosstat.short_term_indicators"
    html = b'<a href="/storage/mediabank/2026-08.xlsx">August 2026</a>'
    index = SourcePayload(html, "text/html", series + ".index", charset="utf-8")
    discovered = discover(DiscoverRosstatRequest(series, index))
    assert discovered.outcome == "succeeded", discovered.diagnostics
    return discovered.value.qualified_assets[0]


def test_raw_acquisition_verifies_content_and_identity():
    body = workbook()
    result = acquire(AcquireRosstatRequest(asset()), transport=Publisher(body))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.source.payload.data == body
    assert result.value.source.payload.identity == ByteIdentity.of(body)
    assert result.value.detected_format == "xlsx"


def test_staged_stream_and_readback(tmp_path):
    body = workbook()
    store = LocalFileStore(str(tmp_path))
    request = AcquireRosstatToStoreRequest(asset(), OriginalDestination("2026-08.xlsx"))
    result = acquire_to_store(request, store=store, transport=Publisher(body))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.source.storage.status == "stored"
    assert (tmp_path / "2026-08.xlsx").read_bytes() == body
    second = acquire_to_store(request, store=store, transport=Publisher(body))
    assert second.outcome == "succeeded"
    assert second.value.source.storage.status == "already_present"


def test_corrupt_html_payload_never_overwrites_original(tmp_path):
    path = tmp_path / "2026-08.xlsx"
    path.write_bytes(workbook())
    before = path.read_bytes()
    store = LocalFileStore(str(tmp_path))
    result = acquire_to_store(
        AcquireRosstatToStoreRequest(asset(), OriginalDestination(path.name)),
        transport=Publisher(b"<html>temporary error</html>"), store=store,
    )
    assert result.outcome == "failed"
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".stratbox-*"))


def test_404_does_not_mutate_store(tmp_path):
    store = LocalFileStore(str(tmp_path))
    result = acquire_to_store(
        AcquireRosstatToStoreRequest(asset(), OriginalDestination("publication.xlsx")),
        transport=Publisher(b"missing", status=404), store=store,
    )
    assert result.outcome == "failed"
    assert not (tmp_path / "publication.xlsx").exists()


def test_unapproved_asset_url_fails_before_http_request():
    from dataclasses import replace
    source = Publisher(workbook())
    fake = replace(asset(), url="https://evil.example/storage/mediabank/2026-08.xlsx")
    result = acquire(AcquireRosstatRequest(fake), transport=source)
    assert result.outcome == "failed"
    assert not source.requests


def test_resolved_public_stream_source_handler_is_executable(tmp_path):
    """The core registry must point to the public operation, not its internal helper."""
    from stratbox.core.operations.source.originals import ReceiveOriginalRequest, ReceiveToStoreRequest
    from stratbox.core.network import HttpRequest, HttpsEndpoint
    from stratbox.operations import operation_catalog

    body = workbook()
    selected = asset()
    request = HttpRequest(
        "GET", selected.url,
        (HttpsEndpoint("rosstat.gov.ru", "/storage/mediabank/", subtree=True),),
        max_response_bytes=1024 * 1024,
    )
    core_request = ReceiveToStoreRequest(
        ReceiveOriginalRequest(request, selected.key.source_id, frozenset({
            "application/octet-stream",
        })),
        OriginalDestination("source_original.xlsx"),
    )
    _, handler, _ = operation_catalog().resolve("source.receive_to_store")
    saved = handler(core_request, transport=Publisher(body), store=LocalFileStore(str(tmp_path)))
    assert saved.outcome == "succeeded", saved.diagnostics
    assert (tmp_path / "source_original.xlsx").read_bytes() == body


def test_complete_offline_example(capsys):
    from runpy import run_path
    code = Path(__file__).resolve().parents[3] / "examples" / "rosstat_originals_offline.py"
    main = run_path(str(code))["main"]
    main()
    assert "consumer_accepted" in capsys.readouterr().out


def test_domain_wrappers_project_core_material_evidence(tmp_path):
    from stratbox.core.observability import RecordMemorySink, capture_operation_result
    transport = Publisher(workbook())
    acquired = acquire(AcquireRosstatRequest(asset()), transport=transport)
    memory = RecordMemorySink()
    capture_operation_result(acquired, memory)
    assert "material.acquired" in {entry.kind for entry in memory.records}

    saved = acquire_to_store(
        AcquireRosstatToStoreRequest(asset(), OriginalDestination("original.xlsx")),
        transport=Publisher(workbook()), store=LocalFileStore(str(tmp_path)),
    )
    capture_operation_result(saved, memory)
    kinds = {entry.kind for entry in memory.records}
    assert "material.stored" in kinds


def test_forged_asset_id_fails_before_network():
    from dataclasses import replace
    from stratbox.domains.rosstat.publications.contracts import IssueKey, AssetKey
    old = asset()
    fake_key = AssetKey(IssueKey("rosstat.short_term_indicators", "2025-08"), "main_workbook")
    transport = Publisher(workbook())
    result = acquire(AcquireRosstatRequest(replace(old, key=fake_key)), transport=transport)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "rosstat.asset_identity_unverified"
    assert not transport.requests



def test_new_valid_file_cannot_overwrite_existing_immutable_original(tmp_path):
    first_bytes = workbook()
    other = BytesIO()
    with ZipFile(other, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr("xl/workbook.xml", "<workbook changed='yes'/>")
        z.writestr("xl/extra.xml", "<extra/>")
    changed_bytes = other.getvalue()
    assert changed_bytes != first_bytes
    request = AcquireRosstatToStoreRequest(
        asset(), OriginalDestination("2026-08.xlsx", mode="immutable"),
    )
    store = LocalFileStore(str(tmp_path))
    assert acquire_to_store(request, store=store, transport=Publisher(first_bytes)).outcome == "succeeded"
    second = acquire_to_store(request, store=store, transport=Publisher(changed_bytes))
    assert second.outcome != "succeeded"
    assert (tmp_path / "2026-08.xlsx").read_bytes() == first_bytes


def test_304_without_qualified_baseline_does_not_claim_unchanged(tmp_path):
    result = acquire_to_store(
        AcquireRosstatToStoreRequest(
            asset(), OriginalDestination("2026-08.xlsx", mode="immutable"),
        ),
        transport=Publisher(b"", status=304),
        store=LocalFileStore(str(tmp_path)),
    )
    assert result.outcome == "failed"
    assert not (tmp_path / "2026-08.xlsx").exists()


def test_no_filename_suffix_accepted_by_qualified_asset_replay():
    from dataclasses import replace
    item = asset()
    invalid = replace(item, url="https://rosstat.gov.ru/storage/mediabank/2026-08")
    transport = Publisher(workbook())
    result = acquire(AcquireRosstatRequest(invalid), transport=transport)
    assert result.outcome == "failed"
    assert not transport.requests
