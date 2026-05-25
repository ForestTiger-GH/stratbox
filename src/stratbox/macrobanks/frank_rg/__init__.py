"""Публичный вход в первый этап работы с файлами Frank RG."""

from stratbox.macrobanks.frank_rg.api import (
    build_frank_rg_catalog,
    run_frank_rg_stage1,
    select_latest_frank_rg_files,
)

__all__ = [
    "build_frank_rg_catalog",
    "select_latest_frank_rg_files",
    "run_frank_rg_stage1",
]
