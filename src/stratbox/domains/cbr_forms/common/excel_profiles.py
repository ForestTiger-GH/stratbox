"""
Профили Excel-представления отчетных форм Банка России.

Модуль не знает физическую структуру DBF. Он получает canonical long и
семантическую модель формы и строит только пользовательские Excel-витрины.
Это позволяет одной и той же форме иметь полноценный машинный long и более
удобное представление для человека без изменения бизнес-данных.
"""

from __future__ import annotations

import pandas as pd


STANDARD_PROFILE = "standard"
HIERARCHICAL_STATEMENT_PROFILE = "hierarchical_statement"


def _hierarchy_levels(model_df: pd.DataFrame) -> dict[tuple[str, str], int]:
    """
    Функция рассчитывает уровень каждой строки по ``parent_code`` модели.

    Уровень строится по явной иерархии внутри ``dataset``, а не по точкам или
    другим символам внутри исходного кода строки.
    """
    by_key = {
        (str(row["dataset"]), str(row["source_code"])): str(row["parent_code"])
        for _, row in model_df.iterrows()
        if str(row["source_code"]).strip() and str(row["source_code"]).strip() != "*"
    }
    cache: dict[tuple[str, str], int] = {}

    def resolve(key: tuple[str, str], trail: tuple[tuple[str, str], ...] = ()) -> int:
        if key in cache:
            return cache[key]
        if key in trail:
            raise RuntimeError(f"Model hierarchy cycle detected: {trail + (key,)}")

        dataset, _ = key
        parent_code = by_key.get(key, "")
        if not parent_code:
            level = 0
        else:
            parent_key = (dataset, parent_code)
            level = resolve(parent_key, trail + (key,)) + 1
        cache[key] = level
        return level

    for key in by_key:
        resolve(key)
    return cache


def _model_meta(model_df: pd.DataFrame) -> pd.DataFrame:
    """
    Функция подготавливает структурные атрибуты модели для Excel-профилей.
    """
    work = model_df.copy()
    work["_order"] = pd.to_numeric(work["order"], errors="raise").astype(int)
    levels = _hierarchy_levels(work)
    work["_level"] = [
        levels.get((str(row["dataset"]), str(row["source_code"])), 0)
        for _, row in work.iterrows()
    ]
    work["_level"] = pd.Series(work["_level"], dtype="int64")
    return work.sort_values("_order", kind="stable").reset_index(drop=True)


def _date_columns(df_long: pd.DataFrame, date_col: str) -> list[str]:
    """
    Функция возвращает отчетные даты в хронологическом порядке.
    """
    return sorted(
        df_long[date_col].astype(str).unique().tolist(),
        key=lambda value: pd.to_datetime(value, dayfirst=True),
    )


def _bank_names(df_banks: pd.DataFrame) -> list[str]:
    """
    Функция возвращает банки в стабильном порядке legacy-каталога.
    """
    return df_banks.sort_values("sort", kind="stable")["bank"].astype(str).tolist()


def _matrix(
    df_long: pd.DataFrame,
    *,
    indicator_ids: list[str],
    bank_names: list[str],
    date_cols: list[str],
    bank_first: bool,
) -> pd.DataFrame:
    """
    Функция строит матрицу значений для выбранного порядка строк.
    """
    keys = ["IndicatorId", "Банк", "Дата"]
    duplicate_mask = df_long.duplicated(subset=keys, keep=False)
    if duplicate_mask.any():
        sample = df_long.loc[duplicate_mask, keys].head(10)
        raise RuntimeError(f"Duplicate long keys before hierarchical Excel pivot: {sample.to_dict('records')}")

    if bank_first:
        row_index = pd.MultiIndex.from_product(
            [bank_names, indicator_ids],
            names=["Банк", "IndicatorId"],
        )
        source = df_long.set_index(["Банк", "IndicatorId", "Дата"])["Значение"].unstack("Дата")
    else:
        row_index = pd.MultiIndex.from_product(
            [indicator_ids, bank_names],
            names=["IndicatorId", "Банк"],
        )
        source = df_long.set_index(["IndicatorId", "Банк", "Дата"])["Значение"].unstack("Дата")

    return source.reindex(index=row_index, columns=date_cols).where(lambda frame: frame.notna(), "").reset_index()


