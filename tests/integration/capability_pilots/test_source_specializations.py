"""Controlled source relationships and a materially different budget layout.

CBR index relationships come from supplied source profiles. Workbook content
is synthetic; these tests establish orchestration rather than live coverage.
The budget test retains the registered period-column/YTD interpretation.
"""
from collections import Counter
from datetime import date
from decimal import Decimal
import re

from stratbox.capabilities.catalog import CatalogContribution, ProfileDefinition
from stratbox.capabilities.model import CascadeDefinition, ScenarioDefinition, GraphBody, Call, OutputRef
from stratbox.capabilities.commands import MATERIAL, OBSERVATIONS
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from .conftest import workbook, row_profile, FixtureHttp


SERIES = (
    ("debt_0105a", "01_05_A_Debt_corp_20261001.xlsx"),
    ("issuance_0104a", "01_04_A_New_loans_corp_20261001.xlsx"),
    ("fd_okved2", "01_03_C_Loans_corp_by_fd_activity_20261001.xlsx"),
    ("sme_fd_okved2", "01_12_A_Loans_sme_by_fd_activity_20261001.xlsx"),
)


def test_cbr_four_series_share_one_index_and_keep_separate_originals(profiled_catalog):
    from stratbox.domains.cbr.publications.profiles import acquisition_profile
    routes = [acquisition_profile("cbr.route." + series) for series, _ in SERIES]
    index = routes[0].default_url
    assert {route.default_url for route in routes} == {index}
    root = "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/"
    content, definitions, profiles = {}, [], []
    content[index] = ("<html>" + "".join(f'<a href="{root}{name}">{name}</a>' for _, name in SERIES) + "</html>").encode()
    for number, ((series, filename), route) in enumerate(zip(SERIES, routes)):
        # Authored profile strings retain JSON escaping in their source; the
        # fixture normalizes that carrier once before compiling an exact regex.
        pattern = route.filename_pattern.replace("\\\\", "\\")
        assert re.fullmatch(pattern, filename)
        identity = "cbr.corporate_lending." + series
        payload = workbook({"Debt": (("Region", "Value"), ("Region-A", number + 10))})
        content[root + filename] = payload
        profiles.append(ProfileDefinition("fixture." + series, row_profile(dataset=identity), method_id="extract.rows"))
        definitions.append(ScenarioDefinition("fixture." + series, GraphBody((
            Call("index", "acquire.material", {"url": index}),
            Call("links", "discover.links", {"material": OutputRef("index", "material")}, {"base_url": index}),
            Call("select", "select.link", {"links": OutputRef("links", "links")}, {"pattern": pattern}),
            Call("original", "acquire.material", {"url": OutputRef("select", "url")}, {"source_id": identity}),
            Call("extract", "extract.observations", {"material": OutputRef("original", "material")}, profile_id="fixture." + series),
        ), {"observations": OutputRef("extract", "observations")}), outputs={"observations": OBSERVATIONS},
            effects=frozenset({"network.receive"})))
    cascade = CascadeDefinition("fixture.cbr_package", GraphBody(tuple(
        Call(series, "fixture." + series) for series, _ in SERIES),
        {series: OutputRef(series, "observations") for series, _ in SERIES}),
        outputs={series: OBSERVATIONS for series, _ in SERIES}, effects=frozenset({"network.receive"}))
    catalog = profiled_catalog.overlay(CatalogContribution(definitions=(*definitions, cascade), profiles=tuple(profiles)))
    provider = FixtureHttp(content)
    with StrategyBox(capabilities=catalog, providers={"http": provider},
                     settings=ExecutionSettings(max_workers=1, per_origin=1)) as box:
        handle = box.submit(box.prepare(cascade.capability_id))
        result = handle.result(20)
        assert result.outcome == "succeeded", [(key, value.outcome, value.diagnostics) for key, value in result.results.items()]
        assert provider.calls[index] == 1
        assert sum(provider.calls.values()) == 5
        assert box.session.ledger.snapshot().spent["requests"] == 5
        assert {result.output(series).dataset_id for series, _ in SERIES} == {
            "cbr.corporate_lending." + series for series, _ in SERIES}
        assert {result.output(series).observations[0].value for series, _ in SERIES} == {10, 11, 12, 13}
        assert len({result.output(series).lineage[0].identity for series, _ in SERIES}) == 4
        assert handle.snapshot().physical_work_count < handle.snapshot().logical_use_count
        # Replay supplied originals uses the same exact operation and profiles.
        for series, filename in SERIES:
            replay = box.invoke("extract.observations", inputs={"material": content[root + filename]},
                profile_id="fixture." + series, timeout=10)
            local, acquired = replay.output("observations"), result.output(series)
            assert (local.dataset_id, local.schema_version, local.release_id, local.observations, local.lineage) == (
                acquired.dataset_id, acquired.schema_version, acquired.release_id, acquired.observations, acquired.lineage)
            assert local.source_uses[0].qualification == "declared"
            assert acquired.source_uses[0].qualification == "observed"
            assert local.source_uses[0].coordinate.material_identity == acquired.source_uses[0].coordinate.material_identity
            expected_profile = catalog.profile("fixture." + series).fingerprint
            assert local.source_uses[0].coordinate.semantic_profile_edition == expected_profile
            assert acquired.source_uses[0].coordinate.semantic_profile_edition == expected_profile
            assert local.evidence.profile_fingerprints == acquired.evidence.profile_fingerprints == (expected_profile,)


