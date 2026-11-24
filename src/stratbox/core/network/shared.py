"""Scoped shared HTTP work, independent of operation and source identities.

Registries return producer/follower claims without scheduling threads. A graph
coordinator can attach followers to the Future and dispatch only its producer.
The transport facade also supports direct synchronous callers; their waits
remain bounded by each caller's deadline and cancellation.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, TimeoutError as FutureTimeout
from contextlib import contextmanager
from dataclasses import dataclass, field, fields, is_dataclass, replace
from hashlib import sha256
from threading import RLock
from time import monotonic, sleep
from tempfile import TemporaryFile
from os import pread
from typing import Callable, Mapping
from uuid import uuid4

from stratbox.core.network.contracts import HttpFailure, HttpRequest, HttpResponse, HttpStreamResponse, public_https_parts
from stratbox.shared.data.source_context import SourceUse
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def _token(value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError("network.scope_invalid")
    return value


@dataclass(frozen=True, slots=True)
class AccessScope:
    """Safe references to a provider's access configuration, never credentials."""
    provider_id: str = "http.local"
    scope_id: str = "public"
    generation: int = 0
    profile: str = "local"
    route_identity: str | None = None
    configuration_identity: str | None = None

    def __post_init__(self):
        for value in (self.provider_id, self.scope_id, self.profile):
            _token(value)
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("network.scope_generation_invalid")
        for value in (self.route_identity, self.configuration_identity):
            if value is not None:
                _token(value)

    @property
    def identity(self):
        return sha256(canonical_manifest_bytes({name: getattr(self, name)
            for name in self.__dataclass_fields__})).hexdigest()


def request_identity(request: HttpRequest, *, provider_id: str,
                     profile: str = "local", scope_id: str | None = None,
                     generation: int = 0, route_identity: str | None = None,
                     configuration_identity: str | None = None) -> str:
    """Exact representation identity; URL syntax/order and body bytes are kept."""
    value = {
        "method": request.method, "url": request.url,
        "headers": dict(request.headers),
        "form": list(request.form_fields.items()) if request.form_fields is not None else None,
        "body": ByteIdentity.of(request.body).sha256 if request.body is not None else None,
        "provider": provider_id, "profile": profile, "scope": scope_id,
        "generation": generation, "route": route_identity,
        "configuration": configuration_identity,
    }
    return sha256(canonical_manifest_bytes(value)).hexdigest()


def acquisition_key(request: HttpRequest, scope: AccessScope, observation_id: str,
                    *, immutable_identity: ByteIdentity | None = None) -> str:
    """Share only equal representations with compatible admission and freshness.

    Observation IDs are explicit run/freshness scopes. Independent fresh runs
    therefore do not reuse a stable URL. An immutable byte identity explicitly
    opts into reuse across observation scopes and is checked after receiving.
    """
    _token(observation_id)
    representation = request_identity(request, provider_id=scope.provider_id,
        profile=scope.profile, scope_id=scope.scope_id, generation=scope.generation,
        route_identity=scope.route_identity, configuration_identity=scope.configuration_identity)
    return sha256(canonical_manifest_bytes({
        "representation": representation,
        "observation": observation_id if immutable_identity is None else None,
        "immutable": None if immutable_identity is None else {
            "sha256": immutable_identity.sha256, "size": immutable_identity.size},
        "admission": {
            "endpoints": [{"host": item.host, "path": item.path, "subtree": item.subtree,
                           "allow_query": item.allow_query} for item in request.endpoints],
            "max_response_bytes": request.max_response_bytes,
            "max_redirects": request.max_redirects, "post_redirect": request.post_redirect,
            "read_only_post": request.read_only_post,
            # Different physical-attempt bounds need independent work. A
            # consumer may still use a shorter wait on a coordinator claim.
            "deadline_seconds": str(request.deadline_seconds),
        },
    })).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedMaterial:
    """One physical representation with independent relational source uses."""
    acquisition_id: str
    request_sha256: str
    response: HttpResponse
    uses: tuple[SourceUse, ...] = ()

    @property
    def identity(self):
        return ByteIdentity.of(self.response.body)

    def with_use(self, use: SourceUse):
        if not isinstance(use, SourceUse):
            raise ValueError("source.use_invalid")
        if use.coordinate.material_identity not in (None, self.identity):
            raise ValueError("source.material_identity_mismatch")
        return self if use in self.uses else replace(self, uses=(*self.uses, use))


