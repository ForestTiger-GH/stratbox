"""Discover catalog entries, receive selected originals and assemble an archive."""

from pathlib import PurePosixPath
import re
from time import monotonic

from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveLimits, safe_member_name, zip_bytes
from stratbox.base.net import HttpTransport
from stratbox.data import Representation, UsedInputReceipt
from stratbox.execution import Completion, ExecutionContext, OperationDefinition, OperationFailure, OperationResult, run
from stratbox.macrobanks._cbr import WORKBOOK_LIMIT, XLSX_TYPES, official_url, receive_cbr, validate_workbook

from .contracts import CbrFileRegistryItem, Collection, CollectedFile, CollectFailure, CollectFilesRequest, DiscoverFilesRequest, PrepareArchiveRequest
from .registry import DEFAULT_CBR_FILE_SOURCES

DISCOVER = OperationDefinition("cbr.file_collector.discover", 1, "cbr-file-catalog-1", DiscoverFilesRequest, tuple)
COLLECT = OperationDefinition("cbr.file_collector.collect_raw", 1, "cbr-file-acquisition-1",
                              CollectFilesRequest, Collection, frozenset({"http"}), partial_allowed=True)
ARCHIVE = OperationDefinition("cbr.file_collector.prepare_archive", 1, "cbr-file-zip-1",
                              PrepareArchiveRequest, Representation)
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


def _download(entry, req, invocation, transport, remaining_batch):
    deadline = monotonic() + req.deadline_per_source_seconds
    last_failure = OperationFailure("http.timeout")
    for url in _variants(entry.url) if req.try_case_variants else (entry.url,):
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        try:
            source = receive_cbr(url, roots=_ROOTS, media_types=XLSX_TYPES,
                                 limit=min(WORKBOOK_LIMIT, remaining_batch), source_id=entry.source_id,
                                 transport=transport, invocation=invocation, retry=req.retry, deadline=remaining)
        except OperationFailure as error:
            if error.diagnostic.code != "http.status_404":
                raise
            last_failure = error
            continue
        validate_workbook(source.payload.data)
        name = entry.expected_file_name or PurePosixPath(official_url(url, roots=_ROOTS)).name
        if not safe_member_name(name) or PurePosixPath(name).name != name:
            raise OperationFailure("source.filename_invalid")
        return CollectedFile(entry.source_id, name, source)
    raise last_failure


def collect_raw(request: CollectFilesRequest, *, transport: HttpTransport | None = None,
                context: ExecutionContext | None = None) -> OperationResult[Collection]:
    def work(req, invocation):
        registry = {entry.source_id: entry for entry in DEFAULT_CBR_FILE_SOURCES}
        selected = req.source_ids
        if not selected or len(set(selected)) != len(selected) or any(key not in registry for key in selected):
            raise OperationFailure("request.source_selection_invalid")
        if not 0 < req.deadline_per_source_seconds <= 600 or not 0 < req.max_batch_bytes <= _ARCHIVE_LIMITS.unpacked_bytes:
            raise OperationFailure("request.acquisition_limits_invalid")
        attempted, completed, failed = [], [], []
        remaining = req.max_batch_bytes
        invocation.stage("acquire")
        for key in selected:
            if remaining == 0 or (invocation.context.cancellation is not None
                                  and invocation.context.cancellation.is_set()):
                break
            attempted.append(key)
            try:
                item = _download(registry[key], req, invocation, transport, remaining)
            except OperationFailure as error:
                failed.append(CollectFailure(key, error.diagnostic.code))
                if error.outcome == "cancelled" or not req.continue_on_error:
                    break
            else:
                completed.append(item)
                remaining -= item.source.payload.identity.size
        value = Collection(selected, tuple(attempted), tuple(completed), tuple(failed), selected[len(attempted):])
        if failed or value.not_attempted:
            code = failed[0].code if failed else "operation.selection_incomplete"
            return Completion(value, "partial" if completed else "failed", code)
        return value

    return run(COLLECT, request, work, context=context, providers={"http": transport})


def prepare_archive(request: PrepareArchiveRequest, *,
                    context: ExecutionContext | None = None) -> OperationResult[Representation]:
    def work(req, invocation):
        invocation.stage("prepare_archive")
        files = {}
        names = set()
        for item in req.files:
            invocation.check_cancelled()
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
            data = zip_bytes(files, limits=_ARCHIVE_LIMITS)
        except ArchiveError as error:
            raise OperationFailure(str(error)) from None
        return Representation("cbr.file_collector.original-zip", 1, "application/zip", data)

    return run(ARCHIVE, request, work, context=context)