def build_hierarchical_overview(
    *,
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    model_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Функция строит компактный обзор верхнего уровня иерархической формы.
    """
    meta = _model_meta(model_df)
    top = meta[meta["parent_code"].astype(str).eq("")].copy()
    indicator_ids = top["id"].astype(str).tolist()
    bank_names = _bank_names(df_banks)
    date_cols = _date_columns(df_long, "Дата")

    matrix = _matrix(
        df_long=df_long[df_long["IndicatorId"].astype(str).isin(indicator_ids)].copy(),
        indicator_ids=indicator_ids,
        bank_names=bank_names,
        date_cols=date_cols,
        bank_first=False,
    )

    meta_by_id = top.set_index("id")
    matrix.insert(0, "Показатель", matrix["IndicatorId"].map(meta_by_id["name"]).fillna(""))
    matrix.insert(0, "Код", matrix["IndicatorId"].map(meta_by_id["source_code"]).fillna(""))
    matrix.insert(0, "Раздел", matrix["IndicatorId"].map(meta_by_id["section"]).fillna(""))
    return matrix.drop(columns=["IndicatorId"]).reset_index(drop=True)


def build_hierarchical_full(
    *,
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    model_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Функция строит полную форму в порядке ``банк -> строка формы``.
    """
    meta = _model_meta(model_df)
    indicator_ids = meta["id"].astype(str).tolist()
    bank_names = _bank_names(df_banks)
    date_cols = _date_columns(df_long, "Дата")

    matrix = _matrix(
        df_long=df_long,
        indicator_ids=indicator_ids,
        bank_names=bank_names,
        date_cols=date_cols,
        bank_first=True,
    )

    meta_by_id = meta.set_index("id")
    matrix.insert(1, "Раздел", matrix["IndicatorId"].map(meta_by_id["section"]).fillna(""))
    matrix.insert(2, "Уровень", matrix["IndicatorId"].map(meta_by_id["_level"]).fillna(0).astype(int))
    matrix.insert(3, "Код", matrix["IndicatorId"].map(meta_by_id["source_code"]).fillna(""))
    matrix.insert(4, "Показатель", matrix["IndicatorId"].map(meta_by_id["name"]).fillna(""))
    return matrix.drop(columns=["IndicatorId"]).reset_index(drop=True)


def build_hierarchical_data(
    *,
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    model_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Функция подготавливает canonical long для машинной работы в Excel.

    К исходным колонкам добавляются только структурные атрибуты модели:
    порядок, родительский код и уровень иерархии.
    """
    meta = _model_meta(model_df)[["id", "_order", "parent_code", "_level"]].copy()
    meta = meta.rename(
        columns={
            "id": "IndicatorId",
            "_order": "Порядок",
            "parent_code": "РодительскийКод",
            "_level": "Уровень",
        }
    )

    out = df_long.merge(meta, on="IndicatorId", how="left", validate="many_to_one")
    if out["Порядок"].isna().any():
        missing = sorted(out.loc[out["Порядок"].isna(), "IndicatorId"].astype(str).unique().tolist())
        raise RuntimeError(f"Long contains indicators absent in model: {missing[:10]}")

    bank_order = {
        str(row["bank"]): int(row["sort"])
        for _, row in df_banks.iterrows()
    }
    out["_bank_order"] = out["Банк"].astype(str).map(bank_order).fillna(10**9)
    out["_date_order"] = pd.to_datetime(out["Дата"], dayfirst=True, errors="raise")
    out = out.sort_values(["_date_order", "_bank_order", "Порядок"], kind="stable")
    out = out.drop(columns=["_bank_order", "_date_order"])

    base_cols = [
        "Форма",
        "Дата",
        "REGN",
        "Банк",
        "IndicatorId",
        "Код",
        "Показатель",
        "Раздел",
        "Порядок",
        "РодительскийКод",
        "Уровень",
        "Measure",
        "Значение",
        "Единица",
    ]
    remaining = [col for col in out.columns if col not in base_cols]
    return out[base_cols + remaining].reset_index(drop=True)


def build_hierarchical_statement_sheets(
    *,
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    model_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Функция формирует три листа иерархического Excel-профиля.
    """
    required = {"Дата", "Банк", "IndicatorId", "Значение"}
    missing = required - set(df_long.columns)
    if missing:
        raise RuntimeError(f"df_long missing required hierarchical Excel columns: {sorted(missing)}")

    return {
        "Обзор": build_hierarchical_overview(
            df_long=df_long,
            df_banks=df_banks,
            model_df=model_df,
        ),
        "Полная форма": build_hierarchical_full(
            df_long=df_long,
            df_banks=df_banks,
            model_df=model_df,
        ),
        "Данные": build_hierarchical_data(
            df_long=df_long,
            df_banks=df_banks,
            model_df=model_df,
        ),
    }
