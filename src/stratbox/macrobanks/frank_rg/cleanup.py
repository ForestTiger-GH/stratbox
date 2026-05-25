"""
Подготовка и выполнение зачистки каталога Frank RG.

Логика модуля:
- сканирует только верхний уровень каталога без захода во вложенные папки;
- определяет актуальный файл по каждому семейству;
- готовит план копирования/переименования актуальных файлов;
- по запросу удаляет прочие обработанные файлы и файлы, исключенные только из-за слишком старого периода.

Важно:
- модуль не открывает содержимое файлов и не меняет их формат;
- все операции выполняются только через FileStore stratbox.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.frank_rg.catalog import build_frank_rg_catalog
from stratbox.macrobanks.frank_rg.selection import select_latest_frank_rg_files


_FORBIDDEN_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*]')


def _join_path(parent: str, name: str) -> str:
    """Склеивает путь в унифицированном виде с косыми слэшами."""
    left = str(parent).replace("\\", "/").rstrip("/")
    right = str(name).replace("\\", "/").lstrip("/")

    if left in ("", "."):
        return right
    if left == "/":
        return f"/{right}"
    return f"{left}/{right}"


def _sanitize_filename_part(text: str) -> str:
    """Подготавливает текст для имени файла без потери основного смысла."""
    value = str(text).strip()
    value = value.replace("\u00a0", " ")
    value = _FORBIDDEN_FILENAME_CHARS_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    return value


def build_frank_rg_latest_file_name(period_text: str | None, family_name: str | None, extension: str | None) -> str:
    """Формирует стандартное имя итогового файла по актуальному семейству."""
    left = _sanitize_filename_part(period_text or "unknown-period")
    right = _sanitize_filename_part(family_name or "Unknown family")
    ext = str(extension or "").strip().lower()

    if ext and not ext.startswith("."):
        ext = f".{ext}"

    return f"{left}_{right}{ext}"


def _should_delete_row(row: dict[str, Any], latest_paths: set[str]) -> bool:
    """Определяет, нужно ли удалить файл в режиме зачистки."""
    path = str(row.get("path") or "")
    if path in latest_paths:
        return False

    is_valid = bool(row.get("is_valid"))
    validity_reason = str(row.get("validity_reason") or "")

    if is_valid:
        return True

    return validity_reason == "period_older_than_family_min_date"


def build_frank_rg_cleanup_plan(
    root_dir: str,
    *,
    delete_others: bool = False,
    filestore: FileStore | None = None,
) -> dict[str, pd.DataFrame]:
    """Строит план зачистки каталога Frank RG без выполнения файловых операций."""
    fs = filestore or get_filestore()

    catalog_df = build_frank_rg_catalog(
        root_dir,
        recursive=False,
        filestore=fs,
    )
    latest_df = select_latest_frank_rg_files(catalog_df)

    plan_rows: list[dict[str, Any]] = []
    latest_paths = set(latest_df["path"].dropna().astype(str).tolist())

    for row in latest_df.to_dict(orient="records"):
        source_path = str(row.get("path") or "")
        target_name = build_frank_rg_latest_file_name(
            period_text=row.get("period_date_text"),
            family_name=row.get("family_name"),
            extension=row.get("extension"),
        )
        target_path = _join_path(root_dir, target_name)

        if source_path == target_path:
            action_type = "keep_latest"
            action_reason = "latest_already_has_target_name"
            will_execute = False
        else:
            action_type = "rename_latest" if delete_others else "copy_latest"
            action_reason = "latest_file_for_family"
            will_execute = True

        plan_rows.append(
            {
                "action_type": action_type,
                "action_reason": action_reason,
                "will_execute": will_execute,
                "family_code": row.get("family_code"),
                "family_name": row.get("family_name"),
                "period_mode": row.get("period_mode"),
                "period_date": row.get("period_date"),
                "period_date_text": row.get("period_date_text"),
                "week_no": row.get("week_no"),
                "source_path": source_path,
                "source_file_name": row.get("file_name"),
                "target_path": target_path,
                "target_file_name": target_name,
            }
        )

    if delete_others and not catalog_df.empty:
        for row in catalog_df.to_dict(orient="records"):
            if not _should_delete_row(row, latest_paths=latest_paths):
                continue

            plan_rows.append(
                {
                    "action_type": "delete_source",
                    "action_reason": str(row.get("validity_reason") or "processed_non_latest_file"),
                    "will_execute": True,
                    "family_code": row.get("family_code"),
                    "family_name": row.get("family_name"),
                    "period_mode": row.get("period_mode"),
                    "period_date": row.get("period_date"),
                    "period_date_text": row.get("period_date_text"),
                    "week_no": row.get("week_no"),
                    "source_path": row.get("path"),
                    "source_file_name": row.get("file_name"),
                    "target_path": None,
                    "target_file_name": None,
                }
            )

    plan_df = pd.DataFrame(plan_rows)

    if plan_df.empty:
        plan_df = pd.DataFrame(
            columns=[
                "action_type",
                "action_reason",
                "will_execute",
                "family_code",
                "family_name",
                "period_mode",
                "period_date",
                "period_date_text",
                "week_no",
                "source_path",
                "source_file_name",
                "target_path",
                "target_file_name",
            ]
        )
    else:
        plan_df["period_date"] = pd.to_datetime(plan_df["period_date"], errors="coerce")
        plan_df["_action_order"] = plan_df["action_type"].map(
            {
                "rename_latest": 10,
                "copy_latest": 20,
                "keep_latest": 30,
                "delete_source": 40,
            }
        ).fillna(99).astype(int)
        plan_df = plan_df.sort_values(
            by=["_action_order", "family_code", "period_date", "week_no", "source_file_name"],
            ascending=[True, True, False, False, True],
            na_position="last",
        ).drop(columns=["_action_order"]).reset_index(drop=True)

    return {
        "catalog": catalog_df,
        "latest": latest_df,
        "plan": plan_df,
    }


def apply_frank_rg_cleanup_plan(
    plan_df: pd.DataFrame,
    *,
    filestore: FileStore | None = None,
    replace_existing: bool = False,
) -> pd.DataFrame:
    """Выполняет подготовленный план зачистки через FileStore."""
    fs = filestore or get_filestore()

    if plan_df is None or plan_df.empty:
        return pd.DataFrame(
            columns=[
                "action_type",
                "status",
                "message",
                "source_path",
                "target_path",
                "family_code",
                "family_name",
            ]
        )

    logs: list[dict[str, Any]] = []

    for row in plan_df.to_dict(orient="records"):
        action_type = str(row.get("action_type") or "")
        source_path = row.get("source_path")
        target_path = row.get("target_path")
        family_code = row.get("family_code")
        family_name = row.get("family_name")

        if not bool(row.get("will_execute")):
            logs.append(
                {
                    "action_type": action_type,
                    "status": "noop",
                    "message": "Action is not required.",
                    "source_path": source_path,
                    "target_path": target_path,
                    "family_code": family_code,
                    "family_name": family_name,
                }
            )
            continue

        try:
            if action_type == "copy_latest":
                if not fs.exists(str(source_path)):
                    raise FileNotFoundError(f"Source file does not exist: {source_path}")

                if fs.exists(str(target_path)):
                    if replace_existing:
                        fs.remove(str(target_path))
                    else:
                        logs.append(
                            {
                                "action_type": action_type,
                                "status": "skipped",
                                "message": "Target file already exists.",
                                "source_path": source_path,
                                "target_path": target_path,
                                "family_code": family_code,
                                "family_name": family_name,
                            }
                        )
                        continue

                fs.copy(str(source_path), str(target_path))
                logs.append(
                    {
                        "action_type": action_type,
                        "status": "done",
                        "message": "File copied.",
                        "source_path": source_path,
                        "target_path": target_path,
                        "family_code": family_code,
                        "family_name": family_name,
                    }
                )
                continue

            if action_type == "rename_latest":
                if not fs.exists(str(source_path)):
                    raise FileNotFoundError(f"Source file does not exist: {source_path}")

                if fs.exists(str(target_path)):
                    if replace_existing:
                        fs.remove(str(target_path))
                    else:
                        logs.append(
                            {
                                "action_type": action_type,
                                "status": "skipped",
                                "message": "Target file already exists.",
                                "source_path": source_path,
                                "target_path": target_path,
                                "family_code": family_code,
                                "family_name": family_name,
                            }
                        )
                        continue

                fs.rename(str(source_path), str(target_path))
                logs.append(
                    {
                        "action_type": action_type,
                        "status": "done",
                        "message": "File renamed.",
                        "source_path": source_path,
                        "target_path": target_path,
                        "family_code": family_code,
                        "family_name": family_name,
                    }
                )
                continue

            if action_type == "delete_source":
                if fs.exists(str(source_path)):
                    fs.remove(str(source_path))
                    logs.append(
                        {
                            "action_type": action_type,
                            "status": "done",
                            "message": "File deleted.",
                            "source_path": source_path,
                            "target_path": target_path,
                            "family_code": family_code,
                            "family_name": family_name,
                        }
                    )
                else:
                    logs.append(
                        {
                            "action_type": action_type,
                            "status": "skipped",
                            "message": "Source file does not exist.",
                            "source_path": source_path,
                            "target_path": target_path,
                            "family_code": family_code,
                            "family_name": family_name,
                        }
                    )
                continue

            logs.append(
                {
                    "action_type": action_type,
                    "status": "error",
                    "message": "Unknown action type.",
                    "source_path": source_path,
                    "target_path": target_path,
                    "family_code": family_code,
                    "family_name": family_name,
                }
            )
        except Exception as exc:
            logs.append(
                {
                    "action_type": action_type,
                    "status": "error",
                    "message": str(exc),
                    "source_path": source_path,
                    "target_path": target_path,
                    "family_code": family_code,
                    "family_name": family_name,
                }
            )

    return pd.DataFrame(logs)[
        [
            "action_type",
            "status",
            "message",
            "source_path",
            "target_path",
            "family_code",
            "family_name",
        ]
    ]


def run_frank_rg_cleanup(
    root_dir: str,
    *,
    delete_others: bool = False,
    execute: bool = False,
    replace_existing: bool = False,
    filestore: FileStore | None = None,
) -> dict[str, pd.DataFrame]:
    """Готовит или выполняет зачистку каталога Frank RG."""
    fs = filestore or get_filestore()

    result = build_frank_rg_cleanup_plan(
        root_dir,
        delete_others=delete_others,
        filestore=fs,
    )
    plan_df = result["plan"]

    if execute:
        execution_df = apply_frank_rg_cleanup_plan(
            plan_df,
            filestore=fs,
            replace_existing=replace_existing,
        )
    else:
        execution_df = pd.DataFrame(
            columns=[
                "action_type",
                "status",
                "message",
                "source_path",
                "target_path",
                "family_code",
                "family_name",
            ]
        )

    return {
        "catalog": result["catalog"],
        "latest": result["latest"],
        "plan": plan_df,
        "execution": execution_df,
    }