def test_minfin_budget_period_columns_same_operation_and_compiler(profiled_catalog):
    material = workbook({"Budget": (("Code", "Indicator", "2026-01", "2026-02"),
        ("1", "Revenue", 100, 230), ("2", "Expenditure", 120, 250))})
    url = "https://fixture.example/budget.xlsx"
    provider = FixtureHttp({url: material})
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider}) as box:
        local = box.invoke("extract.observations", inputs={"material": material}, profile_id="fixture.budget",
            group_id="minfin.budget.columns", timeout=10)
        assert local.outcome == "succeeded", [(key, value.diagnostics) for key, value in local.results.items()]
        value = local.output("observations")
        assert value.dataset_id == "minfin.fedbud.annex3.monthly"
        assert len(value.observations) == 4
        first, second = value.observations[:2]
        assert first.value == Decimal(100) and second.value == Decimal(230)
        assert first.metric.unit == "RUB" and first.metric.scale == Decimal("1000000000")
        assert first.period.start == second.period.start == date(2026, 1, 1)
        assert first.period.end == date(2026, 1, 31) and second.period.end == date(2026, 2, 28)
        # The February cumulative value stays 230; it is not changed to a flow
        # by subtracting January inside extraction.
        definition = ScenarioDefinition("fixture.minfin_acquire", GraphBody((
            Call("original", "acquire.material", {"url": url}),
            Call("extract", "extract.observations", {"material": OutputRef("original", "material")},
                profile_id="fixture.budget", group_id="minfin.budget.columns"),
        ), {"observations": OutputRef("extract", "observations")}), outputs={"observations": OBSERVATIONS},
            effects=frozenset({"network.receive"}))
        plan = box.prepare(definition)
        bound = plan.selected_bindings["fixture.minfin_acquire/extract"]
        assert bound["method_id"] == "extract.minfin_budget"
        assert any(task.operation_id == "minfin.fields.interpret_budget" for task in plan.tasks)
        acquired = box.run(plan, timeout=10)
        assert acquired.outcome == "succeeded"
        assert acquired.output("observations") == value
        assert provider.calls[url] == 1


def test_three_source_uses_share_transfer_and_keep_logical_source_ids(profiled_catalog, two_tables):
    url = "https://fixture.example/shared.xlsx"
    provider = FixtureHttp({url: two_tables})
    definition = ScenarioDefinition("fixture.three_sources", GraphBody(tuple(
        Call(name, "acquire.material", {"url": url}, {"source_id": "source." + name})
        for name in ("alpha", "beta", "gamma")),
        {name: OutputRef(name, "material") for name in ("alpha", "beta", "gamma")}),
        outputs={name: MATERIAL for name in ("alpha", "beta", "gamma")}, effects=frozenset({"network.receive"}))
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider},
                     settings=ExecutionSettings(max_workers=1)) as box:
        result = box.run(box.prepare(definition), timeout=15)
        assert result.outcome == "succeeded"
        assert provider.calls[url] == 1
        assert {result.output(name).source_id for name in ("alpha", "beta", "gamma")} == {
            "source.alpha", "source.beta", "source.gamma"}
        assert {result.output(name).identity for name in ("alpha", "beta", "gamma")} == {two_tables.identity}
        assert all(result.output(name).data == two_tables.data for name in ("alpha", "beta", "gamma"))
        assert box.session.ledger.snapshot().spent["requests"] == 1
        assert box.session.ledger.snapshot().spent["wire_bytes"] == len(two_tables.data)