@dataclass(frozen=True, slots=True)
class SharedClaim:
    key: str
    consumer_id: str
    shared_work_id: str
    future: Future = field(repr=False, compare=False)
    producer: bool = False


@dataclass
class _Work:
    future: Future
    shared_work_id: str
    consumers: dict[str, Callable[[], bool] | None]
    cache: bool = False
    size: int = 0
    expires_at: float | None = None
    invalidated: bool = False


class SharedWorkRegistry:
    """Thread-safe claims; cancellation removes a use, not another use's work."""

    def __init__(self, *, max_entries: int = 64, max_bytes: int = 256 * 1024 * 1024):
        if type(max_entries) is not int or max_entries < 1 or type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("network.shared_capacity_invalid")
        self._lock = RLock()
        self._work = OrderedDict()
        self._max_entries, self._max_bytes = max_entries, max_bytes
        self._bytes = 0
        self._closed = False

    def claim(self, key: str, consumer_id: str, *, cancelled=None) -> SharedClaim:
        _token(key)
        _token(consumer_id)
        with self._lock:
            if self._closed:
                raise RuntimeError("Shared work registry is closed")
            work = self._work.get(key)
            if work is not None and work.future.done() and (
                not work.cache or (work.expires_at is not None and work.expires_at <= monotonic())
            ):
                self._discard(key)
                work = None
            producer = work is None
            if producer:
                self._evict()
                work = _Work(Future(), "shared-" + uuid4().hex, {})
                self._work[key] = work
            elif consumer_id in work.consumers:
                raise ValueError("network.consumer_duplicate")
            work.consumers[consumer_id] = cancelled
            self._work.move_to_end(key)
            return SharedClaim(key, consumer_id, work.shared_work_id, work.future, producer)

    def complete(self, claim: SharedClaim, value, *, cache: bool = True, size: int = 0,
                 ttl_seconds: float | None = None):
        if not claim.producer:
            raise ValueError("network.producer_required")
        if type(size) is not int or size < 0 or (ttl_seconds is not None and ttl_seconds <= 0):
            raise ValueError("network.shared_result_invalid")
        with self._lock:
            work = self._matching(claim)
            if work.future.done():
                raise ValueError("network.shared_already_completed")
            work.cache = cache and not self._closed and not work.invalidated and size <= self._max_bytes
            work.size = size if work.cache else 0
            work.expires_at = None if ttl_seconds is None else monotonic() + ttl_seconds
            self._bytes += work.size
            # Future callbacks may enter the registry; RLock preserves a
            # consistent completed entry before any callback is invoked.
            work.future.set_result(value)
            self._evict()

    def fail(self, claim: SharedClaim, error: BaseException):
        if not claim.producer:
            raise ValueError("network.producer_required")
        with self._lock:
            work = self._matching(claim)
            work.cache = False
            work.future.set_exception(error)

    def detach(self, claim: SharedClaim):
        with self._lock:
            work = self._work.get(claim.key)
            if work is not None and work.shared_work_id == claim.shared_work_id:
                work.consumers.pop(claim.consumer_id, None)
                if work.future.done() and not work.consumers and not work.cache:
                    self._discard(claim.key)
                self._evict()

    def should_cancel(self, claim: SharedClaim) -> bool:
        with self._lock:
            work = self._work.get(claim.key)
            if work is None or work.shared_work_id != claim.shared_work_id:
                return True
            callbacks = tuple(work.consumers.items())
            if self._closed:
                return True
        active = False
        for consumer, callback in callbacks:
            if callback is None or not callback():
                active = True
            else:
                with self._lock:
                    work.consumers.pop(consumer, None)
        return not active

    def invalidate(self, prefix: str = ""):
        """Drop completed cached work; in-flight consumers retain their claims."""
        with self._lock:
            for key, work in tuple(self._work.items()):
                if key.startswith(prefix):
                    work.cache = False
                    work.invalidated = True
                    if work.future.done() and not work.consumers:
                        self._discard(key)

    def close(self):
        with self._lock:
            self._closed = True
            for key, work in tuple(self._work.items()):
                work.cache = False
                work.invalidated = True
                if work.future.done():
                    self._discard(key)

    def _matching(self, claim):
        work = self._work.get(claim.key)
        if work is None or work.shared_work_id != claim.shared_work_id:
            raise ValueError("network.shared_claim_stale")
        return work

    def _discard(self, key):
        work = self._work.pop(key)
        self._bytes -= work.size
        if work.future.done() and not work.future.cancelled():
            try:
                cleanup = getattr(work.future.result(), "_shared_cleanup", None)
                if cleanup is not None:
                    cleanup()
            except BaseException:
                pass

    def _evict(self):
        for key, work in tuple(self._work.items()):
            if len(self._work) <= self._max_entries and self._bytes <= self._max_bytes:
                break
            if work.future.done() and not work.consumers:
                self._discard(key)

    def snapshot(self):
        with self._lock:
            return {"entries": len(self._work), "retained_bytes": self._bytes,
                    "running": sum(not work.future.done() for work in self._work.values()),
                    "consumers": sum(len(work.consumers) for work in self._work.values())}


