"""
_loader.py — служебные функции для чтения ресурсов (файлов), встроенных в пакет.

Важно:
- реестры лежат в src/stratbox/registries/_resources/...
- чтение идёт через importlib.resources, чтобы работало и из исходников, и из установленного пакета
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class RegistryFile:
    """Структура для выбранного файла реестра."""
    path: str  # относительный путь внутри пакета (например "_resources/cbr_banks/xxx.xlsx")
    name: str  # имя файла
    kind: str  # тип (xlsx/csv/meta/structure/data)


def _list_resource_paths(package: str, rel_dir: str) -> list[str]:
    """
    Возвращает список относительных путей (внутри package) для файлов в rel_dir.

    Пример:
        package="stratbox.registries"
        rel_dir="_resources/cbr_banks"
    """
    root = resources.files(package).joinpath(rel_dir)
    if not root.is_dir():
        return []

    out: list[str] = []
    for entry in root.iterdir():
        if entry.is_file():
            # получаем относительный путь "rel_dir/filename"
            out.append(f"{rel_dir}/{entry.name}")
    return out


def _resource_mtime(package: str, rel_path: str) -> float:
    """
    Пытается получить mtime ресурса. В установленном wheel ресурсы обычно
    доступны как реальные файлы (или временная распаковка), поэтому stat() часто работает.

    Если вдруг stat недоступен, возвращает 0.0 — тогда "самый новый" не определится,
    но при наличии единственного файла это не важно.
    """
    try:
        p = resources.files(package).joinpath(rel_path)
        return p.stat().st_mtime
    except Exception:
        return 0.0


def pick_latest_by_suffix(package: str, rel_dir: str, suffix: str) -> RegistryFile:
    """
    Выбирает самый свежий файл (по времени изменения) с заданным suffix в папке rel_dir.

    Если файлов нет — кидает понятную ошибку.
    """
    paths = _list_resource_paths(package, rel_dir)
    matches = [p for p in paths if p.lower().endswith(suffix.lower())]
    if not matches:
        raise FileNotFoundError(
            f'Registry resource not found: package="{package}", dir="{rel_dir}", suffix="{suffix}"'
        )

    latest = max(matches, key=lambda rp: _resource_mtime(package, rp))
    name = latest.split("/")[-1]
    return RegistryFile(path=latest, name=name, kind=suffix.lstrip(".").lower())


def pick_latest_by_prefix(package: str, rel_dir: str, prefix: str, suffix: str = ".csv") -> RegistryFile:
    """
    Выбирает самый свежий файл (по времени изменения) с именем prefix*suffix в папке rel_dir.
    """
    paths = _list_resource_paths(package, rel_dir)
    matches = []
    for p in paths:
        fname = p.split("/")[-1].lower()
        if fname.startswith(prefix.lower()) and fname.endswith(suffix.lower()):
            matches.append(p)

    if not matches:
        raise FileNotFoundError(
            f'Registry resource not found: package="{package}", dir="{rel_dir}", pattern="{prefix}*{suffix}"'
        )

    latest = max(matches, key=lambda rp: _resource_mtime(package, rp))
    name = latest.split("/")[-1]
    kind = prefix.lower().rstrip("_").rstrip("-")
    return RegistryFile(path=latest, name=name, kind=kind)


def read_resource_bytes(package: str, rel_path: str) -> bytes:
    """
    Читает ресурс как bytes.
    """
    p = resources.files(package).joinpath(rel_path)
    return p.read_bytes()
