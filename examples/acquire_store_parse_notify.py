"""Offline demonstration of acquisition, storage, parsing and qualified notification."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.base.net import HttpResponse
from stratbox.macrobanks import cbr_offices
from stratbox.notifications import (
    DeliverRequest,
    NotificationPolicy,
    NotificationRoute,
    OriginalStoredConfirmed,
    PrepareRequest,
    SendReceipt,
    deliver,
    prepare,
)


class RecordedSource:
    def __init__(self, original):
        self.original = original

    def exchange(self, request, *, cancelled=None):
        return HttpResponse(
            200,
            self.original,
            {"content-type": "text/html"},
            datetime(2026, 11, 11, tzinfo=timezone.utc),
            "https://www.cbr.ru",
        )


class InMemoryChannel:
    def send(self, intent):
        return SendReceipt(intent.effect_key, "accepted", "offline-ack")


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("archive")
    args = parser.parse_args()
    transport = RecordedSource(args.html.read_bytes())
    acquired = require_value(
        cbr_offices.acquire(
            cbr_offices.AcquireOfficesRequest(timezone.utc), transport=transport
        )
    )
    original = acquired.payload
    stored = write_verified_bytes(
        args.archive,
        original.data,
        store=LocalFileStore(),
        expected_sha256=original.identity.sha256,
    )
    if stored.status not in {"stored", "already_present"}:
        raise SystemExit(stored.diagnostic_code)
    parsed = require_value(
        cbr_offices.parse(
            cbr_offices.ParseOfficesRequest(original, acquired.capture_date)
        )
    )
    route = NotificationRoute("archive-update", "demo")
    decision = require_value(
        prepare(
            PrepareRequest(
                OriginalStoredConfirmed(stored, "demo-archive-event"),
                NotificationPolicy(original_storage=True),
                route,
            )
        )
    )
    delivery = require_value(
        deliver(DeliverRequest(decision.intent, route), transport=InMemoryChannel())
    )
    print(parsed.dataset_version.identity.sha256, delivery.state)


if __name__ == "__main__":
    main()
