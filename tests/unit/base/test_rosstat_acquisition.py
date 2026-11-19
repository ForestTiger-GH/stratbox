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
from stratbox.domains.rosstat.publications.operations import acquire, acquire_to_store, discover


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
