"""Transient, invocation-scoped effect receipt accounting.

The resource owner supplies evidence. This accumulator only checks consistency;
it does not perform an effect, authenticate a receipt, or reconcile external state.
"""
from __future__ import annotations

from dataclasses import replace
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Protocol

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
    publication_policy_id: str | None = None
    publication_policy_revision: str | None = None
    contender: bool = False
    destination_current: bool | None = None
    basis_current: bool | None = None
    attempt_authorized: bool = True


@dataclass(slots=True)
class _DestinationEvidence:
    """Admitted writers and observed destination candidates are separate axes."""

    contenders: set
    uncertain: set
    confirmed: set
    ambiguous: bool = False


class EffectAuthorityError(ValueError):
    pass


class PublicationRevisionPolicy(Protocol):
    """Domain/host authority for opaque source revisions and pinned input basis.

    ``perform`` must admit the source basis and provider callback at one guarded
    boundary. The callback still owns destination CAS. ``is_current`` is a
    nonblocking read; spelling and run admission order establish no freshness.
    """
    policy_id: str
    revision: str
    def is_current(self, intent: EffectIntent) -> bool: ...
    def perform(self, intent: EffectIntent, action: Callable[[], EffectReceipt]) -> EffectReceipt: ...


class ExactCurrentRevisionPolicy:
    """Publish only the exact source/basis currently admitted by its owner.

    The host/domain resolves edition ordering before admitting a new pair.
    A policy revision CAS prevents accidental concurrent policy replacement.
    Source identifiers remain opaque and are compared only for equality.
    """
    def __init__(self, policy_id, *, source_revision=None, input_basis=None):
        safe_token(policy_id)
        self._validate_basis(source_revision, input_basis)
        self.policy_id = policy_id
        self._lock = RLock()
        self._current = source_revision, input_basis
        self._revision = 1

    @staticmethod
    def _validate_basis(source_revision, input_basis):
        if any(value is not None and (not isinstance(value, str) or not value)
               for value in (source_revision, input_basis)):
            raise ValueError("effect.source_policy_basis_invalid")

    @property
    def revision(self):
        return str(self._revision)

    def admit_current(self, source_revision, input_basis, *, expected_revision):
        self._validate_basis(source_revision, input_basis)
        with self._lock:
            if expected_revision != self.revision:
                raise EffectAuthorityError("effect.source_policy_conflict")
            self._current = source_revision, input_basis
            self._revision += 1
            return self.revision

    def is_current(self, intent):
        # An immutable tuple read does not wait behind a provider callback.
        return (intent.source_revision, intent.input_basis) == self._current

    def perform(self, intent, action):
        with self._lock:
            if not self.is_current(intent):
                raise EffectAuthorityError("effect.source_revision_rejected")
            return action()


@dataclass(frozen=True, slots=True)
class EffectRetentionSnapshot:
    records: int
    history: int
    attempts: int
    runs: int
    unresolved: int
    pins: int


