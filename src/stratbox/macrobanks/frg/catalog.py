"""
Построение каталога файлов FRG.

На первом этапе модуль:
- обходит каталог с файлами;
- определяет семейство по имени файла;
- поддерживает как исходные, так и внутренние переименованные имена;
- формирует стабильную таблицу-каталог.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from stratbox.base.filestore import FileStore
from stratbox.base.filestore.paths import child_path
from stratbox.base.filestore.types import DIRECTORY_GUARD_NAME
from stratbox.base.limits import BudgetMeter
from stratbox.macrobanks.frg.models import FrgCatalogRecord
from stratbox.macrobanks.frg.naming import parse_file_name


DEFAULT_ALLOWED_EXTENSIONS = {".xlsx", ".xlsb", ".xlsm", ".xls"}


def _iter_paths(
    root_dir: str,
    *,
    filestore: FileStore,
    recursive: bool,
    visit: Callable[[], None],
) -> list[str]:
    """Возвращает список путей к файлам, найденным в каталоге."""
    if not filestore.is_dir(root_dir):
        raise FileNotFoundError("Catalog directory is unavailable")
    if recursive:
        paths: list[str] = []
        for dirpath, dirnames, filenames in filestore.walk(root_dir):
            for _ in dirnames:
                visit()
            for file_name in filenames:
                if file_name != DIRECTORY_GUARD_NAME:
                    visit()
                    path = child_path(dirpath, file_name)
                    info = filestore.stat(path)
                    if info.is_file and not info.is_symlink:
                        paths.append(path)
        return sorted(paths)

    iter_names = getattr(filestore, "iter_names", filestore.listdir)
    paths = []
    for name in iter_names(root_dir):
        if name == DIRECTORY_GUARD_NAME:
            continue
        visit()
        path = child_path(root_dir, name)
        info = filestore.stat(path)
        if info.is_symlink:
            raise PermissionError("Catalog contains a symbolic directory entry")
        if info.is_file:
            paths.append(path)
    return sorted(paths)



def _file_metadata(path: str, *, filestore: FileStore):
    info = filestore.stat(path)
    if not info.is_file or info.is_symlink:
        raise PermissionError("Catalog entry is no longer a regular file")
    mtime = datetime.fromtimestamp(info.mtime, timezone.utc).isoformat(timespec="seconds") if info.mtime is not None else None
    return info.size, info.mtime, mtime


def _build_record(
    path: str,
    *,
    root_dir: str,
    filestore: FileStore,
    allowed_extensions: set[str],
) -> FrgCatalogRecord:
    """Строит одну запись каталога по конкретному пути."""
    parsed = parse_file_name(path)
    size_bytes, mtime, mtime_iso = _file_metadata(path, filestore=filestore)

    is_supported_extension = parsed.extension in allowed_extensions
    family_rule = parsed.family_rule

    validity_reason = "ok"
    is_valid = True

    if not is_supported_extension:
        is_valid = False
        validity_reason = "unsupported_extension"
    elif family_rule is None:
        is_valid = False
        validity_reason = "family_not_recognized"
    elif parsed.period_date is None:
        is_valid = False
        validity_reason = "period_not_parsed"
    elif family_rule.min_period_date is not None and parsed.period_date < family_rule.min_period_date:
        is_valid = False
        validity_reason = "period_older_than_family_min_date"

    return FrgCatalogRecord(
        root_dir=str(root_dir),
        path=str(path),
        file_name=parsed.file_name,
        extension=parsed.extension,
        normalized_name=parsed.normalized_name,
        name_origin=parsed.name_origin,
        name_priority=parsed.name_priority,
        family_code=family_rule.code if family_rule else None,
        family_name=family_rule.title if family_rule else None,
        file_label=family_rule.file_label if family_rule else None,
        parser_group=family_rule.parser_group if family_rule else None,
        parser_key=family_rule.parser_key if family_rule else None,
        period_mode=family_rule.period_mode if family_rule else None,
        period_date=parsed.period_date,
        period_date_text=parsed.period_date_text,
        week_no=parsed.week_no,
        has_week_marker=parsed.has_week_marker,
        has_q_marker=parsed.has_q_marker,
        snapshot_day=parsed.period_date.day if parsed.period_date else None,
        is_supported_extension=is_supported_extension,
        is_recognized=family_rule is not None,
        is_valid=is_valid,
        validity_reason=validity_reason,
        size_bytes=size_bytes,
        mtime=mtime,
        mtime_iso=mtime_iso,
    )



def _mark_superseded_weekly_files(df: pd.DataFrame) -> pd.DataFrame:
    """Помечает устаревшие недельные файлы внутри одного месяца как неактуальные."""
    if df.empty:
        return df

    result = df.copy()
    weekly_mask = (
        result["is_valid"].eq(True)
        & result["period_mode"].eq("weekly")
        & result["family_code"].notna()
        & result["period_date"].notna()
        & result["week_no"].notna()
    )

    if not weekly_mask.any():
        return result

    weekly_df = result.loc[weekly_mask, ["family_code", "period_date", "week_no"]].copy()
    weekly_df["week_no"] = pd.to_numeric(weekly_df["week_no"], errors="coerce").fillna(0).astype(int)
    weekly_df["period_month"] = weekly_df["period_date"].dt.to_period("M")
    max_week_by_month = weekly_df.groupby(["family_code", "period_month"])["week_no"].transform("max")
    superseded_index = weekly_df.index[weekly_df["week_no"] < max_week_by_month]

    if len(superseded_index) == 0:
        return result

    result.loc[superseded_index, "is_valid"] = False
    result.loc[superseded_index, "validity_reason"] = "superseded_by_newer_week_in_same_month"
    return result



def build_frg_catalog(
    root_dir: str,
    *,
    recursive: bool = False,
    filestore: FileStore,
    allowed_extensions: set[str] | None = None,
    budget: BudgetMeter | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> pd.DataFrame:
    """Сканирует каталог FRG и возвращает полный каталог файлов."""
    extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS

    def visit():
        if checkpoint is not None:
            checkpoint()
        if budget is not None:
            budget.charge("objects", 1)

    paths = _iter_paths(root_dir, filestore=filestore, recursive=recursive, visit=visit)
    records = []
    for path in paths:
        if checkpoint is not None:
            checkpoint()
        records.append(_build_record(
            path, root_dir=root_dir, filestore=filestore, allowed_extensions=extensions,
        ))

    if not records:
        return pd.DataFrame(
            columns=[
                "root_dir",
                "path",
                "file_name",
                "extension",
                "normalized_name",
                "name_origin",
                "name_priority",
                "family_code",
                "family_name",
                "file_label",
                "parser_group",
                "parser_key",
                "period_mode",
                "period_date",
                "period_date_text",
                "week_no",
                "has_week_marker",
                "has_q_marker",
                "snapshot_day",
                "is_supported_extension",
                "is_recognized",
                "is_valid",
                "validity_reason",
                "size_bytes",
                "mtime",
                "mtime_iso",
            ]
        )

    df = pd.DataFrame([record.to_dict() for record in records])
    df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
    df = _mark_superseded_weekly_files(df)
    df = df.sort_values(
        by=["is_valid", "family_code", "period_date", "week_no", "name_priority", "file_name"],
        ascending=[False, True, True, True, False, True],
        na_position="last",
    ).reset_index(drop=True)
    return df
