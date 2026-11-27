"""Contiguous fact streams with explicit, consumer-safe retention checkpoints."""
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Mapping
from uuid import uuid4
import json
import os
import tempfile

from stratbox.shared.data.values import canonical_tree, restore_tree, fingerprint
from stratbox.shared.data.journal import JournalFact, JournalPage, JournalCheckpoint, _integer

_MAX_PAGE = 10000
_MAX_SCAN = 100000
_MAX_CONSUMERS = 10000


def _consumer(value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError("journal.consumer_id_invalid")
    return value


def _fsync_directory(directory):
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path, value):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix="checkpoint-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _preflight_metadata(value, limit):
    """Bound work before creating detached metadata buffers; exact charging follows."""
    remaining = limit
    active = set()
    def visit(part, depth=0):
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            raise ValueError("journal.record_limit")
        if depth > 128:
            raise ValueError("journal.data_nesting_limit")
        if isinstance(part, (str, bytes)):
            if len(part) > remaining:
                raise ValueError("journal.record_limit")
            remaining -= len(part.encode() if isinstance(part, str) else part)
            if remaining < 0:
                raise ValueError("journal.record_limit")
        elif part is None or isinstance(part, (bool, float, date, time, timedelta, Decimal)):
            return
        elif isinstance(part, int):
            if part.bit_length() > max(1, remaining) * 4:
                raise ValueError("journal.record_limit")
        elif isinstance(part, (Mapping, tuple, list, set, frozenset)) or is_dataclass(part) and not isinstance(part, type):
            if id(part) in active:
                raise ValueError("journal.data_cycle")
            active.add(id(part))
            if isinstance(part, Mapping):
                for key, item in part.items():
                    visit(key, depth + 1); visit(item, depth + 1)
            elif is_dataclass(part):
                for item in fields(part): visit(getattr(part, item.name), depth + 1)
            else:
                for item in part: visit(item, depth + 1)
            active.remove(id(part))
    visit(value)


def _record_bytes(fact):
    obj = {item.name: getattr(fact, item.name) for item in fields(fact)}
    obj.update(data=canonical_tree(fact.data), occurred_at=fact.occurred_at.isoformat())
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode() + b"\n"


