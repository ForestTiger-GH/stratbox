"""Portable validation and historical display choices preserve scientific inputs."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from stratbox.domains.cbr.common.contracts import FamilySettings, SourceRequirement
from stratbox.domains.cbr.common.provenance import source_use
from stratbox.domains.cbr.methods.actions.industries import validate
from stratbox.domains.cbr.calculations.industry.actions import calculate, REQUIRED
from stratbox.domains.cbr.products import industry
from stratbox.shared.data.history import RevisionPolicy, resolve_revisions
from stratbox.shared.data.values import Material, SourceDataset

SOURCE = "cbr.corporate_lending.debt_0105a"
RULES = SourceRequirement(SOURCE, ("xlsx",), True)


def context(accepted=()):
    return SimpleNamespace(parameters={}, checkpoint=lambda: None,
        method_identity="fixture-industry-validator", build_identity="fixture-build",
        accepted_input=lambda name: {"produced_by": "command.table.interpret"},
        verify_validation_certificate=lambda certificate: certificate.identity in accepted)


def source_dataset(day, value):
    original = Material((day + ":" + str(value)).encode())
    row = {"subject_namespace": "cbr.published_region", "subject": "example", "metric": "published_total",
        "period": day, "period_kind": "as_of", "measure_kind": "stock", "perimeter": "CORPORATE_TOTAL",
        "unit": "RUB", "scale": Decimal(1000000), "value": Decimal(value), "value_status": "reported",
        "evidence_ref": "sha256:" + original.identity.sha256 + "#Sheet!A1", "dimensions": ()}
    # The fixture simulates the accepted output of the real source interpreter.
    return SourceDataset(SOURCE, (row,), {"source": "industry_debt"}, day,
        source_uses=(source_use(SOURCE, day, original.identity),),
        native=SimpleNamespace(validation_issues=()))


def test_history_uses_authoritative_per_issue_certificates_and_rejects_altered_rows():
    parts = tuple(replace(validate({"dataset": source_dataset(day, value)}, RULES, context())["dataset"], native=None)
        for day, value in (("2026-01-01", "10"), ("2026-02-01", "20")))
    assert all(len(part.validation_certificates) == 1 for part in parts)
    accepted = {certificate.identity for part in parts for certificate in part.validation_certificates}
    history, _ = resolve_revisions(parts, RevisionPolicy(expected_issues=("2026-01-01", "2026-02-01")))
    assert validate({"dataset": history}, RULES, context(accepted))["dataset"] == history
    changed = replace(history, rows=({**history.rows[0], "value": Decimal("999")}, *history.rows[1:]))
    with pytest.raises(ValueError, match="validation_evidence_required"):
        validate({"dataset": changed}, RULES, context(accepted))
    with pytest.raises(ValueError, match="validation_evidence_required"):
        validate({"dataset": history}, RULES, context())
    forged = replace(parts[0].validation_certificates[0], rule_id="caller.complete")
    claimed = replace(parts[0], validation_certificates=(forged,))
    with pytest.raises(ValueError, match="validation_evidence_required"):
        validate({"dataset": claimed}, RULES, context({forged.identity}))


def test_missing_calendar_issue_stays_partial_after_validating_actual_source_parts():
    part = replace(validate({"dataset": source_dataset("2026-01-01", "10")}, RULES, context())["dataset"], native=None)
    history, _ = resolve_revisions((part,), RevisionPolicy(expected_issues=("2026-01-01", "2026-02-01")))
    result = validate({"dataset": history}, RULES,
        context({certificate.identity for certificate in part.validation_certificates}))["dataset"]
    assert not result.assessment.complete and result.history_membership.missing_issues == ("2026-02-01",)


def geography_rows():
    return tuple({"metric": "apk", "metric_label": "Agriculture complex", "reporting_date": day,
        "reference_period": day, "subject": "example", "subject_label": label, "subject_kind": "region",
        "subject_parent": parent, "subject_order": 1, "value": Decimal(value),
        "dimensions": (("measure", measure), ("currency_scope", currency))}
        for day, label, parent, value in (("2026-01-01", "Earlier label", "Earlier district", "10"),
            ("2026-02-01", "Later label", "Later district", "20"))
        for measure in ("debt", "overdue_debt")
        for currency in ("rubles", "foreign_currency_and_precious_metals", "total"))


def test_geography_display_edition_preserves_actual_historical_descriptors_and_values():
    rows = geography_rows()
    with pytest.raises(ValueError, match="geography_conflict"):
        industry.prepare(rows)
    prepared = industry.prepare(rows, {"geography_policy": "latest", "include_metadata": True})
    assert len(prepared["sheets"]) == 6
    assert all(sheet[3][0][1] == "Later label" and sheet[3][0][-2:] == (Decimal(10), Decimal(20))
        for sheet in prepared["sheets"])
    assert {row[2] for row in prepared["geography_history"]} == {"Earlier label", "Later label"}
    earlier = industry.prepare(rows, {"geography_policy": "as_of", "geography_date": "2026-01-01"})
    assert earlier["sheets"][0][3][0][1] == "Earlier label"
    book = load_workbook(BytesIO(industry.render(prepared, lambda: None)))
    try:
        assert len(book.sheetnames) == 7 and "Metadata" in book.sheetnames
    finally:
        book.close()


def test_apk_requires_entire_operand_closure_and_keeps_missing_distinct_from_zero():
    metrics = sorted(REQUIRED)
    template = {"subject_namespace": "cbr.published_region", "subject": "example", "period": "2026-01-01",
        "period_kind": "as_of", "measure_kind": "stock", "perimeter": "CORPORATE_TOTAL",
        "unit": "RUB", "scale": Decimal(1000000), "dimensions": (("measure", "debt"), ("currency_scope", "total")),
        "value_status": "reported", "reporting_date": "2026-01-01"}
    rows = tuple({**template, "metric": metric, "value": Decimal(index + 1), "evidence_ref": "fixture:" + metric}
        for index, metric in enumerate(metrics))
    source = SourceDataset(SOURCE, rows)
    settings = FamilySettings(SOURCE, "industry_debt")
    complete = calculate({"dataset": source}, settings, context())["dataset"]
    assert {row["metric"] for row in complete.rows} == {"apk", "lpk"}
    assert all(len(row["operands"]) == 5 for row in complete.rows)
    with pytest.raises(ValueError, match="required_industries_missing"):
        calculate({"dataset": replace(source, rows=rows[:-1])}, settings, context())
    missing = replace(source, rows=({**rows[0], "value": None, "value_status": "blank"}, *rows[1:]))
    output = calculate({"dataset": missing}, settings, context())["dataset"]
    assert not output.assessment.complete and all(row["value"] is None for row in output.rows)
