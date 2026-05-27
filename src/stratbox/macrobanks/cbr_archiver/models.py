"""
models — модели данных домена cbr_archiver.

Домен cbr_archiver работает только с исходными файлами Банка России:
- описывает источники скачивания;
- хранит скачанные bytes без изменения содержимого;
- возвращает понятный итог выполнения.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class CbrArchiveSource:
    """Описание одного исходного файла Банка России для скачивания."""

    url: str
    group: str = "other"
    code: str = ""
    title: str = ""
    file_name: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class CbrDownloadedFile:
    """Скачанный исходный файл Банка России."""

    source: CbrArchiveSource
    file_name: str
    content: bytes = field(repr=False)
    size_bytes: int
    used_url: str
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class CbrDownloadFailure:
    """Ошибка скачивания одного исходного файла Банка России."""

    source: CbrArchiveSource
    error: str
    status_code: int | None = None
    used_url: str | None = None
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class CbrArchiverRunResult:
    """Краткий итог запуска архиватора исходных файлов Банка России."""

    output_path: str
    output_mode: str
    saved_paths: list[str]
    downloaded_files: list[str]
    failed_urls: list[str]
    total_sources: int
    downloaded_count: int
    failed_count: int
    archive_name: str | None = None

    @property
    def ok(self) -> bool:
        """Возвращает True, если все источники скачаны успешно."""
        return self.failed_count == 0

    def to_dict(self) -> dict[str, object]:
        """Преобразует итог выполнения в обычный словарь."""
        return asdict(self)


__all__ = [
    "CbrArchiveSource",
    "CbrArchiverRunResult",
    "CbrDownloadFailure",
    "CbrDownloadedFile",
]
