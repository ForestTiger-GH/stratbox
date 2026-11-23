"""Machine references retain rejection decisions and confirmed storage effects."""

import json
from dataclasses import replace
from datetime import date
from io import BytesIO

from stratbox.core.execution import Diagnostic, ExecutionContext, OperationResult, ResultAdmission
from stratbox.core.execution.machine.references import MemoryValueResolver, invoke_reference
from stratbox.operations import core_catalog
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import WriteSnapshotRequest
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.observations import ObservationBatch


class RejectPublishedResult(ResultAdmission):
    policy_id = "test.publication_postcondition"

    def assess(self, definition, value, *, phase, outcome=None):
        return ((Diagnostic("source.output_series_mismatch", component="source",
            reason_class="source_context"),) if phase == "result" else ())


def test_reference_result_reports_postcondition_failure_without_hiding_commit(tmp_path):
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    snapshot = observation_snapshot(ObservationBatch("test.source", 1, "issue", (), ()))
    vault = MemoryValueResolver()
    request_ref = vault.retain(WriteSnapshotRequest(snapshot))
    catalog = core_catalog()
    definition = catalog.get("dataset.write_snapshot")
    context = ExecutionContext(result_admissions=(RejectPublishedResult(),), bindings=(
        ProviderBinding("files", CapabilityRequirement("dataset_writer"), "ready", store, "test"),))
    response = json.loads(invoke_reference(json.dumps({
        "operation_id": definition.operation_id, "request_ref": request_ref,
    }).encode(), catalog=catalog, values=vault, context=context,
        authorized_effects=definition.possible_effects))
    assert response["outcome"] == "failed" and response["value_ref"] is None
    assert response["diagnostics"][0]["stage"] == "result_admission"
    assert response["diagnostics"][0]["reason_class"] == "source_context"
    assert any(item["kind"] == "dataset.write" and item["state"] == "confirmed"
        for item in response["effects"])
    result = vault.resolve(response["result_ref"], OperationResult)
    assert result.effects and result.value is None
    reference, = store.versions(snapshot.manifest.dataset_id)
    assert store.read_snapshot(reference) == snapshot


def test_real_source_policy_refuses_foreign_prepared_snapshot_before_storage(tmp_path):
    from openpyxl import Workbook
    from stratbox.core.execution import InMemorySink
    from stratbox.core.execution.calls import SourceResultAdmission
    from stratbox.core.formats.spreadsheets.extracts import extract_workbook
    from stratbox.operations import operation_catalog
    from stratbox.core.storage.datasets.operations import write_snapshot
    from stratbox.shared.data.workbooks import workbook_snapshot
    from stratbox.shared.evidence import SourcePayload

    book = Workbook()
    book.active.append(["Loans", 27])
    stream = BytesIO()
    book.save(stream)
    book.close()
    foreign = "cbr.corporate_lending.corp_debt_c"
    prepared = workbook_snapshot(extract_workbook(SourcePayload(stream.getvalue()),
        series_id=foreign, issue_id="2026-10"))
    catalog = operation_catalog()
    sources = catalog.source_catalog()
    expected = sources.source("cbr.corporate_lending.corp_debt_a")
    policy = SourceResultAdmission(catalog.get("dataset.write_snapshot"),
        expected.series_id, expected.family_id, sources)
    sink = InMemorySink()
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    result = write_snapshot(WriteSnapshotRequest(prepared), store=store,
        context=ExecutionContext(sink=sink, result_admissions=(policy,)))
    assert result.outcome == "failed" and result.effects == ()
    assert result.diagnostics[0].code == "source.output_series_mismatch"
    assert result.diagnostics[0].stage == "precommit_admission"
    assert result.used_inputs and result.used_inputs[0].identity == prepared.identity
    assert not tuple(tmp_path.rglob("*"))
    assert sink.events[-1].outcome == "failed"


def test_partial_office_candidates_skip_the_unavailable_success_output(tmp_path, monkeypatch):
    from openpyxl import Workbook
    from stratbox.core.execution import InMemorySink
    from stratbox.core.execution.calls import SourceResultAdmission
    from stratbox.operations import operation_catalog
    from stratbox.domains.cbr.operations.service_network.territorial_offices import operations
    from stratbox.domains.cbr.tables.service_network.territorial_offices.contracts import (
        OfficesRegCandidates, ParseOfficesRegRequest,
    )
    from stratbox.shared.data.operations import OutputPort
    from stratbox.shared.data.processing import DataContract
    from stratbox.shared.evidence import SourcePayload

    book = Workbook()
    sheet = book.active
    sheet.title = "One block"
    sheet.append(["Данные по состоянию на 01.11.2026"])
    sheet.append(["Территория", "Кредитные организации", "Филиалы", "Мобильные офисы", "Всего"])
    for name in ["Российская Федерация", *(f"New territory {i:03d}" for i in range(35))]:
        sheet.append([name, 2, 3, 5, 10])
    book.copy_worksheet(sheet).title = "Another block"
    stream = BytesIO()
    book.save(stream)
    book.close()

    # The complete-release path exists on ParsedRelease, never on candidates.
    definition = replace(operations.PARSE, processing=replace(operations.PARSE.processing, outputs=(
        OutputPort("release", DataContract("cbr.offices_reg.release"), "representation",
            source_policy="primary_source_required"),
        OutputPort("candidates", DataContract("cbr.offices_reg.candidates"),
            outcomes=frozenset({"partial"}), source_policy="source_inapplicable"),
    )))
    monkeypatch.setattr(operations, "PARSE", definition)
    catalog = operation_catalog()
    sources = catalog.source_catalog()
    source = sources.source("cbr.service_network.territorial_offices")
    policy = SourceResultAdmission(definition, source.series_id, source.family_id, sources)
    sink = InMemorySink()
    result = operations.parse(ParseOfficesRegRequest(SourcePayload(stream.getvalue()), date(2026, 11, 1)),
        context=ExecutionContext(sink=sink, result_admissions=(policy,)))
    assert result.outcome == "partial", result.diagnostics
    assert isinstance(result.value, OfficesRegCandidates) and len(result.value.blocks) == 2
    assert not any(item.code.startswith("source.output_") for item in result.diagnostics)
    assert sink.events[-1].outcome == "partial"
