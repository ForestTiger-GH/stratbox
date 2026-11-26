"""Source identity and exact coordinate semantics survive the clean domain seam."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest

from stratbox.domains.frank_rg.domain import DOMAIN
from stratbox.domains.frank_rg.common.naming import canonical_filename
from stratbox.domains.frank_rg.methods import publications, tables
from stratbox.domains.frank_rg.methods.publications import DeliverySettings, recognize
from stratbox.domains.frank_rg.methods.tables import CellAnchor, CellRule, TableRules
from stratbox.shared.data.values import Material, SourceClaim, WorkbookEvidence
from .names import SUPPLIER_NAMES


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def workbook(value="123.456789012345678901234567890", source_id="frg.express.issuance"):
    from openpyxl import Workbook
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    book = Workbook()
    sheet = book.active
    sheet.title = "Supplied layout"
    sheet.append(("Subject", "Reported amount"))
    sheet.append(("Fixture bank", value))
    sheet.append(("Other bank", "-"))
    sheet.merge_cells("D1:E1")
    data = BytesIO()
    book.save(data)
    material = Material(data.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", source_id,
        metadata={"issue_id": "2026-05-01", "format": "xlsx"})
    return WorkbookEvidence(material, read_workbook_cells(material.data))


def rules_for(physical, source_id):
    return TableRules(source_id, (
        CellRule("Supplied layout", 2, 2, "fixture.amount", "fixture", "RUB", "stock", "2026-04-30", "monthly", "fixture_bank_population", subject_namespace="bank"),
        CellRule("Supplied layout", 3, 2, "fixture.amount", "other", "RUB", "stock", "2026-04-30", "monthly", "fixture_bank_population", subject_namespace="bank"),
    ), original_identity=physical.material.identity)


def test_catalog_is_static_immutable_and_does_not_claim_fabricated_publisher_layouts():
    assert set(DOMAIN.series) == {source for source, _ in SUPPLIER_NAMES}
    assert len(DOMAIN.series) == 14
    with pytest.raises(TypeError):
        DOMAIN.series["new"] = None
    assert "publisher_layouts" in DOMAIN.common["scientific_obligations"]
    assert all(not series.semantics.settings["reviewed_business_layout"] for series in DOMAIN.series.values())


@pytest.mark.parametrize("source_id,name", SUPPLIER_NAMES)
def test_supplier_and_canonical_names_resolve_same_continuing_source(source_id, name):
    rule, period, format, problem = recognize(name)
    assert problem is None and rule.source_id == source_id
    canonical = canonical_filename(period, rule, format)
    second, same_period, same_format, problem = recognize(canonical)
    assert problem is None and second.source_id == source_id and same_period == period and format == same_format


@pytest.mark.parametrize("week", (0, 7, 99))
def test_invalid_weeks_are_not_ranked_as_publications(week):
    _, period, _, diagnostic = recognize(f"FRG. Экспресс-мониторинг рынка. Выдачи. Май 2026 {week} неделя.xlsx")
    assert period is None and diagnostic == "publication_period_unresolved"


def test_names_require_whole_phrases_and_reviewed_regional_scope():
    assert recognize("FRG. random letters x p r i. 2026-05-01.xlsx")[0] is None
    assert recognize("FRG. Региональные данные. Выдачи. 2026-03-01.xlsx")[3] == "period_before_reviewed_name_scope"
    assert recognize("FRG. Retail banking market. Volumes. 2026-05-01.xlsx")[0] is None


def test_listing_selection_keeps_competing_same_period_materials_and_week_order():
    weekly = DeliverySettings("frg.express.issuance_weekly")
    names = ("FRG. Экспресс-мониторинг рынка. Выдачи. Апрель 2026 5 неделя.xlsx",
             "FRG. Экспресс-мониторинг рынка. Выдачи. Май 2026 1 неделя.xlsx")
    inventory = tuple({"path": "/delivery/" + name, "filename": name, "size": 10, "mtime": 1} for name in names)
    listing = publications.scan({"index": inventory}, weekly, context())["listing"]
    selected = publications.select({"listing": listing}, weekly, context())["selection"]
    assert selected.entries[0].issue_id == "2026-05 week 1"
    duplicate = replace(listing.entries[0], locator="/another.xlsx")
    ambiguous = publications.select({"listing": replace(listing, entries=(listing.entries[0], duplicate))}, weekly, context())["selection"]
    assert ambiguous.assessment.status == "unknown" and len(ambiguous.entries) == 2
    metadata = publications.assess({"evidence": listing, "baseline": listing}, weekly, context())["assessment"]
    assert metadata.status == "indeterminate" and metadata.basis == "delivered_metadata_only"


@pytest.mark.parametrize("source_id", tuple(DOMAIN.series))
def test_exact_supplied_rules_work_for_each_identity_without_builtin_layout_claim(source_id):
    physical = workbook(source_id=source_id)
    explicit = rules_for(physical, source_id)
    defaults = TableRules(source_id)
    ctx = context(table_rules=explicit)
    selected = tables.extract({"physical": physical}, defaults, ctx)["tables"]
    dataset = tables.interpret({"tables": selected}, defaults, ctx)["dataset"]
    assert physical.workbook.sheets[0].merged_ranges == ("D1:E1",)
    assert dataset.rows[0]["value"] == Decimal("123.456789012345678901234567890")
    assert dataset.rows[1]["value"] is None and dataset.rows[1]["value_status"] == "dash"
    assert dataset.rows[0]["period"] == "2026-04-30"
    assert dataset.rows[0]["source_sheet"] == "Supplied layout"
    assert "caller_supplied_exact_material_rules" in dataset.assessment.qualifications
    aligned = tables.align({"dataset": dataset}, defaults, ctx)["dataset"]
    assert aligned.rows == dataset.rows and aligned.source_uses == dataset.source_uses
    use, = dataset.source_uses
    assert use.coordinate.source_id == source_id
    assert use.coordinate.issue_id == "2026-05-01"
    assert use.coordinate.material_identity == physical.material.identity
    assert use.qualification == "caller_supplied_exact_material_rules"
    from stratbox.core.commands.standard import value_decode, value_encode
    encoded = value_encode({"value": aligned}, None, context())["representation"]
    assert value_decode({"representation": encoded}, None, context())["value"] == aligned


def test_unreviewed_builtin_semantics_and_wrong_bytes_or_source_are_rejected():
    physical = workbook()
    defaults = TableRules("frg.express.issuance")
    selected = tables.extract({"physical": physical}, defaults, context())["tables"]
    assert selected.assessment.status == "unknown"
    with pytest.raises(ValueError, match="reviewed_table_rules_required"):
        tables.interpret({"tables": selected}, defaults, context())
    with pytest.raises(ValueError, match="material_conflict"):
        tables.extract({"physical": workbook("10")}, defaults, context(table_rules=rules_for(physical, defaults.source_id)))
    with pytest.raises(ValueError, match="source_conflict"):
        tables.extract({"physical": physical}, TableRules("frg.express.passives"), context())


def test_supplied_rule_geometry_anchor_period_and_precision_checks():
    physical = workbook()
    rules = rules_for(physical, "frg.express.issuance")
    shape = tuple((sheet.name, sheet.rows, sheet.columns) for sheet in physical.workbook.sheets)
    reviewed = replace(rules, sheet_shapes=shape, anchors=(CellAnchor("Supplied layout", 1, 2, "Reported amount"),),
        reviewed_originals=(physical.material.identity,), review_evidence="Synthetic test scope only")
    selected = tables.extract({"physical": physical}, reviewed, context())["tables"]
    assert "reviewed_layout" in tables.interpret({"tables": selected}, reviewed, context())["dataset"].assessment.qualifications
    with pytest.raises(ValueError, match="anchor_mismatch"):
        tables.extract({"physical": physical}, replace(reviewed, anchors=(CellAnchor("Supplied layout", 1, 2, "Wrong"),)), context())
    with pytest.raises(ValueError, match="stock_date_required"):
        replace(rules.cells[0], period=("2026-01-01", "2026-01-31"))
    with pytest.raises(ValueError, match="flow_interval_required"):
        replace(rules.cells[0], measure_kind="flow")
    with pytest.raises(ValueError, match="duplicate_semantic_key"):
        duplicate = replace(rules.cells[1], subject=rules.cells[0].subject)
        custom = replace(rules, cells=(rules.cells[0], duplicate))
        tables.interpret({"tables": selected}, custom, context())


def test_identification_and_exact_changes_do_not_overwrite_known_provenance():
    material = Material(b"one", source_id="frg.express.issuance")
    settings = DeliverySettings("frg.express.issuance")
    result = publications.identify({"material": material, "claim": SourceClaim(settings.source_id, "2026-05-01")}, settings, context())
    assert result["material"].material is material
    with pytest.raises(ValueError, match="source_conflict"):
        publications.identify({"material": replace(material, source_id="frg.express.passives"), "claim": SourceClaim(settings.source_id, "2026-05-01")}, settings, context())
    assert publications.assess({"evidence": material, "baseline": material}, settings, context())["assessment"].status == "unchanged"
    assert publications.assess({"evidence": Material(b"two"), "baseline": material}, settings, context())["assessment"].status == "changed"
    assert publications.assess({"evidence": material}, settings, context())["assessment"].status == "first_seen"


def test_physical_cells_cannot_claim_a_different_original():
    physical = workbook()
    altered = replace(physical, material=replace(physical.material, data=b"unrelated original"))
    with pytest.raises(ValueError, match="physical_material_identity_conflict"):
        tables.extract({"physical": altered}, TableRules("frg.express.issuance"), context())


def test_standard_sdk_route_accepts_explicit_rules_and_retains_their_qualification():
    from stratbox.capabilities.catalog.domains import DomainCatalog
    from stratbox.capabilities.model.targets import SeriesTarget
    from stratbox.sdk import StrategyBox
    physical = workbook()
    source = "frg.express.issuance"
    with StrategyBox(domains=DomainCatalog({"frank_rg": DOMAIN})) as box:
        result = box.invoke("operation.series.extract_workbook", inputs={"physical": physical},
            parameters={"table_rules": rules_for(physical, source)}, target=SeriesTarget(source), timeout=10)
        assert result.outcome == "succeeded", result.diagnostics
        dataset = result.output("dataset")
        assert dataset.rows[0]["value"] == Decimal("123.456789012345678901234567890")
        use, = dataset.source_uses
        assert use.qualification == "caller_supplied_exact_material_rules"
        assert use.coordinate.material_identity == physical.material.identity


def test_identified_material_carries_its_known_issue_into_workbook_interpretation():
    from stratbox.capabilities.catalog.domains import DomainCatalog
    from stratbox.capabilities.model.targets import SeriesTarget
    from stratbox.sdk import StrategyBox
    physical = workbook()
    source = "frg.express.issuance"
    neutral = replace(physical.material, source_id=None, metadata={})
    target = SeriesTarget(source)
    with StrategyBox(domains=DomainCatalog({"frank_rg": DOMAIN})) as box:
        identified = box.invoke("command.material.identify", inputs={"material": neutral,
            "claim": SourceClaim(source, "2026-05-01")}, target=target).output("material")
        result = box.invoke("operation.series.extract_workbook", inputs={"material": identified},
            parameters={"table_rules": rules_for(physical, source)}, target=target, timeout=10)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("dataset").issue_id == "2026-05-01"
        assert result.output("dataset").source_uses[0].coordinate.source_id == source
