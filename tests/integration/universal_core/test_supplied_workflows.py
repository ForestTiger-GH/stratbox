"""Source recipes prepare typed originals and preserve scientific boundaries."""
from datetime import date

import pytest

from stratbox.capabilities.catalog import CatalogError, ProcessingGroup
from stratbox.composition.source import source_workflow
from stratbox.composition.requests import InvocationRequest
from stratbox.core.execution.session import ExecutionSettings
from stratbox.domains.cbr.operations.collection.material_definitions import CollectMaterial
from stratbox.domains.fns.publications.contracts import ReleaseContext
from stratbox.domains.registry import source_catalog
from stratbox.operations import operation_catalog
from stratbox.sdk import StrategyBox
from stratbox.sdk.bootstrap import default_snapshot
from stratbox.shared.evidence import SourcePayload

from source_fixtures import encoded, fixture


@pytest.fixture(scope="module")
def catalog():
    return default_snapshot()


def _explicit_source_inputs(card, representation, target):
    """Planning fixtures supply publication evidence; parsers are never invoked.

    These contexts establish compilation/admission coverage. They do not certify
    publisher layouts or assign scientific meaning to the placeholder bytes.
    """
    day = date(2026, 1, 1)
    payload = SourcePayload(b"planning-only original evidence", source_id=card.series_id)
    inputs = {}
    for name in target.inputs:
        if name in {"source", "payload", "material"}:
            inputs[name] = payload
        elif name == "original":
            from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
            from stratbox.shared.source_publications import SourceAssetIdentity
            inputs[name] = IdentifiedOriginal(SourceAssetIdentity(card.series_id, day.isoformat(), "main"),
                payload, representation, identification="explicit_planning_fixture")
        elif name == "report":
            from stratbox.domains.frank_rg.publications.contracts import AcquiredReport, ReportPeriod
            inputs[name] = AcquiredReport(card.series_id, ReportPeriod(day), representation, payload, "supplied")
        elif name == "release":
            inputs[name] = ReleaseContext(card.series_id, day.isoformat(), day)
        else:
            pytest.fail(f"A source extraction recipe must start from original evidence, not {target.id}.{name}")
    parameters = {}
    for name in target.required_parameters:
        if name == "family_id":
            # The selected source recipe declares this binding itself.
            continue
        if name == "format":
            parameters[name] = representation
        elif name in {"captured_on", "as_of"}:
            parameters[name] = day
        elif name == "source_name":
            if target.id.startswith("cbr.industries.0105a"):
                parameters[name] = "01_05_A_Debt_corp_20260101.xlsx"
            elif target.id.startswith("cbr.industries.0104a"):
                parameters[name] = "01_04_A_New_loans_corp_20260101.xlsx"
            else:
                parameters[name] = "escrow_20260101.xlsx"
        elif name == "key":
            from stratbox.domains.cbr.tables.reporting_forms.contracts import FormKey
            parameters[name] = FormKey(card.series_id.rsplit(".f", 1)[1], day)
        elif name == "publication":
            from stratbox.domains.minfin.publications.context import PublicationContext
            parameters[name] = PublicationContext(card.series_id, day.isoformat(), "main", published_on=day)
        elif name == "issue_id":
            parameters[name] = day.isoformat()
        elif name == "asset_id":
            parameters[name] = "main"
        elif name == "series_id":
            # This exact source identity is pinned by the recipe.
            continue
        elif name == "member":
            parameters[name] = "reviewed-member.xlsx"
        elif name == "profile":
            from stratbox.domains.rosstat.tables.contracts import CellBinding, ReviewedTableProfile
            binding = CellBinding("planning:A1", "planning.metric", "Planning fixture", "count", "count",
                "stock", "annual", day, day, "rosstat.publisher", "RF", period_kind="as_of",
                sheet="Reviewed" if representation in {"zip", "rar", "xlsx"} else "",
                block_id="reviewed" if representation == "pdf" else "", row=1, column=1)
            parameters[name] = ReviewedTableProfile("planning.only", 1, card.series_id, payload.identity,
                "Controlled planning fixture; no publisher layout certification.", (binding,), "One explicitly declared planning cell.")
        elif name == "layout":
            from stratbox.domains.rosstat.tables.documents import ReviewedDocumentLayout, DocumentTableRegion
            parameters[name] = ReviewedDocumentLayout("planning.only", 1, payload.identity,
                "Controlled planning fixture; no publisher table geometry certification.",
                (DocumentTableRegion(0, "reviewed", 1, 1, 1, separator="|"),))
        else:
            pytest.fail(f"Source preparation requires an explicit fixture for {target.id}.{name}")
    return inputs, parameters


