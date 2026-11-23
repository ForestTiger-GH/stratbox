"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

from dataclasses import dataclass
from stratbox.core.storage.filestore import WriteMode
from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.shared.data.representation import Representation
from ..publications.cleanup import ApplyCleanupRequest, CleanupPlan, PlanCleanupRequest

from stratbox.shared.data.processing import DataContract, DataRole


@dataclass(frozen=True, slots=True)
class StreamArchiveRequest:
    """Publish the approved FRG latest-file selection as a disk-streamed ZIP."""

    plan: CleanupPlan
    destination: str
    report_json: bytes | None = None
    compression: str = "stored"
    mode: WriteMode = "immutable"
    expected_revision: str | None = None


STREAM_ARCHIVE = _registry_definition('frg.prepare_archive_to_store')


PLAN = _registry_definition('frg.plan_cleanup')

APPLY = _registry_definition('frg.apply_cleanup')

ARCHIVE = _registry_definition('frg.prepare_archive')
