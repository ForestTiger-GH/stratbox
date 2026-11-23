"""A retained SORS result must actually support calculation after process exit."""
from dataclasses import fields, replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest
from openpyxl import load_workbook

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.limits import ExecutionBudget
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_value
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
import stratbox.domains.cbr.operations.corporate_lending.sors as sors
from stratbox.domains.cbr.operations.corporate_lending.sors.api import _seal_grids
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import dependencies
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import dependency_manifest
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import original_input
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.common import source_manifest_record
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.evidence import SourcePayload

from test_crosswalk_operations import _strict_with_bundle
from test_identity_provenance import _classifier


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def seal(value):
    def work(value, invocation):
        for receipt in getattr(value, "lineage", ()):
            invocation.use(receipt)
        return _seal_grids(invocation, value)
    return checked(run(OperationDefinition("test.sors.fixture", "synthetic-1", type(value), type(value)), value, work))


def source_inputs():
    return sors.SorsSourceInputs(**{
        item.input_name: SourcePayload(f"synthetic publication {item.source_series}".encode(), source_id=item.source_series)
        for item in DEPENDENCIES if item.required
    })


def strict_context():
    """Small explicit synthetic region; complete declared publication evidence."""
    strict = _strict_with_bundle()
    sources = source_inputs()
    config = sors.SorsRunConfig("2026-06-01", rules_version="test")
    bundle = strict.source_bundle
    lineage = tuple(original_input(getattr(sources, item.input_name), item.source_series)
                    for item in DEPENDENCIES if item.required) + (_classifier(),)
    manifest = pd.DataFrame([
        {**source_manifest_record(item.source_series, getattr(sources, item.input_name),
                                 len(getattr(bundle, f"{item.input_name}_grid")),
                                 required=True, role=item.source_role),
         "series_id": item.series_id, "method_version": item.method_version, "as_of_date": config.as_of_date}
        for item in DEPENDENCIES if item.required
    ])
    bundle = seal(replace(bundle, as_of_date=config.as_of_date, publication_step=config.publication_step,
                          lineage=lineage, source_manifest_grid=manifest,
                          dependency_manifest_grid=dependency_manifest(sources, config.as_of_date, config.publication_step),
                          coverage=SnapshotCoverage("partial", "Synthetic bounded fixture: one region; retained sources are fixture identities.")))
    return seal(replace(strict, source_bundle=bundle, run_config=config, source_manifest_grid=manifest))


def persist(value, tmp_path):
    store = FileDatasetStore(LocalFileStore(tmp_path), "datasets", provider_id="files", scope_id="sors")
    reference = checked(write_snapshot(WriteSnapshotRequest(value), store=store)).reference
    return store, reference


def small_complete_bundle():
    """One region/class and all ten publications constrain three portfolio scopes."""
    base = strict_context().source_bundle
    records = []
    grids = {}
    for item in DEPENDENCIES:
        if not item.required:
            continue
        scope = "SME_IE" if item.input_name.startswith("sme_ie_") else "SME" if item.input_name.startswith("sme_") else "CORPORATE_TOTAL"
        value = {"CORPORATE_TOTAL": 100.0, "SME": 50.0, "SME_IE": 20.0}[scope]
        activity = "01" if item.source_series in {"01_02_C", "01_11_F", "01_11_I"} else "A" if item.source_series in {"01_03_C", "01_12_A"} else "total"
        geo = "fd1" if item.source_series in {"01_03_C", "01_12_A"} else "r1" if "regional" in item.input_name else "country"
        row = {"observation_id": item.source_series + ":fixture", "source_series": item.source_series,
               "geography_node_id": geo, "activity_code": activity, "metric": "debt_rub", "portfolio_scope": scope,
               "value": value, "published_lower": value - .5, "published_upper": value + .5,
               "published_lower_attained": True, "published_upper_attained": False,
               "source_sheet": "synthetic", "source_row": 3, "source_column": 2, "as_of_date": "2026-06-01",
               "unit": "million_rubles", "source_role": item.source_role, "record_origin": "PUBLISHED"}
        records.append(row)
        grids[item.input_name + "_grid"] = pd.DataFrame([row])
    classes = base.okved2_classes_grid[base.okved2_classes_grid["class_code"].eq("01")].copy()
    categories = base.publication_categories_grid[base.publication_categories_grid["member_class_code"].eq("01")].copy()
    geography = pd.DataFrame([
        {"geography_node_id": name, "atomic_region_codes": ("r1",), "geography_kind": kind}
        for name, kind in (("country", "country_total"), ("fd1", "federal_district"), ("r1", "region"))
    ])
    manifest = base.source_manifest_grid.copy()
    manifest["rows"] = 1
    return seal(replace(base, **grids, source_grid=pd.DataFrame(records), source_manifest_grid=manifest,
                        geography_nodes_grid=geography, okved2_classes_grid=classes, publication_categories_grid=categories))


