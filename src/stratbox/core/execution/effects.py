"""Transient, invocation-scoped effect receipt accounting.

The resource owner supplies evidence. This accumulator only checks consistency;
it does not perform an effect, authenticate a receipt, or reconcile external state.
"""
from __future__ import annotations

from dataclasses import replace
from collections.abc import Sequence
from dataclasses import dataclass
from threading import RLock
from typing import Callable

from stratbox.core.execution.contracts import Diagnostic, EffectKey, EffectReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.identifiers import safe_token


@dataclass(frozen=True, slots=True)
class EffectIntent:
    """Pinned inputs and receiving resource that identify one physical effect."""

    run_id: str
    scope_id: str
    work_id: str
    kind: str
    effect_id: str
    resource: str
    input_basis: str | None = None
    expected_revision: str | None = None
    source_revision: str | None = None
    identity: ByteIdentity | None = None

    def __post_init__(self):
        for name in ("run_id", "scope_id", "work_id", "kind", "effect_id"):
            safe_token(getattr(self, name))
        if not isinstance(self.resource, str) or not self.resource or "\x00" in self.resource:
            raise ValueError("effect.resource_invalid")
        for name in ("input_basis", "expected_revision", "source_revision"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError("effect.revision_invalid")
        if self.identity is not None and not isinstance(self.identity, ByteIdentity):
            raise ValueError("effect.identity_invalid")

    @property
    def key(self):
        return self.run_id, self.scope_id, self.kind, self.effect_id

    @property
    def fingerprint(self):
        return ByteIdentity.of(canonical_manifest_bytes({
            name: ((value.sha256, value.size) if isinstance(value, ByteIdentity) else value)
            for name in self.__dataclass_fields__
            for value in (getattr(self, name),)
        })).sha256

    @property
    def physical_fingerprint(self):
        return ByteIdentity.of(canonical_manifest_bytes({
            name: ((value.sha256, value.size) if isinstance(value, ByteIdentity) else value)
            for name in ("kind", "effect_id", "resource", "input_basis", "expected_revision", "source_revision", "identity")
            for value in (getattr(self, name),)
        })).sha256


@dataclass(frozen=True, slots=True)
class EffectRecord:
    intent: EffectIntent
    attempt_id: str
    receipt: EffectReceipt
    revision: int
    current: bool


class EffectAuthorityError(ValueError):
    pass


class EffectAuthority:
    """Session attempt fencing and addressable physical effect evidence.

    A precommit fence prevents an obsolete attempt from starting a write. Once
    a provider starts a write its outcome remains observable even if the
    consumer cancels. Receiving providers still own atomic revision checks;
    this local authority does not claim distributed fencing or persistence.
    """

    def __init__(self, *, max_records=16384):
        if type(max_records) is not int or max_records < 1:
            raise ValueError("effect.capacity_invalid")
        self.max_records = max_records
        self._lock = RLock()
        self._attempts = {}
        self._runs = {}
        self._resources = {}
        self._records = {}
        self._physical = {}
        self._revision = 0
        self._run_revision = 0

    def begin_run(self, run_id):
        safe_token(run_id)
        with self._lock:
            if run_id not in self._runs:
                self._run_revision += 1
                self._runs[run_id] = self._run_revision
            return self._runs[run_id]

    def begin_attempt(self, run_id, scope_id, work_id, attempt_id):
        for token in (run_id, scope_id, work_id, attempt_id):
            safe_token(token)
        with self._lock:
            self.begin_run(run_id)
            self._attempts[run_id, scope_id, work_id] = attempt_id

    def invalidate_attempt(self, run_id, scope_id, work_id, attempt_id=None):
        with self._lock:
            key = run_id, scope_id, work_id
            if attempt_id is None or self._attempts.get(key) == attempt_id:
                self._attempts[key] = None

    def _current(self, intent, attempt_id):
        attempt = intent.run_id, intent.scope_id, intent.work_id
        if self._attempts.get(attempt) != attempt_id:
            return False
        rank = self._runs[intent.run_id]
        resource_rank = self._resources.get(intent.resource, (0, None))[0]
        return rank >= resource_rank

    def lookup(self, run_id, scope_id, effect_id, *, kind=None):
        with self._lock:
            if kind is not None:
                record = self._records.get((run_id, scope_id, kind, effect_id))
            else:
                matches = [record for record in self._records.values()
                           if (record.intent.run_id, record.intent.scope_id, record.intent.effect_id)
                           == (run_id, scope_id, effect_id)]
                if len(matches) > 1:
                    raise EffectAuthorityError("effect.kind_required")
                record = matches[0] if matches else None
            return self._observed(record) if record is not None else None

    def lookup_effect(self, resource, effect_id, *, kind=None):
        with self._lock:
            if kind is not None:
                key = self._physical.get((resource, kind, effect_id))
                record = self._records.get(key)
            else:
                matches = [record for record in self._records.values()
                           if (record.intent.resource, record.intent.effect_id) == (resource, effect_id)
                           and self._physical.get((resource, record.intent.kind, effect_id)) == record.intent.key]
                if len(matches) > 1:
                    raise EffectAuthorityError("effect.kind_required")
                record = matches[0] if matches else None
            return self._observed(record) if record is not None else None

    def _observed(self, record):
        current = (self._current(record.intent, record.attempt_id)
                   and self._resources.get(record.intent.resource, (None, None))[1] == record.intent.key)
        return replace(record, current=current)

    def snapshot(self):
        with self._lock:
            return tuple(self._observed(record) for record in self._records.values())

    def release_run(self, run_id):
        """Release known evidence only after the host/result owner is done.

        Unknown effects retain their recovery obligation and cannot be evicted
        to make room for new writes.
        """
        with self._lock:
            if any(record.intent.run_id == run_id and record.receipt.state == "unknown"
                   for record in self._records.values()):
                raise EffectAuthorityError("effect.unresolved_obligation")
            for key in tuple(self._records):
                if key[0] == run_id:
                    record = self._records[key]
                    self._physical.pop((record.intent.resource, record.intent.kind, record.intent.effect_id), None)
                    del self._records[key]
            for key in tuple(self._attempts):
                if key[0] == run_id:
                    del self._attempts[key]
            self._runs.pop(run_id, None)

    def commit(self, intent: EffectIntent, attempt_id: str,
               action: Callable[[], EffectReceipt]) -> EffectReceipt:
        """Record unknown before the provider boundary; never repeat unknown."""
        with self._lock:
            previous = self._records.get(intent.key)
            if previous is None:
                previous = self._records.get(self._physical.get((intent.resource, intent.kind, intent.effect_id)))
            if previous is not None:
                if previous.intent.physical_fingerprint != intent.physical_fingerprint:
                    raise EffectAuthorityError("effect.identity_conflict")
                if previous.receipt.state == "confirmed":
                    return previous.receipt
                if previous.receipt.state == "unknown":
                    raise EffectAuthorityError("effect.reconciliation_required")
            if not self._current(intent, attempt_id):
                raise EffectAuthorityError("effect.stale_attempt")
            if previous is None and len(self._records) >= self.max_records:
                raise EffectAuthorityError("effect.retention_capacity")
            self._resources[intent.resource] = self._runs[intent.run_id], intent.key
            self._revision += 1
            receipt = EffectReceipt(intent.kind, "unknown", effect_id=intent.effect_id,
                                    stage="commit", identity=intent.identity,
                                    reconciliation_owner="effect.authority")
            self._records[intent.key] = EffectRecord(intent, attempt_id, receipt,
                                                     self._revision, True)
            self._physical[intent.resource, intent.kind, intent.effect_id] = intent.key
        # Provider code runs without the coordinator's authority lock. Its CAS
        # must make expected_revision checking and replacement one operation.
        try:
            receipt = action()
            if (not isinstance(receipt, EffectReceipt) or receipt.kind != intent.kind
                    or receipt.effect_id != intent.effect_id
                    or (intent.identity is not None and receipt.identity not in {None, intent.identity})):
                raise ValueError("effect.receipt_mismatch")
        except Exception:
            receipt = EffectReceipt(intent.kind, "unknown", effect_id=intent.effect_id,
                                    stage="commit", identity=intent.identity,
                                    reconciliation_owner="effect.authority")
        with self._lock:
            self._revision += 1
            current = self._current(intent, attempt_id) and self._resources.get(intent.resource, (None, None))[1] == intent.key
            self._records[intent.key] = EffectRecord(intent, attempt_id, receipt,
                                                     self._revision, current)
        return receipt

    def reconcile(self, run_id, scope_id, effect_id, receipt: EffectReceipt, *, expected_revision: int):
        """Apply competent provider read-back against one exact ledger revision."""
        with self._lock:
            previous = self._records[run_id, scope_id, receipt.kind, effect_id]
            if previous.revision != expected_revision:
                raise EffectAuthorityError("effect.reconciliation_conflict")
            if (receipt.state == "unknown" or receipt.kind != previous.intent.kind
                    or receipt.effect_id != effect_id
                    or (previous.intent.identity is not None and receipt.identity not in {None, previous.intent.identity})):
                raise EffectAuthorityError("effect.reconciliation_invalid")
            if previous.receipt.state != "unknown" and receipt != previous.receipt:
                raise EffectAuthorityError("effect.reconciliation_conflict")
            self._revision += 1
            record = EffectRecord(previous.intent, previous.attempt_id, receipt, self._revision,
                                  self._current(previous.intent, previous.attempt_id))
            self._records[previous.intent.key] = record
            return record


class _EffectView(Sequence[EffectReceipt]):
    """Live read-only view; avoids copying all receipts on each handler read."""

    def __init__(self, accumulator: _EffectAccumulator) -> None:
        self._accumulator = accumulator

    def __len__(self) -> int:
        return len(self._accumulator._items)

    def __getitem__(self, index):
        return self._accumulator._items[index]

    def __iter__(self):
        return iter(self._accumulator._items)


class _EffectAccumulator:
    def __init__(self) -> None:
        self._items: list[EffectReceipt] = []
        self._indexes: dict[EffectKey, int] = {}
        self._conflicts: dict[EffectKey, Diagnostic] = {}
        self._view = _EffectView(self)

    def view(self) -> Sequence[EffectReceipt]:
        return self._view

    @staticmethod
    def _consistent(previous: EffectReceipt, incoming: EffectReceipt) -> bool:
        # Stage is a changing observation label (commit -> verify), not identity.
        for field in ("reference", "identity", "guarantee", "reconciliation_owner"):
            old, new = getattr(previous, field), getattr(incoming, field)
            if old is not None and new is not None and old != new:
                return False
        return previous.state == "unknown" or previous.state == incoming.state

    def register(self, receipt: EffectReceipt) -> None:
        if receipt.effect_id is None:
            # Anonymous receipts are *independent* physical observations.
            self._items.append(receipt)
            return
        key = receipt.key
        position = self._indexes.get(key)
        if position is None:
            self._indexes[key] = len(self._items)
            self._items.append(receipt)
            return
        if key in self._conflicts:
            return  # Conflict is sticky until a separate authoritative reconciliation.
        previous = self._items[position]
        if not self._consistent(previous, receipt):
            self._items[position] = replace(previous, state="unknown")
            self._conflicts[key] = Diagnostic(
                "effect.receipt_conflict", component=receipt.kind, evidence_ref=receipt.effect_id,
                reconciliation_owner=previous.reconciliation_owner or receipt.reconciliation_owner,
                retry_disposition="reconcile",
            )
            return
        self._items[position] = replace(
            previous,
            state=receipt.state,
            stage=receipt.stage if receipt.stage is not None else previous.stage,
            reference=previous.reference if previous.reference is not None else receipt.reference,
            identity=previous.identity if previous.identity is not None else receipt.identity,
            guarantee=previous.guarantee if previous.guarantee is not None else receipt.guarantee,
            reconciliation_owner=(previous.reconciliation_owner if previous.reconciliation_owner is not None
                                  else receipt.reconciliation_owner),
        )

    def snapshot(self) -> tuple[EffectReceipt, ...]:
        return tuple(self._items)

    def integrity_diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(self._conflicts.values())

    def conflict_keys(self) -> frozenset[EffectKey]:
        return frozenset(self._conflicts)
