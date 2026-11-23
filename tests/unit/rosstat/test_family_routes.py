"""All four family routes require real source evidence and explicit semantics."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile
import pytest

from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.shared.data.documents import DocumentBlock,DocumentExtract,document_snapshot,document_from_snapshot
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.reference.geography.editions import TerritoryEdition,TerritoryUnit
from stratbox.core.formats.spreadsheets.extracts import extract_workbook
from stratbox.domains.rosstat.tables.contracts import CellBinding,ReviewedTableProfile
from stratbox.domains.rosstat.tables.documents import DocumentTableRegion,ReviewedDocumentLayout,structure_document
from stratbox.domains.rosstat.tables.mapping import map_reviewed_cells
from stratbox.domains.rosstat.tables.snapshots import flake_snapshot,flake_from_snapshot
from stratbox.domains.rosstat.integration.datasets import integrate_flakes
from stratbox.domains.rosstat.operations import handlers as H
from stratbox.domains.rosstat.operations.contracts import PayloadRequest,MembersRequest,PhysicalRequest,MapCellsRequest
from stratbox.domains.rosstat.publications.discovery.families.rules import parse_issue
from stratbox.domains.rosstat.publications.discovery.families.short_term_indicators import RULE
from stratbox.domains.rosstat.publications.discovery.families.population_municipalities import RULE as POPULATION


def _workbook_bytes():
    openpyxl=pytest.importorskip("openpyxl")
    w=openpyxl.Workbook();s=w.active;s.title="Population"
    s.append(("Code","Population"));s.append(("01000000",123))
    stream=BytesIO();w.save(stream)
    return stream.getvalue()


def _binding(**changes):
    values=dict(source_locator="Population!B2",indicator_id="population",label="Population",unit="person",
        unit_literal="persons",quantity_kind="count",frequency="annual",period_start=date(2024,1,1),period_end=date(2024,1,1),
        geography_namespace="oktmo",geography_id="01000000",period_kind="as_of",sheet="Population",row=2,column=2,
        dimensions=(("geography_edition","2024"),),perimeter="municipality-a")
    values.update(changes)
    return CellBinding(**values)


def _edition():
    payload=SourcePayload(b"reviewed territory fixture","text/plain")
    return TerritoryEdition("fixture.territories","2024",(
        TerritoryUnit("oktmo","01000000","Municipality A","municipality",date(2023,1,1),date(2024,12,31),
            None,None,"municipality-a","fixture-row-1"),),(),(UsedInputReceipt.for_payload(payload,"territory_source"),),
        SnapshotCoverage("complete","One explicitly reviewed municipality."))


def test_population_requires_a_dated_territory_and_keeps_stock_date():
    w=extract_workbook(SourcePayload(_workbook_bytes()),series_id="rosstat.population_municipalities",issue_id="2024",asset_id="population_workbook")
    profile=ReviewedTableProfile("rosstat.population.fixture",1,w.series_id,w.source_identity,"review-fixture",(_binding(),),"One municipality.")
    with pytest.raises(ValueError,match="territory_reference_required"):
        map_reviewed_cells(w,profile)
    profile=replace(profile,territory_edition=_edition())
    flake=map_reviewed_cells(w,profile)
    assert flake.values[0].value==Decimal(123)
    assert flake.values[0].display_date==date(2024,1,1)
    assert flake_from_snapshot(flake_snapshot(flake))==flake
    assert any(receipt.role=="territory_edition" for receipt in flake.lineage)
    integrated=integrate_flakes((flake,),dataset_id="population",release_id="v1")
    row,=integrated.batch.observations
    assert row.period.kind=="as_of" and row.period.as_of==date(2024,1,1)
    assert row.subject.id=="01000000" and dict(row.dimensions)["geography_edition"]=="2024"
    assert row.perimeter=="municipality-a"
    with pytest.raises(ValueError,match="territory_date_unresolved"):
        map_reviewed_cells(w,replace(profile,bindings=(_binding(period_start=date(2025,1,1),period_end=date(2025,1,1)),)))
    with pytest.raises(ValueError,match="perimeter_mismatch"):
        map_reviewed_cells(w,replace(profile,bindings=(_binding(perimeter="different_boundary"),)))
    with pytest.raises(ValueError,match="profile_source_mismatch"):
        map_reviewed_cells(w,replace(profile,source_identity=ByteIdentity.of(b"different edition")))


def test_russia_pdf_page_text_requires_reviewed_structure_then_replays():
    source=SourcePayload(b"%PDF-1.7\nfixture original\n%%EOF","application/pdf")
    document=DocumentExtract("rosstat.socioeconomic_russia","2024-01","report",source.identity,"pdf","document.blocks.v1",1,
        (DocumentBlock(0,"page","Heading\nIndicator|January|Value\nTrade|2024-01|100,2\n1) Preliminary",1,(),"page:1"),),
        (UsedInputReceipt.for_payload(source,"source"),),SnapshotCoverage("partial","PDF page text only."))
    binding=_binding(source_locator="reviewed-trade:R2C3",sheet="",block_id="reviewed-trade",row=2,column=3,
        indicator_id="trade",label="Trade",unit="RUB",unit_literal="billion rubles",quantity_kind="flow",scale=Decimal(10)**9,
        frequency="monthly",period_kind="interval",period_start=date(2024,1,1),period_end=date(2024,1,31),
        geography_namespace="iso3166-1",geography_id="RU",dimensions=(),perimeter="publisher_russia")
    profile=ReviewedTableProfile("rosstat.russia.fixture",1,document.series_id,source.identity,"review-fixture",(binding,),"One reviewed PDF table.")
    with pytest.raises(ValueError,match="profile_block_missing"):
        map_reviewed_cells(document,profile)
    layout=ReviewedDocumentLayout("rosstat.russia.layout.fixture",1,source.identity,"review-fixture",
        (DocumentTableRegion(0,"reviewed-trade",2,3,3,separator="|"),))
    structured=structure_document(document,layout)
    assert structured.blocks[0]==document.blocks[0]
    assert structured.coverage.status=="partial"
    restored=document_from_snapshot(document_snapshot(structured))
    flake=map_reviewed_cells(restored,profile)
    assert flake.values[0].value==Decimal("100.2")
    assert flake.values[0].unit=="RUB" and flake.values[0].scale==Decimal(10)**9
    with pytest.raises(ValueError,match="region_width_mismatch"):
        structure_document(document,replace(layout,regions=(DocumentTableRegion(0,"bad",2,3,4,separator="|"),)))
    with pytest.raises(ValueError,match="reviewed_layout_required"):
        structure_document(document,replace(layout,source_identity=ByteIdentity.of(b"other")))


def test_regional_archive_selection_retains_exact_container_and_member():
    stream=BytesIO()
    with ZipFile(stream,"w") as archive:
        archive.writestr("tables/population.xlsx",_workbook_bytes())
        archive.writestr("notes.txt","Not a statistical table")
    identity=SourceAssetIdentity("rosstat.socioeconomic_regions","2024-01","regional_archive")
    payload=SourcePayload(stream.getvalue(),"application/zip",identity.source_id)
    inventory=H.inspect_archive(PayloadRequest(payload))
    assert inventory.outcome=="succeeded",inventory.diagnostics
    result=H.extract_members(MembersRequest(payload,inventory.value,("tables/population.xlsx",)))
    assert result.outcome=="succeeded",result.diagnostics
    member,=result.value
    assert member.container_identity==payload.identity and member.lineage[-1].member==member.name
    missing=H.extract_workbook(PhysicalRequest(member.payload,identity.series_id,identity.issue_id,identity.asset_id))
    assert missing.outcome=="failed" and missing.diagnostics[0].code=="rosstat.regional_member_lineage_required"
    physical=H.extract_workbook(PhysicalRequest(member.payload,identity.series_id,identity.issue_id,identity.asset_id,payload.identity,member.name))
    assert physical.outcome=="succeeded",physical.diagnostics
    receipt=next(r for r in physical.value.lineage if r.role=="archive_member")
    assert receipt.container==payload.identity and receipt.identity==member.payload.identity
    profile=ReviewedTableProfile("rosstat.regions.fixture",1,identity.series_id,member.payload.identity,"review-fixture",
        (_binding(geography_namespace="iso3166-1",geography_id="RU",dimensions=(),perimeter="publisher_scope"),),"Selected regional archive table.")
    mapped=H.map_reviewed_cells(MapCellsRequest(physical.value,profile))
    assert mapped.outcome=="succeeded",mapped.diagnostics
    assert mapped.value.lineage[-1].container==payload.identity
    bad=H.extract_members(MembersRequest(SourcePayload(b"other"),inventory.value,(member.name,)))
    assert bad.outcome=="failed"
    from stratbox.core.formats.archives.members import ArchiveLimits
    limited=H.inspect_archive(PayloadRequest(payload,ArchiveLimits(packed_bytes=1)))
    assert limited.outcome=="failed" and limited.diagnostics[0].code=="archive.size_limit"


def test_named_issue_periods_and_historical_years_are_not_observation_dates():
    assert parse_issue(RULE,"book.xlsx","Январь — сентябрь 2026 года")[0]=="2026-09"
    assert parse_issue(RULE,"2026-08.xlsx","Сентябрь 2026 года")[0] is None
    assert parse_issue(POPULATION,"BUL_MO_1999.xlsx","Численность населения")[0]=="1999"
