"""Protocols for immutable journal batches and bounded readers."""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Protocol
from stratbox.shared.data import ByteIdentity
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.journal.contracts import JournalWriteReceipt

class RecordWriter(Protocol):
    """Publish an ordered batch and attest its canonical encoded byte identity."""

    @property
    def format(self) -> str:
        """The canonical format used by encode_records, either json or jsonl."""
        ...

    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt: ...


class RecordReader(Protocol):
    def iter_segments(self, paths: Iterable[str], *, expected: Mapping[str, ByteIdentity] | None = None) -> Iterator[JournalRecord]: ...
