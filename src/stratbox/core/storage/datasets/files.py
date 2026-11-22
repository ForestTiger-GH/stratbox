"""Immutable file snapshots: verified components followed by one manifest commit.

A version becomes catalog-visible only when its manifest is confirmed. Failed
publication may leave reusable content-addressed components; it never publishes
a partially available snapshot or silently replaces an existing version.
"""

from __future__ import annotations

from hashlib import sha256

from stratbox.core.storage.bytes import read_bounded_bytes
from stratbox.core.storage.filestore.paths import child_path
from stratbox.core.storage.staging import BoundedStage, commit_staged
from stratbox.shared.data.snapshots import (DatasetAssembly, DatasetSnapshot, SnapshotReference, identity_value,
                                            identifier, manifest_value)
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .codec import (_list, _object, decode_assembly, decode_table, encode_assembly, encode_table, identity_from,
                    loads, manifest_from)
from .ports import (DatasetReadControls, DatasetStorageError, DatasetWriteControls, DatasetWriteResult,
                    materialize_assembly, selected_components, validate_scope, validate_snapshot)


def _hash(value):
    return sha256(value.encode("utf-8")).hexdigest()


class FileDatasetStore:
    def __init__(self, store, root: str, *, provider_id: str, scope_id: str, resolver=None,
                 max_catalog_entries: int = 10_000, max_object_bytes: int = 64 * 1024 * 1024):
        identifier(provider_id)
        identifier(scope_id)
        if not isinstance(root, str) or not root or "\x00" in root:
            raise ValueError("dataset.invalid_root")
        if type(max_catalog_entries) is not int or max_catalog_entries < 1:
            raise ValueError("dataset.invalid_catalog_limit")
        if type(max_object_bytes) is not int or max_object_bytes < 1:
            raise ValueError("dataset.invalid_object_limit")
        self.store = store
        self.root = root
        self.provider_id = provider_id
        self.scope_id = scope_id
        self.resolver = resolver
        self.max_catalog_entries = max_catalog_entries
        self.max_object_bytes = max_object_bytes

    def _reference(self, manifest):
        return SnapshotReference(self.provider_id, self.scope_id, manifest.dataset_id, manifest.version_id, manifest.identity)

    def _versions_root(self):
        return child_path(self.root, "versions")

    def _version_path(self, dataset_id, version_id):
        return child_path(child_path(self._versions_root(), _hash(dataset_id)), _hash(version_id) + ".json")

    def _table_path(self, identity):
        return child_path(child_path(child_path(self.root, "tables"), identity.sha256[:2]), identity.sha256 + ".json")

    def _commit(self, data, path, controls, plan, *, publication=False):
        if len(data) > self.max_object_bytes:
            raise DatasetStorageError("dataset.encoding_limit")
        if not callable(getattr(self.store, "stage_write", None)):
            raise DatasetStorageError("provider.capability_missing")
        controls.checkpoint()
        with self.store.stage_write(path) as stage:
            sink = BoundedStage(stage.stream, controls.budget)
            for offset in range(0, len(data), 65536):
                controls.checkpoint()
                sink.write(data[offset:offset + 65536])
            sink.flush()
            def on_effect(receipt):
                if publication and receipt.stage == "commit" and receipt.status == "unknown" and controls.on_publication is not None:
                    controls.on_publication(DatasetWriteResult(None, "unknown", "effect.outcome_unknown"))
                if controls.on_effect is not None:
                    controls.on_effect(receipt)

            return commit_staged(stage, path, ByteIdentity.of(data), store=self.store, budget=controls.budget,
                                 checkpoint=controls.checkpoint, mode="immutable", plan_identity=plan,
                                 operation_id=controls.operation_id, require_admission=controls.managed,
                                 on_effect=on_effect)

    def write_snapshot(self, snapshot, *, controls: DatasetWriteControls | None = None):
        validate_snapshot(snapshot)
        controls = controls or DatasetWriteControls()
        controls.checkpoint()
        manifest = snapshot.manifest
        reference = self._reference(manifest)
        destination = self._version_path(manifest.dataset_id, manifest.version_id)
        writes = []

        # This is only an optimization. Immutable commit below remains the race
        # boundary; a concurrent conflicting publisher cannot replace a version.
        if self.store.exists(destination):
            previous, _ = self._read_envelope(destination, DatasetReadControls(budget=controls.budget, checkpoint=controls.checkpoint))
            if previous.identity != manifest.identity:
                return DatasetWriteResult(None, "failed", "dataset.version_conflict")
            self.read_snapshot(reference, controls=DatasetReadControls(budget=controls.budget, checkpoint=controls.checkpoint))
            return DatasetWriteResult(reference, "already_present")

        if isinstance(snapshot, DatasetAssembly):
            materialize_assembly(snapshot, selected_components(manifest, None), self, self.resolver,
                                 DatasetReadControls(budget=controls.budget, checkpoint=controls.checkpoint))
            envelope = {"encoding": "stratbox.dataset-files.v1", "kind": "assembly",
                        "assembly": loads(encode_assembly(snapshot))}
        else:
            objects = []
            for name, table in snapshot.tables:
                controls.checkpoint()
                if table.identity.size > self.max_object_bytes:
                    raise DatasetStorageError("dataset.encoding_limit")
                controls.budget.check("temporary_bytes", table.identity.size)
                data = encode_table(table)
                identity = ByteIdentity.of(data)
                receipt = self._commit(data, self._table_path(identity), controls, manifest.identity)
                writes.append(receipt)
                if receipt.status not in {"stored", "already_present"}:
                    return DatasetWriteResult(None, receipt.status, receipt.diagnostic_code, tuple(writes))
                objects.append({"name": name, "identity": identity_value(identity)})
            envelope = {"encoding": "stratbox.dataset-files.v1", "kind": "tables",
                        "manifest": manifest_value(manifest), "objects": objects}
        receipt = self._commit(canonical_manifest_bytes(envelope), destination, controls, manifest.identity, publication=True)
        writes.append(receipt)
        if receipt.status not in {"stored", "already_present"}:
            return DatasetWriteResult(None, receipt.status, receipt.diagnostic_code, tuple(writes))
        return DatasetWriteResult(reference, receipt.status, writes=tuple(writes))

    def _read_envelope(self, path, controls):
        try:
            data = read_bounded_bytes(path, store=self.store, limit=controls.max_object_bytes,
                                      budget=controls.budget, checkpoint=controls.checkpoint)
        except FileNotFoundError as error:
            raise DatasetStorageError("dataset.version_missing") from error
        value = loads(data, max_bytes=controls.max_object_bytes)
        if not isinstance(value, dict) or value.get("encoding") != "stratbox.dataset-files.v1":
            raise DatasetStorageError("dataset.storage_codec_unsupported")
        if value.get("kind") == "assembly":
            _object(value, ("encoding", "kind", "assembly"))
            assembly = decode_assembly(canonical_manifest_bytes(value["assembly"]))
            return assembly.manifest, assembly
        _object(value, ("encoding", "kind", "manifest", "objects"))
        if value["kind"] != "tables":
            raise DatasetStorageError("dataset.storage_codec_unsupported")
        manifest = manifest_from(value["manifest"])
        objects = []
        for obj in _list(value["objects"]):
            obj = _object(obj, ("name", "identity"))
            objects.append((obj["name"], identity_from(obj["identity"])))
        if tuple(name for name, _ in objects) != tuple(c.name for c in manifest.components):
            raise DatasetStorageError("dataset.component_order_mismatch")
        return manifest, tuple(objects)

    def read_snapshot(self, reference, components=None, *, controls=None):
        validate_scope(self, reference)
        controls = (controls or DatasetReadControls()).enter(reference)
        manifest, storage = self._read_envelope(self._version_path(reference.dataset_id, reference.version_id), controls)
        if (manifest.dataset_id, manifest.version_id, manifest.identity) != (reference.dataset_id, reference.version_id, reference.identity):
            raise DatasetStorageError("dataset.snapshot_mismatch")
        names = selected_components(manifest, components)
        if isinstance(storage, DatasetAssembly):
            return materialize_assembly(storage, names, self, self.resolver, controls)
        declared = {component.name: component for component in manifest.components}
        tables = []
        cells = 0
        for name, identity in storage:
            if name not in names:
                continue
            controls.checkpoint()
            component = declared[name]
            cells += component.row_count * max(1, len(component.schema.columns))
            if cells > controls.max_cells:
                raise DatasetStorageError("dataset.cell_limit")
            controls.budget.charge("cells", component.row_count * max(1, len(component.schema.columns)))
            if identity.size > controls.max_object_bytes:
                raise DatasetStorageError("dataset.encoding_limit")
            try:
                data = read_bounded_bytes(self._table_path(identity), store=self.store, limit=identity.size,
                                          budget=controls.budget, checkpoint=controls.checkpoint)
            except FileNotFoundError as error:
                raise DatasetStorageError("dataset.component_missing") from error
            if ByteIdentity.of(data) != identity:
                raise DatasetStorageError("dataset.physical_identity_mismatch")
            tables.append((name, decode_table(data, expected_identity=component.identity, max_bytes=controls.max_object_bytes,
                                              max_cells=controls.max_cells)))
        return DatasetSnapshot(manifest, tuple(tables))

    def _catalog(self, dataset_id=None, *, controls=None):
        root = self._versions_root()
        if not self.store.exists(root):
            return ()
        controls = controls or DatasetReadControls()
        result = []
        directories = (_hash(dataset_id),) if dataset_id is not None else self.store.listdir(root)
        for name in directories:
            if len(name) != 64 or any(c not in "0123456789abcdef" for c in name):
                continue
            directory = child_path(root, name)
            if not self.store.is_dir(directory):
                continue
            for filename in self.store.listdir(directory):
                if not filename.endswith(".json"):
                    continue
                if len(result) >= self.max_catalog_entries:
                    raise DatasetStorageError("dataset.catalog_limit")
                controls.checkpoint()
                controls.budget.charge("objects", 1)
                manifest, _ = self._read_envelope(child_path(directory, filename), controls)
                if name != _hash(manifest.dataset_id) or filename != _hash(manifest.version_id) + ".json":
                    raise DatasetStorageError("dataset.catalog_mismatch")
                if dataset_id is not None and manifest.dataset_id != dataset_id:
                    raise DatasetStorageError("dataset.catalog_mismatch")
                result.append(self._reference(manifest))
        return tuple(sorted(result, key=lambda ref: (ref.dataset_id, ref.version_id)))

    def datasets(self, *, controls=None):
        return tuple(sorted({ref.dataset_id for ref in self._catalog(controls=controls)}))

    def versions(self, dataset_id, *, controls=None):
        identifier(dataset_id)
        return self._catalog(dataset_id, controls=controls)