def test_every_registered_source_has_a_typed_group_and_original_to_extract_goal(catalog):
    admitted = set()
    physical_only = []
    with StrategyBox(capabilities=catalog) as box:
        for card in source_catalog().sources:
            source_formats = []
            for representation in card.formats:
                selection = {"source_id": card.series_id, "representation": representation}
                groups = tuple(group for group in catalog.groups if card.series_id in group.source_ids and group.applies(selection))
                assert groups and all(isinstance(group, ProcessingGroup) for group in groups), (card.series_id, representation)
                try:
                    recipe = catalog.resolve_goal("source.extract", selection=selection)
                except CatalogError as error:
                    assert error.code == "catalog.recipe_unavailable"
                    # Preserving a declared format is separate from claiming an
                    # unavailable extraction route for that representation.
                    original = source_workflow(card.series_id, format=representation, output="original",
                        inputs={"material": SourcePayload(b"opaque publisher bytes")}, catalog=catalog)
                    original_plan = box.prepare(original)
                    assert set(original_plan.outputs) == {"original"}
                    assert all("extract" not in (task.operation_id or "") for task in original_plan.tasks)
                    physical_only.append((card.series_id, representation))
                    continue
                target = catalog.definition(recipe.capability_id)
                inputs, parameters = _explicit_source_inputs(card, representation, target)
                request = source_workflow(card.series_id, format=representation, output="extract",
                    inputs=inputs, parameters=parameters, catalog=catalog)
                assert isinstance(request, InvocationRequest)
                assert request.capability_id == recipe.capability_id and request.recipe_id == recipe.recipe_id
                plan = box.prepare(request)
                assert set(plan.outputs) == set(target.outputs)
                # Extraction goals never render an unrequested product.
                assert not any("render" in (task.operation_id or "") for task in plan.tasks)
                assert plan.tasks
                source_formats.append(representation)
            assert source_formats, card.series_id
            admitted.add(card.series_id)
    assert len(admitted) == 90
    assert physical_only == [("cbr.project_finance.escrow", "html")]
    # Historical DOC extraction is a real conversion route, distinct from a
    # successful original-preservation-only request.
    doc = catalog.resolve_goal("source.extract", selection={"source_id": "minfin.nwf.veb_deposits", "representation": "doc"})
    assert doc.capability_id == "minfin.legacy_document"


def test_all_composite_declarations_have_a_canonical_callable_disposition(catalog):
    from stratbox.capabilities.operations.stages import dispositions
    neutral = dispositions()
    composites = tuple(definition for definition in operation_catalog().definitions
        if definition.processing and definition.processing.composition)
    assert len(composites) == 33
    for prior in composites:
        for identifier in neutral.get(prior.operation_id, (prior.operation_id,)):
            definition = catalog.definition(identifier)
            assert definition.kind in {"operation", "scenario", "cascade"}
            bodies = (definition.body,) if definition.body is not None else tuple(
                method.body for method in catalog.methods if method.operation_id == definition.id)
            assert bodies
            allowed = {"operation": {"command"}, "scenario": {"operation", "scenario"}, "cascade": {"scenario"}}[definition.kind]
            for body in bodies:
                for step in body.steps:
                    if hasattr(step, "capability_id"):
                        assert catalog.definition(step.capability_id).kind in allowed
            assert definition.outputs


def test_fns_source_recipe_matches_the_economic_product_with_one_worker(catalog):
    from stratbox.domains.fns.tables.sme.extraction import extract_json
    from stratbox.domains.fns.tables.sme.projection import project_counts
    from stratbox.domains.fns.integration.sme.alignment import align
    from stratbox.domains.fns.products.views import prepare_view
    from stratbox.domains.fns.products.rendering import render
    day = date(2026, 11, 10)
    payload = SourcePayload(encoded(fixture(day)), "application/json")
    release = ReleaseContext("fns.sme", day.isoformat(), day)
    expected_dataset = align(project_counts(extract_json(payload, release)))
    expected_representation = render(prepare_view(expected_dataset))
    request = source_workflow("fns.sme", format="json", output="product",
        inputs={"payload": payload, "release": release}, catalog=catalog)
    with StrategyBox(capabilities=catalog, settings=ExecutionSettings(max_workers=1)) as box:
        plan = box.prepare(request)
        actual = box.run(plan, timeout=30)
    assert actual.outcome == "succeeded", [(item.operation_id, item.state, item.reason) for item in actual.tasks]
    assert actual.output("representation").data == expected_representation.data
    assert actual.output("dataset").batch.observations == expected_dataset.batch.observations
    assert {task.operation_id for task in plan.tasks if task.operation_id} == {
        "material.read", "fns.sme.command.extract", "fns.sme.command.project", "fns.sme.command.align",
        "fns.sme.command.view", "fns.sme.command.render"}


def _item(key, day, data):
    return CollectMaterial(key, "cbr.service_network.bank_offices", day, "html",
                           payload=SourcePayload(data, "text/html"))


def test_collection_capability_preserves_shared_bytes_and_distinct_source_uses(catalog):
    data = b"<html><body>published material</body></html>"
    items = (_item("a", "2026-01-01", data), _item("b", "2026-01-02", data))
    with StrategyBox(capabilities=catalog) as box:
        result = box.invoke("cbr.file_collector.collect_materials", parameters={"items": items}, timeout=30)
    assert result.outcome == "succeeded", [(value.outcome, value.diagnostics) for value in result.results.values()]
    collection = result.output("collection")
    assert collection.originals[0][1].payload.identity == collection.originals[1][1].payload.identity
    assert collection.originals[0][1].asset != collection.originals[1][1].asset
    assert [member.key for member in collection.manifest.members] == ["a", "b"]
    assert len({original.asset.issue_id for _, original in collection.originals}) == 2


def test_collection_cap_is_aggregate_and_keeps_earlier_confirmed_member(catalog):
    data = b"<html><body>published material</body></html>"
    items = (_item("a", "2026-01-01", data), _item("b", "2026-01-02", data))
    with StrategyBox(capabilities=catalog) as box:
        result = box.invoke("cbr.file_collector.collect_materials", parameters={"items": items, "max_batch_bytes": len(data)}, timeout=30)
    assert result.outcome == "partial", [(value.outcome, value.diagnostics) for value in result.results.values()]
    collection = result.output("collection")
    assert [key for key, _ in collection.originals] == ["a"]
    assert [(member.key, member.status, member.diagnostic) for member in collection.manifest.dispositions] == [
        ("a", "completed", None), ("b", "not_attempted", "budget.batch_bytes")]
