"""Logical source binding and report-name semantics independent of input roots."""
from dataclasses import replace
from datetime import date
from importlib import resources
import json

import pytest

from stratbox.core.registry.sources import publication_families
from stratbox.domains.frank_rg.operations.bindings import bind_family, bind_source, validate_all_profiles
from stratbox.domains.frank_rg.publications.catalog import _decode, all_sources, families
from stratbox.domains.frank_rg.publications.contracts import FileEntry, ReportPeriod, SourceIndex
from stratbox.domains.frank_rg.publications.naming import build_internal_file_name, identify_index
from stratbox.domains.frank_rg.publications.profiles import RecognitionRule
from stratbox.domains.frank_rg.publications.selection import select_latest
from stratbox.shared.identity import ByteIdentity


def inventory(*names, root="."):
    bindings = tuple(bind_family(item.family_id) for item in families())
    index = SourceIndex(root, tuple(FileEntry(root + "/" + name, name) for name in names),
                        ByteIdentity.of("\n".join(names).encode()))
    return identify_index(index, sources=tuple((item.source, item.identification) for item in bindings))


SUPPLIER_NAMES = (
    ("frg.express.issuance", "FRG. Экспресс-мониторинг рынка. Выдачи. 2026-05-01.xlsx"),
    ("frg.express.portfolios", "FRG. Экспресс-мониторинг рынка. Портфели. 2026-05-01.xlsb"),
    ("frg.express.passives", "FRG. Экспресс-мониторинг рынка. Пассивы. 2026-05-01.xlsm"),
    ("frg.express.issuance_cards", "FRG. Кредитные карты. Экспресс-мониторинг рынка. Выдачи. 2026-05-01.xls"),
    ("frg.express.issuance_weekly", "FRG. Экспресс-мониторинг рынка. Выдачи. Май 2026 3 неделя.xlsx"),
    ("frg.regional.issuance", "FRG. Региональные данные. Выдачи. 2026-05-01.xlsx"),
    ("frg.regional.portfolios", "FRG. Региональные данные. Портфели. 2026-05-01.xlsx"),
    ("frg.regional.issuance_mortgage", "FRG. Региональные данные. Выдачи. Ипотека. 2026-05-01.xlsx"),
    ("frg.regional.portfolios_mortgage", "FRG. Региональные данные. Портфели. Ипотека. 2026-05-01.xlsx"),
    ("frg.regional.issuance_cards", "FRG. Региональные данные. Выдачи. Кредитные карты. 2026-05-01.xlsx"),
    ("frg.rbm.volumes_q", "FRG. Retail banking market. Volumes Q. 2026-05-01.xlsx"),
    ("frg.rbm.portfolios_q", "FRG. Retail banking market. Portfolios Q. 2026-05-01.xlsx"),
    ("frg.rbm.volumes_cards_q", "FRG. Cards volumes Q. 2026-05-01.xlsx"),
    ("frg.special.mortgage_refinancing", "FRG. Рефинансирование ипотеки. 2026-05-01.xlsx"),
)


def test_all_logical_sources_bind_without_delivery_locations():
    bound = validate_all_profiles()
    assert len(families()) == 4 and len(bound) == 14
    assert set(all_sources()) == {source for source, _ in SUPPLIER_NAMES}
    assert all(item.parent.source.publisher_id == "frank_rg" for item in bound)
    assert all(not hasattr(item.parent.source, "directory") for item in bound)
    assert all(not hasattr(item.parent.source, "location") for item in bound)


@pytest.mark.parametrize("source_id,name", SUPPLIER_NAMES)
def test_supplier_and_canonical_names_identify_the_same_logical_report(source_id, name):
    asset = inventory(name).assets[0]
    assert asset.valid and asset.recognition == "supplier"
    assert asset.source_id == source_id
    bound = bind_source(source_id)
    canonical = build_internal_file_name(asset.period, bound.rule, format=asset.format, profile=bound.parent.naming)
    renamed = inventory(canonical).assets[0]
    assert renamed.valid and renamed.recognition == "canonical"
    assert (renamed.source_id, renamed.period, renamed.format) == (asset.source_id, asset.period, asset.format)


def test_input_root_changes_evidence_without_changing_source_identity():
    name = SUPPLIER_NAMES[0][1]
    colab = inventory(name, root="/content/reports").assets[0]
    mounted = inventory(name, root="mounted/reports").assets[0]
    assert colab.entry.path != mounted.entry.path
    assert colab.source_id == mounted.source_id == "frg.express.issuance"
    assert colab.period == mounted.period