def assert_grids_equal(before, after):
    for field in fields(before):
        if field.name.endswith("_grid"):
            pd.testing.assert_frame_equal(getattr(before, field.name), getattr(after, field.name))
    assert after.evidence == before.evidence


def test_source_validation_grid_is_portable_with_dates_and_portfolio_sets():
    from types import SimpleNamespace
    from stratbox.core.formats.dataframes import frame_to_table, frame_from_table
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.validation import _validate_structure
    from stratbox.shared.data.processing import DataContract

    bundle = SimpleNamespace(
        source_manifest_grid=pd.DataFrame([{"source_series": "01_05_A", "rows": 14976}]),
        regional_totals_history_grid=pd.DataFrame(),
        atomic_regions_grid=pd.DataFrame(index=range(85)),
        geography_nodes_grid=pd.DataFrame(index=range(96)),
        okved2_classes_grid=pd.DataFrame(index=range(88)),
        source_grid=pd.DataFrame({"as_of_date": ["2026-06-01"] * 3,
                                  "portfolio_scope": ["CORPORATE_TOTAL", "SME", "SME_IE"]}),
    )
    records = []
    _validate_structure(bundle, records)
    frame = pd.DataFrame(records)
    encoded, descriptor = frame_to_table(frame, contract=DataContract("test.sors.validation", 1))
    restored = frame_from_table(encoded, descriptor)
    pd.testing.assert_frame_equal(frame, restored)
    assert restored.set_index("check_id").loc["structure:common_date", "actual"] == ("2026-06-01",)


def test_bundle_manifest_is_shared_exact_and_roundtrips_every_grid(tmp_path):
    declarations = dependencies()
    assert declarations == DEPENDENCIES
    assert sum(item.required for item in declarations) == 10
    assert [item.input_name for item in declarations if not item.required] == ["regional_totals_history"]
    strict = strict_context()
    bundle = strict.source_bundle
    snapshot = checked(sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(bundle)))
    store, reference = persist(snapshot, tmp_path)
    restored = checked(sors.read_bundle_snapshot(sors.ReadSorsSnapshotRequest(
        checked(read_snapshot(ReadSnapshotRequest(reference), store=store)))))
    assert_grids_equal(bundle, restored)
    assert restored.lineage == bundle.lineage
    assert restored.coverage == bundle.coverage
    assert restored.dependency_manifest_grid.iloc[-1]["status"] == "not_supplied"
    assert checked(sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(restored))).identity == snapshot.identity


def test_prepared_view_renders_in_a_process_without_model_execution(tmp_path, small_result):
    views = checked(sors.build_views(sors.BuildSorsViewsRequest(small_result)))
    encoded = checked(sors.build_view_snapshot(sors.SorsViewSnapshotRequest(views)))
    _, reference = persist(encoded, tmp_path)
    request = tmp_path / "views.json"
    request.write_text(json.dumps({"root": str(tmp_path), "reference": reference_value(reference)}))
    script = r'''
import json, sys
from pathlib import Path
sys.modules["highspy"] = None
sys.modules["stratbox.domains.cbr.analytics.corporate_lending.sors.operations"] = None
sys.modules["stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.loader"] = None
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_from
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations.corporate_lending import sors

def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value

info = json.loads(Path(sys.argv[1]).read_text())
store = FileDatasetStore(LocalFileStore(info["root"]), "datasets", provider_id="files", scope_id="sors")
encoded = checked(read_snapshot(ReadSnapshotRequest(reference_from(info["reference"])), store=store))
views = checked(sors.read_view_snapshot(sors.ReadSorsSnapshotRequest(encoded)))
result = checked(sors.render_views(sors.RenderSorsRequest(views)))
Path(info["root"], "views_only.xlsx").write_bytes(result.representation.data)
'''
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    completed = subprocess.run([sys.executable, "-c", script, str(request)], env=env, text=True, capture_output=True, timeout=30)
    assert completed.returncode == 0, completed.stderr + completed.stdout
    workbook = load_workbook(tmp_path / "views_only.xlsx", read_only=True)
    assert tuple(workbook.sheetnames) == tuple(name for name, _ in views.tables)
    workbook.close()


