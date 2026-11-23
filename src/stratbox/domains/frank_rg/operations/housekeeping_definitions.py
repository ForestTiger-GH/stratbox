"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from stratbox.core.storage.filestore import WriteMode
from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from ..publications.cleanup import ApplyCleanupRequest, CleanupPlan, PlanCleanupRequest

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
    ProcessingFunction,
)


@dataclass(frozen=True, slots=True)
class StreamArchiveRequest:
    """Publish the approved FRG latest-file selection as a disk-streamed ZIP."""

    plan: CleanupPlan
    destination: str
    report_json: bytes | None = None
    compression: str = "stored"
    mode: WriteMode = "immutable"
    expected_revision: str | None = None


_STREAM_STORES = frozenset({"filestore", "output_filestore"})

STREAM_ARCHIVE = OperationDefinition(
    "frg.prepare_archive_to_store",
    3,
    "frg-verified-streaming-manifest-zip-profile-4",
    StreamArchiveRequest,
    PathArchiveReceipt,
    _STREAM_STORES,
    frozenset({"storage.write"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER, ProcessingStage.PRESERVE),
        summary="Stream selected original reports into a verified archive commit.",
        inputs=(
            InputPort("plan", DataContract("frg.cleanup_plan", 1, None), path="plan"),
        ),
        outputs=(
            OutputPort(
                "archive", DataContract("frg.stored_archive", 2, DataRole.PRODUCTS)
            ),
        ),
        parameters=(
            "destination",
            "report_json",
            "compression",
            "mode",
            "expected_revision",
        ),
        composition=True,
    ),
)

_STORE = frozenset({"filestore"})

_EFFECTS = frozenset({"storage.copy", "storage.rename", "storage.remove"})

PLAN = OperationDefinition(
    "frg.plan_cleanup",
    1,
    "frg-cleanup-plan-profile-2",
    PlanCleanupRequest,
    CleanupPlan,
    _STORE,
    processing=OperationSemantics(
        stages=(), function=ProcessingFunction.MAINTAIN,
        summary="Prepare a read-only, revision-bound report cleanup proposal.",
        outputs=(OutputPort("plan", DataContract("frg.cleanup_plan", 1, None)),),
        parameters=("directory", "delete_others"),
    ),
)

APPLY = OperationDefinition(
    "frg.apply_cleanup",
    1,
    "frg-conditional-cleanup-profile-2",
    ApplyCleanupRequest,
    tuple,
    _STORE,
    _EFFECTS,
    partial_allowed=True,
    processing=OperationSemantics(
        stages=(), function=ProcessingFunction.MAINTAIN,
        summary="Apply explicitly authorized cleanup effects with per-action receipts.",
        inputs=(
            InputPort("plan", DataContract("frg.cleanup_plan", 1, None), path="plan"),
        ),
        outputs=(
            OutputPort("receipts", DataContract("frg.cleanup_receipts", 1, None)),
        ),
        parameters=("authorized_directory", "expected_sha256"),
    ),
)

ARCHIVE = OperationDefinition(
    "frg.prepare_archive",
    2,
    "frg-latest-manifest-zip-profile-3",
    CleanupPlan,
    Representation,
    _STORE,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Package the selected retained original reports without executing cleanup.",
        inputs=(InputPort("plan", DataContract("frg.cleanup_plan", 1, None)),),
        outputs=(
            OutputPort("archive", DataContract("frg.archive", 2, DataRole.PRODUCTS)),
        ),
    ),
)
