"""Form 101 uses only chapter А to calculate balance-sheet indicators."""
from datetime import date
from importlib.resources import files

import pandas as pd
import pytest

from stratbox.macrobanks import cbr_forms as forms
from stratbox.macrobanks.cbr_forms.common.formula import build_formula_long
from stratbox.macrobanks.cbr_forms.common.models import parse_form_model
from stratbox.macrobanks.cbr_forms.forms.form101 import DEFAULT_SPEC


def _model():
    return parse_form_model(
        files("stratbox.macrobanks.cbr_forms.models").joinpath("form101.csv").read_bytes(),
        "101",
    )


def _rows():
    return pd.DataFrame(
        [
            ("1481", "45.2", "123.4", "А", "1"),
            ("1481", "45.2", "9999.9", "В", "1"),
            ("1481", "45.2", "500.5", "А", "2"),
        ],
        columns=["REGN", "CODE", "VALUE", "PLAN", "SIDE"],
    )


def test_balance_formulas_reject_cross_chapter_value_contamination():
    banks = pd.DataFrame([("Example", "1481", 1)], columns=["bank", "regn", "sort"])
    long, order = build_formula_long(
        [("01.01.2024", _rows())], banks, _model(), DEFAULT_SPEC
    )
    actual = long.loc[long["IndicatorId"].eq("loans_individuals"), "Значение"].tolist()
    assert len(actual) == 1
    assert str(actual[0]) == "123.4"
    assert order["loans_individuals"] == 1


def test_typed_operation_accepts_cross_chapter_account_duplicates():
    key = forms.FormKey("101", date(2024, 1, 1))
    snapshot = forms.FormSnapshot(key, {}, _rows(), ())
    result = forms.build_form_data(
        forms.BuildFormDataRequest(
            (snapshot,), banks=(forms.BankSelection("1481", "Example"),)
        )
    )
    assert result.outcome == "succeeded", result.diagnostics
    row = result.value.long.loc[
        result.value.long["IndicatorId"].eq("loans_individuals")
    ]
    assert str(row.iloc[0]["Значение"]) == "123.4"


def test_missing_chapter_fails_instead_of_combining_unrelated_accounts():
    banks = pd.DataFrame([("Example", "1481", 1)], columns=["bank", "regn", "sort"])
    with pytest.raises(ValueError, match="account-plan chapter"):
        build_formula_long(
            [("01.01.2024", _rows().drop(columns=["PLAN"]))],
            banks,
            _model(),
            DEFAULT_SPEC,
        )


def test_conflicting_duplicates_within_chapter_still_fail():
    frame = pd.concat(
        [_rows(), pd.DataFrame([("1481", "45.2", "777", "А", "1")], columns=_rows().columns)]
    )
    banks = pd.DataFrame([("Example", "1481", 1)], columns=["bank", "regn", "sort"])
    with pytest.raises(ValueError, match="Conflicting source account rows"):
        build_formula_long([("01.01.2024", frame)], banks, _model(), DEFAULT_SPEC)