def test_registry_rejects_physical_configuration_and_callable_references():
    original = next(value for value in publication_families("frank_rg", series_fields=(("source_id", "series_id"), ("title", "title"))) if value["family_id"] == "frg.express")
    for field in ("location", "directory", "url", "filename"):
        value = {**original, field: "provided-at-runtime"}
        with pytest.raises(ValueError, match="frg.registry.invalid_shape"):
            _decode(json.dumps(value).encode())
    value = {**original, "profiles": {**original["profiles"], "discovery": "module:function"}}
    with pytest.raises(ValueError, match="frg.registry.invalid_identity"):
        _decode(json.dumps(value).encode())
    with pytest.raises(ValueError, match="frg.registry.invalid_yaml"):
        _decode(b'{"schema": "first", "schema": "second"}')


def test_identification_requires_phrases_instead_of_individual_characters():
    names = (
        "FRG. c a r d s v o l u m e s Q. 2026-05-01.xlsx",
        "FRG. р е ф и н а н с и р о в а н и е и п о т е к и. 2026-05-01.xlsx",
    )
    assert all(asset.recognition == "unclassified" for asset in inventory(*names).assets)
    with pytest.raises(ValueError, match="frg.profile.invalid_tokens"):
        RecognitionRule("invalid", "Invalid", "snapshot", 1, "cards volumes")


def test_regional_cutoff_and_format_admission_are_explicit():
    before, admitted, unsupported = inventory(
        "2026-03-31_Региональные выдачи.xlsx",
        "2026-04-01_Региональные выдачи.xlsx",
        "2026-05-01_Региональные выдачи.csv",
    ).assets
    assert before.source_id == admitted.source_id == "frg.regional.issuance"
    assert not before.valid and before.diagnostic == "frg.file.period_before_minimum"
    assert admitted.valid
    assert not unsupported.valid and unsupported.diagnostic == "frg.file.unsupported_format"


@pytest.mark.parametrize("week", [0, 7, 99])
def test_invalid_month_week_is_rejected_in_supplier_and_canonical_names(week):
    assets = inventory(
        f"FRG. Экспресс-мониторинг рынка. Выдачи. Май 2026 {week} неделя.xlsx",
        f"2026-05 week {week}_Экспресс выдачи — Weekly.xlsx",
    ).assets
    assert all(item.source_id == "frg.express.issuance_weekly" for item in assets)
    assert all(not item.valid and item.diagnostic == "frg.file.period_invalid" for item in assets)


def test_weekly_selection_orders_calendar_month_before_week_number():
    result = select_latest(inventory(
        "2026-04 week 6_Экспресс выдачи — Weekly.xlsx",
        "2026-05 week 1_Экспресс выдачи — Weekly.xlsx",
        "2026-05 week 2_Экспресс выдачи — Weekly.xlsx",
    ), source_ids=("frg.express.issuance_weekly",))
    assert result[0].state == "selected"
    assert result[0].asset.period == ReportPeriod(date(2026, 5, 1), 2)


def test_same_period_candidates_remain_ambiguous_despite_canonical_name_or_mtime():
    value = inventory(SUPPLIER_NAMES[0][1], "2026-05-01_Экспресс выдачи.xlsx")
    modified = replace(value.assets[1], entry=replace(value.assets[1].entry, mtime=99999999999.0))
    result = select_latest(replace(value, assets=(value.assets[0], modified)), source_ids=("frg.express.issuance",))
    assert result[0].state == "ambiguous" and result[0].asset is None
    assert len(result[0].candidates) == 2


def test_naming_dispatches_the_supplied_typed_profile_callback():
    bound = bind_source("frg.express.issuance")
    calls = []

    def build(period, rule, *, format, profile):
        calls.append((period, rule, format, profile.profile_id))
        return "selected-by-profile.xlsx"

    profile = replace(bound.parent.naming, build=build)
    period = ReportPeriod(date(2026, 5, 1))
    assert build_internal_file_name(period, bound.rule, format="xlsx", profile=profile) == "selected-by-profile.xlsx"
    assert calls == [(period, bound.rule, "xlsx", profile.profile_id)]


def test_duplicate_candidates_and_invalid_calendar_dates_are_not_silently_ranked():
    with pytest.raises(ValueError, match="frg.index.duplicate_path"):
        inventory(SUPPLIER_NAMES[0][1], SUPPLIER_NAMES[0][1])
    asset = inventory("2026-02-30_Экспресс выдачи.xlsx").assets[0]
    assert not asset.valid and asset.diagnostic == "frg.file.period_invalid"
