"""
Публичный API первого этапа обработки FRG.

Назначение:
- построить каталог файлов;
- выбрать наиболее свежие файлы по семействам;
- прогнать диспетчеризацию в заглушки парсеров;
- подготовить и выполнить зачистку каталога по найденным семействам.
"""

from __future__ import annotations

from stratbox.base.filestore import FileStore
from stratbox.macrobanks.frg.catalog import build_frg_catalog
from stratbox.macrobanks.frg.cleanup import (
    apply_frg_cleanup_plan,
    build_frg_actuals_archive_name,
    build_frg_cleanup_plan,
    build_frg_latest_file_name,
    run_frg_cleanup,
)
from stratbox.macrobanks.frg.dispatch import dispatch_latest_frg_files
from stratbox.macrobanks.frg.selection import select_latest_frg_files


def run_frg_stage1(
    root_dir: str,
    *,
    recursive: bool = False,
    filestore: FileStore | None = None,
) -> dict[str, object]:
    """Запускает первый этап FRG и возвращает набор таблиц."""
    catalog_df = build_frg_catalog(
        root_dir,
        recursive=recursive,
        filestore=filestore,
    )
    latest_df = select_latest_frg_files(catalog_df)
    dispatch_df = dispatch_latest_frg_files(latest_df)

    return {
        "catalog": catalog_df,
        "latest": latest_df,
        "dispatch": dispatch_df,
    }


__all__ = [
    "apply_frg_cleanup_plan",
    "build_frg_actuals_archive_name",
    "build_frg_catalog",
    "build_frg_cleanup_plan",
    "build_frg_latest_file_name",
    "run_frg_cleanup",
    "select_latest_frg_files",
    "run_frg_stage1",
]
