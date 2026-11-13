"""Discover catalog entries, receive selected originals and assemble an archive."""

from pathlib import PurePosixPath
import re

from stratbox.base.ioapi.archive_paths import ArchiveEntry, PathArchiveReceipt, zip_to_store
from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveLimits, safe_member_name, zip_bytes
from stratbox.base.ioapi.staging import current_revision, storage_scope, store_identity
from stratbox.base.limits import BudgetExceeded, ExecutionBudget
from stratbox.base.net import HttpTransport, StreamingHttpTransport
from stratbox.data import ByteIdentity, Representation, UsedInputReceipt, canonical_manifest_bytes
from stratbox.execution import Completion, ExecutionContext, OperationDefinition, OperationFailure, OperationResult, run
from stratbox.execution.originals import (
    ReceiveOriginalRequest, ReceiveToStoreRequest, receive_original_to_store, storage_effect,
)
from stratbox.macrobanks._cbr import (
    WORKBOOK_LIMIT, XLSX_TYPES, cbr_request, official_url, receive_cbr, validate_workbook,
    validate_workbook_stream,
)

from .contracts import (
    CbrFileRegistryItem, Collection, CollectedFile, CollectFailure, CollectFilesRequest, CollectToStoreRequest,
    DiscoverFilesRequest, PrepareArchiveRequest, StoreArchiveRequest, StoredCollectedFile,
)
from .registry import DEFAULT_CBR_FILE_SOURCES

DISCOVER = OperationDefinition("cbr.file_collector.discover", 1, "cbr-file-catalog-1", DiscoverFilesRequest, tuple)
COLLECT = OperationDefinition("cbr.file_collector.collect_raw", 2, "cbr-file-acquisition-1",
                              CollectFilesRequest, Collection, frozenset({"http"}), partial_allowed=True)
ARCHIVE = OperationDefinition("cbr.file_collector.prepare_archive", 1, "cbr-file-zip-1",
                              PrepareArchiveRequest, Representation)
COLLECT_TO_STORE = OperationDefinition(
    "cbr.file_collector.collect_to_store", 1, "cbr-file-stream-1", CollectToStoreRequest, Collection,
    frozenset({"http", "output_filestore"}), frozenset({"storage.write"}), partial_allowed=True,
    limits=ExecutionBudget(temporary_bytes=256 * 1024 * 1024, output_bytes=256 * 1024 * 1024),
)
ARCHIVE_TO_STORE = OperationDefinition(
    "cbr.file_collector.archive_to_store", 1, "cbr-file-stream-zip-1", StoreArchiveRequest, PathArchiveReceipt,
    frozenset({"filestore", "output_filestore"}), frozenset({"storage.write"}),
    limits=ExecutionBudget(input_bytes=256 * 1024 * 1024, output_bytes=257 * 1024 * 1024,
                           temporary_bytes=257 * 1024 * 1024),
)
_ROOTS = ("/vfs/statistics/", "/content/document/file/")
_ARCHIVE_LIMITS = ArchiveLimits(100, 256 * 1024 * 1024, WORKBOOK_LIMIT, 256 * 1024 * 1024)


def discover(request: DiscoverFilesRequest, *, context: ExecutionContext | None = None
             ) -> OperationResult[tuple[CbrFileRegistryItem, ...]]:
    return run(DISCOVER, request, lambda req, invocation: DEFAULT_CBR_FILE_SOURCES, context=context)


def _variants(url: str) -> tuple[str, ...]:
    candidates = [url]
    for pair in (("BankSector", "banksector"), ("Mortgage", "mortgage"),
                 ("Loans_to_corporations", "loans_to_corporations")):
        candidates.extend(re.sub(rf"/{pair[0]}/", f"/{variant}/", candidate, flags=re.I)
                          for candidate in tuple(candidates) for variant in pair)
    return tuple(dict.fromkeys(candidates))