def test_restoration_replays_real_crosswalk_pivot_and_render_in_a_new_process(tmp_path):
    pytest.importorskip("highspy")
    strict = strict_context()
    snapshot = checked(sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(strict)))
    store, reference = persist(snapshot, tmp_path)
    replayed = checked(sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(
        checked(read_snapshot(ReadSnapshotRequest(reference), store=store)))))
    assert_grids_equal(strict, replayed)
    assert_grids_equal(strict.source_bundle, replayed.source_bundle)
    assert replayed.run_config == strict.run_config
    assert replayed.summary == strict.summary
    assert not hasattr(replayed, "_source_bundle")
    assert not hasattr(replayed, "_strict_problem")
    request_path = tmp_path / "request.json"
    bundle_snapshot = checked(sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(small_complete_bundle())))
    _, bundle_reference = persist(bundle_snapshot, tmp_path)
    request_path.write_text(json.dumps({"root": str(tmp_path), "reference": reference_value(reference),
                                        "bundle_reference": reference_value(bundle_reference)}))
    script = r'''
import json, sys
from pathlib import Path
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_from
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations.corporate_lending import sors

def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value

info = json.loads(Path(sys.argv[1]).read_text())
store = FileDatasetStore(LocalFileStore(info["root"]), "datasets", provider_id="files", scope_id="sors")
# A source bundle also supports the original strict solver after process exit.
bundle_snapshot = checked(read_snapshot(ReadSnapshotRequest(reference_from(info["bundle_reference"])), store=store))
bundle = checked(sors.read_bundle_snapshot(sors.ReadSorsSnapshotRequest(bundle_snapshot)))
calculated = checked(sors.restore(sors.RestoreSorsRequest(bundle, sors.SorsRunConfig(bundle.as_of_date))))
assert calculated.summary.strict_status == "OPTIMAL"
assert calculated.source_bundle.observation_bindings_grid.shape[0] == 10
debt = calculated.regional_okved2_grid.query("class_code == '01' and metric == 'debt_rub'").iloc[0]
assert debt["value"] == 100.0 and debt["is_primary_fact"]
calculated_snapshot = checked(sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(calculated)))
calculated_replay = checked(sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(calculated_snapshot)))
assert calculated_replay.summary == calculated.summary
snapshot = checked(read_snapshot(ReadSnapshotRequest(reference_from(info["reference"])), store=store))
strict = checked(sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(snapshot)))
assert strict.source_bundle.as_of_date == strict.run_config.as_of_date
crosswalk = checked(sors.run_crosswalk(sors.CrosswalkSorsRequest(strict, sors.SorsCrosswalkConfig(mode="feasibility"))))
assert crosswalk.status == "OPTIMAL", crosswalk.status
facts = crosswalk.crosswalk_facts_grid.set_index(["class_code", "metric"])
assert facts.loc[("01", "overdue_rub"), "value"] == 90.0
assert facts.loc[("02", "overdue_rub"), "value"] == 10.0
assert set(crosswalk.solver_runs_grid["solver_backend"]) == {"highspy"}
# Retain the downstream result too: its strict/source contexts remain complete.
encoded = checked(sors.build_crosswalk_snapshot(sors.SorsCrosswalkSnapshotRequest(crosswalk)))
reference = checked(write_snapshot(WriteSnapshotRequest(encoded), store=store)).reference
loaded = checked(read_snapshot(ReadSnapshotRequest(reference), store=store))
restored = checked(sors.read_crosswalk_snapshot(sors.ReadSorsSnapshotRequest(loaded)))
assert restored.crosswalk_config == crosswalk.crosswalk_config
assert restored.strict_result.run_config == strict.run_config
assert restored.evidence == crosswalk.evidence
assert any("crosswalk" in (receipt.source_id or "") for receipt in restored.evidence.inputs)
pivot = checked(sors.build_pivot(sors.PivotSorsRequest(restored, sors.SorsPivotRequest(region_code="r1", metrics=("overdue_rub",)))))
assert pivot.table.set_index("class_code").loc["02", "overdue_rub"] == 10.0
views = checked(sors.build_views(sors.BuildSorsViewsRequest(restored)))
encoded_views = checked(sors.build_view_snapshot(sors.SorsViewSnapshotRequest(views)))
views_ref = checked(write_snapshot(WriteSnapshotRequest(encoded_views), store=store)).reference
replayed_views = checked(sors.read_view_snapshot(sors.ReadSorsSnapshotRequest(
    checked(read_snapshot(ReadSnapshotRequest(views_ref), store=store)))))
assert replayed_views.evidence == views.evidence
workbook = checked(sors.render_views(sors.RenderSorsRequest(replayed_views)))
Path(info["root"], "replayed_sors.xlsx").write_bytes(workbook.representation.data)
'''
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    completed = subprocess.run([sys.executable, "-c", script, str(request_path)], env=env, text=True, capture_output=True, timeout=90)
    assert completed.returncode == 0, completed.stderr + completed.stdout
    workbook = load_workbook(tmp_path / "replayed_sors.xlsx", read_only=True, data_only=True)
    assert "Regional_OKVED2" in workbook.sheetnames
    assert "Crosswalk_Facts" in workbook.sheetnames
    assert workbook["Crosswalk_Facts"].max_row == 3
    workbook.close()


