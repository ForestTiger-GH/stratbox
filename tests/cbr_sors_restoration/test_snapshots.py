"""Exact retained scientific values replay without the retired operation API."""
from dataclasses import fields, replace
import os
from pathlib import Path
import subprocess
import sys
from io import BytesIO
import pandas as pd
import pytest
from openpyxl import load_workbook
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig, SorsCrosswalkConfig
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.calculations.sors.inputs.dependencies import DEPENDENCIES, dependencies, dependency_manifest, original_input, source_uses
from stratbox.domains.cbr.calculations.sors.inputs.common import source_manifest_record
from stratbox.domains.cbr.calculations.sors.identity import seal_content as seal, validate_content
from stratbox.domains.cbr.calculations.sors.admission import validate_bundle_context
from stratbox.domains.cbr.calculations.sors.serialization import encode, decode
from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload
from test_crosswalk_operations import _strict_with_bundle
from test_identity_provenance import _classifier
from support import execute_model_methods


def source_inputs():
    return SorsSourceInputs(**{
        item.input_name: SourcePayload(f"synthetic publication {item.source_series}".encode(), source_id=item.source_series)
        for item in DEPENDENCIES if item.required
    })


def strict_context():
    """Small explicit synthetic region; complete declared publication evidence."""
    strict = _strict_with_bundle()
    sources = source_inputs()
    config = SorsRunConfig("2026-06-01")
    bundle = strict.source_bundle
    lineage = tuple(original_input(getattr(sources, item.input_name), item.source_series)
                    for item in DEPENDENCIES if item.required) + (_classifier(),)
    manifest = pd.DataFrame([
        {**source_manifest_record(item.source_series, getattr(sources, item.input_name),
                                 len(getattr(bundle, f"{item.input_name}_grid")),
                                 required=True, role=item.source_role),
         "series_id": item.series_id, "method_fingerprint": item.method_fingerprint, "as_of_date": config.as_of_date}
        for item in DEPENDENCIES if item.required
    ])
    bundle = seal(replace(bundle, as_of_date=config.as_of_date, publication_step=config.publication_step,
                          lineage=lineage, source_manifest_grid=manifest,
                          dependency_manifest_grid=dependency_manifest(sources, config.as_of_date, config.publication_step),
                          coverage=SnapshotCoverage("partial", "Synthetic bounded fixture: one region; retained sources are fixture identities.")))
    return seal(replace(strict, source_bundle=bundle, run_config=config, source_manifest_grid=manifest))


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
    from stratbox.domains.cbr.calculations.sors.inputs.validation import _validate_structure
    bundle = SimpleNamespace(source_manifest_grid=pd.DataFrame([{"source_series": "01_05_A", "rows": 14976}]),
        regional_totals_history_grid=pd.DataFrame(), atomic_regions_grid=pd.DataFrame(index=range(85)),
        geography_nodes_grid=pd.DataFrame(index=range(96)), okved2_classes_grid=pd.DataFrame(index=range(88)),
        source_grid=pd.DataFrame({"as_of_date": ["2026-06-01"] * 3, "portfolio_scope": ["CORPORATE_TOTAL", "SME", "SME_IE"]}))
    records = []
    _validate_structure(bundle, records)
    frame = pd.DataFrame(records)
    restored = decode(encode(frame))
    pd.testing.assert_frame_equal(frame, restored)
    assert restored.set_index("check_id").loc["structure:common_date", "actual"] == ("2026-06-01",)


def test_bundle_manifest_is_shared_exact_and_roundtrips_every_grid():
    assert dependencies() == DEPENDENCIES
    assert sum(item.required for item in DEPENDENCIES) == 10
    bundle = strict_context().source_bundle
    validate_bundle_context(bundle)
    restored = decode(encode(bundle))
    assert_grids_equal(bundle, restored)
    assert restored.lineage == bundle.lineage and restored.coverage == bundle.coverage
    assert restored.dependency_manifest_grid.iloc[-1]["status"] == "not_supplied"
    assert encode(restored) == encode(bundle)
    validate_bundle_context(restored)