class AccessScopes:
    """Generation-aware preparation claims, shared by compatible consumers."""
    def __init__(self):
        self.preparations = SharedWorkRegistry()
        self._lock = RLock()
        self._generations = {}
        self._expirations = {}

    def current(self, scope: AccessScope) -> AccessScope:
        with self._lock:
            base = self._base(scope)
            generation = max(scope.generation, self._generations.get(base, 0))
            expiry = self._expirations.get(base)
            if expiry is not None and expiry[0] == generation and expiry[1] <= monotonic():
                generation += 1
                self._generations[base] = generation
                self._expirations.pop(base, None)
            return replace(scope, generation=generation)

    def invalidate(self, scope: AccessScope) -> AccessScope:
        with self._lock:
            generation = self.current(scope).generation + 1
            self._generations[self._base(scope)] = generation
            self._expirations.pop(self._base(scope), None)
            return replace(scope, generation=generation)

    def claim(self, scope: AccessScope, method_id: str, parameters: Mapping,
              consumer_id: str, *, cancelled=None):
        scope = self.current(scope)
        key = sha256(canonical_manifest_bytes({"scope": scope.identity,
            "method": _token(method_id), "parameters": dict(parameters)})).hexdigest()
        return scope, self.preparations.claim(key, consumer_id, cancelled=cancelled)

    def complete(self, scope: AccessScope, claim: SharedClaim, value, *, ttl_seconds=None):
        """Publish access readiness and expire its generation atomically."""
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("network.preparation_expiry_invalid")
        with self._lock:
            if ttl_seconds is not None:
                self._expirations[self._base(scope)] = (scope.generation, monotonic() + ttl_seconds)
            self.preparations.complete(claim, value, ttl_seconds=ttl_seconds)

    @staticmethod
    def _base(scope):
        return replace(scope, generation=0).identity