def test_result_without_declared_inputs_or_configuration_is_not_replayable():
    strict = strict_context()
    for incomplete in (replace(strict, source_bundle=None), replace(strict, run_config=None)):
        response = sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(incomplete))
        assert response.outcome == "failed"
    missing = seal(replace(strict.source_bundle, dependency_manifest_grid=pd.DataFrame()))
    response = sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(missing))
    assert response.outcome == "failed"
    assert response.diagnostics[0].code == "sors.snapshot_dependencies_incomplete"
    wrong = strict.source_bundle.dependency_manifest_grid.copy()
    wrong.loc[0, "original_sha256"] = "0" * 64
    tampered = seal(replace(strict.source_bundle, dependency_manifest_grid=wrong))
    response = sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(tampered))
    assert response.outcome == "failed"
    assert response.diagnostics[0].code == "sors.snapshot_dependency_identity_mismatch"


def test_selected_components_and_nested_mutation_are_rejected():
    strict = strict_context()
    snapshot = checked(sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(strict)))
    partial = DatasetSnapshot(snapshot.manifest, snapshot.tables[:-1])
    response = sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(partial))
    assert response.outcome == "failed"
    assert response.diagnostics[0].code == "sors.snapshot_incomplete"
    strict.source_bundle.regional_traditional_grid.loc[0, "published_lower"] = 1.0
    response = sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(strict))
    assert response.outcome == "failed"
    assert response.diagnostics[0].code == "input.identity_mismatch"


@pytest.mark.parametrize("invalid_size", (True, 28.5))
def test_original_byte_size_is_an_exact_integer(invalid_size):
    bundle = strict_context().source_bundle
    manifest = bundle.dependency_manifest_grid.copy()
    manifest.loc[0, "original_size"] = invalid_size
    value = seal(replace(bundle, dependency_manifest_grid=manifest))
    response = sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(value))
    assert response.outcome == "failed"
    assert response.diagnostics[0].code == "sors.snapshot_dependency_identity_mismatch"


def test_snapshot_resources_are_charged_for_encodings_and_reads():
    bundle = strict_context().source_bundle
    encoded = sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(bundle),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=0)))
    assert encoded.outcome == "failed"
    assert encoded.diagnostics[0].code == "budget.output_bytes"
    snapshot = checked(sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(bundle)))
    for resource in ("input_bytes", "cells"):
        decoded = sors.read_bundle_snapshot(sors.ReadSorsSnapshotRequest(snapshot),
            context=ExecutionContext(budget=ExecutionBudget(**{resource: 0})))
        assert decoded.outcome == "failed"
        assert decoded.diagnostics[0].code == "budget." + resource


