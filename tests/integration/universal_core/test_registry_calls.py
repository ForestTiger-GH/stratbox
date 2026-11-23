"""Named catalog calls retain values and evidence across independent stages."""
from io import BytesIO

import pytest

from stratbox.core.execution import HandoffError, prepare_input, project_output
from stratbox.core.registry import operation_catalog
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.evidence import SourcePayload


def _payload():
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.append(["Metric", "Value"])
    workbook.active.append(["Loans", 27])
    stream = BytesIO()
    workbook.save(stream)
    return SourcePayload(stream.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def test_catalog_named_calls_extract_retain_replay_and_render_with_lineage():
    catalog = operation_catalog()
    payload = _payload()
    call = catalog.bind("workbook.extract",
        inputs={"source": prepare_input(payload)},
        parameters={"series_id": "example.loans", "issue_id": "2026-10"})
    extracted = call.invoke()
    assert extracted.outcome == "succeeded", extracted.diagnostics
    encoded = catalog.bind("workbook.snapshot",
        inputs={"workbook": project_output(extracted, "workbook")}).invoke()
    assert encoded.outcome == "succeeded", encoded.diagnostics
    replayed = catalog.bind("workbook.replay",
        inputs={"snapshot": project_output(encoded, "snapshot")}).invoke()
    assert replayed.outcome == "succeeded", replayed.diagnostics
    rendered = catalog.bind("workbook.readable",
        inputs={"workbook": project_output(replayed, "workbook")}).invoke()
    assert rendered.outcome == "succeeded", rendered.diagnostics
    assert replayed.value == extracted.value
    assert any(receipt.identity == payload.identity for receipt in rendered.used_inputs)
    assert rendered.computation.parents[0][1] == replayed.computation


def test_catalog_binding_rejects_unknown_roles_and_wrong_schema_before_execution():
    catalog = operation_catalog()
    with pytest.raises(HandoffError, match="handoff.input_unknown"):
        catalog.bind("workbook.extract", inputs={"typo": prepare_input(_payload())})
    with pytest.raises(HandoffError, match="processing.schema_mismatch"):
        catalog.bind("workbook.extract",
            inputs={"source": prepare_input("wrong", DataContract("wrong.schema", role=DataRole.ORIGINALS))},
            parameters={"series_id": "example.loans", "issue_id": "2026-10"})


def test_catalog_binding_admits_only_declared_parameters():
    catalog = operation_catalog()
    with pytest.raises(HandoffError, match="handoff.parameter_unknown"):
        catalog.bind("workbook.extract", inputs={"source": prepare_input(_payload())},
            parameters={"series_id": "example.loans", "issue_id": "2026-10", "hidden": True})


def test_source_bound_discovery_and_selection_use_the_canonical_route_offline():
    catalog = operation_catalog()
    source = catalog.bind_source("rosstat.short_term_indicators", format="xlsx")
    index_contract = DataContract("rosstat.publications.index_material", role=DataRole.ORIGINALS)
    html = SourcePayload(b'<a href="/storage/mediabank/2026-08.xlsx">August</a>',
                         "text/html", "rosstat.short_term_indicators.index")
    discovered = source.bind("rosstat.publications.discover",
        inputs={"index": prepare_input(html, index_contract)}).invoke()
    assert discovered.outcome == "succeeded", discovered.diagnostics
    selected = source.bind("rosstat.publications.select",
        inputs={"index": project_output(discovered, "index")},
        parameters={"issue_ids": ("2026-08",)}).invoke()
    assert selected.outcome == "succeeded", selected.diagnostics
    assert selected.value[0].key.issue.series_id == source.source.series_id
    assert any(receipt.identity == html.identity for receipt in selected.used_inputs)
    foreign = catalog.bind_source("rosstat.population_municipalities", format="xlsx")
    with pytest.raises(HandoffError, match="source.input_series_mismatch"):
        foreign.bind("rosstat.publications.acquire", inputs={
            "asset": prepare_input(selected.value[0], DataContract("rosstat.publications.asset"))})
    # Stage hints classify a route; the exact input port decides admission.
    hinted = source.bind("rosstat.publications.select", from_stage="calculate",
        inputs={"index": project_output(discovered, "index")})
    assert hinted.request.index == discovered.value


def test_source_binding_rejects_foreign_operations_formats_and_overridden_identity():
    catalog = operation_catalog()
    source = catalog.bind_source("rosstat.short_term_indicators", format="xlsx")
    with pytest.raises(HandoffError, match="source.operation_unbound"):
        source.bind("fns.sme.discover")
    with pytest.raises(HandoffError, match="source.parameter_conflict"):
        source.bind("rosstat.publications.discover", parameters={"series_id": "rosstat.socioeconomic_russia"})
    with pytest.raises(HandoffError, match="source.format_unavailable"):
        catalog.bind_source("rosstat.short_term_indicators", format="pdf")
    html_source = catalog.bind_source("cbr.project_finance.escrow", format="html")
    with pytest.raises(HandoffError, match="source.operation_format_unavailable"):
        html_source.bind("cbr.escrow.parse")
    with pytest.raises(HandoffError, match="source.format_required"):
        catalog.bind_source("cbr.project_finance.escrow").bind("cbr.escrow.parse")
