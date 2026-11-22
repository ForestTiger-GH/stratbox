"""Acquire exact files or admit bytes supplied by a specialized external method."""
from __future__ import annotations

from stratbox.core.storage.bytes import inspect_file_version, read_bounded_bytes
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from .contracts import AcquiredReport, AcquireRequest, CaptureRequest, FileEntry, ReportPeriod

MAX_MATERIAL_BYTES = 512 * 1024 * 1024
MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsm": "application/vnd.ms-excel.sheet.macroenabled.12",
    "xlsb": "application/vnd.ms-excel.sheet.binary.macroenabled.12",
    "xls": "application/vnd.ms-excel",
}


def validate_period(period: ReportPeriod, *, periodicity: str, min_period_date=None) -> None:
    if not isinstance(period, ReportPeriod):
        raise ValueError("frg.period.required")
    if (periodicity == "month_week") != (period.week_no is not None):
        raise ValueError("frg.period.mode_mismatch")
    if min_period_date is not None and period.snapshot_date < min_period_date:
        raise ValueError("frg.period.before_supported_layout")


def capture_material(request: CaptureRequest, *, admitted_formats: frozenset[str],
                     periodicity: str, min_period_date=None, invocation=None) -> AcquiredReport:
    validate_period(request.period, periodicity=periodicity, min_period_date=min_period_date)
    if request.format not in admitted_formats or request.format not in MEDIA_TYPES:
        raise ValueError("frg.material.format_unsupported")
    payload = request.payload
    if not isinstance(payload, SourcePayload) or not 0 < payload.identity.size <= MAX_MATERIAL_BYTES:
        raise ValueError("frg.material.size_invalid")
    if payload.source_id not in {None, request.source_id}:
        raise ValueError("frg.material.source_mismatch")
    if payload.media_type not in {"application/octet-stream", MEDIA_TYPES[request.format]}:
        raise ValueError("frg.material.media_type_mismatch")
    if invocation is not None:
        invocation.check_cancelled()
        invocation.budget.charge("input_bytes", payload.identity.size)
    # The format is admitted metadata. No workbook parser is invoked here.
    identified = SourcePayload(payload.data, MEDIA_TYPES[request.format], request.source_id,
                               expected_sha256=payload.identity.sha256)
    if invocation is not None:
        invocation.use(UsedInputReceipt.for_payload(identified, "supplied_original"))
    return AcquiredReport(request.source_id, request.period, request.format, identified, "supplied")


def acquire_material(request: AcquireRequest, store, invocation) -> AcquiredReport:
    """Read the exact selected file, verifying version and bytes around the read."""
    asset = request.asset
    if not asset.valid or asset.source_id is None or asset.period is None:
        raise ValueError("frg.material.asset_invalid")
    if type(request.max_bytes) is not int or not 0 < request.max_bytes <= MAX_MATERIAL_BYTES:
        raise ValueError("frg.material.limit_invalid")
    if any(not callable(getattr(store, name, None)) for name in ("stat", "inspect_file", "open_read")):
        raise ValueError("frg.material.version_capability_missing")
    observed = store.stat(asset.entry.path)
    if not observed.is_file or observed.is_symlink or observed.size is None:
        raise ValueError("frg.material.file_invalid")
    if observed.size <= 0 or observed.size > request.max_bytes:
        raise ValueError("frg.material.size_invalid")
    if ((asset.entry.size_bytes is not None and observed.size != asset.entry.size_bytes)
            or (asset.entry.mtime is not None and observed.mtime != asset.entry.mtime)):
        raise ValueError("frg.material.discovery_stale")
    before = inspect_file_version(asset.entry.path, store=store, budget=invocation.budget,
                                  checkpoint=invocation.check_cancelled)
    if before.path != asset.entry.path or before.identity.size != observed.size:
        raise ValueError("frg.material.source_changed")
    if request.expected_identity is not None and before.identity != request.expected_identity:
        raise ValueError("frg.material.identity_mismatch")
    data = read_bounded_bytes(asset.entry.path, store=store, limit=observed.size,
                              budget=invocation.budget, checkpoint=invocation.check_cancelled)
    if ByteIdentity.of(data) != before.identity:
        raise ValueError("frg.material.source_changed")
    after = inspect_file_version(asset.entry.path, store=store, budget=invocation.budget,
                                 checkpoint=invocation.check_cancelled)
    if after != before:
        raise ValueError("frg.material.source_changed")
    final_info = store.stat(asset.entry.path)
    if (not final_info.is_file or final_info.is_symlink or final_info.size != observed.size
            or (observed.mtime is not None and final_info.mtime != observed.mtime)):
        raise ValueError("frg.material.source_changed")
    payload = SourcePayload(data, MEDIA_TYPES[asset.format], asset.source_id,
                            expected_sha256=before.identity.sha256)
    invocation.use(UsedInputReceipt.for_payload(payload, "file_original"))
    entry = FileEntry(asset.entry.path, asset.entry.filename, final_info.size, final_info.mtime)
    return AcquiredReport(asset.source_id, asset.period, asset.format, payload, "filestore", after, entry)
