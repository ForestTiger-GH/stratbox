"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from stratbox.core.storage.filestore import WriteMode
from stratbox.core.limits import ExecutionBudget
from stratbox.core.network import HttpRequest, RetryPolicy
from stratbox.shared.evidence import (
    AcquiredSource,
    AcquisitionReceipt,
    MaterialReference,
    SourcePayload,
    StoredBytesReceipt,
)
from stratbox.core.execution.contracts import OperationDefinition

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_HTTP = frozenset({"http"})

_OUTPUT = frozenset({"output_filestore"})

_SOURCE = frozenset({"filestore"})

_WRITE = frozenset({"storage.write"})

_MATERIAL_LIMIT = 512 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReceiveOriginalRequest:
    request: HttpRequest
    source_id: str
    media_types: frozenset[str]
    retry: RetryPolicy = RetryPolicy()
    baseline: AcquiredSource | None = field(default=None, repr=False)
    default_media_type: str | None = None


@dataclass(frozen=True, slots=True)
class OriginalDestination:
    locator: str = field(repr=False)
    mode: WriteMode = "immutable"
    expected_revision: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class SaveOriginalRequest:
    source: SourcePayload | AcquiredSource
    destination: OriginalDestination


@dataclass(frozen=True, slots=True)
class ReceiveToStoreRequest:
    source: ReceiveOriginalRequest
    destination: OriginalDestination
    baseline: StoredOriginal | None = None


@dataclass(frozen=True, slots=True)
class ReadOriginalRequest:
    material: MaterialReference
    limit: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReconcileOriginalRequest:
    receipt: StoredBytesReceipt


@dataclass(frozen=True, slots=True)
class StoredOriginal:
    storage: StoredBytesReceipt
    material: MaterialReference | None
    acquisition: AcquisitionReceipt | None = None


RECEIVE = OperationDefinition(
    "source.receive_original",
    1,
    "http-receive-1",
    ReceiveOriginalRequest,
    AcquiredSource,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Receive exact source bytes without requiring parsing or storage.",
        outputs=(
            OutputPort(
                "source",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
        parameters=(
            "request",
            "source_id",
            "media_types",
            "retry",
            "baseline",
            "default_media_type",
        ),
    ),
)

SAVE = OperationDefinition(
    "source.save_original",
    1,
    "original-storage-1",
    SaveOriginalRequest,
    StoredOriginal,
    _OUTPUT,
    _WRITE,
    limits=ExecutionBudget(
        input_bytes=_MATERIAL_LIMIT,
        output_bytes=_MATERIAL_LIMIT,
        temporary_bytes=_MATERIAL_LIMIT,
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.PRESERVE,),
        summary="Preserve exact original bytes and return separately qualified storage evidence.",
        inputs=(
            InputPort(
                "source",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="source",
            ),
        ),
        outputs=(
            OutputPort(
                "material",
                DataContract("source.material_reference", 1, DataRole.ORIGINALS),
                path="material",
                qualifications=frozenset(("storage.confirmed",)),
            ),
            OutputPort(
                "storage",
                DataContract("source.storage_receipt", 1, None),
                path="storage",
            ),
        ),
        parameters=("destination",),
    ),
)

RECEIVE_TO_STORE = OperationDefinition(
    "source.receive_to_store",
    1,
    "original-stream-1",
    ReceiveToStoreRequest,
    StoredOriginal,
    _HTTP | _OUTPUT,
    _WRITE,
    optional_capabilities=_SOURCE,
    limits=ExecutionBudget(
        input_bytes=_MATERIAL_LIMIT,
        output_bytes=_MATERIAL_LIMIT,
        temporary_bytes=_MATERIAL_LIMIT,
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.PRESERVE),
        summary="Stream an original into a caller-selected store with a confirmed commit boundary.",
        outputs=(
            OutputPort(
                "material",
                DataContract("source.material_reference", 1, DataRole.ORIGINALS),
                path="material",
                qualifications=frozenset(("storage.confirmed",)),
            ),
            OutputPort(
                "storage",
                DataContract("source.storage_receipt", 1, None),
                path="storage",
            ),
        ),
        parameters=("source", "destination", "baseline"),
        composition=True,
    ),
)

READ = OperationDefinition(
    "source.read_original",
    1,
    "original-replay-1",
    ReadOriginalRequest,
    SourcePayload,
    _SOURCE,
    processing=OperationSemantics(
        stages=(ProcessingStage.PRESERVE,),
        summary="Read retained original bytes and verify their exact identity.",
        inputs=(
            InputPort(
                "material",
                DataContract("source.material_reference", 1, DataRole.ORIGINALS),
                path="material",
                qualifications=frozenset(("storage.confirmed",)),
            ),
        ),
        outputs=(
            OutputPort("source", DataContract("source.payload", 1, DataRole.ORIGINALS)),
        ),
        parameters=("limit",),
    ),
)

RECONCILE = OperationDefinition(
    "source.reconcile_original",
    1,
    "original-read-back-1",
    ReconcileOriginalRequest,
    StoredBytesReceipt,
    _SOURCE,
    processing=OperationSemantics(
        stages=(ProcessingStage.VALIDATE,),
        summary="Reconcile original storage using read-back evidence.",
        inputs=(
            InputPort(
                "receipt",
                DataContract("source.storage_receipt", 1, None),
                path="receipt",
            ),
        ),
        outputs=(
            OutputPort("storage", DataContract("source.storage_receipt", 1, None)),
        ),
    ),
)
