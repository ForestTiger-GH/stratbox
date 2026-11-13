from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from gzip import compress
from io import BytesIO
from pathlib import Path
from threading import Event
from zipfile import ZipFile

import pytest

from stratbox.base.filestore import LocalFileStore
from stratbox.base.net import HttpRequest, HttpsEndpoint, RetryPolicy
from stratbox.base.net.transport import _follow
from stratbox.data import ByteIdentity, SourcePayload
from stratbox.execution import ExecutionBudget, ExecutionContext
from stratbox.execution.originals import (
    OriginalDestination, ReadOriginalRequest, ReceiveOriginalRequest, ReceiveToStoreRequest,
    ReconcileOriginalRequest, SaveOriginalRequest, read_original, receive_original, receive_to_store,
    reconcile_original, save_original,
)
from stratbox.macrobanks import cbr_file_collector as collector, cbr_offices

class BodyTransport:
    accounts_http_budget = True

    def __init__(self, *replies, on_open=None):
        self.replies = iter(replies)
        self.requests = []
        self.on_open = on_open

    @contextmanager
    def open_response(self, url, headers, remaining):
        self.requests.append((url, dict(headers)))
        status, fields, content = next(self.replies)
        if self.on_open:
            self.on_open(status)
        yield status, fields, BytesIO(content).read

    def exchange(self, request, *, cancelled=None):
        return _follow(request, self.open_response, cancelled, "tls_host")

    def exchange_into(self, request, sink, *, cancelled=None):
        return _follow(request, self.open_response, cancelled, "tls_host", sink)


def _request():
    return ReceiveOriginalRequest(
        HttpRequest("GET", "https://www.cbr.ru/banking_sector/credit/cstat/",
                    (HttpsEndpoint("www.cbr.ru", "/banking_sector/credit/cstat/"),)),
        "offices", frozenset({"text/html"}), RetryPolicy(2, 0, 0),
    )


def test_buffer_and_stream_share_retries_coding_and_offline_replay(tmp_path):
    fixture = Path(__file__).resolve().parents[2] / "fixtures/universal_core/offices-basic.html"
    content = fixture.read_bytes()
    compressed = compress(content)
    headers = {"content-type": "text/html; charset=utf-8", "content-encoding": "gzip",
               "content-length": str(len(compressed)), "etag": '"release"'}
    attempts = ((503, {}, b"retry"), (200, headers, compressed))
    store = LocalFileStore(str(tmp_path))
    budget = ExecutionContext(budget=ExecutionBudget(requests=2, wire_bytes=len(compressed) + 5))
    buffered = receive_original(_request(), transport=BodyTransport(*attempts), context=budget)
    provider = BodyTransport(*attempts, (304, {"etag": '"release"'}, b""))
    request = ReceiveToStoreRequest(_request(), OriginalDestination("official.html"))
    streamed = receive_to_store(request, transport=provider, store=store, context=budget)
    assert streamed.outcome == buffered.outcome == "succeeded"
    assert streamed.value.material.identity == buffered.value.payload.identity == ByteIdentity.of(content)
    assert streamed.value.acquisition.wire_size == len(compressed)
    assert streamed.value.acquisition.content_encoding == "gzip"
    assert streamed.value.storage.observed_revision
    assert len(provider.requests) == 2
    replay = read_original(ReadOriginalRequest(streamed.value.material), store=store)
    assert replay.value == buffered.value.payload
    day = date(2026, 11, 12)
    assert cbr_offices.parse(cbr_offices.ParseOfficesRequest(replay.value, day)).value == (
        cbr_offices.parse(cbr_offices.ParseOfficesRequest(buffered.value.payload, day)).value
    )
    reused = receive_to_store(replace(request, baseline=streamed.value), transport=provider, store=store)
    assert reused.outcome == "succeeded" and reused.value.acquisition.reused
    assert reused.value.storage.status == "already_present"
    assert provider.requests[-1][1]["if-none-match"] == '"release"'
    (tmp_path / "official.html").write_bytes(b"changed")
    expired = receive_to_store(replace(request, baseline=streamed.value),
                               transport=BodyTransport((304, {}, b"")), store=store)
    assert expired.diagnostics[0].code == "http.full_representation_required"
    assert read_original(ReadOriginalRequest(streamed.value.material), store=store).diagnostics[0].code == (
        "input.material_version_changed"
    )


