"""Narrow logical dataset ports; implementations own layout and commit semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Protocol

from stratbox.core.limits import BudgetMeter, ExecutionBudget
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference
from stratbox.shared.evidence import StoredBytesReceipt


class DatasetStorageError(ValueError):
    @property
    def code(self) -> str:
        return self.args[0]


@dataclass(frozen=True, slots=True)
class DatasetReadControls:
    budget: BudgetMeter = field(default_factory=lambda: BudgetMeter(ExecutionBudget(input_bytes=512 * 1024 * 1024)))
    checkpoint: Callable[[], None] = lambda: None
    max_object_bytes: int = 64 * 1024 * 1024
    max_cells: int = 5_000_000
    active: frozenset[SnapshotReference] = frozenset()

    def __post_init__(self):
        if type(self.max_object_bytes) is not int or self.max_object_bytes < 1 or type(self.max_cells) is not int or self.max_cells < 0:
            raise ValueError("dataset.invalid_read_limits")
        if not isinstance(self.active, frozenset) or any(not isinstance(r, SnapshotReference) for r in self.active):
            raise ValueError("dataset.invalid_active_references")

    def enter(self, reference: SnapshotReference) -> DatasetReadControls:
        from dataclasses import replace
        if reference in self.active or len(self.active) >= 64:
            raise DatasetStorageError("dataset.reference_cycle")
        self.checkpoint()
        self.budget.checkpoint()
        self.budget.charge("objects", 1)
        return replace(self, active=self.active | {reference})


@dataclass(frozen=True, slots=True)
class DatasetWriteControls:
    budget: BudgetMeter = field(default_factory=lambda: BudgetMeter(ExecutionBudget(
        input_bytes=512 * 1024 * 1024, output_bytes=512 * 1024 * 1024, temporary_bytes=512 * 1024 * 1024)))
    checkpoint: Callable[[], None] = lambda: None
    managed: bool = False
    operation_id: str = "dataset.write_snapshot"
    on_effect: Callable[[StoredBytesReceipt], None] | None = None
    on_publication: Callable[[DatasetWriteResult], None] | None = None


@dataclass(frozen=True, slots=True)
class DatasetWriteResult:
    reference: SnapshotReference | None
    status: Literal["stored", "already_present", "failed", "unknown"]
    diagnostic_code: str | None = None
    writes: tuple[StoredBytesReceipt, ...] = ()

    def __post_init__(self):
        if self.status not in {"stored", "already_present", "failed", "unknown"}:
            raise ValueError("dataset.invalid_write_status")
        if (self.reference is not None) != (self.status in {"stored", "already_present"}):
            raise ValueError("dataset.unconfirmed_reference")


class DatasetCatalog(Protocol):
    provider_id: str
    scope_id: str

    def datasets(self, *, controls: DatasetReadControls | None = None) -> tuple[str, ...]: ...
    def versions(self, dataset_id: str, *, controls: DatasetReadControls | None = None) -> tuple[SnapshotReference, ...]: ...


class DatasetReader(Protocol):
    provider_id: str
    scope_id: str

    def read_snapshot(self, reference: SnapshotReference, components: tuple[str, ...] | None = None,
                      *, controls: DatasetReadControls | None = None) -> DatasetSnapshot: ...


class DatasetVersionWriter(Protocol):
    provider_id: str
    scope_id: str

    def write_snapshot(self, snapshot: DatasetSnapshot | DatasetAssembly,
                       *, controls: DatasetWriteControls | None = None) -> DatasetWriteResult: ...


class DatasetResolver(Protocol):
    def resolve(self, reference: SnapshotReference) -> DatasetReader: ...


def selected_components(manifest, components):
    available = tuple(component.name for component in manifest.components)
    if components is None:
        return available
    if (not isinstance(components, tuple) or any(not isinstance(c, str) for c in components)
            or len(set(components)) != len(components) or not set(components) <= set(available)):
        raise DatasetStorageError("dataset.component_selection_invalid")
    return tuple(name for name in available if name in components)


def validate_scope(provider, reference):
    if (provider.provider_id, provider.scope_id) != (reference.provider_id, reference.scope_id):
        raise DatasetStorageError("dataset.scope_mismatch")


def validate_snapshot(snapshot):
    if isinstance(snapshot, DatasetSnapshot):
        if not snapshot.complete:
            raise DatasetStorageError("dataset.incomplete_snapshot")
    elif not isinstance(snapshot, DatasetAssembly):
        raise DatasetStorageError("dataset.snapshot_required")


def materialize_assembly(assembly, names, provider, resolver, controls):
    tables = []
    if sum(c.row_count * max(1, len(c.schema.columns)) for c in assembly.manifest.components if c.name in names) > controls.max_cells:
        raise DatasetStorageError("dataset.cell_limit")
    for link in assembly.links:
        if link.name not in names:
            continue
        controls.checkpoint()
        if (link.snapshot.provider_id, link.snapshot.scope_id) == (provider.provider_id, provider.scope_id):
            reader = provider
        elif resolver is not None:
            reader = resolver.resolve(link.snapshot)
        else:
            raise DatasetStorageError("dataset.resolver_required")
        validate_scope(reader, link.snapshot)
        part = reader.read_snapshot(link.snapshot, (link.component,), controls=controls)
        if part.identity != link.snapshot.identity:
            raise DatasetStorageError("dataset.snapshot_mismatch")
        tables.append((link.name, part.table(link.component)))
    try:
        return DatasetSnapshot(assembly.manifest, tuple(tables))
    except ValueError as error:
        raise DatasetStorageError("dataset.component_mismatch") from error
