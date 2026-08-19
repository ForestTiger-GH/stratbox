"""
Модуль загружает и проверяет семантические модели отчетных форм Банка России.

Каждая форма хранится в отдельном CSV-файле ``models/formXXX.csv``. Файлы
имеют единый schema и описывают смысл показателей, но не физические имена
полей DBF. Физическая структура источника остается в Python-модуле формы.
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


MODEL_COLUMNS = (
    "form",
    "order",
    "id",
    "kind",
    "dataset",
    "source_code",
    "parent_code",
    "measure",
    "name",
    "expression",
    "section",
    "unit",
    "params",
)

ALLOWED_KINDS = {"direct", "formula", "passthrough"}
ALLOWED_UNITS = {"thousand_rub", "percent", "days", "text"}


def _default_models_dir() -> Path:
    """
    Функция возвращает каталог встроенных моделей cbr_forms.
    """
    return Path(__file__).resolve().parents[1] / "models"


def _normalize_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Функция приводит все поля модели к строковому виду без крайних пробелов.
    """
    out = df.copy()
    for col in MODEL_COLUMNS:
        out[col] = out[col].astype(str).str.strip()
    return out


def _expected_form_from_path(path: Path) -> str:
    """
    Функция извлекает короткий код формы из имени ``formXXX.csv``.
    """
    match = re.fullmatch(r"form([0-9]+)", path.stem, flags=re.IGNORECASE)
    if not match:
        raise RuntimeError(f"Invalid model filename: {path.name}; expected formXXX.csv")
    return match.group(1)


def validate_model(df: pd.DataFrame, *, expected_form: str | None = None) -> None:
    """
    Функция проверяет единый контракт семантической модели формы.

    Проверяются schema, уникальность идентификаторов и порядка, допустимые
    ``kind``/``unit`` и обязательные поля для direct/formula/passthrough.
    """
    if list(df.columns) != list(MODEL_COLUMNS):
        raise RuntimeError(
            "Model schema mismatch. "
            f"Expected={list(MODEL_COLUMNS)}; got={list(df.columns)}"
        )

    if len(df) == 0:
        raise RuntimeError("Model is empty.")

    work = _normalize_model(df)

    forms = set(work["form"].tolist())
    if "" in forms or len(forms) != 1:
        raise RuntimeError(f"Model must contain exactly one non-empty form code; got={sorted(forms)}")

    form = next(iter(forms))
    if expected_form is not None and form != str(expected_form).strip():
        raise RuntimeError(f"Model form mismatch: expected={expected_form}; got={form}")

    if work["id"].eq("").any():
        raise RuntimeError(f"Model {form}: id is required for every row.")
    if work["name"].eq("").any():
        raise RuntimeError(f"Model {form}: name is required for every row.")
    if work["dataset"].eq("").any():
        raise RuntimeError(f"Model {form}: dataset is required for every row.")
    if work["measure"].eq("").any():
        raise RuntimeError(f"Model {form}: measure is required for every row.")

    orders = pd.to_numeric(work["order"], errors="coerce")
    if orders.isna().any() or (orders <= 0).any() or (orders % 1 != 0).any():
        raise RuntimeError(f"Model {form}: order must contain positive integers only.")

    if work["id"].duplicated().any():
        dup = work.loc[work["id"].duplicated(keep=False), "id"].tolist()
        raise RuntimeError(f"Model {form}: duplicated id values: {dup}")

    if orders.duplicated().any():
        dup = work.loc[orders.duplicated(keep=False), "order"].tolist()
        raise RuntimeError(f"Model {form}: duplicated order values: {dup}")

    unknown_kinds = sorted(set(work["kind"]) - ALLOWED_KINDS)
    if unknown_kinds:
        raise RuntimeError(f"Model {form}: unknown kind values: {unknown_kinds}")

    unknown_units = sorted(set(work["unit"]) - ALLOWED_UNITS)
    if unknown_units:
        raise RuntimeError(f"Model {form}: unknown unit values: {unknown_units}")

    direct = work[work["kind"] == "direct"]
    if direct["source_code"].eq("").any():
        raise RuntimeError(f"Model {form}: direct rows require source_code.")
    if direct["expression"].ne("").any():
        raise RuntimeError(f"Model {form}: direct rows must not contain expression.")

    formula = work[work["kind"] == "formula"]
    if formula["expression"].eq("").any():
        raise RuntimeError(f"Model {form}: formula rows require expression.")

    passthrough = work[work["kind"] == "passthrough"]
    if passthrough["source_code"].ne("*").any():
        raise RuntimeError(f"Model {form}: passthrough rows require source_code='*'.")
    if passthrough["expression"].ne("").any():
        raise RuntimeError(f"Model {form}: passthrough rows must not contain expression.")

    # Родительские коды проверяются внутри того же логического dataset.
    for dataset, sub in work.groupby("dataset", sort=False):
        available_codes = set(sub.loc[sub["source_code"].ne("*"), "source_code"].tolist())
        for parent_code in sub.loc[sub["parent_code"].ne(""), "parent_code"].tolist():
            if parent_code not in available_codes:
                raise RuntimeError(
                    f"Model {form}: parent_code={parent_code!r} is absent in dataset={dataset!r}."
                )


def load_models(models_dir: str | Path | None = None) -> pd.DataFrame:
    """
    Функция загружает все ``form*.csv`` и объединяет их в единый каталог.
    """
    root = Path(models_dir) if models_dir is not None else _default_models_dir()
    paths = sorted(root.glob("form*.csv"), key=lambda p: p.name.lower())
    if not paths:
        raise FileNotFoundError(f"No form model CSV files found: {root}")

    frames: list[pd.DataFrame] = []
    for path in paths:
        expected_form = _expected_form_from_path(path)
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        validate_model(frame, expected_form=expected_form)
        frames.append(_normalize_model(frame))

    out = pd.concat(frames, ignore_index=True)
    if out.duplicated(subset=["form", "id"]).any():
        raise RuntimeError("Combined model catalog contains duplicated (form, id).")

    out["_order_num"] = pd.to_numeric(out["order"], errors="raise").astype(int)
    out = out.sort_values(["form", "_order_num"], kind="stable").drop(columns=["_order_num"])
    return out.reset_index(drop=True)


def get_model_for(models_df: pd.DataFrame, *, form: str) -> pd.DataFrame:
    """
    Функция возвращает только модель указанной формы в порядке ``order``.
    """
    code = str(form).strip()
    out = models_df[models_df["form"].astype(str).str.strip() == code].copy()
    if len(out) == 0:
        raise RuntimeError(f"No model rows for form {code}.")

    validate_model(out, expected_form=code)
    out["_order_num"] = pd.to_numeric(out["order"], errors="raise").astype(int)
    return out.sort_values("_order_num", kind="stable").drop(columns=["_order_num"]).reset_index(drop=True)


def get_model_rows(
    model_df: pd.DataFrame,
    *,
    kind: str | None = None,
    dataset: str | None = None,
) -> pd.DataFrame:
    """
    Функция фильтрует уже выбранную модель формы по ``kind`` и ``dataset``.
    """
    out = model_df.copy()
    if kind is not None:
        out = out[out["kind"].astype(str) == str(kind).strip()].copy()
    if dataset is not None:
        out = out[out["dataset"].astype(str) == str(dataset).strip()].copy()

    out["_order_num"] = pd.to_numeric(out["order"], errors="raise").astype(int)
    return out.sort_values("_order_num", kind="stable").drop(columns=["_order_num"]).reset_index(drop=True)
