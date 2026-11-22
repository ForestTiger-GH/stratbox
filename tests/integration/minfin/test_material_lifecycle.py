"""One Minfin business path across supplied, HTTP and separately retained stores."""
from datetime import datetime, timezone
from io import BytesIO

from openpyxl import Workbook

from stratbox.core.execution import ExecutionContext
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.network import HttpResponse
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.core.operations.materials.definitions import (
    ArtifactDestination, ReadArtifactRequest, ReadLocationRequest, SaveArtifactRequest, TransferArtifactRequest,
)
from stratbox.core.operations.materials.operations import (
    artifact_from_output, project_artifact, read_artifact, read_location, save_artifact, transfer_artifact,
)
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.materials import ArtifactReference
from stratbox.domains.minfin import (
    AcquireRequest, DiscoverRequest, ExtractRequest, MetricBinding, ReadFlakeRequest, SummaryRequest,
    acquire, build_source_flake, calculate_headlines, discover, extract,
    read_source_flake, serialize_source_flake, map_observations,
)
from stratbox.domains.minfin.operations import definitions as D

SERIES = "minfin.fedbud.annex3.monthly"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workbook():
    book = Workbook()
    sheet = book.active
    sheet.title = "Federal budget"
    sheet.append(["Code", "Indicator", "2025-10", "2026-10"])
    sheet.append(["1", "Доходы, всего", 100, 110])
    sheet.append(["2", "Расходы, всего", 120, 135])
    sheet.append(["3", "Дефицит (-)/Профицит (+)", -20, -25])
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def _assert(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result


def _binding(role, scope, provider):
    return ProviderBinding("files", CapabilityRequirement(role), "ready", provider, scope)


def test_file_http_retained_and_transferred_flakes_have_identical_financial_meaning(tmp_path):
    source_root, first_root, second_root = (tmp_path / name for name in ("incoming", "first", "second"))
    for path in (source_root, first_root, second_root):
        path.mkdir()
    body = _workbook()
    (source_root / "arbitrary_source_name.xlsx").write_bytes(body)
    source, first, second = (LocalFileStore(str(path)) for path in (source_root, first_root, second_root))
    context = ExecutionContext(bindings=(
        _binding("filestore", "incoming", source), _binding("filestore", "first", first),
        _binding("filestore", "second", second), _binding("output_filestore", "first", first),
        _binding("output_filestore", "second", second),
    ))
    loaded = _assert(read_location(ReadLocationRequest("arbitrary_source_name.xlsx", XLSX, SERIES),
                                   selection=ProviderSelection("files", "incoming"), context=context))
    cells = _assert(bind_request(D.EXTRACT, {"original": project_output(loaded, "source")},
                                parameters={"family_id": "minfin.fedbud", "format": "xlsx"}).invoke(extract))
    mapped = _assert(bind_request(D.MAP, {"extract": project_output(cells, "extract")},
                                  parameters={"bindings": (MetricBinding("Federal budget", 2, 4,
                                      "budget.revenue", "2026-10", "ytd", "billion_rub"),)})
                     .invoke(map_observations))
    assert mapped.value.observations[0].value == "110"
    cleaned = _assert(bind_request(D.BUILD_FLAKE, {"source": project_output(cells, "extract")},
                                  parameters={"source_id": SERIES}).invoke(build_source_flake))
    serialized = _assert(bind_request(D.SERIALIZE_FLAKE, {"flake": project_output(cleaned, "flake")})
                         .invoke(serialize_source_flake))
    artifact = artifact_from_output(serialized, "representation", series_id=SERIES)
    saved = _assert(save_artifact(SaveArtifactRequest(artifact, ArtifactDestination("flakes/budget.json")),
                                 selection=ProviderSelection("files", "first"), context=context))
    cold_reference = ArtifactReference.from_bytes(saved.value.artifact.to_bytes())
    transferred = _assert(transfer_artifact(
        TransferArtifactRequest(cold_reference, ArtifactDestination("retained/renamed.json")),
        source_selection=ProviderSelection("files", "first"),
        output_selection=ProviderSelection("files", "second"), context=context))
    assert transferred.value.artifact.material.identity == saved.value.artifact.material.identity
    assert transferred.value.artifact.identity == saved.value.artifact.identity
    assert transferred.value.artifact.material.store_scope != saved.value.artifact.material.store_scope
    # Recreate the store adapter and portable reference as a later process would.
    reopened = _assert(read_artifact(
        ReadArtifactRequest(ArtifactReference.from_bytes(transferred.value.artifact.to_bytes())),
        store=LocalFileStore(str(second_root))))
    assert reopened.value == artifact
    assert reopened.value.computation.parents
    decoded = _assert(bind_request(D.READ_FLAKE, {"representation": project_artifact(reopened)})
                      .invoke(read_source_flake))
    assert decoded.computation.parents == (("representation", artifact.computation),)
    assert decoded.value == cleaned.value
    direct = _assert(calculate_headlines(SummaryRequest(cleaned.value)))
    retained = _assert(calculate_headlines(SummaryRequest(decoded.value)))
    assert direct.value == retained.value
    assert direct.computation.computation_id == retained.computation.computation_id
    assert [metric.value for metric in retained.value.metrics] == ["110", "135", "-25"]

    # The HTTP route yields the same bytes, source identity and domain extract.
    page = SourcePayload(b'<div class="document_card" data-href="?id_57=80042-report">'
                         b'<a class="file_item" href="/common/upload/library/renamed.xlsx">x</a></div>',
                         "text/html", "minfin.fedbud.index")
    asset, = _assert(discover(DiscoverRequest("minfin.fedbud", page))).value.assets
    class Http:
        def exchange(self, request, *, cancelled=None):
            assert request.url == asset.url
            return HttpResponse(200, body, {"content-type": XLSX},
                                datetime(2026, 11, 23, tzinfo=timezone.utc), "https://minfin.gov.ru")
    acquired = _assert(acquire(AcquireRequest(asset), transport=Http()))
    from_http = _assert(extract(ExtractRequest("minfin.fedbud", acquired.value.source.payload, "xlsx")))
    assert from_http.value == cells.value
    assert from_http.computation.computation_id == cells.computation.computation_id


def test_missing_explicit_disk_input_fails_without_using_available_http(tmp_path):
    calls = []
    class ForbiddenHttp:
        def exchange(self, request, **kwargs):
            calls.append(request)
            raise AssertionError("Explicit disk input cannot fall back to HTTP")
    context = ExecutionContext(bindings=(
        _binding("filestore", "incoming", LocalFileStore(str(tmp_path))),
        ProviderBinding("http", CapabilityRequirement("http"), "ready", ForbiddenHttp(), "default"),
    ))
    result = read_location(ReadLocationRequest("missing.xlsx", XLSX, SERIES),
                           selection=ProviderSelection("files", "incoming"), context=context)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "input.material_unavailable"
    assert calls == []
