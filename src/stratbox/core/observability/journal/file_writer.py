"""Immutable journal writing, read-back attestation and reconciliation."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from hashlib import sha256
from stratbox.shared.identity import ByteIdentity
from stratbox.core.storage.filestore import FileStore
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.journal.contracts import JournalNamespace, JournalWriteReceipt
from stratbox.core.observability.journal.codecs import JournalDecodeError, encode_records, DEFAULT_MAX_SEGMENT_BYTES, MAX_SEGMENT_BYTES
from stratbox.core.observability.journal.file_reader import _read_bounded_segment, _check_segment
from stratbox.core.observability.journal.manifests import JournalManifest, MAX_MANIFEST_BYTES, encode_manifest
from stratbox.core.observability.journal.policies import PersistencePolicy

class FileJournalWriter:
    def __init__(self, store: FileStore, root: str, *, writer_id: str,
                 policy: PersistencePolicy | None = None,
                 max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES):
        if not 4096 <= max_segment_bytes <= MAX_SEGMENT_BYTES:
            raise ValueError("Invalid maximum journal segment size")
        self.policy = policy or PersistencePolicy()
        self.namespace = JournalNamespace(root, writer_id, self.policy.format)
        self.store, self.max_segment_bytes = store, max_segment_bytes
        self.root, self.writer_id = self.namespace.root, self.namespace.writer_id

    @property
    def format(self) -> str:
        return self.namespace.format

    def segment_path(self, segment_id: str) -> str:
        return self.namespace.segment_path(segment_id)

    def _publish(self, path: str, data: bytes) -> tuple[bool | None, str | None]:
        staged = callable(getattr(self.store, "stage_write", None))
        atomic = callable(getattr(self.store, "create_if_absent", None))
        if not (staged or atomic):
            return None, "journal.immutable_capability_missing"
        try:
            self.store.makedirs(f"{self.root}/{self.writer_id}")
        except Exception:
            return None, "journal.destination_unavailable"
        entered_commit = False
        try:
            if staged:
                with self.store.stage_write(path) as stage:
                    stage.stream.write(data)
                    entered_commit = True
                    created = stage.commit("immutable", None)
            else:
                entered_commit = True
                created = self.store.create_if_absent(path, data)
        except Exception:
            return None, "journal.commit_unknown" if entered_commit else "journal.staging_failed"
        return created, None

    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt:
        data = encode_records(records, format=self.format, max_bytes=self.max_segment_bytes)
        batch = _check_segment(data, None, self.format, expected=None, max_bytes=self.max_segment_bytes)
        if not batch:
            raise ValueError("Cannot persist an empty journal segment")
        ids = tuple(rec.record_id for rec in batch)
        identity = ByteIdentity.of(data)
        chosen = segment_id or sha256((self.writer_id + ":" + identity.sha256 + ":" + ":".join(ids)).encode("utf-8")).hexdigest()
        path = self.segment_path(chosen)
        def receipt(state: str, error: str | None = None, already: bool = False) -> JournalWriteReceipt:
            return JournalWriteReceipt(state, chosen, identity, ids, "immutable_read_back", path, error, already)
        created, issue = self._publish(path, data)
        if issue and issue != "journal.commit_unknown":
            return receipt("failed", issue)
        if issue == "journal.commit_unknown":
            return receipt("unknown", issue)
        observed, reason = _read_bounded_segment(self.store, path, self.max_segment_bytes)
        if observed is None:
            return receipt("unknown", reason)
        if ByteIdentity.of(observed) != identity:
            return receipt("failed", "journal.segment_conflict" if not created else "journal.read_back_mismatch")
        return receipt("confirmed", already=not created)

    def reconcile(self, receipt: JournalWriteReceipt) -> JournalWriteReceipt:
        return reconcile_write(self.store, receipt, namespace=self.namespace,
                               max_segment_bytes=self.max_segment_bytes)

    def write_manifest(self, manifest: JournalManifest) -> JournalWriteReceipt:
        if manifest.writer_id != self.writer_id:
            raise ValueError("Manifest writer mismatch")
        if any(not self.namespace.admits(s.logical_locator) or self.segment_path(s.segment_id) != s.logical_locator
               for s in manifest.segments):
            raise ValueError("Manifest contains a segment outside the writer namespace")
        data = encode_manifest(manifest)
        identity = ByteIdentity.of(data)
        path = self.namespace.manifest_path(manifest.manifest_id)
        def receipt(state, code=None, already=False):
            return JournalWriteReceipt(state, manifest.manifest_id, identity, (),
                                       "immutable_read_back", path, code, already)
        created, issue = self._publish(path, data)
        if issue:
            return receipt("unknown" if issue == "journal.commit_unknown" else "failed", issue)
        observed, reason = _read_bounded_segment(self.store, path, MAX_MANIFEST_BYTES)
        if observed is None:
            return receipt("unknown", reason)
        return receipt("confirmed", already=not created) if ByteIdentity.of(observed) == identity else receipt("failed", "journal.manifest_conflict")


def reconcile_write(store: FileStore, receipt: JournalWriteReceipt, *, namespace: JournalNamespace,
                    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES) -> JournalWriteReceipt:
    """One read, one identical byte buffer for digest + records + receipt IDs."""
    if not namespace.admits(receipt.locator) or namespace.segment_path(receipt.segment_id) != receipt.locator:
        raise ValueError("journal.namespace_mismatch")
    data, status = _read_bounded_segment(store, receipt.locator, max_segment_bytes)
    if data is None:
        if status == "journal.segment_too_large":
            state, code = "failed", status
        else:
            state, code = "unknown", "journal.reconciliation_incomplete"
    else:
        try:
            _check_segment(data, receipt, namespace.format, expected=receipt.content_identity,
                           max_bytes=max_segment_bytes)
        except JournalDecodeError:
            state, code = "failed", "journal.segment_conflict"
        else:
            state, code = "confirmed", None
    return JournalWriteReceipt(state, receipt.segment_id, receipt.content_identity, receipt.record_ids,
                               receipt.guarantee, receipt.locator, code,
                               already_present=state == "confirmed")