def test_prepared_view_renders_in_a_process_without_solver_or_sources(tmp_path, small_result):
    from stratbox.domains.cbr.products.corporate_lending.sors.pack import build_sors_views
    from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsWorkbookRequest
    views = build_sors_views(small_result, SorsWorkbookRequest())
    request = tmp_path / "views.json"
    request.write_bytes(encode(views))
    script = r'''
import sys
from pathlib import Path
sys.modules['highspy'] = None
from stratbox.domains.cbr.calculations.sors.serialization import decode
from stratbox.domains.cbr.products.corporate_lending.sors.rendering import render_sors_views
views = decode(Path(sys.argv[1]).read_bytes())
Path(sys.argv[2]).write_bytes(render_sors_views(views).representation.data)
'''
    destination = tmp_path / 'views.xlsx'
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    run = subprocess.run([sys.executable, '-c', script, str(request), str(destination)],
                         env=env, text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    workbook = load_workbook(destination, read_only=True)
    assert tuple(workbook.sheetnames) == tuple(name for name, _ in views.tables)
    workbook.close()


def test_restoration_replays_real_crosswalk_pivot_and_render_in_new_process(tmp_path):
    pytest.importorskip('highspy')
    strict = strict_context()
    request = tmp_path / 'strict.json'
    request.write_bytes(encode(strict))
    script = r'''
import sys
from pathlib import Path
from stratbox.domains.cbr.calculations.sors.serialization import encode, decode
from stratbox.domains.cbr.calculations.sors.contracts import SorsCrosswalkConfig
from stratbox.domains.cbr.products.corporate_lending.sors.views import build_sors_pivot
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsPivotRequest, SorsWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.sors.pack import build_sors_views
from stratbox.domains.cbr.products.corporate_lending.sors.rendering import render_sors_views
from support import execute_model_methods
strict = decode(Path(sys.argv[1]).read_bytes())
crosswalk = execute_model_methods(strict, SorsCrosswalkConfig(mode='feasibility'), crosswalk=True)
assert crosswalk.status == 'OPTIMAL'
facts = crosswalk.crosswalk_facts_grid.set_index(['class_code', 'metric'])
assert facts.loc[('01','overdue_rub'),'value'] == 90
assert facts.loc[('02','overdue_rub'),'value'] == 10
replayed = decode(encode(crosswalk))
assert replayed.strict_result.source_bundle.lineage == strict.source_bundle.lineage
pivot = build_sors_pivot(replayed, SorsPivotRequest(class_code='02', metrics=('overdue_rub',)))
assert pivot.table.iloc[0]['overdue_rub'] == 10
views = build_sors_views(replayed, SorsWorkbookRequest())
Path(sys.argv[2]).write_bytes(render_sors_views(views).representation.data)
'''
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(Path(__file__).resolve().parents[2] / "src"), str(Path(__file__).parent)))}
    destination = tmp_path / 'replayed.xlsx'
    run = subprocess.run([sys.executable,'-c',script,str(request),str(destination)], env=env,
                         text=True,capture_output=True,timeout=90)
    assert run.returncode == 0, run.stderr
    workbook = load_workbook(destination,read_only=True)
    assert 'Crosswalk_Facts' in workbook.sheetnames
    assert workbook['Crosswalk_Facts'].max_row == 3
    workbook.close()


def test_model_input_context_rejects_missing_and_tampered_dependencies():
    bundle = strict_context().source_bundle
    with pytest.raises(ValueError, match='dependencies_incomplete'):
        validate_bundle_context(seal(replace(bundle, dependency_manifest_grid=pd.DataFrame())))
    manifest = bundle.dependency_manifest_grid.copy()
    manifest.loc[0,'original_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='dependency_identity_mismatch'):
        validate_bundle_context(seal(replace(bundle, dependency_manifest_grid=manifest)))


def test_nested_source_mutation_and_truncated_encoding_are_rejected():
    strict = strict_context()
    encoded = encode(strict)
    with pytest.raises(ValueError, match='structure_invalid'):
        decode(encoded[:-1])
    strict.source_bundle.regional_traditional_grid.loc[0,'published_lower'] = 1
    with pytest.raises(ValueError, match='content_identity_mismatch'):
        validate_content(strict.source_bundle)


@pytest.mark.parametrize('invalid_size', (True,28.5))
def test_original_byte_size_is_an_exact_integer(invalid_size):
    bundle = strict_context().source_bundle
    manifest = bundle.dependency_manifest_grid.copy()
    manifest.loc[0,'original_size'] = invalid_size
    with pytest.raises(ValueError, match='dependency_identity_mismatch'):
        validate_bundle_context(seal(replace(bundle,dependency_manifest_grid=manifest)))


def test_selected_sors_region_keeps_full_source_vector_through_products_and_replay():
    from stratbox.domains.cbr.products.corporate_lending.sors.views import build_sors_pivot
    from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsPivotRequest, SorsWorkbookRequest
    from stratbox.domains.cbr.products.corporate_lending.sors.pack import build_sors_views
    strict = strict_context()
    uses = source_uses(source_inputs())
    assert len(uses) == 10
    strict = seal(replace(strict,source_bundle=seal(replace(strict.source_bundle,source_uses=uses))))
    restored = decode(encode(strict))
    assert restored.source_bundle.source_uses == uses
    pivot = build_sors_pivot(restored,SorsPivotRequest(region_code='r1',metrics=('overdue_rub',)))
    assert pivot.source_uses == uses
    views = build_sors_views(restored,SorsWorkbookRequest())
    assert decode(encode(views)).source_uses == uses
