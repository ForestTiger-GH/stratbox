"""Directory and supplied-material routes share logical source and byte identity."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import os
import sys
from threading import Event

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.limits import ExecutionBudget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg
from stratbox.domains.frank_rg.publications.contracts import (
    AcquireRequest, AssessMaterialRequest, CaptureRequest, Catalog,
    DiscoveryRequest, InspectionRequest, PrepareFileRequest, ReportPeriod, SelectionRequest,
    SourceCheckpoint, UpdateRequest,
)
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


SOURCE = "frg.express.issuance"
NAME = "2026-05-01_Экспресс выдачи.xlsx"
PERIOD = ReportPeriod(date(2026, 5, 1))
# Opaque bytes intentionally exercise file handling without a workbook parser.
ORIGINAL = b"opaque original workbook material"


def value(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def catalog(store, directory="."):
    index = value(frg.discover(DiscoveryRequest(directory), store=store))
    inventory = value(frg.inspect(InspectionRequest(index)))
    selections = value(frg.select(SelectionRequest(inventory)))
    return Catalog(inventory, selections)


def selected(catalog_value, source_id=SOURCE):
    selection = next(item for item in catalog_value.selections if item.source_id == source_id)
    assert selection.state == "selected"
    assert selection.asset is not None
    return selection.asset


def captured(data=ORIGINAL, *, source_id=SOURCE, period=PERIOD, format="xlsx", payload_source=None):
    return frg.capture(CaptureRequest(
        source_id, period, SourcePayload(data, source_id=payload_source), format,
    ))


def test_runtime_directory_changes_leave_logical_source_and_material_unchanged(tmp_path):
    store = LocalFileStore(root=str(tmp_path))
    for directory in ("content", "mounted_share"):
        target = tmp_path / directory
        target.mkdir()
        (target / NAME).write_bytes(ORIGINAL)
    left = selected(catalog(store, "content"))
    right = selected(catalog(store, "mounted_share"))
    assert left.entry.path != right.entry.path
    assert left.source_id == right.source_id == SOURCE
    a = value(frg.acquire(AcquireRequest(left), store=store))
    b = value(frg.acquire(AcquireRequest(right), store=store))
    assert a.payload.identity == b.payload.identity == ByteIdentity.of(ORIGINAL)
    baseline = SourceCheckpoint(a.source_id, a.period, a.payload.identity, a.entry)
    comparison = value(frg.assess_material(AssessMaterialRequest(b, baseline)))
    assert comparison.state == "unchanged"


def test_supplied_material_needs_no_filename_or_filesystem_provider():
    result = captured()
    report = value(result)
    assert report.route == "supplied"
    assert report.entry is report.file_version is None
    assert report.source_id == report.payload.source_id == SOURCE
    assert report.payload.data == ORIGINAL
    assert report.payload.identity == ByteIdentity.of(ORIGINAL)
    assert not result.effects
    assert not hasattr(report, "status_code")


def test_canonical_naming_preserves_the_exact_bytes_for_both_input_routes(tmp_path):
    (tmp_path / NAME).write_bytes(ORIGINAL)
    store = LocalFileStore(root=str(tmp_path))
    file_report = value(frg.acquire(AcquireRequest(selected(catalog(store))), store=store))
    supplied_report = value(captured())
    left = value(frg.prepare_file(PrepareFileRequest(file_report)))
    right = value(frg.prepare_file(PrepareFileRequest(supplied_report)))
    assert left.filename == right.filename == NAME
    assert left.source_id == right.source_id == SOURCE
    assert left.naming_profile_id == right.naming_profile_id
    assert left.naming_method_version == right.naming_method_version
    assert left.payload.data == right.payload.data == ORIGINAL
    assert left.payload.identity == right.payload.identity == ByteIdentity.of(ORIGINAL)


@pytest.mark.parametrize("arguments", [
    {"source_id": "frg.unregistered.report"},
    {"format": "pdf"},
    {"payload_source": "frg.express.portfolios"},
    {"source_id": "frg.express.issuance_weekly"},
    {"period": ReportPeriod(date(2026, 5, 1), 2)},
    {"source_id": "frg.regional.issuance", "period": ReportPeriod(date(2026, 3, 1))},
])
def test_supplied_material_admission_checks_source_format_and_period(arguments):
    result = captured(**arguments)
    assert result.outcome == "failed"
    assert result.value is None and not result.effects


def test_acquisition_rechecks_filename_and_declared_source(tmp_path):
    (tmp_path / NAME).write_bytes(ORIGINAL)
    store = LocalFileStore(root=str(tmp_path))
    asset = selected(catalog(store))
    forged_source = replace(asset, source_id="frg.express.portfolios", slot="portfolios")
    with pytest.raises(ValueError):
        replace(asset.entry, filename="2026-05-01_Экспресс портфели.xlsx")
    result = frg.acquire(AcquireRequest(forged_source), store=store)
    assert result.outcome == "failed" and result.value is None
    assert not result.effects


def test_acquisition_rejects_changed_discovery_metadata_and_wrong_expected_bytes(tmp_path):
    target = tmp_path / NAME
    target.write_bytes(ORIGINAL)
    store = LocalFileStore(root=str(tmp_path))
    asset = selected(catalog(store))
    mismatch = frg.acquire(AcquireRequest(asset, ByteIdentity.of(b"different")), store=store)
    assert mismatch.outcome == "failed" and mismatch.value is None
    target.write_bytes(ORIGINAL + b"replacement")
    changed = frg.acquire(AcquireRequest(asset), store=store)
    assert changed.outcome == "failed" and changed.value is None
    assert not changed.effects


def test_acquisition_rejects_replacement_between_version_check_and_read(tmp_path):
    target = tmp_path / NAME
    target.write_bytes(ORIGINAL)

    class ReplacingStore(LocalFileStore):
        def open_read(self, path):
            target.write_bytes(b"X" * len(ORIGINAL))
            return super().open_read(path)

    store = ReplacingStore(root=str(tmp_path))
    asset = selected(catalog(store))
    result = frg.acquire(AcquireRequest(asset), store=store)
    assert result.outcome == "failed" and result.value is None
    assert not result.effects


def test_identical_file_metadata_never_claims_identical_bytes(tmp_path):
    target = tmp_path / NAME
    target.write_bytes(b"version A")
    store = LocalFileStore(root=str(tmp_path))
    initial = catalog(store)
    report = value(frg.acquire(AcquireRequest(selected(initial)), store=store))
    baseline = SourceCheckpoint(SOURCE, PERIOD, report.payload.identity, report.entry)
    stamp = target.stat()
    target.write_bytes(b"version B")
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    refreshed = catalog(store)
    assert selected(refreshed).entry == selected(initial).entry
    plan = value(frg.plan_updates(UpdateRequest(refreshed, (baseline,), force_refresh=True)))
    decision = next(item for item in plan.decisions if item.source_id == SOURCE)
    assert decision.state == "metadata_unchanged"
    assert decision.acquisition_required
    revised = value(frg.acquire(AcquireRequest(decision.asset), store=store))
    comparison = value(frg.assess_material(AssessMaterialRequest(revised, baseline)))
    assert comparison.state == "revised"
    assert comparison.original_identity == ByteIdentity.of(b"version B")


def test_same_period_competing_files_are_ambiguous_before_acquisition(tmp_path):
    (tmp_path / NAME).write_bytes(b"canonical revision")
    (tmp_path / "FRG. Экспресс-мониторинг рынка. Выдачи. 2026.05.01.xlsx").write_bytes(b"supplier revision")
    result = catalog(LocalFileStore(root=str(tmp_path)))
    selection = next(item for item in result.selections if item.source_id == SOURCE)
    assert selection.state == "ambiguous"
    assert selection.asset is None and len(selection.candidates) == 2
    plan = value(frg.plan_updates(UpdateRequest(result, force_refresh=True)))
    decision = next(item for item in plan.decisions if item.source_id == SOURCE)
    assert decision.state == "ambiguous" and not decision.acquisition_required


def test_update_plan_rejects_a_selection_inconsistent_with_its_inventory(tmp_path):
    (tmp_path / NAME).write_bytes(ORIGINAL)
    result = catalog(LocalFileStore(root=str(tmp_path)))
    real = next(item for item in result.selections if item.source_id == SOURCE)
    forged = replace(real, source_id="frg.express.portfolios")
    tampered = Catalog(result.inventory, (forged,))
    planned = frg.plan_updates(UpdateRequest(tampered))
    assert planned.outcome == "failed" and planned.value is None
    assert not planned.effects


def test_capture_budgets_and_cancellation_propagate_without_effects():
    request = CaptureRequest(SOURCE, PERIOD, SourcePayload(ORIGINAL), "xlsx")
    rejected = frg.capture(request, context=ExecutionContext(budget=ExecutionBudget(input_bytes=1)))
    assert rejected.outcome == "failed"
    assert any(item.code == "budget.input_bytes" for item in rejected.diagnostics)
    assert not rejected.effects
    event = Event()
    event.set()
    cancelled = frg.capture(request, context=ExecutionContext(cancellation=event))
    assert cancelled.outcome == "cancelled" and cancelled.value is None
    assert not cancelled.effects


@pytest.mark.parametrize("operation", ["acquire", "capture", "prepare_file"])
def test_material_return_operations_enforce_output_byte_budget(operation, tmp_path):
    providers = {}
    if operation == "acquire":
        (tmp_path / NAME).write_bytes(ORIGINAL)
        store = LocalFileStore(root=str(tmp_path))
        request = AcquireRequest(selected(catalog(store)))
        providers["store"] = store
    elif operation == "capture":
        request = CaptureRequest(SOURCE, PERIOD, SourcePayload(ORIGINAL), "xlsx")
    else:
        request = PrepareFileRequest(value(captured()))
    result = getattr(frg, operation)(
        request, **providers,
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=0)),
    )
    assert result.outcome == "failed"
    assert any(item.code == "budget.output_bytes" for item in result.diagnostics)
    assert not result.effects


def test_directory_budget_stops_before_acquisition(tmp_path):
    (tmp_path / NAME).write_bytes(ORIGINAL)
    result = frg.discover(
        DiscoveryRequest("."), store=LocalFileStore(root=str(tmp_path)),
        context=ExecutionContext(budget=ExecutionBudget(objects=0)),
    )
    assert result.outcome == "failed"
    assert any(item.code == "budget.objects" for item in result.diagnostics)
    assert not result.effects


def test_recursive_discovery_rejects_symbolic_directory_cycles(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / NAME).write_bytes(ORIGINAL)
    try:
        (nested / "parent_link").symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable")
    result = frg.discover(
        DiscoveryRequest(".", recursive=True), store=LocalFileStore(root=str(tmp_path)),
    )
    assert result.outcome == "failed" and result.value is None
    assert not result.effects


def test_source_file_lifecycle_runs_without_table_decoding_packages(tmp_path, monkeypatch):
    for package in ("pandas", "openpyxl", "xlrd", "pyxlsb"):
        monkeypatch.setitem(sys.modules, package, None)
    (tmp_path / NAME).write_bytes(ORIGINAL)
    store = LocalFileStore(root=str(tmp_path))
    asset = selected(catalog(store))
    report = value(frg.acquire(AcquireRequest(asset), store=store))
    prepared = value(frg.prepare_file(PrepareFileRequest(report)))
    assert prepared.filename == NAME and prepared.payload.data == ORIGINAL
    assert value(captured()).payload.identity == prepared.payload.identity


def test_force_refresh_changes_plan_computation_for_the_same_file_evidence(tmp_path):
    (tmp_path / NAME).write_bytes(ORIGINAL)
    current = catalog(LocalFileStore(root=str(tmp_path)))
    asset = selected(current)
    baseline = SourceCheckpoint(SOURCE, PERIOD, ByteIdentity.of(ORIGINAL), asset.entry)
    normal = frg.plan_updates(UpdateRequest(current, (baseline,)))
    forced = frg.plan_updates(UpdateRequest(current, (baseline,), force_refresh=True))
    assert normal.outcome == forced.outcome == "succeeded"
    a = next(item for item in normal.value.decisions if item.source_id == SOURCE)
    b = next(item for item in forced.value.decisions if item.source_id == SOURCE)
    assert a.acquisition_required is False and b.acquisition_required is True
    assert normal.computation.computation_id != forced.computation.computation_id