class _Retention:
    def checkpoint(self):
        with self._lock:
            return JournalCheckpoint(self.stream_id, self._floor, self._archived, self._tail, self._consumers)

    def register_consumer(self, consumer_id, *, after=0):
        """Protect unread facts before consumption; existing registration is idempotent."""
        _consumer(consumer_id)
        _integer(after, "journal.invalid_cursor")
        with self._lock:
            self._before_mutation()
            if consumer_id in self._consumers:
                current = self._consumers[consumer_id]
                if after not in (0, current):
                    raise ValueError("journal.consumer_already_registered")
                return current
            if not self._floor <= after <= self._tail:
                raise ValueError("journal.cursor_expired" if after < self._floor else "journal.cursor_ahead")
            if len(self._consumers) >= _MAX_CONSUMERS:
                raise RuntimeError("journal.consumer_capacity_exhausted")
            self._consumers[consumer_id] = after
            self._save_checkpoint()
            return after

    def acknowledge(self, consumer_id, page):
        """Advance only after the consumer has durably retained every selected intent."""
        _consumer(consumer_id)
        if not isinstance(page, JournalPage) or page.stream_id != self.stream_id:
            raise ValueError("journal.stream_identity_conflict")
        with self._lock:
            self._before_mutation()
            if consumer_id not in self._consumers:
                raise ValueError("journal.consumer_not_registered")
            previous = self._consumers[consumer_id]
            if page.scanned_through <= previous:
                return previous
            if page.after != previous or page.scanned_through > self._tail:
                raise ValueError("journal.consumer_coverage_gap")
            expected = self.read_page(after=page.after, limit=_MAX_PAGE,
                run_id=page.filters.get("run_id"), scan_limit=page.scanned_through - page.after)
            if expected.scanned_through != page.scanned_through or fingerprint(expected.facts) != fingerprint(page.facts):
                raise ValueError("journal.consumer_page_conflict")
            self._consumers[consumer_id] = page.scanned_through
            self._save_checkpoint()
            return page.scanned_through

    def unregister_consumer(self, consumer_id):
        """Release a caught-up consumer; lagging registrations cannot be discarded."""
        with self._lock:
            self._before_mutation()
            if consumer_id not in self._consumers:
                return False
            if self._consumers[consumer_id] != self._tail:
                raise ValueError("journal.consumer_lagging")
            del self._consumers[consumer_id]
            self._save_checkpoint()
            return True

    def _prune_allowed(self, through):
        _integer(through, "journal.invalid_cursor")
        if not self._consumers:
            raise ValueError("journal.consumer_checkpoint_required")
        if through > min(self._consumers.values()):
            raise ValueError("journal.consumer_lagging")
        if through > self._tail:
            raise ValueError("journal.cursor_ahead")

    def _page(self, iterator, after, limit, run_id, scan_limit):
        _integer(after, "journal.invalid_page")
        _integer(limit, "journal.invalid_page", minimum=1, maximum=_MAX_PAGE)
        _integer(scan_limit, "journal.invalid_scan_limit", minimum=1, maximum=_MAX_SCAN)
        if after < self._floor:
            raise ValueError("journal.cursor_expired")
        if after > self._tail:
            raise ValueError("journal.cursor_ahead")
        selected, scanned = [], after
        for fact in iterator:
            if fact.sequence != scanned + 1:
                raise ValueError("journal.coverage_gap")
            scanned = fact.sequence
            if run_id is None or fact.run_id == run_id:
                selected.append(fact)
            if scanned - after == scan_limit or len(selected) == limit:
                break
        return JournalPage(self.stream_id, after, scanned, tuple(selected), self._tail,
            self._floor, {} if run_id is None else {"run_id": run_id})

    def read(self, after=0, limit=1000, *, run_id=None, scan_limit=10000):
        page = self.read_page(after=after, limit=limit, run_id=run_id, scan_limit=scan_limit)
        # A bare tuple cannot report a scanned interval or its continuation.
        if page.has_more and page.scanned_through - page.after >= scan_limit and len(page.facts) < limit:
            raise ValueError("journal.scan_limit")
        return page.facts


class MemoryJournal(_Retention):
    """A bounded stream blocks on exhaustion until acknowledged facts are pruned."""
    def __init__(self, capacity=10000, *, max_record_bytes=1024 * 1024, max_bytes=64 * 1024 * 1024):
        _integer(capacity, "journal.invalid_capacity", minimum=1)
        _integer(max_record_bytes, "journal.invalid_limits", minimum=1)
        _integer(max_bytes, "journal.invalid_limits", minimum=1)
        self.capacity, self._facts, self._lock = capacity, [], RLock()
        self.max_record_bytes, self.max_bytes, self._bytes, self._sizes = max_record_bytes, max_bytes, 0, {}
        self.stream_id, self._tail, self._floor, self._archived = uuid4().hex, 0, 0, 0
        self._consumers = {}

    def _before_mutation(self):
        pass

    def _save_checkpoint(self):
        pass

    def append(self, *, kind, run_id, scope_id="", command_id=None, output_name=None,
               physical_work_id=None, attempt_id=None, data=None):
        with self._lock:
            if len(self._facts) >= self.capacity:
                raise RuntimeError("journal.capacity_exhausted")
            _preflight_metadata(data or {}, self.max_record_bytes)
            fact = JournalFact(self._tail + 1, kind, run_id, scope_id, command_id,
                output_name, physical_work_id, attempt_id, data or {}, datetime.now(timezone.utc), self.stream_id)
            size = len(_record_bytes(fact))
            if size > self.max_record_bytes:
                raise ValueError("journal.record_limit")
            if self._bytes + size > self.max_bytes:
                raise RuntimeError("journal.byte_capacity_exhausted")
            self._sizes[fact.sequence] = size
            self._bytes += size
            self._facts.append(fact); self._tail = fact.sequence
            return fact

    def read_page(self, after=0, limit=1000, *, run_id=None, scan_limit=10000):
        with self._lock:
            return self._page((fact for fact in self._facts if fact.sequence > after), after, limit, run_id, scan_limit)

    def prune(self, through):
        with self._lock:
            self._prune_allowed(through)
            if through > self._floor:
                self._facts = [fact for fact in self._facts if fact.sequence > through]
                for sequence in tuple(self._sizes):
                    if sequence <= through:
                        self._bytes -= self._sizes.pop(sequence)
                self._floor = through
            return self.checkpoint()


