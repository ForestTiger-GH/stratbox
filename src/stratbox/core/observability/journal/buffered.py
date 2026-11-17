"""Bounded journal write buffering and unknown-commit reconciliation."""
from __future__ import annotations

from collections.abc import Iterable
from threading import RLock
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.journal.contracts import JournalWriteReceipt, JournalBarrierError
from stratbox.core.observability.journal.codecs import encode_record
from stratbox.core.observability.journal.file_writer import FileJournalWriter

class BufferedFileJournal:
    """Bounded pending buffer with explicit reconciliation of unknown commits."""
    def __init__(self, writer: FileJournalWriter, *, max_retained_receipts: int = 4096):
        if not 1 <= max_retained_receipts <= 100_000:
            raise ValueError("journal.receipt_limit_invalid")
        self.max_retained_receipts = max_retained_receipts
        self.writer = writer
        self._buffer: list[JournalRecord] = []
        self._bytes = 0
        self._receipts: dict[str, JournalWriteReceipt] = {}
        self._pending_receipt: JournalWriteReceipt | None = None
        self._closed = False
        self._lock = RLock()
        self._confirmed = self._failed = self._unknown = 0

    def _size_with(self, size: int) -> int:
        if self.writer.format == "jsonl":
            return self._bytes + size + 1
        return (self._bytes if self._buffer else 2) + size + (1 if self._buffer else 0)

    def append(self, record: JournalRecord) -> JournalWriteReceipt | None:
        size = len(encode_record(record))
        with self._lock:
            if self._closed:
                raise RuntimeError("Journal is closed")
            if size + 2 > min(self.writer.policy.max_buffer_bytes, self.writer.max_segment_bytes):
                raise ValueError("journal.record_buffer_limit")
            result = None
            if self._buffer and (len(self._buffer) >= self.writer.policy.max_buffer_records or
                                 self._size_with(size) > self.writer.policy.max_buffer_bytes or
                                 self._size_with(size) > self.writer.max_segment_bytes):
                result = self.flush()
                if result is not None and result.state != "confirmed":
                    raise JournalBarrierError(result)
            self._bytes = self._size_with(size)
            self._buffer.append(record)
            if len(self._buffer) >= self.writer.policy.max_buffer_records:
                result = self.flush()
            return result

    def flush(self) -> JournalWriteReceipt | None:
        with self._lock:
            if not self._buffer:
                return None
            if self._pending_receipt is not None:
                return self._pending_receipt
            # Capacity is checked BEFORE publishing, so a successfully committed
            # segment can never be orphaned by an exhausted receipt catalogue.
            if len(self._receipts) >= self.max_retained_receipts:
                raise ValueError("journal.receipt_capacity_exceeded")
            receipt = self.writer.write_batch(tuple(self._buffer))
            self._receipts[receipt.segment_id] = receipt
            if receipt.state == "confirmed":
                self._confirmed += 1
                self._buffer.clear()
                self._bytes = 0
            else:
                self._pending_receipt = receipt
                if receipt.state == "unknown":
                    self._unknown += 1
                else:
                    self._failed += 1
            return receipt

    def reconcile_pending(self) -> JournalWriteReceipt | None:
        with self._lock:
            if self._pending_receipt is None:
                return None
            receipt = self.writer.reconcile(self._pending_receipt)
            self._receipts[receipt.segment_id] = receipt
            if receipt.state == "confirmed":
                self._confirmed += 1
                self._buffer.clear()
                self._bytes = 0
                self._pending_receipt = None
            else:
                self._pending_receipt = receipt
            return receipt

    def close(self) -> tuple[JournalWriteReceipt, ...]:
        with self._lock:
            if not self._closed and (self.flush() is None or self._pending_receipt is None):
                self._closed = True
            return tuple(self._receipts.values())

    @property
    def close_status(self) -> str:
        with self._lock:
            if self._pending_receipt is not None:
                return "pending_unconfirmed" if self._pending_receipt.state == "unknown" else "closed_failed"
            return "closed_confirmed" if self._closed else "open"

    @property
    def pending(self) -> tuple[JournalRecord, ...]:
        with self._lock:
            return tuple(self._buffer)

    @property
    def pending_bytes(self) -> int:
        with self._lock:
            return self._bytes

    @property
    def receipts(self) -> tuple[JournalWriteReceipt, ...]:
        with self._lock:
            return tuple(self._receipts.values())


    def snapshot_receipts(self) -> tuple[JournalWriteReceipt, ...]:
        """Bounded immutable handoff for a caller-controlled manifest or catalogue."""
        return self.receipts

    def acknowledge_receipts(self, segment_ids: Iterable[str]) -> int:
        """Only independently handled *confirmed* receipts may be released."""
        with self._lock:
            requested = tuple(segment_ids)
            if len(requested) > self.max_retained_receipts or len(set(requested)) != len(requested):
                raise ValueError("journal.receipt_ack_invalid")
            for segment_id in requested:
                receipt = self._receipts.get(segment_id)
                if receipt is None or receipt.state != "confirmed" or (
                    self._pending_receipt is not None and self._pending_receipt.segment_id == segment_id
                ):
                    raise ValueError("journal.receipt_ack_unconfirmed")
            for segment_id in requested:
                del self._receipts[segment_id]
            return len(requested)
    @property
    def flush_counts(self) -> tuple[int, int, int]:
        with self._lock:
            return self._confirmed, self._failed, self._unknown
