"""Locate packaged registry snapshots by their published filename versions."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from datetime import date
import re


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


def _resource_version(rel_path: str) -> tuple[date, str]:
    name = rel_path.rsplit("/", 1)[-1]
    stamp = re.search(r"_T([0-9]{2})_([0-9]{2})_([0-9]{4})(?:\.|_)", name)
    if stamp:
        day, month, year = map(int, stamp.groups())
        return date(year, month, day), name
    stamp = re.search(r"(?<![0-9])(20[0-9]{6})(?![0-9])", name)
    if stamp:
        value = stamp[1]
        return date(int(value[:4]), int(value[4:6]), int(value[6:])), name
    return date.min, name


def pick_latest_by_suffix(package: str, rel_dir: str, suffix: str) -> RegistryFile:
    """
    Выбирает самый свежий файл (by its versioned filename) с заданным suffix в папке rel_dir.

    Если файлов нет — кидает понятную ошибку.
    """
    paths = _list_resource_paths(package, rel_dir)
    matches = [p for p in paths if p.lower().endswith(suffix.lower())]
    if not matches:
        raise FileNotFoundError(
            f'Registry resource not found: package="{package}", dir="{rel_dir}", suffix="{suffix}"'
        )

    latest = max(matches, key=_resource_version)
    name = latest.split("/")[-1]
    return RegistryFile(path=latest, name=name, kind=suffix.lstrip(".").lower())


def pick_latest_by_prefix(package: str, rel_dir: str, prefix: str, suffix: str = ".csv") -> RegistryFile:
    """
    Выбирает самый свежий файл (by its versioned filename) с именем prefix*suffix в папке rel_dir.
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

    latest = max(matches, key=_resource_version)
    name = latest.split("/")[-1]
    kind = prefix.lower().rstrip("_").rstrip("-")
    return RegistryFile(path=latest, name=name, kind=kind)


def read_resource_bytes(package: str, rel_path: str) -> bytes:
    """
    Читает ресурс как bytes.
    """
    p = resources.files(package).joinpath(rel_path)
    return p.read_bytes()