def _download(entry, req, invocation, transport, remaining_batch, *, destination=None, store=None):
    deadline = invocation.context.clock.monotonic() + req.deadline_per_source_seconds
    last_failure = OperationFailure("http.timeout")
    for url in _variants(entry.url) if req.try_case_variants else (entry.url,):
        remaining = deadline - invocation.context.clock.monotonic()
        if remaining <= 0:
            break
        name = entry.expected_file_name or PurePosixPath(official_url(url, roots=_ROOTS)).name
        if not safe_member_name(name) or PurePosixPath(name).name != name:
            raise OperationFailure("source.filename_invalid")
        limit = min(WORKBOOK_LIMIT, remaining_batch)
        try:
            if destination is not None:
                request = cbr_request(url, roots=_ROOTS, media_types=XLSX_TYPES, limit=limit, deadline=remaining)
                item = ReceiveOriginalRequest(request, entry.source_id, XLSX_TYPES, req.retry,
                                              default_media_type="application/octet-stream")
                stored = receive_original_to_store(
                    ReceiveToStoreRequest(item, destination), transport=transport, store=store,
                    invocation=invocation,
                    validate=lambda stream, size: validate_workbook_stream(stream, size, budget=invocation.budget),
                )
                return StoredCollectedFile(entry.source_id, name, stored)
            source = receive_cbr(url, roots=_ROOTS, media_types=XLSX_TYPES, limit=limit,
                                 source_id=entry.source_id, transport=transport, invocation=invocation,
                                 retry=req.retry, deadline=remaining)
        except OperationFailure as error:
            if error.diagnostic.code != "http.status_404":
                raise
            last_failure = error
            continue
        invocation.use(UsedInputReceipt.for_payload(source.payload, "received_workbook"))
        validate_workbook(source.payload.data, budget=invocation.budget)
        return CollectedFile(entry.source_id, name, source)
    raise last_failure


def _collect(req, invocation, transport, *, destinations=None, store=None):
    registry = {entry.source_id: entry for entry in DEFAULT_CBR_FILE_SOURCES}
    selected = req.source_ids
    if not selected or len(set(selected)) != len(selected) or any(key not in registry for key in selected):
        raise OperationFailure("request.source_selection_invalid")
    if not 0 < req.deadline_per_source_seconds <= 600 or not 0 < req.max_batch_bytes <= _ARCHIVE_LIMITS.unpacked_bytes:
        raise OperationFailure("request.acquisition_limits_invalid")
    if destinations is not None:
        if not callable(getattr(transport, "exchange_into", None)):
            raise OperationFailure("provider.capability_missing")
        if destinations.keys() != set(selected) or len({x.locator for x in destinations.values()}) != len(selected):
            raise OperationFailure("request.archive_destinations_invalid")
    attempted, completed, failed = [], [], []
    remaining = req.max_batch_bytes
    interrupted = unresolved = stop = None
    invocation.stage("acquire")
    for key in selected:
        if invocation.cancelled():
            stop = "operation.cancelled"
            break
        if remaining == 0:
            stop = "budget.batch_bytes"
            break
        try:
            invocation.budget.checkpoint()
        except BudgetExceeded as error:
            stop = error.code
            break
        attempted.append(key)
        try:
            item = _download(
                registry[key], req, invocation, transport, remaining,
                destination=destinations[key] if destinations is not None else None, store=store,
            )
            if isinstance(item, StoredCollectedFile):
                storage = item.source.storage
                if storage.status == "unknown":
                    unresolved = item
                    stop = storage.diagnostic_code
                    interrupted = CollectFailure(key, stop)
                    break
                if storage.status == "failed":
                    raise OperationFailure(storage.diagnostic_code)
                size = storage.identity.size
            else:
                size = item.source.payload.identity.size
        except BudgetExceeded as error:
            stop = error.code
            interrupted = CollectFailure(key, stop)
            break
        except OperationFailure as error:
            if error.outcome == "cancelled":
                stop = error.diagnostic.code
                interrupted = CollectFailure(key, stop)
                break
            failed.append(CollectFailure(key, error.diagnostic.code))
            if not req.continue_on_error:
                stop = error.diagnostic.code
                break
        except Exception as error:
            stop = invocation.incident(error)
            interrupted = CollectFailure(key, stop.code)
            break
        else:
            completed.append(item)
            remaining -= size
    if stop == "operation.cancelled" and not completed:
        raise OperationFailure(stop, outcome="cancelled")
    reason = stop if isinstance(stop, str) else stop.code if stop is not None else None
    value = Collection(
        selected, tuple(attempted), tuple(completed), tuple(failed),
        selected[len(attempted):], interrupted, reason, unresolved,
    )
    if unresolved is not None:
        return Completion(value, "unknown", reason)
    if stop is not None or failed:
        code = stop if stop is not None else failed[0].code
        return Completion(value, "partial" if completed else "failed", code)
    return value


