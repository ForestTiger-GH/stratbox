"""Form 101 uses only chapter А to calculate balance-sheet indicators."""
from datetime import date
from importlib.resources import files

import pandas as pd
import pytest

from .support import calculate, dataset
from stratbox.domains.cbr.calculations.reporting_forms.formula import build_formula_long
from stratbox.domains.cbr.calculations.reporting_forms.model import parse_form_model
from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.form101 import DEFAULT_SPEC


def _model():
    return parse_form_model(
        files("stratbox.domains.cbr.calculations.reporting_forms.models").joinpath("form101.csv").read_bytes(),
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


def test_formula_command_accepts_cross_chapter_account_duplicates():
    source = dataset("101", ("REGN", "NUM_SC", "IITG", "PLAN", "A_P"),
        tuple(_rows().itertuples(index=False, name=None)), issue_id="2024-01-01")
    result = calculate("101", source)
    value = next(row["value"] for row in result.rows if row["metric"] == "loans_individuals")
    assert str(value) == "123.4"


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
