"""Bounded factual streams, with an optional segmented durable provider."""
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping
from threading import RLock
from pathlib import Path
import json
import os
from uuid import uuid4
from stratbox.shared.data.values import canonical_tree, restore_tree

@dataclass(frozen=True)
class JournalFact:
    sequence: int
    kind: str
    run_id: str
    scope_id: str
    command_id: str | None
    output_name: str | None
    physical_work_id: str | None
    attempt_id: str | None
    data: Mapping[str, object]
    occurred_at: datetime
    stream_id: str = ""

class MemoryJournal:
    """Retained bounded fact stream; an exhausted journal applies backpressure."""
    def __init__(self, capacity=10000):
        self.capacity, self._facts, self._lock = capacity, [], RLock()
        self.stream_id = uuid4().hex

    def append(self, *, kind, run_id, scope_id="", command_id=None, output_name=None,
               physical_work_id=None, attempt_id=None, data=None):
        with self._lock:
            if len(self._facts) >= self.capacity:
                raise RuntimeError("journal.capacity_exhausted")
            fact = JournalFact(len(self._facts) + 1, kind, run_id, scope_id, command_id,
                output_name, physical_work_id, attempt_id, MappingProxyType(dict(data or {})), datetime.now(timezone.utc), self.stream_id)
            self._facts.append(fact)
            return fact

    def read(self, after=0, limit=1000, *, run_id=None):
        if after < 0 or not 0 < limit <= self.capacity:
            raise ValueError("journal.invalid_page")
        with self._lock:
            return tuple(f for f in self._facts if f.sequence > after and (run_id is None or f.run_id == run_id))[:limit]


class FileJournal:
    """Segmented single-writer journal; durable records survive service restart."""
    def __init__(self, directory, *, segment_size=1000, max_record_bytes=1024 * 1024):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.segment_size, self.max_record_bytes = segment_size, max_record_bytes
        if segment_size < 1 or max_record_bytes < 1: raise ValueError("journal.invalid_limits")
        self._lock = RLock()
        self._tail = 0
        segments = sorted(self.directory.glob("facts-*.jsonl"))
        identity_path = self.directory / "stream-id"
        if segments and not identity_path.exists(): raise ValueError("journal.stream_identity_missing")
        if not identity_path.exists():
            try:
                with identity_path.open("x") as stream:
                    stream.write(uuid4().hex); stream.flush(); os.fsync(stream.fileno())
            except FileExistsError: pass
        self.stream_id = identity_path.read_text().strip()
        if len(self.stream_id) != 32 or any(c not in "0123456789abcdef" for c in self.stream_id):
            raise ValueError("journal.stream_identity_invalid")
        for expected_segment, path in enumerate(segments):
            if path.name != f"facts-{expected_segment:012d}.jsonl": raise ValueError("journal.coverage_gap")
            count = 0
            for fact in self._read_segment(path):
                if fact.sequence != self._tail + 1 or self._path(fact.sequence) != path:
                    raise ValueError("journal.sequence_conflict")
                self._tail, count = fact.sequence, count + 1
            if not count or expected_segment < len(segments) - 1 and count != self.segment_size:
                raise ValueError("journal.coverage_gap")

    def _path(self, sequence):
        return self.directory / f"facts-{(sequence-1)//self.segment_size:012d}.jsonl"

    def _read_segment(self, path):
        with path.open("rb") as stream:
            for raw in stream:
                if len(raw) > self.max_record_bytes or not raw.endswith(b"\n"):
                    raise ValueError("journal.corrupt_record")
                obj = json.loads(raw)
                if obj.get("stream_id") != self.stream_id: raise ValueError("journal.stream_identity_conflict")
                yield JournalFact(obj["sequence"], obj["kind"], obj["run_id"], obj["scope_id"],
                    obj["command_id"], obj["output_name"], obj["physical_work_id"], obj["attempt_id"],
                    MappingProxyType(restore_tree(obj["data"])), datetime.fromisoformat(obj["occurred_at"]), self.stream_id)

    def append(self, *, kind, run_id, scope_id="", command_id=None, output_name=None,
               physical_work_id=None, attempt_id=None, data=None):
        with self._lock:
            sequence = self._tail + 1
            when = datetime.now(timezone.utc)
            obj = dict(sequence=sequence, kind=kind, run_id=run_id, scope_id=scope_id, stream_id=self.stream_id,
                command_id=command_id, output_name=output_name, physical_work_id=physical_work_id,
                attempt_id=attempt_id, data=canonical_tree(data or {}), occurred_at=when.isoformat())
            raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
            if len(raw) > self.max_record_bytes: raise ValueError("journal.record_limit")
            with self._path(sequence).open("ab") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            self._tail = sequence
            return JournalFact(sequence, kind, run_id, scope_id, command_id, output_name,
                physical_work_id, attempt_id, MappingProxyType(dict(data or {})), when, self.stream_id)

    def read(self, after=0, limit=1000, *, run_id=None, scan_limit=10000):
        if after < 0 or not 0 < limit <= 10000: raise ValueError("journal.invalid_page")
        if type(scan_limit) is not int or scan_limit < 1: raise ValueError("journal.invalid_scan_limit")
        results = []
        scanned = 0
        with self._lock:
            start = after // self.segment_size
            end = (self._tail - 1) // self.segment_size if self._tail else -1
            for segment in range(start, end + 1):
                path = self.directory / f"facts-{segment:012d}.jsonl"
                if not path.exists(): raise ValueError("journal.coverage_gap")
                for fact in self._read_segment(path):
                    scanned += 1
                    if scanned > scan_limit: raise ValueError("journal.scan_limit")
                    if fact.sequence > after and (run_id is None or fact.run_id == run_id):
                        results.append(fact)
                        if len(results) == limit: return tuple(results)
        return tuple(results)