def collect_raw(request: CollectFilesRequest, *, transport: HttpTransport | None = None,
                context: ExecutionContext | None = None) -> OperationResult[Collection]:
    return run(COLLECT, request, lambda req, invocation: _collect(req, invocation, transport),
               context=context, providers={"http": transport})


def collect_to_store(request: CollectToStoreRequest, *, transport: StreamingHttpTransport, store,
                     context: ExecutionContext | None = None) -> OperationResult[Collection]:
    def work(req, invocation):
        return _collect(req.selection, invocation, transport, destinations=dict(req.destinations), store=store)
    return run(COLLECT_TO_STORE, request, work, context=context,
               providers={"http": transport, "output_filestore": store})


def prepare_archive(request: PrepareArchiveRequest, *,
                    context: ExecutionContext | None = None) -> OperationResult[Representation]:
    def work(req, invocation):
        invocation.stage("prepare_archive")
        files = {}
        names = set()
        for item in req.files:
            invocation.check_cancelled()
            invocation.budget.charge("objects", 1)
            invocation.budget.charge("input_bytes", item.source.payload.identity.size)
            if not safe_member_name(item.file_name) or "/" in item.file_name or "\\" in item.file_name:
                raise OperationFailure("request.archive_filename_invalid")
            if item.source.receipt.identity != item.source.payload.identity:
                raise OperationFailure("input.digest_mismatch")
            file = PurePosixPath(item.file_name)
            name = file.name
            index = 2
            while name.casefold() in names:
                name = f"{file.stem}_{index}{file.suffix}"
                index += 1
            names.add(name.casefold())
            files[name] = item.source.payload.data
            invocation.use(UsedInputReceipt.for_payload(item.source.payload, item.source_id))
        try:
            data = zip_bytes(files, limits=_ARCHIVE_LIMITS, budget=invocation.budget)
        except ArchiveError as error:
            raise OperationFailure(str(error)) from None
        return Representation("cbr.file_collector.original-zip", 1, "application/zip", data)

    return run(ARCHIVE, request, work, context=context)


def archive_to_store(request: StoreArchiveRequest, *, source_store, output_store,
                     context: ExecutionContext | None = None) -> OperationResult[PathArchiveReceipt]:
    def work(req, invocation):
        invocation.stage("prepare_archive")
        entries = []
        for item in req.files:
            invocation.check_cancelled()
            material = item.source.material
            if material is None or material.store_id != store_identity(source_store):
                raise OperationFailure("input.material_unavailable")
            try:
                if material.store_scope is not None and storage_scope(source_store, material.locator) != material.store_scope:
                    raise OperationFailure("input.material_store_mismatch")
                if material.revision is not None and current_revision(source_store, material.locator) != material.revision:
                    raise OperationFailure("input.material_version_changed")
            except OSError:
                raise OperationFailure("input.material_unavailable") from None
            entries.append(ArchiveEntry(material.locator, item.file_name, material.identity))
            invocation.use(UsedInputReceipt("archive_member", material.identity, material.media_type,
                                            "reference_only", item.source_id))
        target = req.destination
        plan = ByteIdentity.of(canonical_manifest_bytes({
            "members": [[entry.name, entry.identity.sha256, entry.identity.size] for entry in entries],
        }))
        if invocation.context.profile == "managed" and target.mode == "best_effort_verified":
            raise OperationFailure("effect.mode_forbidden")
        try:
            value = zip_to_store(
                tuple(entries), target.locator, source_store=source_store, output_store=output_store,
                budget=invocation.budget, checkpoint=invocation.check_cancelled, mode=target.mode,
                expected_revision=target.expected_revision, operation_id=ARCHIVE_TO_STORE.operation_id,
                require_admission=invocation.context.profile == "managed",
                plan_identity=plan,
                on_effect=lambda receipt: storage_effect(invocation, receipt),
            )
        except ArchiveError as error:
            raise OperationFailure(str(error)) from None
        except OSError:
            raise OperationFailure("effect.staging_failed") from None
        if value.storage.status in {"failed", "unknown"}:
            return Completion(value, value.storage.status, value.storage.diagnostic_code)
        return value
    return run(ARCHIVE_TO_STORE, request, work, context=context,
               providers={"filestore": source_store, "output_filestore": output_store})