def test_crosswalk_retains_mapping_inputs_and_all_diagnostic_tables(tmp_path):
    pytest.importorskip("highspy")
    crosswalk = checked(sors.run_crosswalk(sors.CrosswalkSorsRequest(strict_context(), sors.SorsCrosswalkConfig(mode="feasibility"))))
    snapshot = checked(sors.build_crosswalk_snapshot(sors.SorsCrosswalkSnapshotRequest(crosswalk)))
    store, reference = persist(snapshot, tmp_path)
    restored = checked(sors.read_crosswalk_snapshot(sors.ReadSorsSnapshotRequest(
        checked(read_snapshot(ReadSnapshotRequest(reference), store=store)))))
    assert_grids_equal(crosswalk, restored)
    assert_grids_equal(crosswalk.strict_result, restored.strict_result)
    assert restored.strict_result.source_bundle.lineage == crosswalk.strict_result.source_bundle.lineage
    assert restored.crosswalk_config == crosswalk.crosswalk_config
    before = checked(sors.build_pivot(sors.PivotSorsRequest(crosswalk, sors.SorsPivotRequest(class_code="02", metrics=("overdue_rub",)))))
    after = checked(sors.build_pivot(sors.PivotSorsRequest(restored, sors.SorsPivotRequest(class_code="02", metrics=("overdue_rub",)))))
    pd.testing.assert_frame_equal(before.table, after.table)


def test_selected_sors_region_keeps_full_source_vector_through_products_and_replay():
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import source_uses
    strict = strict_context()
    uses = source_uses(source_inputs())
    assert len(uses) == 10
    bundle = seal(replace(strict.source_bundle, source_uses=uses))
    strict = seal(replace(strict, source_bundle=bundle))
    encoded = checked(sors.build_restoration_snapshot(sors.SorsRestorationSnapshotRequest(strict)))
    restored = checked(sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(encoded)))
    assert restored.source_bundle.source_uses == uses
    pivot = checked(sors.build_pivot(sors.PivotSorsRequest(restored,
        sors.SorsPivotRequest(region_code="r1", metrics=("overdue_rub",)))))
    assert pivot.source_uses == uses
    views = checked(sors.build_views(sors.BuildSorsViewsRequest(restored)))
    assert views.source_uses == uses
    saved = checked(sors.build_view_snapshot(sors.SorsViewSnapshotRequest(views)))
    replayed = checked(sors.read_view_snapshot(sors.ReadSorsSnapshotRequest(saved)))
    assert replayed.source_uses == uses


def test_explicit_source_binding_extension_replays_sors_with_the_canonical_dependency_vector(monkeypatch):
    """SORS stays a multi-source catalog operation; an extension owns its binding."""
    from stratbox.operations import operation_catalog
    from stratbox.domains.registry.catalog import SourceCatalog, SourceOperation
    from stratbox.core.execution import prepare_input, project_output
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import source_uses
    catalog = operation_catalog()
    sources = catalog.source_catalog()
    primary = sources.source("cbr.corporate_lending.debt_0105a")
    operations = ("cbr.sors.restoration_snapshot", "cbr.sors.read_restoration_snapshot",
        "cbr.sors.build_views", "cbr.sors.view_snapshot", "cbr.sors.read_view_snapshot")
    extended = replace(primary, operations=(*primary.operations,
        *(SourceOperation(operation_id) for operation_id in operations)))
    extension_catalog = SourceCatalog(tuple(extended if source.series_id == primary.series_id else source
        for source in sources.sources), catalog)
    monkeypatch.setattr(type(catalog), "source_catalog", lambda self: extension_catalog)
    bound = catalog.bind_source(primary.series_id, format="xlsx")
    strict = strict_context()
    uses = source_uses(source_inputs())
    strict = seal(replace(strict, source_bundle=seal(replace(strict.source_bundle, source_uses=uses))))
    supplied = None
    for operation_id in operations:
        definition = catalog.get(operation_id)
        port = definition.processing.inputs[0]
        incoming = supplied if supplied is not None else prepare_input(strict, port.contract)
        result = bound.bind(operation_id, inputs={port.name: incoming}).invoke()
        assert result.outcome == "succeeded", (operation_id, result.diagnostics)
        supplied = project_output(result, definition.processing.outputs[0].name)
    assert result.value.source_uses == uses
