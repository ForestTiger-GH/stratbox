"""Publication selection, observed updates and exact material handoffs."""
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook

from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.network import HttpResponse
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ARCHIVE
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations.collection.materials import (
    CollectMaterial, CollectMaterialsRequest, collect_materials,
)
from stratbox.domains.cbr.operations.publications import (
    AcquirePublicationRequest, AssessUpdatesRequest, DiscoverRequest, IdentifyRequest,
    SelectPublicationRequest, acquire, assess_updates, discover, identify, select,
)
from stratbox.domains.cbr.operations.publications.definitions import ACQUIRE, SELECT
from stratbox.domains.cbr.publications.contracts import (
    DestinationObservation, ProcessingCheckpoint,
)
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.material_collections import decode_collection

SERIES = "cbr.funding.funds_all"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def workbook():
    book = Workbook()
    book.active.append(["Published data", 1])
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


class Transport:
    def __init__(self, data):
        self.data, self.calls = data, []

    def exchange(self, request, *, cancelled=None):
        self.calls.append(request)
        return HttpResponse(200, self.data, {"content-type": XLSX},
            datetime(2026, 11, 1, tzinfo=timezone.utc), "https://www.cbr.ru")


def original(data=None, issue="2026-11-01", series=SERIES):
    return checked(identify(IdentifyRequest(series, issue, SourcePayload(data or workbook(), XLSX), "xlsx")))


def test_typed_discovery_selection_acquisition_retains_exact_receipt():
    inventory = discover(DiscoverRequest(SERIES))
    selected = bind_request(SELECT, {"inventory": project_output(inventory, "inventory")}).invoke(select)
    transport = Transport(workbook())
    missing = bind_request(ACQUIRE, {"asset": project_output(selected, "asset")}).invoke(acquire, transport=transport)
    assert missing.diagnostics[0].code == "cbr.publication.issue_context_required"
    assert not transport.calls
    received = bind_request(ACQUIRE, {"asset": project_output(selected, "asset")},
        parameters={"issue_id": "2026-11-01"}).invoke(acquire, transport=transport)
    value = checked(received)
    assert len(transport.calls) == 1
    assert value.payload.data == transport.data
    assert value.acquisition.identity == value.payload.identity
    assert value.acquisition.origin_assurance == "provider_reported"
    assert value.lineage[0] in received.used_inputs
    assert project_output(received, "artifact").value == value.artifact
    assert value.artifact.representation.data == transport.data


def test_alternative_publication_routes_require_explicit_choice():
    inventory = checked(discover(DiscoverRequest(SERIES)))
    asset = replace(inventory.assets[0], alternative_urls=("https://www.cbr.ru/alternate.xlsx",))
    inventory = replace(inventory, assets=(asset,))
    failed = select(SelectPublicationRequest(inventory))
    assert failed.diagnostics[0].code == "cbr.selection.publication_ambiguous"
    chosen = checked(select(SelectPublicationRequest(inventory, url=asset.alternative_urls[0])))
    assert chosen.url == asset.alternative_urls[0] and not chosen.alternative_urls
    missing = select(SelectPublicationRequest(inventory, url="https://www.cbr.ru/absent.xlsx"))
    assert missing.diagnostics[0].code == "cbr.selection.publication_missing"


def test_updates_keep_source_method_and_destination_states_independent():
    first = original()
    method, result = ByteIdentity.of(b"mapping-1"), ByteIdentity.of(b"dataset-1")
    checkpoint = ProcessingCheckpoint(first.asset, first.payload.identity, method, result)
    destinations = (DestinationObservation("left", result), DestinationObservation("right"))
    request = AssessUpdatesRequest(first, method, checkpoint, "processed", destinations)
    same = checked(assess_updates(request))
    assert same.source_state == "unchanged" and not same.processing_required
    assert same.destination_actions == (("left", "confirmed"), ("right", "write_required"))
    changed_method = checked(assess_updates(replace(request, processing_signature=ByteIdentity.of(b"mapping-2"))))
    assert changed_method.source_state == "unchanged" and changed_method.processing_required
    assert changed_method.destination_actions == (("left", "await_processing"), ("right", "await_processing"))
    assert changed_method.checkpoint_candidate.result_identity is None
    recapture = original(first.payload.data, issue="2026-11-02")
    capture = checked(assess_updates(replace(request, original=recapture)))
    assert capture.source_state == "new_capture_same_bytes" and not capture.processing_required
    revised = replace(first, payload=SourcePayload(first.payload.data + b"revision", XLSX))
    revision = checked(assess_updates(replace(request, original=revised)))
    assert revision.source_state == "revised_bytes" and revision.processing_required
    unchanged_original = checked(assess_updates(replace(request, target="original", destinations=(
        DestinationObservation("source", first.payload.identity),), processing_signature=ByteIdentity.of(b"mapping-2"))))
    assert unchanged_original.processing_required
    assert unchanged_original.destination_actions == (("source", "confirmed"),)


def test_dated_issue_context_requires_processing_even_when_bytes_agree():
    first = original(series="cbr.project_finance.escrow", issue="2026-10-01")
    method, result = ByteIdentity.of(b"method"), ByteIdentity.of(b"dataset")
    checkpoint = ProcessingCheckpoint(first.asset, first.payload.identity, method, result)
    next_issue = original(first.payload.data, series=first.asset.series_id, issue="2026-11-01")
    plan = checked(assess_updates(AssessUpdatesRequest(next_issue, method, checkpoint)))
    assert plan.source_state == "new_issue" and plan.processing_required


def test_partial_collection_handoff_preserves_complete_selection_manifest(tmp_path):
    data = workbook()
    result = collect_materials(CollectMaterialsRequest((
        CollectMaterial("good", SERIES, "2026-11-01", "xlsx", payload=SourcePayload(data, XLSX)),
        CollectMaterial("bad", SERIES, "2026-11-02", "xlsx", payload=SourcePayload(b"broken")),
        CollectMaterial("later", SERIES, "2026-11-03", "xlsx", payload=SourcePayload(data, XLSX)),
    ), continue_on_error=False))
    assert result.outcome == "partial", result.diagnostics
    bound = bind_request(ARCHIVE, {
        "members": project_output(result, "archive_members"),
        "manifest": project_output(result, "manifest"),
    }, parameters={"destination": OriginalDestination("retained.zip")})
    store = LocalFileStore(str(tmp_path))
    archived = checked(bound.invoke(archive_materials, output_store=store))
    assert archived.manifest == result.value.manifest
    with ZipFile(BytesIO(store.read_bytes("retained.zip"))) as value:
        manifest = decode_collection(value.read("manifest.json"))
        assert [item.status for item in manifest.dispositions] == ["completed", "failed", "not_attempted"]
        assert value.read(manifest.members[0].name) == data
        assert len(value.namelist()) == 2
