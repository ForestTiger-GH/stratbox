from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from stratbox.macrobanks.cbr_forms.common.models import (
    MODEL_COLUMNS,
    get_model_for,
    load_models,
    validate_model,
)


def _valid_formula_row(*, form: str = "999", order: str = "1", indicator_id: str = "x") -> dict[str, str]:
    return {
        "form": form,
        "order": order,
        "id": indicator_id,
        "kind": "formula",
        "dataset": "main",
        "source_code": "",
        "parent_code": "",
        "measure": "total",
        "name": "Test",
        "expression": "1+2",
        "section": "DERIVED",
        "unit": "thousand_rub",
        "params": "",
    }


def _frame(*rows: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=MODEL_COLUMNS)


def test_each_model_csv_has_exact_schema() -> None:
    models_dir = Path(__file__).resolve().parents[4] / "src/stratbox/macrobanks/cbr_forms/models"
    paths = sorted(models_dir.glob("form*.csv"))
    assert paths
    for path in paths:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        assert list(frame.columns) == list(MODEL_COLUMNS)


def test_model_filename_matches_form_column(tmp_path: Path) -> None:
    frame = _frame(_valid_formula_row(form="102"))
    frame.to_csv(tmp_path / "form101.csv", index=False)
    with pytest.raises(RuntimeError, match="Model form mismatch"):
        load_models(tmp_path)


def test_model_ids_unique_within_form() -> None:
    frame = _frame(
        _valid_formula_row(order="1", indicator_id="dup"),
        _valid_formula_row(order="2", indicator_id="dup"),
    )
    with pytest.raises(RuntimeError, match="duplicated id"):
        validate_model(frame, expected_form="999")


def test_model_order_unique_within_form() -> None:
    frame = _frame(
        _valid_formula_row(order="1", indicator_id="a"),
        _valid_formula_row(order="1", indicator_id="b"),
    )
    with pytest.raises(RuntimeError, match="duplicated order"):
        validate_model(frame, expected_form="999")


def test_direct_requires_source_code() -> None:
    row = _valid_formula_row()
    row.update({"kind": "direct", "expression": "", "source_code": ""})
    with pytest.raises(RuntimeError, match="direct rows require source_code"):
        validate_model(_frame(row), expected_form="999")


def test_formula_requires_expression() -> None:
    row = _valid_formula_row()
    row["expression"] = ""
    with pytest.raises(RuntimeError, match="formula rows require expression"):
        validate_model(_frame(row), expected_form="999")


def test_passthrough_requires_dataset() -> None:
    row = _valid_formula_row()
    row.update({"kind": "passthrough", "dataset": "", "source_code": "*", "expression": ""})
    with pytest.raises(RuntimeError, match="dataset is required"):
        validate_model(_frame(row), expected_form="999")


def test_load_models_concatenates_all_forms() -> None:
    models = load_models()
    assert set(models["form"]) == {"101", "102", "123", "135", "802", "805"}
    assert len(models) == 128


def test_get_model_for_returns_only_requested_form() -> None:
    models = load_models()
    model802 = get_model_for(models, form="802")
    assert set(model802["form"]) == {"802"}
    assert model802["order"].astype(int).tolist() == list(range(1, 87))


def test_form802_model_has_expected_row_count_and_codes() -> None:
    model802 = get_model_for(load_models(), form="802")
    assert len(model802) == 86
    assert model802["source_code"].is_unique
    assert {"1", "14", "15.4", "15.5", "21", "32.1", "34"}.issubset(set(model802["source_code"]))


def test_form802_repeated_names_do_not_collide_by_id() -> None:
    model802 = get_model_for(load_models(), form="802")
    repeated = model802[model802["name"].str.lower() == "цифровые финансовые активы"]
    assert repeated["source_code"].tolist() == ["4.3", "5.4", "6.6", "15.7", "16.7"]
    assert repeated["id"].is_unique


def test_existing_models_preserve_previous_analytical_indicator_sets() -> None:
    models = load_models()

    model101 = get_model_for(models, form="101")
    assert model101["name"].tolist() == [
        "Кредиты ФЛ",
        "Кредиты ЮЛ",
        "Средства ФЛ",
        "Средства ЮЛ",
        "СР ЮЛ Гос средства",
        "СР ЮЛ Ср на счетах+эскроу",
        "СР ЮЛ Депозиты",
        "Ценные бумаги",
        "Эскроу",
        "Кредиты ЦБ до переоценки",
        "Депозиты в ЦБ и кредиты банкам",
    ]
    assert model101["kind"].eq("formula").all()

    model102 = get_model_for(models, form="102")
    assert model102["name"].tolist() == [
        "ЧПД",
        "ЧКД",
        "Прочие доходы",
        "Операц. расходы",
        "Резервы",
        "Прибыль до налогов",
        "Налоги",
        "Чистая прибыль",
    ]
    assert model102["kind"].eq("formula").all()

    model123 = get_model_for(models, form="123")
    assert model123["expression"].tolist() == ["000", "102", "102+105"]

    model135 = get_model_for(models, form="135")
    assert model135["name"].tolist() == [
        "H1.0", "H1.1", "H1.2", "H1.4", "H2", "H3", "H4",
        "H6", "H7", "H12", "H18", "H27", "H29",
    ]
    assert model135["kind"].eq("direct").all()

    model805 = get_model_for(models, form="805")
    assert model805["name"].tolist() == ["H20.0", "H20.1", "H20.2", "H20.4", "H22", "H26", "H28"]
    assert model805["kind"].eq("direct").all()
