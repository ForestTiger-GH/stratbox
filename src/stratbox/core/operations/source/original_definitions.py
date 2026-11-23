"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

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

from stratbox.shared.data.processing import DataContract, DataRole

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


RECEIVE = _registry_definition('source.receive_original')

SAVE = _registry_definition('source.save_original')

RECEIVE_TO_STORE = _registry_definition('source.receive_to_store')

READ = _registry_definition('source.read_original')

RECONCILE = _registry_definition('source.reconcile_original')
