"""Dataset providers keep immutable snapshots independently of render artifacts."""
from dataclasses import replace
from pathlib import Path
from threading import RLock
import json

from stratbox.shared.data.values import SourceDataset, SnapshotRef, canonical_tree, restore_tree, fingerprint, select_dataset
from stratbox.shared.identity import ByteIdentity


def _select(dataset, query):
    if not isinstance(query, dict) and not hasattr(query, "items"):
        raise ValueError("dataset.query_mapping_required")
    unknown = set(query) - {"filters", "periods", "limit"}
    if unknown:
        raise ValueError("dataset.query_unknown_field")
    filters, periods, limit = query.get("filters", {}), query.get("periods"), query.get("limit")
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("dataset.query_invalid_limit")
    rows = tuple(row for row in dataset.rows if all(row.get(key) == value for key, value in filters.items())
                 and (periods is None or row.get("period") in periods))
    if limit is not None:
        rows = rows[:limit]
    return select_dataset(dataset, rows)


class MemoryDatasetStore:
    provider_id = "datasets.memory"

    def __init__(self, *, scope_id):
        if not scope_id:
            raise ValueError("dataset.explicit_scope_required")
        self.scope_id, self._values, self._lock = scope_id, {}, RLock()

    def ingest(self, dataset, *, destination, identity):
        if not isinstance(dataset, SourceDataset) or fingerprint(dataset) != identity:
            raise ValueError("dataset.identity_mismatch")
        # Canonical round trip creates an independently owned retained value.
        retained = restore_tree(canonical_tree(dataset))
        key = str(destination).rstrip("/") + "/" + identity
        with self._lock:
            self._values.setdefault(key, retained)
        return SnapshotRef(key, self.provider_id, identity, self.scope_id)

    def query(self, reference, query):
        with self._lock:
            value = self._values[reference.snapshot_id]
        if reference.provider_id != self.provider_id or reference.provider_scope != self.scope_id or fingerprint(value) != reference.identity:
            raise ValueError("dataset.snapshot_conflict")
        return _select(restore_tree(canonical_tree(value)), query)


class FileDatasetStore:
    provider_id = "datasets.files"

    def __init__(self, directory, *, admitted_types=None, max_bytes=256 * 1024 * 1024):
        from stratbox.core.storage.filestore import LocalFileStore
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.scope_id, self.store = str(self.directory), LocalFileStore(str(self.directory))
        self.admitted_types, self.max_bytes = dict(admitted_types or {}), max_bytes

    def ingest(self, dataset, *, destination, identity):
        if not isinstance(dataset, SourceDataset) or fingerprint(dataset) != identity:
            raise ValueError("dataset.identity_mismatch")
        raw = json.dumps(canonical_tree(dataset), sort_keys=True, separators=(",", ":")).encode()
        if len(raw) > self.max_bytes:
            raise ValueError("dataset.snapshot_size_limit")
        # Fail unsupported replay before any effect.
        if fingerprint(restore_tree(json.loads(raw), admitted_types=self.admitted_types)) != identity:
            raise ValueError("dataset.replay_identity_mismatch")
        namespace = fingerprint(str(destination))
        location = f"{namespace}/{ByteIdentity.of(raw).sha256}"
        self.store.create_immutable(location, raw)
        return SnapshotRef(location, self.provider_id, identity, self.scope_id)

    def query(self, reference, query):
        if reference.provider_id != self.provider_id or reference.provider_scope != self.scope_id:
            raise ValueError("dataset.provider_mismatch")
        with self.store.open_read(reference.snapshot_id) as stream:
            raw = stream.read(self.max_bytes + 1)
        if len(raw) > self.max_bytes:
            raise ValueError("dataset.snapshot_size_limit")
        value = restore_tree(json.loads(raw), admitted_types=self.admitted_types)
        if not isinstance(value, SourceDataset) or fingerprint(value) != reference.identity:
            raise ValueError("dataset.snapshot_conflict")
        return _select(value, query)
