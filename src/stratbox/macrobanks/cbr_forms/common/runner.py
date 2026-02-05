"""
Модуль содержит общий раннер для форм Банка России:
- генерация дат (передаётся извне)
- скачивание по URL
- распаковка rar
- выбор DBF + чтение в DataFrame
- отдача результата наружу (обычно в виде df_long)

Важно:
- распаковка rar оставлена "исполняемым" кодом внутри раннера (как попросили).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from stratbox.base.filestore import make_workdir
from stratbox.base.net.http import download_bytes
from stratbox.macrobanks.cbr_forms.common.dbf import DBFLayout, read_dbf_to_df
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates, pick_dbf_and_layout


@dataclass(frozen=True)
class RunnerConfig:
    """
    Настройки раннера.
    """
    timeout: int = 60
    retries: int = 2
    backoff: float = 0.5
    min_bytes_ok: int = 512


def _pick_rar_tool() -> str:
    """
    Находит доступную утилиту распаковки rar.
    """
    for c in ["unrar", "7z", "7zz"]:
        if shutil.which(c):
            return c
    raise RuntimeError("No 'unrar' or '7z' found. Install unrar or p7zip.")


def _extract_rar(archive_path: Path, out_dir: Path) -> None:
    """
    Распаковывает rar в out_dir.
    """
    tool = _pick_rar_tool()
    out_dir.mkdir(parents=True, exist_ok=True)

    if tool == "unrar":
        cmd = [tool, "x", "-o+", str(archive_path), str(out_dir)]
    else:
        cmd = [tool, "x", f"-o{out_dir}", str(archive_path), "-y"]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Archive extract failed:\n" + (p.stderr or p.stdout or ""))


def run_dates_to_dbf_df(
    dates: list[pd.Timestamp],
    build_url: Callable[[pd.Timestamp], str],
    candidates: LayoutCandidates,
    prefer_stem_contains: str | None,
    cfg: RunnerConfig | None = None,
) -> list[tuple[str, pd.DataFrame]]:
    """
    Универсальный шаг: по списку дат качает архивы, распаковывает, выбирает DBF, читает в df.

    Возвращает список кортежей:
      (date_str_dd_mm_yyyy, df_dbf)

    df_dbf имеет колонки: REGN, A, B (см. common/dbf.py).
    """
    cfg = cfg or RunnerConfig()

    work_dir = Path(make_workdir(prefix="cbr_forms_"))
    out: list[tuple[str, pd.DataFrame]] = []

    try:
        for i, d in enumerate(dates):
            d = pd.Timestamp(d)
            date_str = d.strftime("%d.%m.%Y")
            url = build_url(d)

            res = download_bytes(
                url=url,
                timeout=cfg.timeout,
                retries=cfg.retries,
                backoff=cfg.backoff,
                min_bytes_ok=cfg.min_bytes_ok,
                headers=None,
            )
            if not res.ok or not res.content:
                continue

            ymd = d.strftime("%Y%m%d")
            rar_path = work_dir / f"tmp_{ymd}.rar"
            rar_path.write_bytes(res.content)

            ex_dir = work_dir / f"ex_{ymd}"
            _extract_rar(rar_path, ex_dir)

            dbf_path, layout = pick_dbf_and_layout(ex_dir, candidates=candidates, prefer_stem_contains=prefer_stem_contains)

            df_dbf = read_dbf_to_df(str(dbf_path), layout=layout)
            out.append((date_str, df_dbf))

        print(f"[INFO] DBF dates processed: {len(out)}")
        return out

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