class FileJournal(_Retention):
    """One explicit writer, bounded scans, readable cold segments and durable cursors."""
    def __init__(self, directory, *, segment_size=None, max_record_bytes=1024 * 1024):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        _integer(max_record_bytes, "journal.invalid_limits", minimum=1)
        self.max_record_bytes, self._lock, self._writer, self._closed = max_record_bytes, RLock(), None, False
        self._requested_segment_size = segment_size
        identity_path, state_path = self.directory / "stream-id", self.directory / "retention.json"
        if not identity_path.exists():
            if any(self.directory.glob("facts-*.jsonl")) or state_path.exists():
                raise ValueError("journal.stream_identity_missing")
            try:
                with identity_path.open("x") as stream:
                    stream.write(uuid4().hex); stream.flush(); os.fsync(stream.fileno())
                _fsync_directory(self.directory)
            except FileExistsError:
                pass
        self.stream_id = identity_path.read_text().strip()
        if len(self.stream_id) != 32 or any(c not in "0123456789abcdef" for c in self.stream_id):
            raise ValueError("journal.stream_identity_invalid")
        state = json.loads(state_path.read_bytes()) if state_path.exists() else None
        self.segment_size = state["segment_size"] if state else (1000 if segment_size is None else segment_size)
        _integer(self.segment_size, "journal.invalid_limits", minimum=1)
        if segment_size is not None and segment_size != self.segment_size:
            raise ValueError("journal.segment_geometry_conflict")
        self._floor, self._archived, self._cleaned, self._consumers = 0, 0, 0, {}
        if state:
            if state["stream_id"] != self.stream_id:
                raise ValueError("journal.stream_identity_conflict")
            self._floor, self._archived = state["retained_after"], state["archived_through"]
            self._consumers = dict(state["consumers"])
            self._cleaned = state.get("cleaned_through", 0)
            for cursor in (self._floor, self._archived, self._cleaned, state["tail"], *self._consumers.values()):
                _integer(cursor, "journal.checkpoint_invalid")
            if (self._floor % self.segment_size or self._archived % self.segment_size or self._cleaned % self.segment_size
                    or self._cleaned > self._floor
                    or not self._floor <= self._archived <= state["tail"]
                    or any(not self._floor <= value <= state["tail"] for value in self._consumers.values())):
                raise ValueError("journal.checkpoint_invalid")
            for name in self._consumers: _consumer(name)
        self._tail = max(self._floor, self._archived)
        self._recover_hot_tail()
        if state and self._tail < state["tail"]:
            raise ValueError("journal.coverage_gap")

    def _active(self, segment):
        return self.directory / f"facts-{segment:012d}.jsonl"

    def _cold(self, segment):
        return self.directory / "archive" / f"{segment // 1000:012d}" / f"facts-{segment:012d}.jsonl"

    def _segment(self, segment):
        active, cold = self._active(segment), self._cold(segment)
        if active.exists() and cold.exists():
            raise ValueError("journal.segment_location_conflict")
        return active if active.exists() else cold if cold.exists() else None

    def _recover_hot_tail(self):
        segment = self._tail // self.segment_size
        while (path := self._segment(segment)) is not None:
            count = 0
            for fact in self._read_segment(path):
                if fact.sequence != self._tail + 1 or (fact.sequence - 1) // self.segment_size != segment:
                    raise ValueError("journal.sequence_conflict")
                self._tail, count = fact.sequence, count + 1
            if not count or count > self.segment_size:
                raise ValueError("journal.coverage_gap")
            segment += 1
            if count < self.segment_size:
                break
        if any(int(path.stem.split("-")[1]) >= segment for path in self.directory.glob("facts-*.jsonl")):
            raise ValueError("journal.coverage_gap")

    def _before_mutation(self):
        if self._closed:
            raise RuntimeError("journal.closed")
        if (self.directory / 'writer-closed.json').exists():
            raise RuntimeError('journal.writer_namespace_closed')
        if self._writer is not None:
            return
        stream = (self.directory / "writer.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0); stream.write(b"0"); stream.flush(); stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            stream.close()
            raise RuntimeError("journal.writer_already_owned") from error
        try:
            current = type(self)(self.directory, segment_size=self.segment_size, max_record_bytes=self.max_record_bytes)
            if (current._tail, current._floor, current._archived, current._cleaned, current._consumers) != (self._tail, self._floor, self._archived, self._cleaned, self._consumers):
                raise RuntimeError("journal.writer_state_stale_reopen_required")
        except Exception:
            stream.close()
            raise
        self._writer = stream
        if not (self.directory / "retention.json").exists():
            self._save_checkpoint()

    def refresh(self):
        """Refresh a read-only observer before scanning newly committed records."""
        with self._lock:
            if self._closed:
                raise RuntimeError("journal.closed")
            if self._writer is None:
                current = type(self)(self.directory, segment_size=self._requested_segment_size, max_record_bytes=self.max_record_bytes)
                self.segment_size = current.segment_size
                self._tail, self._floor, self._archived = current._tail, current._floor, current._archived
                self._cleaned, self._consumers = current._cleaned, dict(current._consumers)
            return self.checkpoint()

    def _save_checkpoint(self):
        _atomic_json(self.directory / "retention.json", {"stream_id": self.stream_id,
            "segment_size": self.segment_size, "retained_after": self._floor,
            "archived_through": self._archived, "cleaned_through": self._cleaned,
            "tail": self._tail, "consumers": self._consumers})

    def _read_segment(self, path):
        with path.open("rb") as stream:
            while raw := stream.readline(self.max_record_bytes + 1):
                if len(raw) > self.max_record_bytes or not raw.endswith(b"\n"):
                    raise ValueError("journal.corrupt_record")
                obj = json.loads(raw)
                if obj.get("stream_id") != self.stream_id:
                    raise ValueError("journal.stream_identity_conflict")
                yield JournalFact(obj["sequence"], obj["kind"], obj["run_id"], obj["scope_id"],
                    obj["command_id"], obj["output_name"], obj["physical_work_id"], obj["attempt_id"],
                    restore_tree(obj["data"]), datetime.fromisoformat(obj["occurred_at"]), self.stream_id)

    def append(self, *, kind, run_id, scope_id="", command_id=None, output_name=None,
               physical_work_id=None, attempt_id=None, data=None):
        with self._lock:
            self._before_mutation()
            _preflight_metadata(data or {}, self.max_record_bytes)
            fact = JournalFact(self._tail + 1, kind, run_id, scope_id, command_id, output_name,
                physical_work_id, attempt_id, data or {}, datetime.now(timezone.utc), self.stream_id)
            raw = _record_bytes(fact)
            if len(raw) > self.max_record_bytes:
                raise ValueError("journal.record_limit")
            path = self._active((fact.sequence - 1) // self.segment_size)
            with path.open("ab") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            if (fact.sequence - 1) % self.segment_size == 0:
                _fsync_directory(self.directory)
            self._tail = fact.sequence
            # Persist an independent high-watermark before acknowledging the
            # append. A later missing final segment must not look like a valid
            # older stream merely because no consumer had checkpointed yet.
            self._save_checkpoint()
            return fact

    def _facts_after(self, after):
        first, last = after // self.segment_size, (self._tail - 1) // self.segment_size
        for segment in range(first, last + 1):
            path = self._segment(segment)
            if path is None:
                raise ValueError("journal.coverage_gap")
            for fact in self._read_segment(path):
                if after < fact.sequence <= self._tail:
                    yield fact

    def recovery_metadata(self):
        """Describe the finite replay cut owned by this single writer."""
        with self._lock:
            return {'provider_id': 'journal.files', 'checkpoint': self.checkpoint(),
                    'directory': str(self.directory.resolve()), 'segment_size': self.segment_size,
                    'max_record_bytes': self.max_record_bytes}

    def export_checkpoint(self, destination, *, max_bytes=None, max_files=None, max_file_bytes=None):
        """Copy the exact retained suffix and cursors while holding writer ownership."""
        from stratbox.core.storage.readable import copy_stream
        import shutil
        if any(value is not None and (type(value) is not int or value < 1)
               for value in (max_bytes, max_files, max_file_bytes)):
            raise ValueError('journal.checkpoint_limit_invalid')
        destination = Path(destination).resolve()
        if destination.exists() or destination.is_relative_to(self.directory.resolve()):
            raise ValueError('journal.checkpoint_destination_invalid')
        with self._lock:
            self._before_mutation()
            self._save_checkpoint()
            def paths():
                for name in ('stream-id', 'retention.json'):
                    yield self.directory / name
                for segment in range(self._floor // self.segment_size, (self._tail - 1) // self.segment_size + 1):
                    path = self._segment(segment)
                    if path is None:
                        raise ValueError('journal.coverage_gap')
                    yield path
            count = total = 0
            for path in paths():
                count += 1
                size = path.stat().st_size
                total += size
                if (max_files is not None and count > max_files
                        or max_bytes is not None and total > max_bytes
                        or max_file_bytes is not None and size > max_file_bytes):
                    raise ValueError('journal.checkpoint_size_limit')
            destination.mkdir(parents=True)
            try:
                for path in paths():
                    target_path = destination / path.relative_to(self.directory)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('rb') as source, target_path.open('xb') as target:
                        copy_stream(source, target, limit=path.stat().st_size)
                        target.flush(); os.fsync(target.fileno())
                _fsync_directory(destination)
                return str(destination)
            except BaseException:
                shutil.rmtree(destination)
                raise

    def read_page(self, after=0, limit=1000, *, run_id=None, scan_limit=10000):
        with self._lock:
            return self._page(self._facts_after(after), after, limit, run_id, scan_limit)

    def archive(self, through, *, max_segments=1000):
        """Move closed segments to cold storage; lagging consumers still read them."""
        _integer(through, "journal.invalid_cursor")
        _integer(max_segments, "journal.invalid_archive_limit", minimum=1, maximum=10000)
        with self._lock:
            self._before_mutation()
            if through > self._tail:
                raise ValueError("journal.cursor_ahead")
            target = through // self.segment_size * self.segment_size
            moved = 0
            while self._archived < target and moved < max_segments:
                segment = self._archived // self.segment_size
                if self._archived < self._floor:
                    self._archived = self._floor
                    continue
                path = self._segment(segment)
                if path is None:
                    raise ValueError("journal.coverage_gap")
                cold = self._cold(segment)
                cold.parent.mkdir(parents=True, exist_ok=True)
                if path != cold:
                    os.replace(path, cold)
                    _fsync_directory(cold.parent); _fsync_directory(self.directory)
                self._archived += self.segment_size
                self._save_checkpoint()
                moved += 1
            return self.checkpoint()

    def prune(self, through, *, max_segments=1000):
        """Expire an acknowledged prefix, then reclaim a bounded number of segments."""
        _integer(max_segments, "journal.invalid_archive_limit", minimum=1, maximum=10000)
        with self._lock:
            self._before_mutation()
            self._prune_allowed(through)
            target = through // self.segment_size * self.segment_size
            if target > self._floor:
                previous = self._floor, self._archived
                self._floor, self._archived = target, max(self._archived, target)
                try:
                    self._save_checkpoint()
                except Exception:
                    self._floor, self._archived = previous
                    raise
            self.cleanup_pruned(max_segments=max_segments)
            return self.checkpoint()

    def cleanup_pruned(self, *, max_segments=1000):
        """Resume physical cleanup after a crash; the durable floor is authoritative."""
        _integer(max_segments, "journal.invalid_archive_limit", minimum=1, maximum=10000)
        with self._lock:
            self._before_mutation()
            stop = min(self._floor, self._cleaned + max_segments * self.segment_size)
            while self._cleaned < stop:
                segment = self._cleaned // self.segment_size
                for path in (self._active(segment), self._cold(segment)):
                    path.unlink(missing_ok=True)
                    if path.parent.exists():
                        _fsync_directory(path.parent)
                self._cleaned += self.segment_size
                self._save_checkpoint()
            return self.checkpoint()

    def close(self):
        with self._lock:
            self._closed = True
            if self._writer is not None:
                stream, self._writer = self._writer, None
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                stream.close()

    def __enter__(self):
        if self._closed: raise RuntimeError("journal.closed")
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try: self.close()
        except Exception: pass
