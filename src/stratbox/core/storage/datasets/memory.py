"""Atomic in-memory reference adapter for the logical snapshot contract."""

from threading import RLock

from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference, identifier
from .ports import (DatasetReadControls, DatasetStorageError, DatasetWriteControls, DatasetWriteResult,
                    materialize_assembly, selected_components, validate_scope, validate_snapshot)


class MemoryDatasetStore:
    def __init__(self, *, provider_id: str, scope_id: str, resolver=None):
        identifier(provider_id)
        identifier(scope_id)
        self.provider_id = provider_id
        self.scope_id = scope_id
        self.resolver = resolver
        self._snapshots: dict[tuple[str, str], DatasetSnapshot | DatasetAssembly] = {}
        self._lock = RLock()

    def _reference(self, value):
        return SnapshotReference(self.provider_id, self.scope_id, value.manifest.dataset_id,
                                 value.manifest.version_id, value.identity)

    def write_snapshot(self, snapshot, *, controls: DatasetWriteControls | None = None):
        validate_snapshot(snapshot)
        controls = controls or DatasetWriteControls()
        controls.checkpoint()
        controls.budget.account_output(f"dataset:{self.provider_id}:{self.scope_id}:{snapshot.manifest.dataset_id}:{snapshot.manifest.version_id}", snapshot.identity)
        if isinstance(snapshot, DatasetSnapshot):
            for name, table in snapshot.tables:
                controls.budget.account_output(f"dataset-component:{self.provider_id}:{self.scope_id}:{snapshot.identity.sha256}:{name}", table.identity)
        if isinstance(snapshot, DatasetAssembly):
            materialize_assembly(snapshot, selected_components(snapshot.manifest, None), self, self.resolver, DatasetReadControls(
                budget=controls.budget, checkpoint=controls.checkpoint))
        key = (snapshot.manifest.dataset_id, snapshot.manifest.version_id)
        with self._lock:
            previous = self._snapshots.get(key)
            if previous is not None and previous.identity != snapshot.identity:
                return DatasetWriteResult(None, "failed", "dataset.version_conflict")
            if previous is None and controls.on_publication is not None:
                controls.on_publication(DatasetWriteResult(None, "unknown", "effect.outcome_unknown"))
            self._snapshots.setdefault(key, snapshot)
            return DatasetWriteResult(self._reference(snapshot), "already_present" if previous is not None else "stored")

    def read_snapshot(self, reference, components=None, *, controls=None):
        validate_scope(self, reference)
        controls = (controls or DatasetReadControls()).enter(reference)
        with self._lock:
            value = self._snapshots.get((reference.dataset_id, reference.version_id))
        if value is None:
            raise DatasetStorageError("dataset.version_missing")
        if value.identity != reference.identity:
            raise DatasetStorageError("dataset.snapshot_mismatch")
        controls.budget.charge("input_bytes", value.manifest.identity.size)
        names = selected_components(value.manifest, components)
        if isinstance(value, DatasetAssembly):
            return materialize_assembly(value, names, self, self.resolver, controls)
        if sum(len(table.rows) * max(1, len(table.schema.columns)) for name, table in value.tables if name in names) > controls.max_cells:
            raise DatasetStorageError("dataset.cell_limit")
        controls.budget.charge("cells", sum(len(table.rows) * max(1, len(table.schema.columns)) for name, table in value.tables if name in names))
        controls.budget.charge("input_bytes", sum(table.identity.size for name, table in value.tables if name in names))
        return DatasetSnapshot(value.manifest, tuple((name, table) for name, table in value.tables if name in names))

    def datasets(self, *, controls=None):
        controls = controls or DatasetReadControls()
        controls.checkpoint()
        with self._lock:
            result = tuple(sorted({dataset for dataset, _ in self._snapshots}))
        controls.budget.charge("objects", len(result))
        return result

    def versions(self, dataset_id, *, controls=None):
        identifier(dataset_id)
        controls = controls or DatasetReadControls()
        controls.checkpoint()
        with self._lock:
            result = tuple(self._reference(value) for key, value in sorted(self._snapshots.items()) if key[0] == dataset_id)
        controls.budget.charge("objects", len(result))
        return result
