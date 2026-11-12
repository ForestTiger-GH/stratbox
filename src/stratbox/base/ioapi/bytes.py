"""Read bytes and qualify writes using explicit storage capabilities."""

from __future__ import annotations

from hashlib import sha256
from typing import BinaryIO, Callable, Literal

from stratbox.base.filestore import FileStore, LocalFileStore, MutationRejected
from stratbox.data import ByteIdentity, StoredBytesReceipt

WriteMode = Literal["immutable", "replace_expected_revision", "best_effort_verified"]


def open_read(path: str, store: FileStore | None = None) -> BinaryIO:
    return (store if store is not None else LocalFileStore()).open_read(path)


def open_write(path: str, store: FileStore | None = None) -> BinaryIO:
    return (store if store is not None else LocalFileStore()).open_write(path)


def read_bytes(path: str, store: FileStore | None = None) -> bytes:
    return (store if store is not None else LocalFileStore()).read_bytes(path)


def file_identity(
    path: str, *, store: FileStore, limit: int | None = None
) -> ByteIdentity:
    digest = sha256()
    size = 0
    with store.open_read(path) as stream:
        while chunk := stream.read(65536):
            size += len(chunk)
            if limit is not None and size > limit:
                raise ValueError("File exceeds the expected size")
            digest.update(chunk)
    return ByteIdentity(digest.hexdigest(), size)


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
    guarantee = {
        "immutable": "atomic_create",
        "replace_expected_revision": "compare_and_replace",
        "best_effort_verified": "read_back",
    }[mode]

    def receipt(status, code=None):
        return StoredBytesReceipt(
            destination, identity, status, guarantee, store_id, code
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
        return receipt("unknown", "effect.outcome_unknown")
    if mode == "replace_expected_revision" and committed is False:
        return receipt("failed", "effect.conflict")
    if mode != "best_effort_verified" and not isinstance(committed, bool):
        return receipt("unknown", "effect.outcome_unknown")
    try:
        actual = file_identity(destination, store=store, limit=identity.size)
    except ValueError:
        actual = None
    except Exception:
        return receipt("unknown", "effect.read_back_unavailable")
    if actual != identity:
        if committed is False:
            return receipt("failed", "effect.conflict")
        return receipt("unknown", "effect.read_back_mismatch")
    return receipt("already_present" if committed is False else "stored")


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


def read_bounded_bytes(path: str, *, store: FileStore, limit: int) -> bytes:
    """Read up to limit bytes from a store, including streams that short-read."""
    if limit < 0:
        raise ValueError("Read limit must be nonnegative")
    data = bytearray()
    with store.open_read(path) as stream:
        while chunk := stream.read(min(65536, limit - len(data) + 1)):
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("File exceeds the read limit")
    return bytes(data)
