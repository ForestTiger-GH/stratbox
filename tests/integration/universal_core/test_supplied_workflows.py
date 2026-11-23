"""Real publisher workflows preserve semantic boundaries through one scheduler."""
from datetime import date

import pytest

from stratbox.composition import compile_workflow
from stratbox.composition.builtins import composition_dispositions, expand_operation, source_workflow
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.domains.cbr.operations.collection.material_definitions import CollectMaterial, CollectMaterialsRequest
from stratbox.domains.fns.operations import sme
from stratbox.domains.fns.operations.contracts import ProcessRequest
from stratbox.domains.fns.publications.contracts import ReleaseContext
from stratbox.operations import operation_catalog
from stratbox.shared.evidence import SourcePayload

from source_fixtures import encoded, fixture


@pytest.fixture(scope="module")
def catalog():
    return operation_catalog()


def test_every_registered_source_has_an_explicit_supported_workflow(catalog):
    admitted = []
    for card in catalog.source_catalog().sources:
        source_format = next((item for item in card.formats if item in
            {"xlsx", "html", "json", "csv", "pdf", "zip", "rar"}), card.formats[0])
        output = "original" if source_format == "doc" else "extract"
        workflow = source_workflow(card.series_id, payload=SourcePayload(b"not decoded during planning"),
            issue_id="2026-01-01", format=source_format, catalog=catalog, output=output,
            parameters={"member_names": ("reviewed-member.xlsx",)} if card.publisher_id == "rosstat" and source_format in {"zip", "rar"} else None)
        plan = compile_workflow(workflow, catalog)
        assert set(plan.outputs) == {output}
        admitted.append(card.series_id)
        # Planning a requested source extract does not render an unused product.
        assert not any(task.operation_id and ".render" in task.operation_id for task in plan.tasks)
    assert len(admitted) == 90
    with pytest.raises(ValueError, match="legacy_doc_unsupported"):
        source_workflow("minfin.nwf.veb_deposits", payload=SourcePayload(b"doc"),
                        issue_id="2026-01-01", catalog=catalog)


def test_all_composite_declarations_have_an_explicit_disposition(catalog):
    composites = {definition.operation_id for definition in catalog.definitions
                  if definition.processing and definition.processing.composition}
    dispositions = composition_dispositions()
    assert len(dispositions) == len({item.operation_id for item in dispositions}) == 33
    assert {item.operation_id for item in dispositions} == composites
    assert sum(item.strategy == "graph" for item in dispositions) == 21
    assert all(item.reason for item in dispositions)


def test_fns_full_route_matches_existing_economic_product_with_one_worker(catalog):
    day = date(2026, 11, 10)
    payload = SourcePayload(encoded(fixture(day)), "application/json")
    release = ReleaseContext("fns.sme", day.isoformat(), day)
    request = ProcessRequest(payload, release)
    expected = sme.process(request)
    assert expected.outcome == "succeeded", expected.diagnostics
    plan = compile_workflow(expand_operation("fns.sme.process", request), catalog)
    assert len(plan.tasks) == 5
    with ExecutionSession(catalog, settings=ExecutionSettings(max_workers=1)) as session:
        actual = session.run(plan)
    assert actual.outcome == "succeeded", [(item.operation_id, item.state, item.reason) for item in actual.tasks]
    assert actual.output("representation").data == expected.value.representation.data
    assert actual.output("dataset").batch.observations == expected.value.dataset.batch.observations
    assert len(actual.results) == 5


def _item(key, day, data):
    return CollectMaterial(key, "cbr.service_network.bank_offices", day, "html",
                           payload=SourcePayload(data, "text/html"))


def test_collection_graph_preserves_shared_bytes_and_distinct_source_uses(catalog):
    data = b"<html><body>published material</body></html>"
    request = CollectMaterialsRequest((_item("a", "2026-01-01", data), _item("b", "2026-01-02", data)))
    plan = compile_workflow(expand_operation("cbr.file_collector.collect_materials", request), catalog)
    with ExecutionSession(catalog) as session:
        result = session.run(plan)
    assert result.outcome == "succeeded"
    collection = result.output("collection")
    assert len(result.results) == 2
    assert collection.originals[0][1].payload.identity == collection.originals[1][1].payload.identity
    assert collection.originals[0][1].asset != collection.originals[1][1].asset
    assert [member.key for member in collection.manifest.members] == ["a", "b"]


def test_collection_cap_is_aggregate_and_keeps_earlier_confirmed_member(catalog):
    data = b"<html><body>published material</body></html>"
    request = CollectMaterialsRequest((_item("a", "2026-01-01", data), _item("b", "2026-01-02", data)),
                                      max_batch_bytes=len(data))
    plan = compile_workflow(expand_operation("cbr.file_collector.collect_materials", request), catalog)
    with ExecutionSession(catalog) as session:
        result = session.run(plan)
    assert result.outcome == "partial"
    collection = result.output("collection")
    assert [key for key, _ in collection.originals] == ["a"]
    assert [(member.key, member.status, member.diagnostic) for member in collection.manifest.dispositions] == [
        ("a", "completed", None), ("b", "not_attempted", "budget.batch_bytes")]
