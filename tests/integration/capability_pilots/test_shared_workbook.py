"""P11 shared decode across exact operations and independent semantic scopes."""
from decimal import Decimal

from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, PortContract
from stratbox.capabilities.commands import MATERIAL_INPUT, OBSERVATIONS, REPRESENTATION
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from .conftest import row_profile, FixtureHttp, workbook


def three_uses():
    return ScenarioDefinition("fixture.three_uses", GraphBody((
        Call("debt", "extract.observations", {"material": InputRef("material")}, profile_id="fixture.debt"),
        Call("total", "extract.observations", {"material": InputRef("material")}, profile_id="fixture.total"),
        Call("readable", "convert.readable", {"material": InputRef("material")}),
        Call("ratio", "calculate.ratio", {"numerator": OutputRef("debt", "observations"),
            "denominator": OutputRef("total", "observations")}),
    ), {"ratio": OutputRef("ratio", "observations"), "readable": OutputRef("readable", "readable")}),
        inputs={"material": MATERIAL_INPUT}, outputs={"ratio": OBSERVATIONS, "readable": REPRESENTATION})


def test_three_uses_one_decode_different_operation_ids(profiled_catalog, two_tables, monkeypatch):
    import stratbox.core.capabilities.workbooks as codec
    original, calls = codec.read_workbook_cells, []
    def decode(*args, **options):
        calls.append(1)
        return original(*args, **options)
    monkeypatch.setattr(codec, "read_workbook_cells", decode)
    with StrategyBox(capabilities=profiled_catalog, settings=ExecutionSettings(max_workers=1)) as box:
        plan = box.prepare(three_uses(), inputs={"material": two_tables})
        handle = box.submit(plan)
        result = handle.result(15)
        assert result.outcome == "succeeded", result.diagnostics
        assert calls == [1]
        assert [row.value for row in result.output("ratio").observations] == [Decimal("0.1"), Decimal("0.05")]
        assert result.output("readable").data.count(b'"kind":"sheet"') == 2
        assert all(state == "succeeded" for state in result.scopes.values()), result.scopes
        facts = handle.snapshot()
        assert facts.physical_work_count < facts.logical_use_count
        decode_uses = [use for use, binding in plan.selected_bindings.items() if binding["capability_id"] == "workbook.decode"]
        assert len(decode_uses) == 3
        assert {binding["capability_id"] for binding in plan.selected_bindings.values()} >= {"extract.observations", "convert.readable"}


def test_cascade_required_save_and_parallel_preview(profiled_catalog, two_tables, tmp_path):
    store = LocalFileStore(str(tmp_path))
    with StrategyBox(capabilities=profiled_catalog, providers={"output_filestore": store},
                     settings=ExecutionSettings(max_workers=1, active_runs=2)) as box:
        plan = box.prepare("cascade.observation_package", inputs={"material": two_tables}, parameters={
            "numerator_profile": row_profile(), "denominator_profile": row_profile("Total", "fixture.total"),
            "destination": "ratio.csv"}, outputs=("ratio", "readable"))
        assert any(task.operation_id == "store.commit" for task in plan.tasks)
        package = box.submit(plan)
        preview = box.submit(box.prepare("convert.readable", inputs={"material": two_tables}))
        result, other = package.result(15), preview.result(15)
        assert result.outcome == other.outcome == "succeeded"
        assert result.scopes["cascade.observation_package/source"] == "succeeded"
        assert result.scopes["cascade.observation_package/ratio"] == "succeeded"
        assert {scope.kind for scope in plan.scopes} == {"command", "operation", "scenario", "cascade"}
        assert (tmp_path / "ratio.csv").read_bytes().startswith(b"subject_namespace,")
        assert [o.value for o in result.output("ratio").batch.observations] == [Decimal("0.1"), Decimal("0.05")]
        receipt = [effect for value in result.results.values() for effect in value.effects if effect.kind == "storage.write"]
        assert len(receipt) == 1 and receipt[0].state == "confirmed"
        assert result.scope_outputs["cascade.observation_package/ratio/save"]["receipt"].effect_id == receipt[0].effect_id
        assert result.output("readable").identity == other.output("readable").identity


def test_supplied_material_and_acquisition_have_same_extraction_contract(profiled_catalog, two_tables):
    provider = FixtureHttp({"https://fixture.example/book.xlsx": two_tables})
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider}) as box:
        acquired = box.invoke("acquire.material", inputs={"url": "https://fixture.example/book.xlsx"}, timeout=10)
        assert acquired.outcome == "succeeded"
        online = box.invoke("extract.observations", inputs={"material": acquired.output("material")}, profile_id="fixture.debt", timeout=10)
        offline = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.debt", timeout=10)
        assert online.outcome == offline.outcome == "succeeded"
        assert online.output("observations") == offline.output("observations")
        assert provider.calls["https://fixture.example/book.xlsx"] == 1


def test_missing_member_rejects_extract_without_invalidating_readable(profiled_catalog, two_tables):
    from stratbox.capabilities.catalog import CatalogContribution, ProfileDefinition
    broken = profiled_catalog.overlay(CatalogContribution(profiles=(
        ProfileDefinition("fixture.missing", row_profile("Absent"), method_id="extract.rows"),)))
    with StrategyBox(capabilities=broken) as box:
        failed = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.missing", timeout=10)
        assert failed.outcome == "failed"
        assert any(d.code == "table.member_missing" for value in failed.results.values() for d in value.diagnostics)
        assert "observations" not in failed.outputs
        readable = box.invoke("convert.readable", inputs={"material": two_tables}, timeout=10)
        assert readable.outcome == "succeeded"


def test_interpretation_preserves_zero_dash_withheld_and_missing(profiled_catalog):
    material = workbook({"Debt": (("Region", "Value"), ("Zero", 0), ("Dash", "—"),
        ("Withheld", "C"), ("Missing", None))})
    profile = row_profile(status_tokens={"C": "withheld"})
    with StrategyBox(capabilities=profiled_catalog) as box:
        result = box.invoke("extract.observations", inputs={"material": material}, parameters={"profile": profile}, timeout=10)
        assert result.outcome == "succeeded"
        rows = result.output("observations").observations
        assert [row.value_status for row in rows] == ["reported", "dash", "withheld", "missing"]
        assert [row.value for row in rows] == [0, None, None, None]
        assert rows[1].raw_token == "—" and rows[2].raw_token == "C"


def test_unsupported_workbook_is_qualified_failure(profiled_catalog):
    with StrategyBox(capabilities=profiled_catalog) as box:
        result = box.invoke("convert.readable", inputs={"material": b"unsupported workbook bytes"}, timeout=10)
        assert result.outcome == "failed"
        codes = [diagnostic.code for item in result.results.values() for diagnostic in item.diagnostics]
        assert any(code.startswith(("workbook.", "archive.")) for code in codes)
        assert "internal.error" not in codes
