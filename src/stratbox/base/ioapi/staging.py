"""Bounded staging and read-back for conditionally committed byte streams."""

from __future__ import annotations

from hashlib import sha256
from typing import BinaryIO, Callable

from stratbox.base.filestore import FileMutation, MutationRejected, StagedWrite, StagedWriter, WriteMode
from stratbox.base.limits import BudgetMeter
from stratbox.data import ByteIdentity, StoredBytesReceipt, canonical_manifest_bytes

from .bytes import file_identity

WRITE_GUARANTEES = {
    "immutable": "atomic_create",
    "replace_expected_revision": "compare_and_replace",
    "best_effort_verified": "read_back",
}


class BoundedStage:
    def __init__(self, stream: BinaryIO, budget: BudgetMeter):
        self.stream = stream
        self.budget = budget
        self.high_water = 0

    def write(self, data: bytes) -> int:
        end = self.stream.tell() + len(data)
        if end > self.high_water:
            self.budget.charge("temporary_bytes", end - self.high_water)
            self.high_water = end
        count = self.stream.write(data)
        if count != len(data):
            raise OSError("Short staging write")
        return count

    def seek(self, offset, whence=0):
        return self.stream.seek(offset, whence)

    def tell(self):
        return self.stream.tell()

    def truncate(self, size=None):
        return self.stream.truncate(size)

    def flush(self):
        self.stream.flush()


def stream_identity(stream: BinaryIO, checkpoint: Callable[[], None], *, limit: int | None = None) -> ByteIdentity:
    stream.seek(0)
    digest = sha256()
    size = 0
    while True:
        checkpoint()
        chunk = stream.read(1024 * 1024 if limit is None else min(1024 * 1024, limit - size + 1))
        if not chunk:
            break
        size += len(chunk)
        if limit is not None and size > limit:
            raise ValueError("Stream exceeds the expected size")
        digest.update(chunk)
    return ByteIdentity(digest.hexdigest(), size)


def store_identity(store: object) -> str:
    return getattr(store, "store_id", type(store).__name__)


def storage_scope(store: object, destination: str) -> str:
    identify = getattr(store, "storage_scope", None)
    return identify(destination) if callable(identify) else store_identity(store)


def current_revision(store, destination):
    inspect = getattr(store, "current_revision", None)
    return inspect(destination) if callable(inspect) else None


def commit_staged(
    stage: StagedWrite, destination: str, identity: ByteIdentity, *, store: StagedWriter,
    budget: BudgetMeter, checkpoint: Callable[[], None], mode: WriteMode,
    expected_revision: str | None = None, plan_identity: ByteIdentity | None = None,
    operation_id: str | None = None, require_admission: bool = False,
    source_directory: str | None = None,
    on_effect: Callable[[StoredBytesReceipt], None] | None = None,
) -> StoredBytesReceipt:
    """Apply the receiving store's commit and verify the destination independently."""
    if mode not in WRITE_GUARANTEES or (mode == "replace_expected_revision" and not expected_revision):
        raise ValueError("Invalid staged write mode or revision")
    if not destination or destination in {".", ".."} or "\x00" in destination:
        raise ValueError("Invalid staged destination")
    store_id = store_identity(store)
    scope = storage_scope(store, destination)
    effect_id = ByteIdentity.of(canonical_manifest_bytes({
        "plan": plan_identity.sha256 if plan_identity else None, "destination": destination,
        "operation": operation_id, "store": scope, "mode": mode, "revision": expected_revision,
        "payload": identity.sha256,
    })).sha256

    def receipt(status, code=None, *, stage="verify", actual=None, revision=None):
        value = StoredBytesReceipt(
            destination, identity, status, WRITE_GUARANTEES[mode], store_id, code,
            stage=stage, observed_identity=actual, expected_revision=expected_revision, effect_id=effect_id,
            observed_revision=revision,
            store_scope=scope,
        )
        if on_effect is not None:
            on_effect(value)
        return value

    budget.charge("output_bytes", identity.size)
    checkpoint()
    admitted_commit = getattr(stage, "commit_admitted", None)
    if require_admission and (operation_id is None or plan_identity is None or not callable(admitted_commit)):
        return receipt("failed", "provider.capability_missing", stage="preflight")
    receipt("unknown", "effect.outcome_unknown", stage="commit")
    try:
        if require_admission:
            committed = admitted_commit(FileMutation(
                operation_id, effect_id, plan_identity, "write",
                directory=source_directory, destination=destination, content=identity, mode=mode,
                expected_revision=expected_revision,
            ))
        else:
            committed = stage.commit(mode, expected_revision)
    except MutationRejected as error:
        return receipt("failed", error.code, stage="commit")
    except Exception:
        return receipt("unknown", "effect.outcome_unknown", stage="commit")
    if type(committed) is not bool:
        return receipt("unknown", "effect.outcome_unknown", stage="commit")
    if not committed and mode != "immutable":
        return receipt("failed", "effect.conflict", stage="commit")
    try:
        # A consumer cancellation cannot revoke an accepted commit. The deadline
        # may still prevent verification, in which case the effect stays unknown.
        revision = current_revision(store, destination)
        actual = file_identity(destination, store=store, limit=identity.size, checkpoint=budget.checkpoint)
        if revision != current_revision(store, destination):
            return receipt("unknown", "effect.read_back_unavailable")
    except ValueError:
        actual = None
    except Exception:
        return receipt("unknown", "effect.read_back_unavailable")
    if actual != identity:
        return receipt("unknown" if committed else "failed",
                       "effect.read_back_mismatch" if committed else "effect.conflict", actual=actual)
    return receipt("stored" if committed else "already_present", actual=actual, revision=revision)
