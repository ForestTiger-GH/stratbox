from __future__ import annotations

from pathlib import Path

from app.runtime.context import AppContext


def default_cbr_target_dir(context: AppContext) -> str:
    base = context.workspace_root_path if context.workspace_root_path is not None else Path('.')
    return str((base / 'output' / 'cbr_file_collector').as_posix())