class EffectAuthority:
    """Bounded owned evidence and explicit publication revision admission.

    Live results, independent cache/host pins and unresolved recovery obligations
    retain receipts. Completed attempts have no independent historical owner.
    Source ordering belongs to a registered publication policy, while the
    receiving provider owns atomic destination revision checks.
    """

    def __init__(self, *, max_records=16384, history_limit=128, attempt_limit=16384):
        for limit in (max_records, attempt_limit):
            if type(limit) is not int or limit < 1:
                raise ValueError("effect.capacity_invalid")
        if type(history_limit) is not int or history_limit < 0:
            raise ValueError("effect.capacity_invalid")
        self.max_records, self.history_limit, self.attempt_limit = max_records, history_limit, attempt_limit
        self._lock = RLock()
        self._attempts = {}
        self._runs = set()
        self._destinations = {}
        self._intervals = {}
        self._records = {}
        self._physical = {}
        self._owners = {}
        self._owner_keys = {}
        self._history = OrderedDict()
        self._history_physical = {}
        self._revision_policies = {}
        self._revision = 0

    @staticmethod
    def _run_owner(run_id):
        return "run:" + run_id

    def begin_run(self, run_id):
        safe_token(run_id)
        with self._lock:
            self._runs.add(run_id)
            self._owner_keys.setdefault(self._run_owner(run_id), set())

    def begin_attempt(self, run_id, scope_id, work_id, attempt_id):
        for token in (run_id, scope_id, work_id, attempt_id):
            safe_token(token)
        with self._lock:
            key = run_id, scope_id, work_id
            if key not in self._attempts and len(self._attempts) >= self.attempt_limit:
                raise EffectAuthorityError("effect.attempt_capacity")
            self.begin_run(run_id)
            self._attempts[key] = attempt_id

    def finish_attempt(self, run_id, scope_id, work_id, attempt_id=None):
        with self._lock:
            key = run_id, scope_id, work_id
            if attempt_id is None or self._attempts.get(key) == attempt_id:
                self._attempts.pop(key, None)

    def finish_run(self, run_id):
        """All physical workers returned; result pins remain until close."""
        with self._lock:
            for key in tuple(self._attempts):
                if key[0] == run_id:
                    del self._attempts[key]
            owner = self._run_owner(run_id)
            if not self._owner_keys.get(owner):
                self._owner_keys.pop(owner, None)
                self._runs.discard(run_id)

    def invalidate_attempt(self, run_id, scope_id, work_id, attempt_id=None):
        with self._lock:
            key = run_id, scope_id, work_id
            current = self._attempts.get(key)
            if attempt_id is None or current == attempt_id:
                self._attempts.pop(key, None)
                for identity, record in tuple(self._records.items()):
                    intent = record.intent
                    if ((intent.run_id, intent.scope_id, intent.work_id) == key
                            and (attempt_id is None or record.attempt_id == attempt_id)):
                        self._records[identity] = replace(record, current=False, attempt_authorized=False)

    def register_revision_policy(self, resource, policy: PublicationRevisionPolicy):
        if not isinstance(resource, str) or not resource:
            raise ValueError("effect.resource_invalid")
        if (not isinstance(getattr(policy, "policy_id", None), str)
                or not isinstance(getattr(policy, "revision", None), str) or not policy.revision
                or not callable(getattr(policy, "perform", None))
                or not callable(getattr(policy, "is_current", None))):
            raise ValueError("effect.source_policy_invalid")
        safe_token(policy.policy_id)
        with self._lock:
            previous = self._revision_policies.get(resource)
            if previous is not None and previous is not policy:
                raise EffectAuthorityError("effect.source_policy_conflict")
            self._revision_policies[resource] = policy

    def _attempt_current(self, intent, attempt_id):
        return self._attempts.get((intent.run_id, intent.scope_id, intent.work_id)) == attempt_id

    def _observed(self, record):
        policy = self._revision_policies.get(record.intent.resource)
        basis = policy.is_current(record.intent) if policy is not None else None
        state = self._destinations.get(record.intent.resource)
        contender = state is not None and record.intent.key in state.contenders
        if record.receipt.state == "failed":
            destination = False
        elif record.receipt.state == "unknown":
            destination = None
        elif state is None or record.intent.key not in state.confirmed:
            destination = False
        elif state.contenders or state.uncertain or state.ambiguous:
            destination = None
        else:
            destination = True
        current = (record.receipt.state == "confirmed" and destination is True
                   and basis is not False and record.attempt_authorized)
        return replace(record, current=current, contender=contender,
                       destination_current=destination, basis_current=basis)

    def _start_destination(self, intent):
        state = self._destinations.setdefault(intent.resource, _DestinationEvidence(set(), set(), set()))
        self._intervals[intent.key] = self._revision, None
        state.contenders.add(intent.key)

    def _settle_destination(self, record, *, observation=False):
        state = self._destinations.setdefault(record.intent.resource, _DestinationEvidence(set(), set(), set()))
        key = record.intent.key
        started, _ = self._intervals.get(key, (record.revision, None))
        self._intervals[key] = started, record.revision
        state.contenders.discard(key)
        state.uncertain.discard(key)
        if record.receipt.state == "unknown":
            state.uncertain.add(key)
        elif record.receipt.state == "confirmed":
            # Completion order cannot establish the physical ordering of two
            # overlapping successful callbacks. A competent reconciliation
            # supplies a fresh observation instead of guessing from arrival.
            competing = set() if observation else {
                candidate for candidate in state.confirmed
                if candidate != key and self._intervals.get(candidate, (0, 0))[1] >= started}
            state.confirmed = competing | {key}
            state.ambiguous = bool(competing)

    def _needed_destination_evidence(self, record):
        state = self._destinations.get(record.intent.resource)
        return (state is not None and record.intent.key in state.confirmed
                and bool(state.contenders or state.uncertain))

    def _prune_destination_evidence(self):
        retained = self._records.keys() | self._history.keys()
        for resource, state in tuple(self._destinations.items()):
            state.contenders.intersection_update(retained)
            state.uncertain.intersection_update(retained)
            state.confirmed.intersection_update(retained)
            if not (state.contenders or state.uncertain or state.confirmed):
                del self._destinations[resource]
        for key in tuple(self._intervals):
            if key not in retained:
                del self._intervals[key]

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
            kinds = {physical[1] for physical in (*self._physical, *self._history_physical)
                     if physical[0] == resource and physical[2] == effect_id
                     and (kind is None or physical[1] == kind)}
            matches = []
            for selected_kind in kinds:
                physical = resource, selected_kind, effect_id
                key = self._physical.get(physical)
                record = self._records.get(key)
                if record is None:
                    record = self._history.get(self._history_physical.get(physical))
                if record is not None:
                    matches.append(record)
            if len(matches) > 1:
                raise EffectAuthorityError("effect.kind_required")
            return self._observed(matches[0]) if matches else None

    def snapshot(self):
        with self._lock:
            return tuple(self._observed(record) for record in self._records.values())

    def retention_snapshot(self):
        with self._lock:
            return EffectRetentionSnapshot(len(self._records), len(self._history), len(self._attempts),
                len(self._runs), sum(record.receipt.state == "unknown" for record in self._records.values()),
                sum(len(owners) for owners in self._owners.values()))

    def _pin(self, key, owner):
        self._owners.setdefault(key, set()).add(owner)
        self._owner_keys.setdefault(owner, set()).add(key)

    def retain_run(self, run_id, owner):
        """Pin receipts before transferring ownership to cache or a host."""
        safe_token(owner)
        with self._lock:
            for key in tuple(self._owner_keys.get(self._run_owner(run_id), ())):
                self._pin(key, owner)

    def release_owner(self, owner):
        with self._lock:
            for key in self._owner_keys.pop(owner, ()):
                owners = self._owners.get(key)
                if owners is not None:
                    owners.discard(owner)
                    if not owners:
                        self._owners.pop(key, None)
            self._collect()

    def release_run(self, run_id):
        """Close a result; unresolved effects keep intrinsic recovery ownership."""
        with self._lock:
            self.finish_run(run_id)
            self._runs.discard(run_id)
            self.release_owner(self._run_owner(run_id))

    def _collect(self):
        for key, record in tuple(self._records.items()):
            if (self._owners.get(key) or record.receipt.state == "unknown"
                    or self._needed_destination_evidence(record)):
                continue
            physical = record.intent.resource, record.intent.kind, record.intent.effect_id
            if self._physical.get(physical) == key:
                self._physical.pop(physical, None)
            self._records.pop(key)
            if self.history_limit:
                self._history[key] = record
                self._history.move_to_end(key)
                previous = self._history.get(self._history_physical.get(physical))
                if previous is None or previous.revision < record.revision:
                    self._history_physical[physical] = key
        while len(self._history) > self.history_limit:
            key, record = self._history.popitem(last=False)
            physical = record.intent.resource, record.intent.kind, record.intent.effect_id
            if self._history_physical.get(physical) == key:
                self._history_physical.pop(physical, None)
        self._prune_destination_evidence()

    def _restore_history(self, record):
        if len(self._records) >= self.max_records:
            raise EffectAuthorityError("effect.retention_capacity")
        self._history.pop(record.intent.key, None)
        self._history_physical.pop((record.intent.resource, record.intent.kind, record.intent.effect_id), None)
        self._records[record.intent.key] = record
        self._physical[record.intent.resource, record.intent.kind, record.intent.effect_id] = record.intent.key

    def commit(self, intent: EffectIntent, attempt_id: str,
               action: Callable[[], EffectReceipt]) -> EffectReceipt:
        with self._lock:
            if not self._attempt_current(intent, attempt_id):
                raise EffectAuthorityError("effect.stale_attempt")
            policy = self._revision_policies.get(intent.resource)
            if intent.source_revision is not None and policy is None:
                raise EffectAuthorityError("effect.source_policy_required")
            if policy is not None and not policy.is_current(intent):
                raise EffectAuthorityError("effect.source_revision_rejected")
            previous = self._records.get(intent.key)
            physical = intent.resource, intent.kind, intent.effect_id
            if previous is None:
                previous = self._records.get(self._physical.get(physical))
            historical = previous is None
            if historical:
                previous = self._history.get(self._history_physical.get(physical))
            if previous is not None:
                if previous.intent.physical_fingerprint != intent.physical_fingerprint:
                    raise EffectAuthorityError("effect.identity_conflict")
                if previous.receipt.state == "confirmed":
                    if historical:
                        self._restore_history(previous)
                    self._pin(previous.intent.key, self._run_owner(intent.run_id))
                    return previous.receipt
                if previous.receipt.state == "unknown":
                    self._pin(previous.intent.key, self._run_owner(intent.run_id))
                    raise EffectAuthorityError("effect.reconciliation_required")
            if len(self._records) >= self.max_records and intent.key not in self._records:
                raise EffectAuthorityError("effect.retention_capacity")
            self._revision += 1
            self._start_destination(intent)
            receipt = EffectReceipt(intent.kind, "unknown", effect_id=intent.effect_id,
                                    stage="commit", identity=intent.identity,
                                    reconciliation_owner="effect.authority")
            self._records[intent.key] = EffectRecord(intent, attempt_id, receipt, self._revision, False,
                policy.policy_id if policy is not None else None,
                policy.revision if policy is not None else None)
            self._physical[physical] = intent.key
            self._pin(intent.key, self._run_owner(intent.run_id))
        rejected = None
        action_started = False
        policy_revision = policy.revision if policy is not None else None
        def physical_action():
            nonlocal action_started, policy_revision
            policy_revision = policy.revision if policy is not None else None
            action_started = True
            return action()
        try:
            receipt = policy.perform(intent, physical_action) if policy is not None else physical_action()
            if (not isinstance(receipt, EffectReceipt) or receipt.kind != intent.kind
                    or receipt.effect_id != intent.effect_id
                    or (intent.identity is not None and receipt.identity not in {None, intent.identity})):
                raise ValueError("effect.receipt_mismatch")
        except EffectAuthorityError as error:
            if action_started:
                receipt = EffectReceipt(intent.kind, "unknown", effect_id=intent.effect_id,
                                        stage="commit", identity=intent.identity,
                                        reconciliation_owner="effect.authority")
            else:
                rejected = error
                receipt = EffectReceipt(intent.kind, "failed", effect_id=intent.effect_id,
                                        stage="preflight", identity=intent.identity)
        except Exception:
            receipt = EffectReceipt(intent.kind, "unknown", effect_id=intent.effect_id,
                                    stage="commit", identity=intent.identity,
                                    reconciliation_owner="effect.authority")
        with self._lock:
            self._revision += 1
            record = EffectRecord(intent, attempt_id, receipt, self._revision, False,
                policy.policy_id if policy is not None else None, policy_revision,
                attempt_authorized=self._attempt_current(intent, attempt_id))
            self._records[intent.key] = record
            self._settle_destination(record)
            self._collect()
        if rejected is not None:
            raise rejected
        return receipt

    def reconcile(self, run_id, scope_id, effect_id, receipt: EffectReceipt, *, expected_revision: int):
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
            record = replace(previous, receipt=receipt, revision=self._revision)
            self._records[previous.intent.key] = record
            self._settle_destination(record, observation=receipt.state == "confirmed")
            observed = self._observed(record)
            self._collect()
            return observed


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
