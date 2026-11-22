"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from stratbox.core.storage.filestore import WriteMode
from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .cleanup import ApplyCleanupRequest, CleanupPlan, PlanCleanupRequest

@dataclass(frozen=True, slots=True)
class StreamArchiveRequest:
    """Publish the approved FRG latest-file selection as a disk-streamed ZIP."""
    plan: CleanupPlan
    destination: str
    report_json: bytes | None = None
    compression: str = "stored"
    mode: WriteMode = "immutable"
    expected_revision: str | None = None

@dataclass(frozen=True, slots=True)
class ScanRequest:
    directory: str
    recursive: bool = False

@dataclass(frozen=True, slots=True)
class Catalog:
    files: DataFrame
    latest: DataFrame
    dispatch: DataFrame

_STREAM_STORES = frozenset({"filestore", "output_filestore"})

STREAM_ARCHIVE = OperationDefinition(
    "frg.prepare_archive_to_store",
    2,
    "frg-verified-streaming-zip-2",
    StreamArchiveRequest,
    PathArchiveReceipt,
    _STREAM_STORES,
    frozenset({"storage.write"}),
)

_STORE = frozenset({"filestore"})

_EFFECTS = frozenset({"storage.copy", "storage.rename", "storage.remove"})

SCAN = OperationDefinition("frg.scan", 1, "frg-catalog-1", ScanRequest, Catalog, _STORE)

PLAN = OperationDefinition(
    "frg.plan_cleanup", 1, "frg-cleanup-plan-1", PlanCleanupRequest, CleanupPlan, _STORE
)

APPLY = OperationDefinition(
    "frg.apply_cleanup",
    1,
    "frg-conditional-cleanup-1",
    ApplyCleanupRequest,
    tuple,
    _STORE,
    _EFFECTS,
    partial_allowed=True,
)

ARCHIVE = OperationDefinition(
    "frg.prepare_archive", 1, "frg-latest-zip-1", CleanupPlan, Representation, _STORE
)