class _StagedTransfer:
    """Disk-backed immutable bytes; readers use private offsets and small chunks."""
    def __init__(self, network, covered_owner=None):
        self.network = network
        requirements = (network.staging_ledger.requirements(covered_owner)
            if network.staging_ledger is not None and covered_owner is not None else {})
        self.covered_limit = requirements.get("staging_bytes")
        self.file = TemporaryFile(mode="w+b")
        self.owner = "network-stage:" + uuid4().hex
        self.size = 0
        self.response = None
        self.identity = None
        self.closed = False

    def write(self, chunk):
        size = max(self.size, self.file.tell() + len(chunk))
        with self.network._stage_lock:
            delta = size - self.size
            if self.network._stage_bytes + delta > self.network.max_staging_bytes:
                raise OSError("resource.staging_bytes")
            ledger = self.network.staging_ledger
            if self.covered_limit is not None:
                if size > self.covered_limit:
                    raise OSError("resource.staging_bytes")
            elif ledger is not None and not ledger.replace(self.owner, {"staging_bytes": size}):
                raise OSError("resource.staging_bytes")
            written = self.file.write(chunk)
            self.network._stage_bytes += delta
            self.size = size
            return written

    def seek(self, offset, whence=0):
        return self.file.seek(offset, whence)

    def tell(self):
        return self.file.tell()

    def truncate(self, size=None):
        size = self.file.tell() if size is None else size
        with self.network._stage_lock:
            self.file.truncate(size)
            self.network._stage_bytes -= self.size - size
            self.size = size
            if self.network.staging_ledger is not None and self.covered_limit is None:
                self.network.staging_ledger.replace(self.owner, {"staging_bytes": size})

    def copy_into(self, sink, *, cancelled=None, deadline=None):
        self.file.flush()
        offset = 0
        while offset < self.size:
            if cancelled is not None and cancelled():
                return HttpFailure("cancelled", "body")
            if deadline is not None and monotonic() >= deadline:
                return HttpFailure("timeout", "body")
            chunk = pread(self.file.fileno(), min(65536, self.size - offset), offset)
            if not chunk or sink.write(chunk) != len(chunk):
                return HttpFailure("staging_failed", "body")
            offset += len(chunk)
        return None

    def _shared_cleanup(self):
        if self.closed:
            return
        self.closed = True
        self.file.close()
        with self.network._stage_lock:
            self.network._stage_bytes -= self.size
            if self.network.staging_ledger is not None and self.covered_limit is None:
                self.network.staging_ledger.release(self.owner)
            self.size = 0


class SessionNetwork:
    """Own session-created pools and scope shared work to explicit observations."""
    def __init__(self, transport=None, *, owned: bool | None = None,
                 per_origin: int = 2, max_entries: int = 64,
                 max_bytes: int = 256 * 1024 * 1024, journal=None,
                 max_staging_bytes: int | None = None, staging_ledger=None):
        from stratbox.core.network.transport import RequestsTransport
        self.transport = transport if transport is not None else RequestsTransport(per_origin=per_origin)
        self.owned = transport is None if owned is None else owned
        self.acquisitions = SharedWorkRegistry(max_entries=max_entries, max_bytes=max_bytes)
        self.staging = SharedWorkRegistry(max_entries=max_entries, max_bytes=max_bytes)
        self.max_staging_bytes = max_bytes if max_staging_bytes is None else max_staging_bytes
        self.staging_ledger = staging_ledger
        self._stage_lock, self._stage_bytes = RLock(), 0
        self.scopes = AccessScopes()
        self._closed = False
        self.journal = journal

    def __enter__(self):
        if self._closed:
            raise RuntimeError("Session network is closed")
        return self

    def __exit__(self, *exc):
        self.close()

    def transport_for(self, observation_id: str, *, scope: AccessScope | None = None,
                      reservation_owner=None, ledger=None, scheduler_owned_retries=True,
                      immutable_identity: ByteIdentity | None = None, run_id=None, task_id=None):
        if self._closed:
            raise RuntimeError("Session network is closed")
        if (reservation_owner is None) != (ledger is None):
            raise ValueError("network.reservation_context_incomplete")
        return SharedHttpTransport(self, _token(observation_id), scope or AccessScope(),
            reservation_owner, ledger, scheduler_owned_retries, immutable_identity, run_id, task_id)

    def _provider_scope(self, scope: AccessScope) -> AccessScope:
        provided = getattr(self.transport, "scope", None)
        if provided is None:
            provided = getattr(self.transport, "access_scope", None)
        if not isinstance(provided, AccessScope):
            return scope
        return replace(scope,
            scope_id=provided.scope_id if scope.scope_id == "public" else scope.scope_id,
            generation=max(scope.generation, provided.generation),
            route_identity=scope.route_identity or provided.route_identity,
            configuration_identity=scope.configuration_identity or provided.configuration_identity)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.acquisitions.close()
        self.staging.close()
        self.scopes.preparations.close()
        if self.owned:
            close = getattr(self.transport, "close", None)
            if callable(close):
                close()


