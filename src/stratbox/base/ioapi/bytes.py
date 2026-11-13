"""Read bytes and qualify writes using explicit storage capabilities."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from typing import BinaryIO, Callable

from stratbox.base.filestore import FileStore, FileVersion, LocalFileStore, MutationRejected, SourceStore, WriteMode
from stratbox.base.filestore.base import FileVersionReader
from stratbox.data import ByteIdentity, StoredBytesReceipt, canonical_manifest_bytes
from stratbox.base.limits import BudgetMeter


class OutputBuffer(BytesIO):
    """Enforce a size ceiling during materialization, before the caller charges the final bytes."""

    def __init__(self, budget: BudgetMeter | None, *, limit: int | None = None):
        super().__init__()
        self.budget = budget
        self.limit = limit

    def write(self, data):
        end = self.tell() + len(data)
        if self.budget is not None:
            self.budget.check("output_bytes", end)
        if self.limit is not None and end > self.limit:
            raise ValueError("Output exceeds the format limit")
        return super().write(data)


def open_read(path: str, store: FileStore | None = None) -> BinaryIO:
    return (store if store is not None else LocalFileStore()).open_read(path)


def open_write(path: str, store: FileStore | None = None) -> BinaryIO:
    return (store if store is not None else LocalFileStore()).open_write(path)


def read_bytes(path: str, store: FileStore | None = None) -> bytes:
    return (store if store is not None else LocalFileStore()).read_bytes(path)


def file_identity(
    path: str, *, store: SourceStore, limit: int | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> ByteIdentity:
    digest = sha256()
    size = 0
    with store.open_read(path) as stream:
        while True:
            if checkpoint is not None:
                checkpoint()
            chunk = stream.read(65536 if limit is None else min(65536, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if limit is not None and size > limit:
                raise ValueError("File exceeds the expected size")
            digest.update(chunk)
    return ByteIdentity(digest.hexdigest(), size)


def inspect_file_version(
    path: str, *, store: FileVersionReader, budget: BudgetMeter, checkpoint: Callable[[], None],
) -> FileVersion:
    checkpoint()
    inspect_bounded = getattr(store, "inspect_file_budgeted", None)
    if callable(inspect_bounded):
        return inspect_bounded(path, budget=budget, checkpoint=checkpoint)
    info = store.stat(path)
    if not info.is_file or info.is_symlink or info.size is None:
        raise MutationRejected("Expected a size-qualified regular file")
    budget.charge("input_bytes", info.size)
    version = store.inspect_file(path)
    if version.identity.size != info.size:
        raise MutationRejected("File changed while inspecting it")
    checkpoint()
    return version


def write_verified_bytes(
    destination: str,
    data: bytes,
    *,
    store: FileStore,
    expected_sha256: str,
    mode: WriteMode = "immutable",
    expected_revision: str | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> StoredBytesReceipt:
    """Return observed storage evidence and the guarantee the store provided."""
    data = bytes(data)
    identity = ByteIdentity.of(data)
    store_id = getattr(store, "store_id", type(store).__name__)
    guarantees = {
        "immutable": "atomic_create",
        "replace_expected_revision": "compare_and_replace",
        "best_effort_verified": "read_back",
    }
    if mode not in guarantees:
        raise ValueError("Invalid write mode")
    guarantee = guarantees[mode]
    effect_id = ByteIdentity.of(canonical_manifest_bytes({
        "mode": mode, "store": store_id, "destination": destination,
        "revision": expected_revision, "payload": identity.sha256,
    })).sha256

    def receipt(status, code=None, *, stage="preflight", observed=None):
        return StoredBytesReceipt(
            destination, identity, status, guarantee, store_id, code,
            stage=stage, observed_identity=observed, expected_revision=expected_revision,
            effect_id=effect_id,
        )

    if identity.sha256 != expected_sha256:
        return receipt("failed", "input.digest_mismatch")
    if not destination or "\x00" in destination:
        return receipt("failed", "effect.destination_invalid")
    if mode == "immutable":
        commit = getattr(store, "create_if_absent", None)
    elif mode == "replace_expected_revision":
        if not expected_revision:
            return receipt("failed", "effect.revision_required")
        commit = getattr(store, "replace_if_revision", None)
    else:
        commit = store.write_bytes
    if not callable(commit):
        return receipt("failed", "provider.capability_missing")
    if cancelled is not None and cancelled():
        return receipt("failed", "operation.cancelled")
    try:
        if mode == "replace_expected_revision":
            committed = commit(destination, data, expected_revision)
        else:
            committed = commit(destination, data)
    except MutationRejected as error:
        return receipt(
            "failed",
            "provider.capability_missing"
            if error.capability_missing
            else "effect.rejected",
        )
    except Exception:
        return receipt("unknown", "effect.outcome_unknown", stage="commit")
    if mode == "replace_expected_revision" and committed is False:
        return receipt("failed", "effect.conflict", stage="commit")
    if mode != "best_effort_verified" and not isinstance(committed, bool):
        return receipt("unknown", "effect.outcome_unknown", stage="commit")
    def check_read_back():
        if cancelled is not None and cancelled():
            raise InterruptedError("Read-back interrupted")

    try:
        actual = file_identity(
            destination, store=store, limit=identity.size,
            checkpoint=check_read_back if cancelled is not None else None,
        )
    except ValueError:
        actual = None
    except Exception:
        return receipt("unknown", "effect.read_back_unavailable", stage="verify")
    if actual != identity:
        if committed is False:
            return receipt("failed", "effect.conflict", stage="verify", observed=actual)
        return receipt("unknown", "effect.read_back_mismatch", stage="verify", observed=actual)
    return receipt("already_present" if committed is False else "stored", stage="verify", observed=actual)


def write_bytes(
    path: str, data: bytes, store: FileStore | None = None
) -> StoredBytesReceipt:
    """Write bytes with read-back qualification using the selected store."""
    target = store if store is not None else LocalFileStore()
    result = write_verified_bytes(
        path,
        data,
        store=target,
        expected_sha256=ByteIdentity.of(data).sha256,
        mode="best_effort_verified",
    )
    if result.status not in {"stored", "already_present"}:
        raise OSError(result.diagnostic_code)
    return result


def read_bounded_bytes(
    path: str, *, store: FileStore, limit: int, budget: BudgetMeter | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> bytes:
    """Read up to limit bytes from a store, including streams that short-read."""
    if limit < 0:
        raise ValueError("Read limit must be nonnegative")
    data = bytearray()
    with store.open_read(path) as stream:
        while True:
            if checkpoint is not None:
                checkpoint()
            if budget is not None:
                budget.checkpoint()
            chunk = stream.read(min(65536, limit - len(data) + 1))
            if not chunk:
                break
            if budget is not None:
                budget.charge("input_bytes", len(chunk))
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("File exceeds the read limit")
    return bytes(data)
