"""Exact fiscal command graphs, retained results and explicit DOC conversion."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path

import pytest

from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.domains.minfin.capabilities import contribution, dispositions, stage_matrix
from stratbox.domains.minfin.publications.catalog import families
from stratbox.domains.minfin.publications.context import PublicationContext
from stratbox.sdk import StrategyBox
from stratbox.shared.evidence import SourcePayload


def catalog():
    base = catalog_snapshot()
    if any(d.capability_id == "minfin.extract" for d in base.definitions):
        return base
    return base.overlay(contribution())


def invoke(box, capability, **options):
    result = box.invoke(capability, timeout=20, **options)
    assert result.outcome == "succeeded", [(k, v.outcome, v.diagnostics) for k,v in result.results.items()]
    return result.output("value")


def workbook(series, family):
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Fiscal"
    periods = {"monthly": ("2025-10", "2026-10"), "quarterly": ("3 кв. 2025", "3 кв. 2026"), "annual": ("2025", "2026")}[series.periodicity]
    sheet.append(("Code", "Indicator", *periods))
    if family.family_id == "minfin.nwf":
        rows = (("2", "Объем на конец периода", 100, 130),
                ("5", "Размещено в иные разрешенные активы на конец периода", 30, 40),
                ("7", "Dollar asset requiring its own unit mapping", 2, 3))
    else:
        rows = (("1", "Доходы, всего", 100, 110), ("2", "Расходы, всего", 120, 135),
                ("3", "Дефицит (-)/Профицит (+)", -20, -25))
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    book.save(stream)
    return SourcePayload(stream.getvalue(), source_id=series.source_id)


TABLE_SERIES = tuple((f,s) for f in families() for s in f.series if s.kind == "table")


def test_every_declared_stage_has_canonical_disposition_and_metadata_remains_lightweight():
    expected = {json.loads(p.read_text())["definition"]["operation_id"] for p in
        Path("src/stratbox/operations/specifications/domains/minfin/operations").glob("*.yaml")}
    assert len(expected) == 34
    assert expected <= dispositions().keys()
    definitions = {d.capability_id: d for d in contribution().definitions}
    assert all(dispositions()[key]["kind"] == definitions[key].kind for key in expected)
    assert len(stage_matrix()) == 13
    assert len(contribution().profiles) == 36
    snap = catalog()
    for family in families():
        for series in family.series:
            recipe = snap.resolve_goal("source.extract", selection={"source_id": series.source_id})
            assert recipe.capability_id in definitions
    assert definitions["minfin.capture"].kind == "scenario"
    assert all("operations.handlers" not in d.implementation_ref and "document_handlers" not in d.implementation_ref
        for d in definitions.values() if d.kind == "command")


@pytest.mark.parametrize("family,series", TABLE_SERIES, ids=[s.source_id for _,s in TABLE_SERIES])
def test_all_ten_fiscal_series_run_exact_stages_with_period_and_unit_semantics(family, series):
    payload = workbook(series, family)
    publication = PublicationContext(series.source_id, "edition-42", "annex", date(2026,11,12), date(2026,11,13), "42", "https://minfin.gov.ru/example")
    with StrategyBox(capabilities=catalog()) as box:
        plan = box.prepare("minfin.extract", inputs={"payload": payload}, parameters={"family_id": family.family_id, "format": "xlsx", "publication": publication})
        assert all(task.operation_id.startswith("minfin.stage.") for task in plan.tasks if task.operation_id)
        extracted = box.run(plan, timeout=20).output("value")
        assert extracted.source_identity == payload.identity
        assert extracted.publication == publication
        validation=invoke(box,"minfin.validate",inputs={"extract":extracted})
        assert validation.level=="structural_only" and validation.sheets==1
        physical=invoke(box,"minfin.serialize",inputs={"extract":extracted})
        assert invoke(box,"minfin.read_representation",inputs={"representation":physical})==extracted
        flake = invoke(box, "minfin.build_flake", inputs={"extract": extracted}, parameters={"source_id": series.source_id})
        assert (flake.frequency, flake.value_basis) == (series.periodicity, series.basis)
        batch = invoke(box, "minfin.integrate", inputs={"flake": flake}, parameters={"dataset_id": "fiscal.reviewed", "release_id": "edition-42"})
        assert all(o.metric.unit == "RUB" and o.metric.scale == Decimal("1e9") for o in batch.observations)
        if series.basis == "stock":
            assert all(o.period.kind == "as_of" for o in batch.observations)
            # Row seven remains physical evidence, without receiving a RUB unit.
            assert flake.rows[2].unit is None
        else:
            assert all(o.period.kind == "interval" and o.period.start.month == 1 for o in batch.observations)
        retained = invoke(box, "minfin.observation_snapshot", inputs={"batch": batch})
        assert invoke(box, "minfin.read_observations", inputs={"snapshot": retained}) == batch
        product = box.invoke("minfin.table_product", inputs={"extract": extracted}, parameters={"source_id": series.source_id,
            "dataset_id": "fiscal.reviewed", "release_id": "edition-42", "view_id": "headline"}, timeout=20)
        assert product.outcome == "succeeded", [(k,v.diagnostics) for k,v in product.results.items()]
        assert product.output("observations") == batch
        assert b"metric" in product.output("value").data


def document_bytes():
    from docx import Document
    doc = Document()
    doc.add_paragraph("NWF reviewed layout edition A")
    table = doc.add_table(rows=3, cols=3)
    for cells, vals in zip(table.rows, (("Assets", "RUB", "USD"), ("Fund assets", "0", "12,5"), ("Unavailable", "—", ""))):
        for cell,value in zip(cells.cells, vals):
            cell.text = value
    doc.add_paragraph("Source note: explicit currencies and stock date.")
    stream = BytesIO()
    doc.save(stream)
    return stream.getvalue()


def reviewed_profile(series_id):
    from stratbox.domains.minfin.integration.document_observations import DocumentField, DocumentInterpretationProfile
    from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
    def field(row, column, metric_id, currency, label):
        return DocumentField(1,row,column,MetricRef(metric_id,currency,"stock","reviewed.A",Decimal(1)),
            PeriodRef("as_of",as_of=date(2026,10,31)),SubjectRef("geography","RU"),"nwf_assets",label)
    return DocumentInterpretationProfile("minfin.document.reviewed.A", "1", series_id,
        (field(1,1,"fund.rubles","RUB","Fund assets"),field(1,2,"fund.dollars","USD","Fund assets"),
         field(2,1,"fund.unavailable","RUB","Unavailable")), ("NWF reviewed layout edition A", "Source note:"))


@pytest.mark.parametrize("series_id", ["minfin.nwf.volume", "minfin.nwf.preferred_shares", "minfin.nwf.veb_deposits"])
def test_document_routes_preserve_order_and_reviewed_mixed_units_without_source_reacquisition(series_id):
    converted = document_bytes()
    publication = PublicationContext(series_id,"issue-A","main",date(2026,11,12),date(2026,11,13),"publisher-A","https://minfin.gov.ru/example")
    class Converter:
        provider_id, revision = "controlled.fixture", "1"
        calls = 0
        def convert(self,payload,*,target_format,max_bytes,checkpoint):
            self.calls += 1
            assert payload.data == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1exact original DOC fixture"
            assert target_format == "docx" and max_bytes >= len(converted)
            checkpoint()
            return SourcePayload(converted,"application/vnd.openxmlformats-officedocument.wordprocessingml.document",source_id=payload.source_id)
    converter = Converter()
    legacy = series_id.endswith("veb_deposits")
    payload = SourcePayload(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1exact original DOC fixture" if legacy else converted,source_id=series_id)
    with StrategyBox(capabilities=catalog(),providers={"document_converter": converter}) as box:
        value = invoke(box,"minfin.legacy_document" if legacy else "minfin.extract_document",inputs={"payload":payload},
            parameters={"family_id":"minfin.nwf","publication":publication})
        assert tuple(block.kind for block in value.document.blocks)==("paragraph","table","paragraph")
        retained = invoke(box,"minfin.document_snapshot",inputs={"document":value})
        replay = invoke(box,"minfin.read_document",inputs={"snapshot":retained})
        assert replay == value and replay.publication == publication
        if legacy:
            assert converter.calls == 1
            assert value.document.source_identity != payload.identity
            assert {i.identity for i in value.document.lineage} == {payload.identity,SourcePayload(converted).identity}
        batch = invoke(box,"minfin.document_observations",inputs={"document":replay},parameters={"profile":reviewed_profile(series_id),"dataset_id":"nwf.reviewed","release_id":"A"})
        assert [row.value_status for row in batch.observations]==["reported","reported","dash"]
        assert [row.value for row in batch.observations]==[Decimal(0),Decimal("12.5"),None]
        assert [row.metric.unit for row in batch.observations]==["RUB","USD","RUB"]
        assert all(row.period.as_of==date(2026,10,31) for row in batch.observations)
        wrong = replace(reviewed_profile(series_id),required_text=("Absent reviewed anchor",))
        rejected=box.invoke("minfin.document_observations",inputs={"document":replay},parameters={"profile":wrong,"dataset_id":"nwf.reviewed","release_id":"A"},timeout=20)
        assert rejected.outcome=="failed"
        assert converter.calls == int(legacy)


def test_legacy_conversion_requires_explicit_provider_and_checks_source_attribution():
    from stratbox.domains.minfin.documents.conversion import convert_legacy_document
    original=SourcePayload(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1fixture",source_id="minfin.nwf.veb_deposits")
    class WrongSource:
        provider_id,revision="test","1"
        def convert(self,payload,**options):
            return SourcePayload(document_bytes(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document",source_id="minfin.nwf.volume")
    with pytest.raises(ValueError,match="conversion_output_invalid"):
        convert_legacy_document(original,WrongSource())
    with StrategyBox(capabilities=catalog()) as box:
        plan=box.prepare("minfin.convert_document",inputs={"payload":original})
        result=box.run(plan,timeout=20)
        assert result.outcome=="failed"


def test_reviewed_layout_profile_changes_column_interpretation_and_pins_computation_identity():
    from dataclasses import asdict
    from stratbox.capabilities.catalog import CatalogContribution, ProfileDefinition
    from stratbox.domains.minfin.tables.profiles import table_profile
    from stratbox.domains.minfin.tables.contracts import Cell, Sheet, TableExtract
    from stratbox.shared.identity import ByteIdentity
    source_id = "minfin.fedbud.annex3.monthly"
    table = TableExtract("minfin.fedbud", source_id, ByteIdentity.of(b"alternate reviewed layout"), "xlsx",
        (Sheet("Budget", 2, 4, (Cell("Budget",1,1,"text","Indicator"),Cell("Budget",1,2,"text","Code"),
            Cell("Budget",1,3,"text","2025-10"),Cell("Budget",1,4,"text","2026-10"),
            Cell("Budget",2,1,"text","Доходы, всего"),Cell("Budget",2,2,"text","1"),
            Cell("Budget",2,3,"number","100"),Cell("Budget",2,4,"number","110"))),))
    layout=asdict(replace(table_profile("minfin.budget_table"),code_column=2,indicator_column=1))
    profile=ProfileDefinition("minfin.reviewed.alternate", {"source_id":source_id,"layout":layout},
        method_id="minfin.method.build_flake",group_id=source_id+".processing")
    snap=catalog().overlay(CatalogContribution(profiles=(profile,)))
    with StrategyBox(capabilities=snap) as box:
        plan=box.prepare("minfin.build_flake",inputs={"extract":table},profile_id=profile.profile_id)
        bound=plan.selected_bindings["minfin.build_flake"]
        assert bound["identities"]["profile"]==profile.fingerprint
        flake=box.run(plan,timeout=20).output("value")
        assert flake.rows[0].code=="1"
        assert flake.rows[0].indicator=="Доходы, всего"
        assert flake.rows[0].values==("100","110")


def test_document_validation_and_dataset_ingestion_replay_both_physical_and_integrated_values():
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    from stratbox.domains.minfin.documents.snapshots import document_from_dataset
    from stratbox.shared.data.observation_snapshots import observations_from_snapshot
    source_id="minfin.nwf.volume"
    store=MemoryDatasetStore(provider_id="controlled",scope_id="fiscal")
    payload=SourcePayload(document_bytes(),source_id=source_id)
    publication=PublicationContext(source_id,"A","main")
    with StrategyBox(capabilities=catalog(),providers={"dataset_writer":store,"dataset_reader":store}) as box:
        document=invoke(box,"minfin.extract_document",inputs={"payload":payload},parameters={"family_id":"minfin.nwf","publication":publication})
        validation=invoke(box,"minfin.validate_document",inputs={"document":document})
        assert validation.valid and validation.tables==1 and validation.cells==9
        reference=invoke(box,"minfin.ingest_document",inputs={"document":document})
        retained=invoke(box,"query.dataset",inputs={"reference":reference})
        assert document_from_dataset(retained)==document
        batch=invoke(box,"minfin.document_observations",inputs={"document":document},parameters={"profile":reviewed_profile(source_id),"dataset_id":"fiscal.reviewed","release_id":"A"})
        reference=invoke(box,"minfin.ingest_observations",inputs={"batch":batch})
        retained=invoke(box,"query.dataset",inputs={"reference":reference})
        assert observations_from_snapshot(retained)==batch


def test_document_ratio_uses_reviewed_fields_and_exact_pair_semantics():
    from docx import Document
    from stratbox.domains.minfin.integration.document_observations import DocumentField,DocumentInterpretationProfile
    from stratbox.shared.data.observations import MetricRef,SubjectRef,PeriodRef
    source_id="minfin.nwf.volume"
    source=Document()
    source.add_paragraph("NWF reviewed ratio layout")
    table=source.add_table(rows=2,cols=3)
    for row,fields in zip(table.rows,(("Total assets","RUB","25"),("Liquid assets","RUB","10"))):
        for cell,text in zip(row.cells,fields):cell.text=text
    stream=BytesIO();source.save(stream)
    def profile(row,metric,label):
        field=DocumentField(1,row,2,MetricRef(metric,"RUB","stock","ratio.layout.1",Decimal(1)),
            PeriodRef("as_of",as_of=date(2026,10,31)),SubjectRef("geography","RU"),"fund_assets",label)
        return DocumentInterpretationProfile("minfin."+metric,"1",source_id,(field,),("NWF reviewed ratio layout",))
    def operand(dataset,metric):
        return {"dataset_id":dataset,"metric_id":metric,"unit":"RUB","quantity_kind":"stock","definition_version":"ratio.layout.1","scale":"1"}
    pair={"id":"nwf.liquid_share","revision":"1","rationale":"Reviewed liquid asset stock divided by reviewed total asset stock in the same currency on the same date.",
        "numerator":operand("nwf.liquid","liquid"),"denominator":operand("nwf.total","total"),
        "result":{"metric_id":"nwf.liquid_share","unit":"ratio","quantity_kind":"ratio","scale":"1"},
        "period_policy":"equal","origin_policy":"common_material","release_policy":"same"}
    with StrategyBox(capabilities=catalog()) as box:
        document=invoke(box,"minfin.extract_document",inputs={"payload":SourcePayload(stream.getvalue(),source_id=source_id)},
            parameters={"family_id":"minfin.nwf","publication":PublicationContext(source_id,"A","main")})
        parameters={"numerator_profile":profile(1,"liquid","Liquid assets"),"denominator_profile":profile(0,"total","Total assets"),
            "numerator_dataset_id":"nwf.liquid","denominator_dataset_id":"nwf.total","release_id":"A","pair":pair}
        result=box.invoke("minfin.document_ratio",inputs={"numerator":document,"denominator":document},parameters=parameters,timeout=20)
        assert result.outcome=="succeeded",[(k,v.diagnostics) for k,v in result.results.items()]
        value=result.output("observations")
        assert value.observations[0].value==Decimal("0.4")
        assert "calculation.admitted" in value.evidence.qualifications
        bad={**pair,"denominator":{**pair["denominator"],"unit":"USD"}}
        rejected=box.invoke("minfin.document_ratio",inputs={"numerator":document,"denominator":document},parameters={**parameters,"pair":bad},timeout=20)
        assert rejected.outcome=="failed"


def test_all_minfin_required_stage_routes_resolve_to_actual_capabilities():
    required={"discover","acquire","inspect","preserve","extract","readable","read_extract","validate","compare","integrate","ingest","calculate","view","render","publish"}
    snap=catalog()
    for source in stage_matrix():
        assert required <= source["stages"].keys()
        assert all(snap.definition(source["stages"][stage]) for stage in required)