class SharedHttpTransport:
    """A run-scoped facade; bytes remain distinct from source-specific use."""
    shares_http_requests = True

    def __init__(self, network, observation_id, scope, reservation_owner=None,
                 ledger=None, scheduler_owned_retries=True, immutable_identity=None, run_id=None, task_id=None):
        self.network, self.observation_id, self._scope_base = network, observation_id, scope
        self.reservation_owner, self.ledger = reservation_owner, ledger
        self.scheduler_owned_retries = scheduler_owned_retries
        self.immutable_identity = immutable_identity
        self.run_id, self.task_id = run_id, task_id

    @property
    def scope(self):
        return self.network.scopes.current(self.network._provider_scope(self._scope_base))

    @property
    def accounts_http_budget(self):
        return getattr(self.network.transport, "accounts_http_budget", False)

    def route_for(self, request):
        route = getattr(self.network.transport, "route_for", None)
        return route(request) if callable(route) else None

    def accepts_response(self, request, response):
        accepts = getattr(self.network.transport, "accepts_response", None)
        if callable(accepts):
            return accepts(request, response)
        host = public_https_parts(response.effective_locator_safe).hostname
        return response.route_id is None and any(item.host == host for item in request.endpoints)

    def exchange_identified(self, request, identity_request, *, cancelled=None):
        return self._exchange(request, identity_request, cancelled=cancelled)

    def exchange(self, request, *, cancelled=None):
        return self._exchange(request, request, cancelled=cancelled)

    def _exchange(self, request, identity_request, *, cancelled=None):
        if not request.permits(request.url):
            return HttpFailure("destination_forbidden", "admission")
        if self.network._closed:
            return HttpFailure("capability_missing", "admission")
        if cancelled is not None and cancelled():
            return HttpFailure("cancelled", "admission")
        if request.method != "GET" and not request.read_only_post:
            return self._perform(request, cancelled)
        scope = self.network.scopes.current(self.scope)
        key = acquisition_key(identity_request, scope, self.observation_id,
                              immutable_identity=self.immutable_identity)
        registry = self.network.acquisitions
        consumer = uuid4().hex
        claim = registry.claim(key, consumer, cancelled=cancelled)
        deadline = monotonic() + request.deadline_seconds
        self._emit("shared_work.attached", claim)
        if not claim.producer and claim.future.done():
            self._emit("shared_work.reused", claim, state="reused")
        try:
            if claim.producer:
                self._emit("shared_work.started", claim, state="running")
                try:
                    response = self._perform(request, lambda: registry.should_cancel(claim))
                    if isinstance(response, HttpResponse) and self.immutable_identity is not None:
                        if ByteIdentity.of(response.body) != self.immutable_identity:
                            response = HttpFailure("invalid_http", "body")
                    if isinstance(response, HttpResponse) and response.shared_work_id is None:
                        response = replace(response, shared_work_id=claim.shared_work_id)
                    cache = isinstance(response, HttpResponse) and response.status_code == 200
                    registry.complete(claim, response, cache=cache,
                                      size=len(response.body) if cache else 0)
                    successful = isinstance(response, HttpResponse) and (
                        200 <= response.status_code < 300 or response.status_code == 304)
                    outcome = "succeeded" if successful else ("cancelled" if isinstance(response, HttpFailure)
                        and response.reason == "cancelled" else "failed")
                    self._emit("shared_work.finished", claim, state="finished", outcome=outcome)
                except BaseException as error:
                    if not claim.future.done():
                        registry.fail(claim, error)
                    self._emit("shared_work.finished", claim, state="finished", outcome="failed")
                    raise
            while True:
                if cancelled is not None and cancelled():
                    return HttpFailure("cancelled", "admission")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return HttpFailure("timeout", "admission")
                try:
                    result = claim.future.result(timeout=min(0.05, remaining))
                    if isinstance(result, HttpResponse) and not claim.producer:
                        # Every logical consumer retains the representation's
                        # bytes and observation time. Only the physical owner
                        # reports the wire expenditure for this acquisition.
                        result = replace(result, shared_reused=True, wire_size=0)
                    return result
                except FutureTimeout:
                    continue
        finally:
            registry.detach(claim)
            self._emit("shared_work.detached", claim)

    def exchange_into_identified(self, request, identity_request, sink, *, cancelled=None):
        return self._exchange_into(request, identity_request, sink, cancelled=cancelled)

    def exchange_into(self, request, sink, *, cancelled=None):
        return self._exchange_into(request, request, sink, cancelled=cancelled)

    def _exchange_into(self, request, identity_request, sink, *, cancelled=None):
        if not request.permits(request.url):
            return HttpFailure("destination_forbidden", "admission")
        if self.network._closed:
            return HttpFailure("capability_missing", "admission")
        registry = self.network.staging
        key = "stage:" + acquisition_key(identity_request, self.scope, self.observation_id,
            immutable_identity=self.immutable_identity)
        if request.method != "GET" and not request.read_only_post:
            key += ":" + uuid4().hex
        claim = registry.claim(key, uuid4().hex, cancelled=cancelled)
        deadline, accepted = monotonic() + request.deadline_seconds, False
        self._emit("shared_work.attached", claim)
        try:
            if claim.producer:
                stage = _StagedTransfer(self.network, self.reservation_owner)
                self._emit("shared_work.started", claim, state="running")
                try:
                    response = self._perform_into(request, stage,
                        lambda: registry.should_cancel(claim))
                    if isinstance(response, HttpStreamResponse):
                        if self.immutable_identity is not None and response.identity != self.immutable_identity:
                            response = HttpFailure("invalid_http", "body")
                    if isinstance(response, HttpStreamResponse):
                        stage.response = replace(response.response, shared_work_id=claim.shared_work_id)
                        stage.identity = response.identity
                        stage.file.flush()
                        registry.complete(claim, stage,
                            cache=stage.response.status_code == 200 and stage.covered_limit is None,
                            size=stage.size)
                        self._emit("shared_work.finished", claim, state="finished", outcome="succeeded")
                    else:
                        stage._shared_cleanup()
                        registry.complete(claim, response, cache=False)
                        self._emit("shared_work.finished", claim, state="finished", outcome="failed")
                except BaseException as error:
                    stage._shared_cleanup()
                    if not claim.future.done():
                        registry.fail(claim, error)
                    raise
            while not claim.future.done():
                if cancelled is not None and cancelled():
                    return HttpFailure("cancelled", "admission")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return HttpFailure("timeout", "admission")
                try:
                    claim.future.result(timeout=min(0.05, remaining))
                except FutureTimeout:
                    pass
            value = claim.future.result()
            if isinstance(value, HttpFailure):
                return value
            failure = value.copy_into(sink, cancelled=cancelled, deadline=deadline)
            if failure is not None:
                return failure
            accepted = True
            response = value.response if claim.producer else replace(value.response, shared_reused=True, wire_size=0)
            return HttpStreamResponse(response, value.identity)
        except OSError:
            return HttpFailure("staging_failed", "body")
        finally:
            registry.detach(claim)
            self._emit("shared_work.detached", claim)
            if not accepted:
                sink.seek(0)
                sink.truncate(0)

    def _perform_into(self, request, sink, cancelled):
        from stratbox.core.network.transport import _hop_admission
        token = _hop_admission.set(self._admit_hop if self.ledger is not None else None)
        try:
            if request.budget is not None and not self.accounts_http_budget:
                request.budget.charge("requests", 1)
            stream = getattr(self.network.transport, "exchange_into", None)
            if stream is not None:
                return stream(request, sink, cancelled=cancelled)
            # A bytes-only injected provider still has its declared bound. The
            # shipped transport streams directly into shared disk staging.
            response = self.network.transport.exchange(request, cancelled=cancelled)
            if isinstance(response, HttpFailure):
                return response
            for start in range(0, len(response.body), 65536):
                chunk = response.body[start:start + 65536]
                if sink.write(chunk) != len(chunk):
                    return HttpFailure("staging_failed", "body")
            return HttpStreamResponse(replace(response, body=b""), ByteIdentity.of(response.body))
        finally:
            _hop_admission.reset(token)

    def _emit(self, kind, claim, **fields):
        journal = self.network.journal
        if journal is None:
            return
        from stratbox.core.execution.contracts import Correlation
        from stratbox.core.observability.records.contracts import ObjectRef
        correlation = Correlation(session_id=journal.session_id, run_id=self.run_id,
            task_id=self.task_id, shared_work_id=claim.shared_work_id)
        references = (() if self.run_id is None else
            (ObjectRef(namespace="run", object_id=self.run_id, relation="consumer"),))
        journal.emit(kind, correlation, references=references, **fields)

    def _perform(self, request, cancelled):
        from stratbox.core.network.transport import _hop_admission
        token = _hop_admission.set(self._admit_hop if self.ledger is not None else None)
        try:
            if request.budget is not None and not self.accounts_http_budget:
                request.budget.charge("requests", 1)
            return self.network.transport.exchange(request, cancelled=cancelled)
        finally:
            _hop_admission.reset(token)

    def _admit_hop(self, url, seconds, cancelled):
        key = "origin:https://" + public_https_parts(url).hostname
        requirements = self.ledger.requirements(self.reservation_owner)
        origins = {name: value for name, value in requirements.items() if name.startswith("origin:")}
        if origins == {key: 1}:
            return
        base = {name: value for name, value in requirements.items() if not name.startswith("origin:")}
        # Release the previous hop's origin before waiting for the next.
        if not self.ledger.replace(self.reservation_owner, base):
            raise RuntimeError("network.origin_release_failed")
        deadline = monotonic() + seconds
        while not self.ledger.replace(self.reservation_owner, {**base, "network": 1, key: 1}):
            from stratbox.core.network.transport import _ReadFailure
            if cancelled is not None and cancelled():
                raise _ReadFailure("cancelled")
            if monotonic() >= deadline:
                raise _ReadFailure("timeout")
            sleep(min(0.01, max(0, deadline - monotonic())))


def network_resources(parameters) -> dict[str, int]:
    """Known request origins can be reserved by the coordinator before dispatch."""
    origins = set()
    seen = set()

    def member(name, value):
        if name in {"url", "locator", "index_url", "page_url"} and isinstance(value, str):
            try:
                origins.add("origin:https://" + public_https_parts(value).hostname)
            except ValueError:
                pass
        else:
            visit(value)

    def visit(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, HttpRequest):
            origins.add("origin:https://" + public_https_parts(value.url).hostname)
        elif isinstance(value, Mapping):
            for name, item in value.items():
                member(name, item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                visit(item)
        elif is_dataclass(value) and not isinstance(value, type):
            # Iterate actual fields. Temporary dicts can be collected while
            # traversing and have their IDs reused, corrupting the cycle guard.
            for item in fields(value):
                member(item.name, getattr(value, item.name))

    visit(parameters)
    return {"network": 1, **dict.fromkeys(origins, 1)} if origins else {}
