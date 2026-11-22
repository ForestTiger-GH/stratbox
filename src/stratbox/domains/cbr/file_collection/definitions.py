"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import (
    CollectFilesRequest,
    CollectToStoreRequest,
    Collection,
    DiscoverFilesRequest,
    PrepareArchiveRequest,
    StoreArchiveRequest,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

DISCOVER = OperationDefinition(
    "cbr.file_collector.discover",
    1,
    "cbr-file-catalog-1",
    DiscoverFilesRequest,
    tuple,
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Select registered source-file routes without downloading material.",
        outputs=(
            OutputPort("sources", DataContract("cbr.file_collector.sources", 1, None)),
        ),
    ),
)

COLLECT = OperationDefinition(
    "cbr.file_collector.collect_raw",
    2,
    "cbr-file-acquisition-1",
    CollectFilesRequest,
    Collection,
    frozenset({"http"}),
    partial_allowed=True,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire independently qualified original files with an explicit remaining-work set.",
        outputs=(
            OutputPort(
                "collection",
                DataContract("cbr.file_collector.collection", 1, DataRole.ORIGINALS),
            ),
        ),
        parameters=(
            "source_ids",
            "continue_on_error",
            "try_case_variants",
            "deadline_per_source_seconds",
            "max_batch_bytes",
            "retry",
        ),
    ),
)

ARCHIVE = OperationDefinition(
    "cbr.file_collector.prepare_archive",
    2,
    "cbr-file-manifest-zip-2",
    PrepareArchiveRequest,
    Representation,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render a manifest-bearing archive whose members retain their original role.",
        inputs=(
            InputPort(
                "files",
                DataContract(
                    "cbr.file_collector.collected_files", 1, DataRole.ORIGINALS
                ),
                path="files",
            ),
        ),
        outputs=(
            OutputPort(
                "archive",
                DataContract("cbr.file_collector.archive", 2, DataRole.PRODUCTS),
            ),
        ),
    ),
)

COLLECT_TO_STORE = OperationDefinition(
    "cbr.file_collector.collect_to_store",
    1,
    "cbr-file-stream-1",
    CollectToStoreRequest,
    Collection,
    frozenset({"http", "output_filestore"}),
    frozenset({"storage.write"}),
    partial_allowed=True,
    limits=ExecutionBudget(
        temporary_bytes=256 * 1024 * 1024, output_bytes=256 * 1024 * 1024
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.PRESERVE),
        summary="Acquire and preserve selected originals with per-file outcomes.",
        outputs=(
            OutputPort(
                "collection",
                DataContract(
                    "cbr.file_collector.stored_collection", 1, DataRole.ORIGINALS
                ),
            ),
        ),
        parameters=("selection", "destinations"),
        composition=True,
    ),
)

ARCHIVE_TO_STORE = OperationDefinition(
    "cbr.file_collector.archive_to_store",
    2,
    "cbr-file-stream-manifest-zip-2",
    StoreArchiveRequest,
    PathArchiveReceipt,
    frozenset({"filestore", "output_filestore"}),
    frozenset({"storage.write"}),
    limits=ExecutionBudget(
        input_bytes=256 * 1024 * 1024,
        output_bytes=257 * 1024 * 1024,
        temporary_bytes=257 * 1024 * 1024,
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER, ProcessingStage.PRESERVE),
        summary="Stream retained original files into a verified archive commit.",
        inputs=(
            InputPort(
                "files",
                DataContract("cbr.file_collector.stored_files", 1, DataRole.ORIGINALS),
                path="files",
            ),
        ),
        outputs=(
            OutputPort(
                "archive",
                DataContract(
                    "cbr.file_collector.stored_archive", 2, DataRole.PRODUCTS
                ),
            ),
        ),
        parameters=("destination",),
        composition=True,
    ),
)
