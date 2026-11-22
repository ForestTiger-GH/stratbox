"""Declarative logical dataset operation contracts, without executable handlers."""

from __future__ import annotations

from dataclasses import dataclass

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference
from .ports import DatasetWriteResult

_LIMITS = ExecutionBudget(input_bytes=512 * 1024 * 1024, output_bytes=512 * 1024 * 1024, temporary_bytes=512 * 1024 * 1024)
_SNAPSHOT = DataContract("dataset.snapshot", 1)
_REFERENCE = DataContract("dataset.snapshot_reference", 1)


@dataclass(frozen=True, slots=True)
class ReadSnapshotRequest:
    reference: SnapshotReference
    components: tuple[str, ...] | None = None
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class WriteSnapshotRequest:
    snapshot: DatasetSnapshot | DatasetAssembly
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class ListVersionsRequest:
    dataset_id: str
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class DatasetVersions:
    dataset_id: str
    references: tuple[SnapshotReference, ...]


READ = OperationDefinition("dataset.read_snapshot", 1, "dataset-read-1", ReadSnapshotRequest, DatasetSnapshot,
    frozenset({"dataset_reader"}), limits=_LIMITS,
    processing=OperationSemantics((ProcessingStage.PRESERVE,),
        inputs=(InputPort("reference", _REFERENCE, path="reference", qualifications=frozenset({"storage.confirmed"})),),
        outputs=(OutputPort("snapshot", _SNAPSHOT),), parameters=("components", "selection"),
        summary="Read selected typed components from a pinned logical dataset version."))

WRITE = OperationDefinition("dataset.write_snapshot", 1, "dataset-write-1", WriteSnapshotRequest, DatasetWriteResult,
    frozenset({"dataset_writer"}), frozenset({"dataset.write", "storage.write"}), partial_allowed=True, limits=_LIMITS,
    processing=OperationSemantics((ProcessingStage.INGEST, ProcessingStage.PRESERVE),
        inputs=(InputPort("snapshot", _SNAPSHOT, path="snapshot", alternatives=(DataContract("dataset.assembly", 1),)),),
        outputs=(OutputPort("reference", _REFERENCE, path="reference", qualifications=frozenset({"storage.confirmed"})),
                 OutputPort("receipt", DataContract("dataset.write_receipt", 1))),
        parameters=("selection",), summary="Publish an immutable logical dataset version through a selected adapter."))

LIST = OperationDefinition("dataset.list_versions", 1, "dataset-catalog-1", ListVersionsRequest, DatasetVersions,
    frozenset({"dataset_catalog"}), limits=_LIMITS,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        outputs=(OutputPort("versions", DataContract("dataset.version_catalog", 1)),),
        parameters=("dataset_id", "selection"), summary="List explicit immutable versions within one selected dataset scope."))

