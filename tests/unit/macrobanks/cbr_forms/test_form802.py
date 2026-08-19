from __future__ import annotations

import pandas as pd
import pytest

from stratbox.macrobanks.cbr_forms.common.direct_form import build_direct_long, normalize_code_plain, normalize_regn
from stratbox.macrobanks.cbr_forms.common.models import get_model_for, load_models
from stratbox.macrobanks.cbr_forms.common.wide import build_wide_table
from stratbox.macrobanks.cbr_forms.forms import form802
from stratbox.macrobanks.cbr_forms.forms.registry import FORM_REGISTRY


def _banks() -> pd.DataFrame:
    return pd.DataFrame([{"bank": "ВТБ", "regn": 1000, "sort": 1}])


def _raw_snapshot() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"REGN": "1000", "CODE": "1", "total": 378425603, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "4.3", "total": 0, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "5.4", "total": 0, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "6.5", "total": None, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "14", "total": 37345098439, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "15.4", "total": 14587960720, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "15.5", "total": 14106276611, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "21", "total": 34024581294, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "32.1", "total": 197469209, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
            {"REGN": "1000", "CODE": "34", "total": 3320517145, "consolidation_plus": None, "consolidation_minus": None, "intragroup_adjustment": None},
        ]
    )


def _long() -> tuple[pd.DataFrame, dict[str, int]]:
    model = get_model_for(load_models(), form="802")
    return build_direct_long(
        date_raw_list=[("01.04.2026", _raw_snapshot())],
        banks_df=_banks(),
        model_df=model,
        spec=form802.DEFAULT_SPEC,
    )



def test_regn_normalization_does_not_turn_1000_float_into_10000() -> None:
    assert normalize_regn(1000) == "1000"
    assert normalize_regn(1000.0) == "1000"
    assert normalize_regn("1000.0") == "1000"

def test_registry_contains_802() -> None:
    assert FORM_REGISTRY["802"].title == "0409802"


def test_form802_url_and_physical_measures() -> None:
    assert form802.build_url(pd.Timestamp("2026-04-01")).endswith("/802-20260401.rar")
    assert form802.DEFAULT_SPEC.code_fields == ("STR",)
    assert form802.DEFAULT_SPEC.measure_fields == {
        "total": ("VSEGO",),
        "consolidation_plus": ("KORR_P",),
        "consolidation_minus": ("KORR_M",),
        "intragroup_adjustment": ("KORR_GR",),
    }


def test_form802_long_has_all_86_rows_for_bank_and_date() -> None:
    long, order = _long()
    assert len(long) == 86
    assert len(order) == 86
    assert long["IndicatorId"].is_unique


def test_form802_preserves_blank_and_zero_semantics() -> None:
    long, _ = _long()
    by_code = long.set_index("Код")["Значение"]
    assert by_code["4.3"] == 0.0
    assert by_code["6.5"] == ""
    assert by_code["7"] == ""
    assert by_code["14"] == 37345098439.0


def test_form802_control_values_match_official_snapshot_fixture() -> None:
    long, _ = _long()
    by_code = long.set_index("Код")["Значение"]
    assert by_code["1"] == 378425603.0
    assert by_code["15.4"] == 14587960720.0
    assert by_code["15.5"] == 14106276611.0
    assert by_code["21"] == 34024581294.0
    assert by_code["32.1"] == 197469209.0
    assert by_code["34"] == 3320517145.0


def test_form802_wide_keeps_repeated_names_as_separate_rows() -> None:
    long, order = _long()
    repeated = long[long["Код"].isin(["4.3", "5.4"])].copy()
    wide = build_wide_table(repeated, _banks(), indicator_order=order)
    assert wide["Код"].tolist() == ["4.3", "5.4"]
    assert wide["Показатель"].tolist() == ["цифровые финансовые активы", "цифровые финансовые активы"]
    assert wide["01.04.2026"].tolist() == [0.0, 0.0]


def test_plain_code_normalization_treats_pandas_missing_values_as_blank() -> None:
    assert normalize_code_plain(pd.NA) == ""
    assert normalize_code_plain(float("nan")) == ""
    assert normalize_code_plain(" 2.1.1 ") == "2.1.1"


def test_direct_long_fails_on_duplicate_physical_bank_code_keys() -> None:
    model = get_model_for(load_models(), form="802")
    duplicate_raw = pd.concat([_raw_snapshot(), _raw_snapshot().iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="Duplicate physical keys"):
        build_direct_long(
            date_raw_list=[("01.04.2026", duplicate_raw)],
            banks_df=_banks(),
            model_df=model,
            spec=form802.DEFAULT_SPEC,
        )