@pytest.mark.parametrize("reason", ["short", "budget", "cancelled", "baseline"])
def test_stream_does_not_commit_an_incomplete_original(tmp_path, reason):
    store = LocalFileStore(str(tmp_path))
    token = Event()
    fields = {"content-type": "text/html", "content-length": "10"}
    reply = (200, fields, b"short") if reason == "short" else (200, {"content-type": "text/html"}, b"a" * 4096)
    if reason == "baseline":
        reply = (304, {}, b"")
    provider = BodyTransport(reply, reply, on_open=lambda _: token.set() if reason == "cancelled" else None)
    result = receive_to_store(ReceiveToStoreRequest(_request(), OriginalDestination("partial")),
                              transport=provider, store=store, context=ExecutionContext(
                                  cancellation=token, budget=ExecutionBudget(temporary_bytes=4 if reason == "budget" else None),
                              ))
    assert result.diagnostics[0].code == {
        "short": "http.truncated", "budget": "budget.temporary_bytes",
        "cancelled": "operation.cancelled", "baseline": "http.full_representation_required",
    }[reason]
    assert not result.effects and not list(tmp_path.iterdir())


def test_original_lost_ack_is_reconciled_with_stable_effect_key(tmp_path):
    class LostAckStore(LocalFileStore):
        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                original = stage.commit

                def lost(mode, revision):
                    original(mode, revision)
                    raise TimeoutError("lost acknowledgement")

                stage.commit = lost
                yield stage

    source = SourcePayload(b"opaque permitted original")
    request = SaveOriginalRequest(source, OriginalDestination("source"))
    lost = save_original(request, store=LostAckStore(str(tmp_path)))
    assert lost.outcome == "unknown" and lost.effects[0].state == "unknown"
    assert lost.diagnostics[0].retry_disposition == "reconcile"
    assert (tmp_path / "source").read_bytes() == source.data
    store = LocalFileStore(str(tmp_path))
    matched = reconcile_original(ReconcileOriginalRequest(lost.value.storage), store=store)
    assert matched.outcome == "succeeded" and matched.value.effect_id == lost.effects[0].effect_id
    reused = save_original(request, store=store)
    assert reused.outcome == "succeeded" and reused.value.storage.status == "already_present"
    assert reused.value.storage.effect_id == lost.value.storage.effect_id
    stale = save_original(replace(request, destination=OriginalDestination(
        "source", "replace_expected_revision", "stale",
    )), store=store)
    assert stale.diagnostics[0].code == "effect.conflict"
    assert (tmp_path / "source").read_bytes() == source.data


def test_collector_retains_accepted_files_when_cancelled_and_archives_references(tmp_path):
    from openpyxl import Workbook

    book = Workbook()
    book.active.append(["Observed", 1])
    buffer = BytesIO()
    book.save(buffer)
    book.close()
    raw = buffer.getvalue()
    ids = tuple(item.source_id for item in collector.discover(collector.DiscoverFilesRequest()).value[:3])
    request = collector.CollectFilesRequest(ids, try_case_variants=False, retry=RetryPolicy(1))
    replies = (200, {"content-type": "application/octet-stream"}, raw)
    event = Event()
    seen = []

    class SetBetweenItems:
        def exchange(self, req, *, cancelled=None):
            from datetime import datetime, timezone
            from stratbox.base.net import HttpResponse

            seen.append(req)
            event.set()
            return HttpResponse(200, raw, replies[1], datetime.now(timezone.utc), "https://www.cbr.ru")

    partial = collector.collect_raw(request, transport=SetBetweenItems(), context=ExecutionContext(cancellation=event))
    assert partial.outcome == "partial" and partial.value.stop_reason == "operation.cancelled"
    assert partial.value.attempted == ids[:1] and partial.value.not_attempted == ids[1:] and len(seen) == 1
    assert collector.collect_raw(request, transport=SetBetweenItems(),
                                 context=ExecutionContext(cancellation=event)).outcome == "cancelled"
    store = LocalFileStore(str(tmp_path))
    selected = replace(request, source_ids=ids[:1])
    saved = collector.collect_to_store(collector.CollectToStoreRequest(
        selected, {ids[0]: OriginalDestination("original.xlsx")},
    ), transport=BodyTransport(replies), store=store)
    assert saved.outcome == "succeeded", saved.diagnostics
    archive = collector.archive_to_store(
        collector.StoreArchiveRequest(saved.value.completed, OriginalDestination("package.zip")),
        source_store=store, output_store=store,
    )
    assert archive.outcome == "succeeded", archive.diagnostics
    with ZipFile(tmp_path / "package.zip") as reader:
        assert reader.namelist() == [saved.value.completed[0].file_name]
        assert reader.read(reader.namelist()[0]) == raw
