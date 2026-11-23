"""Process-local confirmed transitions with bounded, explicit evidence retention."""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

from stratbox.core.observability.journal.codecs import JournalDecodeError, encode_record
from stratbox.core.observability.journal.sources import (
    JournalCursor, JournalEntry, JournalHead, JournalPage, JournalReadLimits,
    JournalReadProblem, StreamKey,
)
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.shared.identifiers import safe_token


class LiveJournalSource:
    """Snapshot-consistent heads over a live, process-local transition journal.

    Only admitted terminal transitions enter this source. Diagnostic ring-buffer
    loss therefore cannot erase a notification obligation. The owner must reserve
    capacity before admitting work and explicitly acknowledge retained evidence
    after all interested consumers no longer need it. This is not crash recovery.
    """

    def __init__(self, stream: StreamKey, *, epoch_id: str, source_authority_id: str,
                 max_records: int = 4096, max_bytes: int = 16 * 1024**2):
        for token in (epoch_id, source_authority_id):
            safe_token(token)
        if type(max_records) is not int or max_records < 1 or type(max_bytes) is not int or max_bytes < 8192:
            raise ValueError("journal.retention_limit_invalid")
        self.stream, self.epoch_id = stream, epoch_id
        self.source_authority_id = source_authority_id
        # A terminal record is capped at 8 KiB before publication; reservations
        # account for its complete worst-case retained size.
        self.capacity = min(max_records, max_bytes // 8192)
        self._entries: OrderedDict[int, JournalEntry] = OrderedDict()
        self._reserved: set[str] = set()
        self._by_run: dict[str, int] = {}
        self._tail = 0
        self._first = 1
        self._lock = RLock()

    def reserve(self, run_id: str) -> None:
        safe_token(run_id)
        with self._lock:
            if run_id in self._reserved or run_id in self._by_run:
                raise ValueError("journal.run_already_reserved")
            if len(self._entries) + len(self._reserved) >= self.capacity:
                raise ValueError("orchestration.retention_capacity")
            self._reserved.add(run_id)

    def has_reservation(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._reserved

    def release(self, run_id: str) -> None:
        with self._lock:
            self._reserved.discard(run_id)

    def append_terminal(self, record: JournalRecord) -> JournalEntry:
        if record.kind != "run.finished" or record.record_type != "orchestration":
            raise ValueError("journal.terminal_transition_required")
        run_id = record.correlation.run_id
        with self._lock:
            if run_id in self._by_run:
                old = self._entries[self._by_run[run_id]]
                if old.record != record:
                    raise ValueError("journal.transition_identity_conflict")
                return old
            if run_id not in self._reserved:
                raise ValueError("journal.terminal_reservation_required")
            if len(encode_record(record)) > 8192:
                raise ValueError("journal.terminal_record_too_large")
            entry = JournalEntry.from_record(self._tail + 1, record, self.epoch_id)
            self._entries[entry.offset] = entry
            self._by_run[run_id] = entry.offset
            self._reserved.remove(run_id)
            self._tail = entry.offset
            return entry

    def acknowledge(self, through_offset: int) -> None:
        """Owner-attested retention release, never automatic after preparation."""
        with self._lock:
            if type(through_offset) is not int or not self._first - 1 <= through_offset <= self._tail:
                raise ValueError("journal.acknowledgement_invalid")
            while self._entries and next(iter(self._entries)) <= through_offset:
                _, entry = self._entries.popitem(last=False)
                self._by_run.pop(entry.record.correlation.run_id, None)
            self._first = through_offset + 1

    def head(self, stream: StreamKey) -> JournalHead:
        if stream != self.stream:
            raise JournalDecodeError("journal.stream_mismatch")
        with self._lock:
            return JournalHead(stream, self.epoch_id, f"head.{self._first}.{self._tail}",
                               self.source_authority_id, "local_snapshot", self._first, self._tail)

    def read_page(self, after: JournalCursor, *, head: JournalHead,
                  limits: JournalReadLimits) -> JournalPage:
        with self._lock:
            current = self.head(self.stream)
            if (head.stream != current.stream or head.epoch_id != current.epoch_id
                    or head.source_authority_id != current.source_authority_id
                    or head.profile != current.profile
                    or head.head_ref != f"head.{head.first_retained}.{head.tail_offset}"):
                raise JournalDecodeError("journal.source_binding_mismatch")
            head.check(after)
            current.check(after)
            if head.tail_offset > current.tail_offset:
                raise JournalDecodeError("journal.cursor_ahead")
            entries, size, problem = [], 0, None
            for offset in range(after.last_offset + 1, head.tail_offset + 1):
                entry = self._entries[offset]
                if size + entry.identity.size > limits.max_bytes:
                    if not entries:
                        problem = JournalReadProblem(offset, offset, "journal.page_entry_too_large")
                    break
                entries.append(entry)
                size += entry.identity.size
                if len(entries) >= limits.max_positions:
                    break
            return JournalPage(head, after, tuple(entries), problem,
                               "incomplete" if problem else "indeterminate", "complete", "not_applicable")

    @property
    def pending(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def reserved(self) -> int:
        with self._lock:
            return len(self._reserved)
