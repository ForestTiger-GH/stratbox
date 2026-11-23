"""Source format coverage and neutral-storage admission stay explicit."""
from datetime import datetime, timezone

from stratbox.operations.catalog import OperationCatalog
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.network import HttpResponse
from stratbox.core.operations.materials.definitions import ReadLocationRequest
from stratbox.core.operations.materials.operations import read_location
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations import project_finance as escrow
from stratbox.domains.cbr.operations.project_finance import definitions
from stratbox.operations import operation_catalog
from stratbox.shared.evidence import SourcePayload

from .test_replay import publication, checked


def test_historical_html_remains_discoverable_and_acquirable_without_false_parser_support():
    index = SourcePayload(b'''
<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">2019</a>
<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2020-01-01/">2020</a>
<a href="/Collection/Collection/File/62244/01072026.xlsx">2026</a>
<a href="/analytics/finansirovanie-dolevogo-stroitelstva/">section</a>
<a href="https://other.example/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">external</a>
''', "text/html")
    sources = checked(escrow.discover(escrow.DiscoverEscrowRequest(index)))
    assert [(source.format, source.extraction_status) for source in sources] == [
        ("html", "unsupported_layout"), ("html", "unsupported_layout"), ("xlsx", "supported")]
    assert [source.file_date_hint for source in sources] == ["2019-08-26", "2020-01-01", "2026-07-01"]
    data = b"<html><table><tr><td>Original historical material</td></tr></table></html>"
    class Publisher:
        def exchange(self, request, **options):
            assert request.url == sources[0].url
            return HttpResponse(200, data, {"content-type": "text/html"}, datetime.now(timezone.utc), "https://www.cbr.ru")
    original = checked(escrow.acquire(sources[0], transport=Publisher()))
    assert original.payload.data == data
    result = escrow.parse(escrow.ParseEscrowRequest(original.payload, sources[0].source_name))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "source.escrow_layout_unsupported"


def test_neutral_byte_read_and_complete_snapshot_handoff(tmp_path):
    request = publication()
    store = LocalFileStore(tmp_path)
    store.write_bytes("input.xlsx", request.payload.data)
    source = read_location(ReadLocationRequest("input.xlsx"), store=store)
    checked(source)
    parsed = bind_request(definitions.PARSE, {"source": project_output(source, "source")}, parameters={"source_name": request.source_name}).invoke(escrow.parse)
    checked(parsed)
    snapshot = bind_request(definitions.FLAKE_SNAPSHOT, {"flake": project_output(parsed, "file")}).invoke(escrow.build_flake_snapshot)
    checked(snapshot)
    restored = bind_request(definitions.READ_FLAKE_SNAPSHOT, {"snapshot": project_output(snapshot, "snapshot")}).invoke(escrow.read_flake_snapshot)
    checked(restored)
    assert restored.value.df_cells.equals(parsed.value.df_cells)
    dataset = escrow.integrate_flakes(escrow.IntegrateEscrowRequest((restored.value,)))
    checked(dataset)
    view = bind_request(definitions.VIEWS, {"dataset": project_output(dataset, "dataset")}).invoke(escrow.build_views)
    checked(view)
    rendered = bind_request(definitions.RENDER, {"views": project_output(view, "views")}).invoke(escrow.render_workbook)
    checked(rendered)


def test_all_escrow_registrations_resolve_to_the_declared_operations():
    catalog = OperationCatalog(tuple(ref for ref in operation_catalog().references
        if ref.handler_ref.startswith("stratbox.domains.cbr.operations.project_finance.")))
    assert len(catalog.references) == 17
    for reference in catalog.references:
        definition, handler, codec = catalog.resolve(reference.operation_id)
        assert definition.operation_id == reference.operation_id
        assert definition == catalog.get(reference.operation_id)
        assert callable(handler)
