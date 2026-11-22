from dataclasses import asdict, replace
from datetime import datetime, timezone
from io import BytesIO

import pytest
from openpyxl import Workbook

from stratbox.core.execution import ExecutionContext
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.limits import ExecutionBudget
from stratbox.core.network import HttpResponse
from stratbox.core.operations.materials.definitions import ReadLocationRequest
from stratbox.core.operations.materials.operations import read_location
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.publications import (
    DiscoverRequest, IdentifyRequest, ListSourcesRequest, discover, identify, list_sources,
)
from stratbox.domains.cbr.publications.definitions import IDENTIFY
from stratbox.domains.cbr.publications.registry import CATALOG_SERIES, all_sources, validate_profiles
from stratbox.domains.cbr.publications.profiles import processing_profile
from stratbox.domains.cbr.file_collection.materials import CollectMaterial, CollectMaterialsRequest, collect_materials
from stratbox.domains.registry import operation_catalog
from stratbox.shared.data.processing import DataRole
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


def workbook():
    value = Workbook()
    value.active.append(["Published table", 1])
    stream = BytesIO()
    value.save(stream)
    return stream.getvalue()


def good(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


class StaticTransport:
    def __init__(self, data, media_type="text/html"):
        self.data, self.media_type, self.calls = data, media_type, []

    def exchange(self, request, *, cancelled=None):
        self.calls.append(request)
        return HttpResponse(200, self.data, {"content-type": self.media_type},
            datetime(2026, 11, 1, tzinfo=timezone.utc), "https://www.cbr.ru")


def test_logical_registry_has_no_locations_and_unifies_collector_sources():
    sources = good(list_sources(ListSourcesRequest()))
    assert len(sources) == 57
    assert len({item.series_id for item in sources}) == len(sources)
    assert validate_profiles()
    assert all("https://" not in str(asdict(item)) and "url" not in asdict(item) for item in sources)
    fixed = {item.series_id for item in sources if item.issue_model == "rolling"}
    assert set(CATALOG_SERIES.values()) <= fixed
    escrow_accounts = next(item for item in sources if item.series_id == CATALOG_SERIES["escrow_accounts"])
    escrow_project = next(item for item in sources if item.series_id == "cbr.project_finance.escrow")
    assert escrow_accounts.family_id != escrow_project.family_id
    operations = operation_catalog()
    for series in sources:
        for profile_id in (series.extraction_profile, series.normalization_profile):
            if profile_id is not None:
                profile = processing_profile(profile_id)
                definition, handler, _ = operations.resolve(profile.operation_id, profile.contract_version)
                assert definition.operation_id == profile.operation_id and callable(handler)


def test_dated_discovery_retains_source_only_forms_and_rejects_invalid_urls():
    html = SourcePayload(b'''<html><a href="/vfs/credit/forms/803-20261001.rar">one</a>
        <a href="/vfs/credit/forms/803-20260231.rar">invalid date</a>
        <a href="https://other.example/803-20260901.rar">external</a></html>''', "text/html")
    index = good(discover(DiscoverRequest("cbr.reporting_forms.f803", html)))
    assert len(index.assets) == 1 and index.assets[0].issue_id == "2026-10-01"
    assert index.assets[0].extraction_profile is not None
    assert index.rejected_links == 2
    assert index.coverage.status == "unknown"
    invalid = discover(DiscoverRequest("cbr.reporting_forms.f101", SourcePayload(b"broken")))
    assert invalid.outcome == "failed"  # Explicit offline input is never replaced by HTTP.


def test_escrow_html_is_an_explicit_unsupported_extraction_candidate():
    html = SourcePayload(b'<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">2019</a>')
    value = good(discover(DiscoverRequest("cbr.project_finance.escrow", html)))
    assert value.assets[0].format == "html" and value.assets[0].recognition == "unsupported_layout"
    original = good(identify(IdentifyRequest(value.series_id, "2019-08-26", SourcePayload(b"<html>original</html>", "text/html"), "html")))
    assert original.artifact.contract.role is DataRole.ORIGINALS


def test_typed_neutral_read_can_be_admitted_with_explicit_source_context(tmp_path):
    store = LocalFileStore(str(tmp_path))
    data = workbook()
    store.write_bytes("renamed.xlsx", data)
    loaded = read_location(ReadLocationRequest("renamed.xlsx"), store=store)
    bound = bind_request(IDENTIFY, {"material": project_output(loaded, "source")},
        parameters={"series_id": CATALOG_SERIES["corp_debt_a"], "issue_id": "2026-11-23", "format": "xlsx"})
    admitted = good(bound.invoke(identify))
    assert admitted.payload.data == data
    assert admitted.asset.series_id == CATALOG_SERIES["corp_debt_a"]
    assert admitted.identification == "caller_context_and_verified_format"


def test_mixed_collection_reads_independent_adapters_and_preserves_exact_originals(tmp_path):
    data = workbook()
    left, right = (LocalFileStore(str(tmp_path / name)) for name in ("left", "right"))
    left.write_bytes("report", data)
    right.write_bytes("report", b"wrong unrelated data")
    reference = good(read_location(ReadLocationRequest("report"), store=left)).material
    context = ExecutionContext(bindings=(
        ProviderBinding("left", CapabilityRequirement("filestore"), "ready", left),
        ProviderBinding("right", CapabilityRequirement("filestore"), "ready", right),
    ))
    result = good(collect_materials(CollectMaterialsRequest((
        CollectMaterial("disk", CATALOG_SERIES["corp_debt_a"], "2026-11-23", "xlsx",
                        material=reference, selection=ProviderSelection("left")),
        CollectMaterial("inline", CATALOG_SERIES["corp_debt_c"], "2026-11-23", "xlsx", payload=SourcePayload(data)),
    )), context=context))
    assert result.manifest.complete and result.manifest.coverage.status == "unknown"
    assert all(original.payload.data == data for _, original in result.originals)
    assert all(member.identity == ByteIdentity.of(data) for member in result.manifest.members)
    assert len({member.source_asset.series_id for member in result.manifest.members}) == 2


def test_failed_explicit_material_never_falls_back_or_leaks_into_completed_set(tmp_path):
    data = workbook()
    store = LocalFileStore(str(tmp_path))
    store.write_bytes("valid", data)
    reference = good(read_location(ReadLocationRequest("valid"), store=store)).material
    missing = replace(reference, locator="missing", revision=None, store_scope=store.storage_scope("missing"))
    items = (
        CollectMaterial("first", CATALOG_SERIES["corp_debt_a"], "2026-11-23", "xlsx", payload=SourcePayload(data)),
        CollectMaterial("missing", CATALOG_SERIES["corp_debt_c"], "2026-11-23", "xlsx", material=missing),
        CollectMaterial("last", CATALOG_SERIES["sme_debt"], "2026-11-23", "xlsx", payload=SourcePayload(data)),
    )
    result = collect_materials(CollectMaterialsRequest(items, continue_on_error=False), store=store)
    assert result.outcome == "partial", result.diagnostics
    assert [x.status for x in result.value.manifest.dispositions] == ["completed", "failed", "not_attempted"]
    assert [x.key for x in result.value.manifest.members] == ["first"]
    assert not result.effects


def test_discovery_resolves_context_http_binding_and_preserves_alternative_routes():
    first = "/vfs/credit/forms/101-20261001.rar"
    alternate = "/Collection/Collection/File/12345/101-20261001.rar"
    html = f'''<a href="{first}">one</a><a href="{alternate}">alternative</a>
        <a href="{first}">duplicate anchor</a>
        <a href="/vfs/credit/forms/101-20261001.zip">format variant</a>
        <a href="https://[broken]/101-20261001.rar">broken URL</a>'''.encode()
    chosen, unused = StaticTransport(html), StaticTransport(b"wrong")
    context = ExecutionContext(bindings=(
        ProviderBinding("chosen", CapabilityRequirement("http"), "ready", chosen),
        ProviderBinding("unused", CapabilityRequirement("http"), "ready", unused),
    ))
    value = good(discover(DiscoverRequest("cbr.reporting_forms.f101"),
        selection=ProviderSelection("chosen"), context=context))
    assert len(chosen.calls) == 1 and not unused.calls
    assert len(value.assets) == 2
    assert value.assets[0].url.endswith(first)
    assert value.assets[0].alternative_urls == ("https://www.cbr.ru" + alternate,)
    assert value.assets[1].format == "zip" and not value.assets[1].alternative_urls
    assert value.coverage.status == "unknown" and value.rejected_links == 1


def test_fixed_source_without_extractor_is_original_only_and_explicit_empty_page_is_invalid():
    payload = SourcePayload(b'<a href="/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx">file</a>')
    value = good(discover(DiscoverRequest(CATALOG_SERIES["corp_debt_a"], payload)))
    assert value.assets[0].recognition == "original_only"
    assert value.assets[0].extraction_profile is None
    invalid = discover(DiscoverRequest(CATALOG_SERIES["corp_debt_a"], payload, page_url=""))
    assert invalid.outcome == "failed" and invalid.diagnostics[0].code == "request.source_url_invalid"


@pytest.mark.parametrize("issue", ["20261001", "2026-W40-4"])
def test_dated_identification_requires_one_canonical_issue_key(issue):
    result = identify(IdentifyRequest("cbr.reporting_forms.f101", issue,
        SourcePayload(b"PK\x03\x04test"), "zip"))
    assert result.outcome == "failed" and result.diagnostics[0].code == "cbr.publication.issue_invalid"


def test_http_dbf_collection_retains_input_lineage_and_charges_returned_originals():
    header = bytearray(65)
    header[0:4] = bytes((3, 126, 10, 1))
    header[4:8] = (1).to_bytes(4, "little")
    header[8:10] = (65).to_bytes(2, "little")
    header[10:12] = (2).to_bytes(2, "little")
    header[32:37], header[43], header[48], header[64] = b"VALUE", ord("C"), 1, 13
    data = bytes(header) + b" x\x1a"
    transport = StaticTransport(data, "application/x-dbf")
    result = collect_materials(CollectMaterialsRequest((CollectMaterial(
        "dbf", "cbr.reporting_forms.f101", "2026-10-01", "dbf",
        url="https://www.cbr.ru/vfs/credit/forms/101-20261001.dbf"),)), transport=transport)
    value = good(result)
    assert value.originals[0][1].payload.data == data
    assert len(value.manifest.inputs) == 1
    assert value.manifest.inputs[0].identity == ByteIdentity.of(data)
    assert value.manifest.inputs[0].role == "original"
    assert value.manifest.inputs[0].source_id == "cbr.reporting_forms.f101"
    assert result.computation.inputs == value.manifest.inputs
    assert dict(result.resources_used)["output_bytes"] == len(data)


def test_collection_logical_identity_survives_inline_file_and_http_routes(tmp_path):
    payload = SourcePayload(b"<html>Same exact supplied publication</html>", "text/html")
    store = LocalFileStore(str(tmp_path))
    store.write_bytes("page", payload.data)
    material = good(read_location(ReadLocationRequest("page", "text/html"), store=store)).material
    common = dict(key="release", series_id="cbr.service_network.bank_offices",
                  issue_id="2026-11-23", format="html")
    inline = good(collect_materials(CollectMaterialsRequest((CollectMaterial(**common, payload=payload),))))
    retained = good(collect_materials(CollectMaterialsRequest((CollectMaterial(**common, material=material),)), store=store))
    received = good(collect_materials(CollectMaterialsRequest((CollectMaterial(**common),)),
                                      transport=StaticTransport(payload.data)))
    assert inline.manifest.identity == retained.manifest.identity == received.manifest.identity
    assert inline.manifest.members == retained.manifest.members == received.manifest.members


def test_collection_output_budget_preserves_completed_members_and_stops_remaining():
    data = workbook()
    items = tuple(CollectMaterial(key, CATALOG_SERIES["corp_debt_a"], "2026-11-23", "xlsx",
        payload=SourcePayload(data), name=key + ".xlsx") for key in ("first", "second", "third"))
    result = collect_materials(CollectMaterialsRequest(items),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=len(data))))
    assert result.outcome == "partial", result.diagnostics
    assert result.diagnostics[0].code == "budget.output_bytes"
    assert [item.status for item in result.value.manifest.dispositions] == ["completed", "failed", "not_attempted"]
    assert [key for key, _ in result.value.originals] == ["first"]
    assert dict(result.resources_used)["output_bytes"] == len(data)
    blocked = collect_materials(CollectMaterialsRequest(items),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=0)))
    assert blocked.outcome == "failed" and not blocked.value.originals
    assert not blocked.value.manifest.members


def test_collection_rejects_explicit_empty_name_and_bad_key_without_internal_failure():
    data = workbook()
    item = CollectMaterial("a", CATALOG_SERIES["corp_debt_a"], "2026-11-23", "xlsx",
        payload=SourcePayload(data), name="")
    failed = collect_materials(CollectMaterialsRequest((item,)))
    assert failed.outcome == "failed" and not failed.value.originals
    assert failed.value.manifest.dispositions[0].diagnostic == "collection.name_invalid"
    bad_key = collect_materials(CollectMaterialsRequest((replace(item, key=[]),)))
    assert bad_key.outcome == "failed" and bad_key.diagnostics[0].code != "internal.error"
