"""
Публичный API первого этапа обработки Frank RG.

Назначение:
- построить каталог файлов;
- выбрать наиболее свежие файлы по семействам;
- прогнать диспетчеризацию в заглушки парсеров.
"""

from __future__ import annotations

from stratbox.base.filestore import FileStore
from stratbox.macrobanks.frank_rg.catalog import build_frank_rg_catalog
from stratbox.macrobanks.frank_rg.dispatch import dispatch_latest_frank_rg_files
from stratbox.macrobanks.frank_rg.selection import select_latest_frank_rg_files


def run_frank_rg_stage1(
    root_dir: str,
    *,
    recursive: bool = False,
    filestore: FileStore | None = None,
) -> dict[str, object]:
    """Запускает первый этап Frank RG и возвращает набор таблиц."""
    catalog_df = build_frank_rg_catalog(
        root_dir,
        recursive=recursive,
        filestore=filestore,
    )
    latest_df = select_latest_frank_rg_files(catalog_df)
    dispatch_df = dispatch_latest_frank_rg_files(latest_df)

    return {
        "catalog": catalog_df,
        "latest": latest_df,
        "dispatch": dispatch_df,
    }


__all__ = [
    "build_frank_rg_catalog",
    "select_latest_frank_rg_files",
    "run_frank_rg_stage1",
]
