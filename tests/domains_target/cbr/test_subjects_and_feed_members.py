"""Caller subjects and physical form membership retain independent namespaces."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from stratbox.domains.cbr.calculations.reporting_forms.methods import calculate
from stratbox.domains.cbr.methods.actions.forms import extract
from stratbox.domains.cbr.products import actions
from stratbox.domains.cbr.products.specifications import ProductSettings
from stratbox.domains.cbr.series.reporting_forms import F101_TABLE, F135_TABLE, F805_TABLE
from stratbox.shared.data.selection import SubjectChoice
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import DBFField, DBFRecord, DbfEvidence, Material, SourceDataset


DAY = "2026-04-01"
BANK = "cbr.bank.registration"
GROUP = "cbr.banking_group.registration"
FEED = "cbr.reporting_forms.publications"


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None, verify_source_use=lambda use: False)


def ratio_row(form, namespace, subject, value):
    dataset = "section3" if form == "135" else "normatives"
    code = "H1.0" if form == "135" else "H20.0"
    return {"form": form, "value_status": "reported", "value": Decimal(value), "reporting_date": DAY,
        "source_code": code, "measure": "actual", "source_dataset": dataset,
        "metric": f"cbr.forms.{form}.{dataset}.{code}.actual", "unit": "percent", "scale": Decimal(1),
        "measure_kind": "ratio", "subject_namespace": namespace, "subject": subject,
        "perimeter": "consolidated_group" if namespace == GROUP else "credit_institution",
        "period": DAY, "period_kind": "as_of", "evidence_ref": "fixture:" + namespace + ":" + subject}


def test_same_registration_token_for_bank_and_group_does_not_merge_model_axes():
    dataset = SourceDataset(F805_TABLE.series_id,
        (ratio_row("805", BANK, "1000", "11"), ratio_row("805", GROUP, "1000", "22")))
    choices = (SubjectChoice(GROUP, "1000", "Selected group"), SubjectChoice(BANK, "1000", "Selected bank"))
    ctx = context(subject_selection=choices)
    calculated = calculate({"dataset": dataset}, F805_TABLE, ctx)["dataset"]
    actual = tuple(row for row in calculated.rows if row["metric"] == "f805.h20.0")
    assert [(row["subject_namespace"], row["value"]) for row in actual] == [(GROUP, Decimal(22)), (BANK, Decimal(11))]
    assert [row["subject_label"] for row in actual] == ["Selected group", "Selected bank"]
    with pytest.raises(ValueError, match="subject_namespace_required"):
        calculate({"dataset": dataset}, F805_TABLE, context(subjects=("1000",)))


def test_external_subject_order_and_labels_reach_form_workbook_without_resource_preset():
    dataset = SourceDataset(F135_TABLE.series_id,
        (ratio_row("135", BANK, "1000", "10"), ratio_row("135", BANK, "2000", "20")))
    choices = (SubjectChoice(BANK, "2000", "Second selected first", "external-reference-basis"),
        SubjectChoice(BANK, "1000", "First selected second"))
    ctx = context(subject_selection=choices)
    calculated = calculate({"dataset": dataset}, F135_TABLE, ctx)["dataset"]
    assert calculated.rows[0]["subject"] == "2000"
    assert calculated.rows[0]["subject_reference"] == "external-reference-basis"
    view = actions.prepare({"dataset": calculated}, ProductSettings("forms"), ctx)["view"]
    product = actions.render({"view": view}, ProductSettings("forms"), ctx)["product"]
    book = load_workbook(BytesIO(product.data), data_only=True)
    try:
        labels = [cell.value for row in book.active for cell in row
            if cell.value in {"Second selected first", "First selected second"}]
        assert labels.index("Second selected first") < labels.index("First selected second")
    finally:
        book.close()
    with pytest.raises(ValueError, match="inputs_empty"):
        calculate({"dataset": dataset}, F135_TABLE, context(subject_selection=()))


def physical_member(*, form="101", qualified=True):
    parent = Material(b"accepted form archive")
    use = SourceUse(SourceCoordinate(source_id=FEED, issue_id=DAY,
        asset_id="form-0409" + form, material_identity=parent.identity),
        "publication_acquisition", "verified", "sha256:" + parent.identity.sha256)
    member = Material(b"physical DBF", source_id=FEED,
        metadata={"issue_id": DAY, "member": "data.dbf", "asset_id": "data.dbf",
            "container_asset_id": "form-0409" + form, "parent": parent.identity.sha256},
        lineage=(parent.identity,), source_uses=(use,) if qualified else ())
    fields = tuple(DBFField(name, "C", 8, 0, 1 + index * 8)
        for index, name in enumerate(("REGN", "NUM_SC", "IITG", "PLAN", "A_P")))
    physical = DbfEvidence(member, fields, (DBFRecord(1, False, ("1000", "30102", "10", "A", "1")),))
    return physical, use


def test_feed_member_requires_qualified_parent_relation_before_form_schema_admission():
    physical, use = physical_member()
    rejected = context(issue_id=DAY)
    with pytest.raises(ValueError, match="feed_relation_unqualified"):
        extract({"physical": physical}, F101_TABLE, rejected)
    accepted = context(issue_id=DAY)
    accepted.verify_source_use = lambda candidate: candidate == use
    tables = extract({"physical": physical}, F101_TABLE, accepted)["tables"]
    assert tables.source_id == F101_TABLE.series_id and tables.material.source_id == FEED
    assert {item.coordinate.source_id for item in tables.metadata["source_uses"]} == {FEED, F101_TABLE.series_id}
    wrong_form, wrong_use = physical_member(form="802")
    accepted.verify_source_use = lambda candidate: candidate == wrong_use
    with pytest.raises(ValueError, match="feed_relation_unqualified"):
        extract({"physical": wrong_form}, F101_TABLE, accepted)
    tampered = replace(physical, material=replace(physical.material,
        metadata={**physical.material.metadata, "parent": "0" * 64}))
    with pytest.raises(ValueError, match="feed_relation_unqualified"):
        extract({"physical": tampered}, F101_TABLE, accepted)
