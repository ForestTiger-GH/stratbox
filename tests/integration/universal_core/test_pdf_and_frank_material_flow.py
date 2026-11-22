"""Byte acquisition is format-neutral; domain decoding is an independent choice."""
from datetime import date, datetime, timezone
from hashlib import sha256

from stratbox.core.execution import ExecutionContext
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.network import HttpRequest, HttpResponse, HttpsEndpoint
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.materials.definitions import ArtifactDestination, ReadArtifactRequest, ReadLocationRequest, SaveArtifactRequest
from stratbox.core.operations.materials.operations import read_artifact, read_location, save_artifact
from stratbox.core.operations.source.original_definitions import OriginalDestination, ReadOriginalRequest, ReceiveOriginalRequest, SAVE, SaveOriginalRequest
from stratbox.core.operations.source.originals import read_original, receive_original, save_original
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg
from stratbox.domains.frank_rg.operations.definitions import CAPTURE, PREPARE_FILE
from stratbox.domains.frank_rg.publications.contracts import ReportPeriod
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.materials import MaterialArtifact


def good(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def test_pdf_download_can_be_preserved_before_any_readable_conversion(tmp_path):
    pdf = b"%PDF-1.7\nsynthetic binary original\x00\xff\n%%EOF"
    url = "https://publisher.example/reports/national.pdf"
    class Publisher:
        def exchange(self, request, **options):
            return HttpResponse(200, pdf, {"content-type": "application/pdf"},
                datetime(2026, 11, 23, tzinfo=timezone.utc), "https://publisher.example",
                target_sha256=sha256(request.url.encode()).hexdigest())
    received = receive_original(ReceiveOriginalRequest(
        HttpRequest("GET", url, (HttpsEndpoint("publisher.example", "/reports/", subtree=True),)),
        "publisher.national_report", frozenset({"application/pdf"})), transport=Publisher())
    original = good(received)
    store = LocalFileStore(str(tmp_path))
    retained = good(save_original(SaveOriginalRequest(original, OriginalDestination("originals/national.pdf")), store=store))
    assert good(read_original(ReadOriginalRequest(retained.material), store=store)).data == pdf
    assert store.read_bytes("originals/national.pdf") == pdf
    # A supplied conversion result models an external reader/AI boundary. Core
    # stores its declared schema and provenance; it does not claim to run AI.
    readable = MaterialArtifact(DataContract("sample.readable_document", 1, DataRole.READABLE),
        Representation("sample.markdown", 1, "text/markdown", b"# Extracted document\n", "utf-8"),
        (UsedInputReceipt.for_payload(original.payload, "original_pdf"),), "publisher.national_report")
    saved = good(save_artifact(SaveArtifactRequest(readable, ArtifactDestination("scrolls/national.md")), store=store))
    restored = good(read_artifact(ReadArtifactRequest(saved.artifact), store=store))
    assert restored == readable and restored.inputs[0].identity == original.payload.identity
    assert retained.material.identity != saved.artifact.material.identity


def test_frank_supplied_file_can_be_handed_to_naming_storage_and_common_archive(tmp_path):
    source, output = LocalFileStore(str(tmp_path / "source")), LocalFileStore(str(tmp_path / "output"))
    data = b"opaque workbook bytes without parsing"
    source.write_bytes("delivery/custom-name.xlsx", data)
    context = ExecutionContext(bindings=(
        ProviderBinding("incoming", CapabilityRequirement("filestore"), "ready", source),
        ProviderBinding("archive-reader", CapabilityRequirement("filestore"), "ready", output),
        ProviderBinding("saved", CapabilityRequirement("output_filestore"), "ready", output)))
    source_id = "frg.express.issuance"
    loaded = read_location(ReadLocationRequest("delivery/custom-name.xlsx"),
                           selection=ProviderSelection("incoming"), context=context)
    report = bind_request(CAPTURE, {"payload": project_output(loaded, "source")}, parameters={
        "source_id": source_id, "period": ReportPeriod(date(2026, 5, 1)), "format": "xlsx",
    }).invoke(frg.capture)
    prepared = bind_request(PREPARE_FILE, {"report": project_output(report, "report")}).invoke(frg.prepare_file)
    name = good(prepared).filename
    saved = bind_request(SAVE, {"source": project_output(prepared, "payload")},
        parameters={"destination": OriginalDestination(name)}).invoke(save_original,
            selection=ProviderSelection("saved"), context=context)
    retained = good(saved)
    assert output.read_bytes(name) == data
    archive = archive_materials(ArchiveRequest((ArchiveMember(name, retained.material, ProviderSelection("archive-reader")),),
                                               OriginalDestination("selected.zip")),
                                output_selection=ProviderSelection("saved"), context=context)
    good(archive)
    assert archive.value.members[0][1].source_id == source_id
    assert archive.value.members[0][1].identity == loaded.value.payload.identity
    assert prepared.computation.inputs and saved.used_inputs
