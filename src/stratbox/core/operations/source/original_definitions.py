"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from stratbox.core.storage.filestore import WriteMode
from stratbox.core.limits import ExecutionBudget
from stratbox.core.network import HttpRequest, RetryPolicy
from stratbox.shared.evidence import AcquiredSource, AcquisitionReceipt, MaterialReference, SourcePayload, StoredBytesReceipt
from stratbox.core.execution.contracts import OperationDefinition

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

RECEIVE = OperationDefinition("source.receive_original", 1, "http-receive-1", ReceiveOriginalRequest,
                              AcquiredSource, _HTTP)

SAVE = OperationDefinition("source.save_original", 1, "original-storage-1", SaveOriginalRequest,
                           StoredOriginal, _OUTPUT, _WRITE,
                           limits=ExecutionBudget(input_bytes=_MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT,
                                                  temporary_bytes=_MATERIAL_LIMIT))

RECEIVE_TO_STORE = OperationDefinition(
    "source.receive_to_store", 1, "original-stream-1", ReceiveToStoreRequest, StoredOriginal,
    _HTTP | _OUTPUT, _WRITE,
    optional_capabilities=_SOURCE,
    limits=ExecutionBudget(input_bytes=_MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT,
                           temporary_bytes=_MATERIAL_LIMIT),
)

READ = OperationDefinition("source.read_original", 1, "original-replay-1", ReadOriginalRequest, SourcePayload, _SOURCE)

RECONCILE = OperationDefinition("source.reconcile_original", 1, "original-read-back-1", ReconcileOriginalRequest,
                               StoredBytesReceipt, _SOURCE)

