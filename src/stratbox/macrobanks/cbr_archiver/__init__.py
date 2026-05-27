"""cbr_archiver — скачивание и сохранение исходных статистических файлов Банка России."""

from stratbox.macrobanks.cbr_archiver.api import run_cbr_archiver
from stratbox.macrobanks.cbr_archiver.models import CbrArchiveSource, CbrArchiverRunResult
from stratbox.macrobanks.cbr_archiver.registry import DEFAULT_CBR_ARCHIVE_SOURCES

__all__ = [
    "CbrArchiveSource",
    "CbrArchiverRunResult",
    "DEFAULT_CBR_ARCHIVE_SOURCES",
    "run_cbr_archiver",
]
