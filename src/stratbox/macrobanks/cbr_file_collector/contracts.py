"""
contracts — контракты домена загрузки исходных файлов Банка России.

Домен работает с жёстким встроенным реестром источников и возвращает
структурированный результат загрузки без предобработки содержимого файлов.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Mapping


SaveMode = Literal["zip", "files"]


@dataclass(frozen=True, slots=True)
class CbrFileRegistryItem:
    """Один встроенный источник исходного файла Банка России."""

    source_id: str
    url: str
    title: str = ""
    expected_file_name: str | None = None


@dataclass(frozen=True, slots=True)
class CbrFileCollectRequest:
    """Запрос на загрузку и сохранение исходных файлов Банка России."""

    target_path: str
    save_mode: SaveMode = "zip"
    overwrite: bool = True
    continue_on_error: bool = True
    retry_attempts: int = 3
    retry_backoff_sec: float = 0.5
    timeout_sec: int = 60
    min_bytes_ok: int = 512
    try_case_variants: bool = True
    plugin_only: bool = True
    headers: Mapping[str, str] | None = None
    show_progress: bool = True


@dataclass(frozen=True, slots=True)
class CbrDownloadedFileSource:
    """Внутреннее представление скачанного источника с байтами файла."""

    source_id: str
    url: str
    file_name: str
    content: bytes = field(repr=False)
    size_bytes: int = 0
    used_url: str = ""
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class CbrCollectedFile:
    """Сведения об одном успешно собранном исходном файле."""

    source_id: str
    url: str
    file_name: str
    size_bytes: int
    used_url: str
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class CbrFileCollectFailure:
    """Сведения о неудачной загрузке одного источника."""

    source_id: str
    url: str
    error: str
    status_code: int | None = None
    attempts_used: int = 0
    used_url: str | None = None
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class CbrFileCollectResult:
    """Итог загрузки и сохранения набора исходных файлов Банка России."""

    target_path: str
    save_mode: SaveMode
    saved_paths: tuple[str, ...]
    collected_files: tuple[CbrCollectedFile, ...]
    failures: tuple[CbrFileCollectFailure, ...]
    requested_count: int
    success_count: int
    failure_count: int

    @property
    def ok(self) -> bool:
        return self.failure_count == 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


__all__ = [
    "CbrCollectedFile",
    "CbrDownloadedFileSource",
    "CbrFileRegistryItem",
    "CbrFileCollectRequest",
    "CbrFileCollectResult",
    "CbrFileCollectFailure",
    "SaveMode",
]
