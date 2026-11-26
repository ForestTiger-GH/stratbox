"""Static FNS declarations and scientific methods through standard value contracts."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from stratbox.core.commands.standard import json_decode, workbook_decode
from stratbox.domains.fns.domain import DOMAIN
from stratbox.domains.fns.common.publications import LEGAL_PUBLICATION, SME_PUBLICATION
from stratbox.domains.fns.common.semantics import LEGAL_RULES, SME_RULES
from stratbox.domains.fns.methods import legal_entities, publications, sme
from stratbox.shared.data.values import AssetSelection, JsonEvidence, Material, PublicationAsset
from .fixtures import FORM_EPOCHS, encoded, fixture, form_workbook


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def sme_value(day=date(2026, 11, 10), *, payload=None):
    material = Material(payload or encoded(fixture(day)), "application/json", "fns.sme")
    ctx = context(as_of=day.isoformat())
    physical = json_decode({"material": material}, None, ctx)["physical"]
    tables = sme.select_records({"physical": physical}, SME_RULES, ctx)["tables"]
    return sme.interpret_counters({"tables": tables}, SME_RULES, ctx)["dataset"]


def test_catalog_is_exact_immutable_and_every_method_resolves():
    assert set(DOMAIN.series) == {"fns.sme", "fns.1yur"}
    with pytest.raises(TypeError):
        DOMAIN.series["invented"] = None
    for series in DOMAIN.series.values():
        for identifier, specification in series.commands.items():
            assert identifier.startswith("command.")
            assert callable(specification.method.resolve())
    assert not any("profile" in field for field in DOMAIN.__dataclass_fields__)


def test_readonly_post_and_asset_locator_preserve_the_published_date():
    asset = PublicationAsset("fns.sme", "2026-11-10", "statistics", SME_PUBLICATION.data_url, "json")
    request = publications.prepare_request({"locator": asset}, SME_PUBLICATION, context(role="asset"))["request"]
    assert request.method == "POST" and request.read_only
    assert dict(request.form) == {"statDate": "10.11.2026"}
    assert request.metadata["issue_id"] == "2026-11-10"
    index = publications.prepare_request({}, SME_PUBLICATION, context(role="index"))["request"]
    assert index.method == "GET" and index.url == SME_PUBLICATION.index_url


def test_legal_asset_request_is_dated_get_and_rejects_wrong_source():
    asset = PublicationAsset("fns.1yur", "2026-11-01", "main", "https://www.nalog.gov.ru/files/docs/gosreg/release.xlsx", "xlsx")
    request = publications.prepare_request({"locator": asset}, LEGAL_PUBLICATION, context(role="asset"))["request"]
    assert request.method == "GET" and request.form is None
    with pytest.raises(ValueError, match="source_mismatch"):
        publications.prepare_request({"locator": replace(asset, source_id="fns.sme")}, LEGAL_PUBLICATION, context())


def test_sme_all_present_counters_levels_and_unknown_fields_have_exact_coverage():
    values = fixture(count=3)
    values[0]["unknown"] = {"nested": True}
    dataset = sme_value(payload=encoded(values))
    assert {row["subject_namespace"] for row in dataset.rows} == {"fns.ssrf", "fns.sme.country"}
    assert len([row for row in dataset.rows if row["geographic_level"] == 0]) == 3 * 9
    assert any("unmapped_field:unknown" in item for item in dataset.assessment.findings)
    assert dataset.assessment.status == "partial"
    aligned = sme.align_observations({"dataset": dataset}, SME_RULES, context())["dataset"]
    assert {row["metric"] for row in aligned.rows} >= {"total", "ul_total", "ip_total"}
    assert all(row["measure_kind"] == "stock" for row in aligned.rows)


def test_json_types_and_numeric_lexemes_are_physical_evidence_not_coerced_values():
    ctx = context()
    physical = json_decode({"material": Material(b'[{"n":1.2300e+2,"s":"101"}]')}, None, ctx)["physical"]
    assert physical.value[0]["n"] == Decimal("123.00")
    assert physical.tokens[(0, "n")] == "1.2300e+2"
    assert physical.value[0]["s"] == "101"


@pytest.mark.parametrize("damage", [
    lambda values: values[0].update(stat_date="09.11.2026 00:00:00"),
    lambda values: values[-1].update(cnt_total=True),
    lambda values: values[-1].update(cnt_total=999),
    lambda values: values.append(dict(values[-1])),
])
def test_sme_rejects_date_boolean_total_and_duplicate_contradictions(damage):
    values = fixture(count=3)
    damage(values)
    with pytest.raises(ValueError):
        sme_value(payload=encoded(values))


@pytest.mark.parametrize("day,source_epoch,indicators,kinds", FORM_EPOCHS)
def test_historical_legal_fields_use_cells_and_preserve_source_perimeter(day, source_epoch, indicators, kinds):
    ctx = context(as_of=day.isoformat())
    physical = workbook_decode({"material": Material(form_workbook(indicators, kinds, legacy=source_epoch == "A"))}, None, ctx)["physical"]
    tables = legal_entities.select_tables({"physical": physical}, LEGAL_RULES, ctx)["tables"]
    dataset = legal_entities.interpret({"tables": tables}, LEGAL_RULES, ctx)["dataset"]
    aligned = legal_entities.align({"dataset": dataset}, LEGAL_RULES, ctx)["dataset"]
    assert len(dataset.rows) > 100
    assert {row["perimeter"] for row in dataset.rows} == {"published_national", "published_district", "published_territory"}
    assert any(row["metric"] == "not_ceased" and row["measure_kind"] == "stock" for row in aligned.rows)
    ceased = [row for row in aligned.rows if row["metric"] == "ceased_bankruptcy_liquidation"]
    assert ceased and all(row["measure_kind"] == "count" for row in ceased)
    assert all(row["time_basis"] == "published_reporting_date_unspecified_accumulation" for row in ceased)
    assert all("#member=" in row["evidence_ref"] and "cell=" in row["evidence_ref"] for row in dataset.rows)
    if source_epoch == "B":
        assert not any(row["source_legal_kind"] == "1023" for row in aligned.rows)


def test_json_physical_source_conflict_does_not_change_requested_series():
    physical = JsonEvidence(Material(b"[]", source_id="fns.1yur"), ({},))
    with pytest.raises(ValueError, match="source_mismatch"):
        sme.select_records({"physical": physical}, SME_RULES, context())


def test_legal_part_two_cannot_masquerade_as_part_one():
    assert legal_entities._selected_member(("release_I.xlsx", "release_II.xlsx")) == "release_I.xlsx"
    with pytest.raises(ValueError, match="PART_II"):
        legal_entities._selected_member(("release_II.xlsx",))


def test_standard_archive_recipe_selects_part_one_after_decoding_workbook_collection():
    from stratbox.core.formats.archives.members import zip_bytes
    from stratbox.sdk import StrategyBox
    day, _, indicators, kinds = FORM_EPOCHS[-1]
    data = form_workbook(indicators, kinds)
    original = Material(zip_bytes({"release_I.xlsx": data, "release_II.xlsx": data,
        "readme.txt": b"Publication companion"}), "application/zip", "fns.1yur")
    with StrategyBox() as box:
        result = box.invoke("operation.series.extract_archive", target="fns.1yur",
            inputs={"material": original, "issue": {"as_of": day.isoformat()}},
            parameters={"format": "zip", "as_of": day.isoformat()})
        assert result.outcome == "succeeded", result.diagnostics
        value = result.output("dataset")
        assert value.rows and all("member=release_I.xlsx" in row["evidence_ref"] for row in value.rows)
        assert any("release_II.xlsx" in finding for finding in value.assessment.findings)
        assert value.source_uses[0].coordinate.issue_id == day.isoformat()


def test_reviewed_sparse_2019_release_retains_geography_and_excluded_kind_evidence():
    from io import BytesIO
    import openpyxl
    from stratbox.domains.fns.common.mappings import KINDS
    kinds = tuple(KINDS)[:33]
    book = openpyxl.load_workbook(BytesIO(form_workbook((1, 12), " ".join(kinds))))
    for kind in kinds:
        sheet = book[kind]
        row = next(index for index in range(1, sheet.max_row + 1) if sheet.cell(index, 1).value == "53")
        sheet.cell(row, 2, "Новгородская область")
        if kind != "1000":
            sheet.delete_rows(row)
    output = BytesIO()
    book.save(output)
    ctx = context(as_of="2019-06-01")
    physical = workbook_decode({"material": Material(output.getvalue())}, None, ctx)["physical"]
    tables = legal_entities.select_tables({"physical": physical}, LEGAL_RULES, ctx)["tables"]
    value = legal_entities.interpret({"tables": tables}, LEGAL_RULES, ctx)["dataset"]
    assert {row["source_legal_kind"] for row in value.rows} == {"1000"}
    assert len(value.semantics["coverage"]["excluded_incomplete_kind_sheets"]) == 32
    assert len(tables.tables[0].sheets) > 33
    with pytest.raises(ValueError):
        legal_entities.interpret({"tables": tables, "issue": "2019-07-01"}, LEGAL_RULES, ctx)


def test_source_dataset_roundtrip_preserves_native_fields_exact_values_and_evidence():
    from stratbox.core.commands.standard import value_decode, value_encode
    value = sme_value()
    encoded_value = value_encode({"value": value}, None, context())["representation"]
    replay = value_decode({"representation": encoded_value}, None, context())["value"]
    assert replay == value and replay.identity == value.identity
    assert replay.assessment == value.assessment
    assert replay.source_uses == value.source_uses and value.source_uses
    use = replay.source_uses[0]
    assert use.qualification == "domain_validated"
    assert use.coordinate.source_id == "fns.sme" and use.coordinate.issue_id == "2026-11-10"
    assert len(use.coordinate.layout_identity) == len(use.coordinate.semantic_identity) == 64
    assert use.coordinate.material_identity in value.lineage


def test_stock_change_never_promotes_unknown_event_accumulation_to_stock():
    from stratbox.core.commands.standard import calculate_change
    from stratbox.core.execution.service import ExecutionFailure
    from stratbox.domains.fns.calculations.rules import STOCK_CHANGE
    from stratbox.shared.data.values import SourceDataset
    before = sme_value(date(2026, 10, 10))
    after = sme_value(date(2026, 11, 10))
    history = SourceDataset("fns.sme", (*before.rows, *after.rows))
    result = calculate_change({"observations": history}, STOCK_CHANGE.settings, context())["dataset"]
    assert result.rows and all(row["value"] == 0 for row in result.rows)
    assert all(row["measure_kind"] == "net_change" and row["period_kind"] == "interval"
        and row["period"] == ("2026-10-10", "2026-11-10") for row in result.rows)
    unresolved = replace(history, rows=tuple({**row, "measure_kind": "count"} for row in history.rows))
    with pytest.raises(ExecutionFailure, match="measure_kind_mismatch"):
        calculate_change({"observations": unresolved}, STOCK_CHANGE.settings, context())
