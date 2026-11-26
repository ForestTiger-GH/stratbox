"""Bounded optional fact delivery, independent of required execution workers."""
from collections import deque
from dataclasses import dataclass
from threading import Condition, Thread

from .owned_values import _size


@dataclass(frozen=True)
class ObserverDiagnostic:
    code: str
    stream_id: str
    sequence: int
    run_id: str


@dataclass(frozen=True)
class ObserverStatus:
    queued: int
    queued_bytes: int
    active: bool
    active_bytes: int
    delivered: int
    failed: int
    dropped: int
    closed: bool
    diagnostics: tuple[ObserverDiagnostic, ...]
    history_truncated: bool
    first_missed: tuple[str,int] | None
    active_coordinate: tuple[str,int] | None

    @property
    def replay_after(self):
        """Earliest retained missed coordinate per stream; no replay is implied."""
        starts = {}
        for coordinate in (self.first_missed,self.active_coordinate):
            if coordinate is not None:
                starts[coordinate[0]] = min(starts.get(coordinate[0],coordinate[1]-1),coordinate[1]-1)
        for item in self.diagnostics:
            starts[item.stream_id] = min(starts.get(item.stream_id,item.sequence-1),item.sequence-1)
        return tuple(sorted(starts.items()))


class ObserverDispatcher:
    """One daemon callback lane; a stuck callback never spawns replacements."""
    def __init__(self, callback, *, capacity, byte_capacity, diagnostic_capacity):
        self._callback = callback
        self._capacity, self._byte_capacity = capacity, byte_capacity
        self._condition = Condition()
        self._queue, self._diagnostics = deque(), deque(maxlen=diagnostic_capacity)
        self._bytes = self._delivered = self._failed = self._dropped = 0
        self._active_bytes = 0
        self._first_missed = self._active_coordinate = None
        self._closed = self._active = self._truncated = False
        self._thread = Thread(target=self._dispatch,name="stratbox-observer",daemon=True)
        self._thread.start()

    def _miss(self, fact, code):
        if self._first_missed is None: self._first_missed = (fact.stream_id,fact.sequence)
        if len(self._diagnostics) == self._diagnostics.maxlen: self._truncated = True
        self._diagnostics.append(ObserverDiagnostic(code,fact.stream_id,fact.sequence,fact.run_id))

    def offer(self, fact):
        size = _size(fact)
        with self._condition:
            if self._closed or len(self._queue) >= self._capacity or self._bytes+self._active_bytes+size > self._byte_capacity:
                self._dropped += 1
                self._miss(fact,"observation.optional_sink_closed" if self._closed else "observation.optional_sink_overflow")
                return False
            self._queue.append((fact,size)); self._bytes += size
            self._condition.notify()
            return True

    def _dispatch(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda:self._queue or self._closed)
                if self._closed: return
                fact,size = self._queue.popleft(); self._bytes -= size; self._active = True; self._active_bytes = size
                self._active_coordinate = (fact.stream_id,fact.sequence)
            try:
                self._callback(fact)
            except BaseException:
                with self._condition:
                    self._failed += 1
                    self._miss(fact,"observation.optional_sink_failed")
            else:
                with self._condition: self._delivered += 1
            finally:
                with self._condition:
                    self._active = False
                    self._active_bytes = 0
                    self._active_coordinate = None
                    self._condition.notify_all()
                fact = None

    def status(self):
        with self._condition:
            return ObserverStatus(len(self._queue),self._bytes,self._active,self._active_bytes,self._delivered,
                self._failed,self._dropped,self._closed,tuple(self._diagnostics),self._truncated,
                self._first_missed,self._active_coordinate)

    def close(self):
        """Detach queued facts immediately; an active optional callback is not joined."""
        with self._condition:
            self._closed = True
            while self._queue:
                fact,_ = self._queue.popleft(); self._dropped += 1
                self._miss(fact,"observation.optional_sink_closed")
            self._bytes = 0
            self._condition.notify_all()
