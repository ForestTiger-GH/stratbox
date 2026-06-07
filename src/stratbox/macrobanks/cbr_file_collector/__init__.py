"""cbr_file_collector — загрузка и сохранение исходных статистических файлов Банка России."""

from stratbox.macrobanks.cbr_file_collector.contracts import (
    CbrCollectedFile,
    CbrFileRegistryItem,
    CbrFileCollectRequest,
    CbrFileCollectResult,
    CbrFileCollectFailure,
)
from stratbox.macrobanks.cbr_file_collector.operations import collect_cbr_files, list_cbr_file_sources
from stratbox.macrobanks.cbr_file_collector.registry import (
    DEFAULT_CBR_FILE_SOURCES,
    DEFAULT_CBR_FILES_ARCHIVE_NAME,
    DEFAULT_CBR_FILES_DIRECTORY_NAME,
)

__all__ = [
    "CbrCollectedFile",
    "CbrFileRegistryItem",
    "CbrFileCollectRequest",
    "CbrFileCollectResult",
    "CbrFileCollectFailure",
    "DEFAULT_CBR_FILE_SOURCES",
    "DEFAULT_CBR_FILES_ARCHIVE_NAME",
    "DEFAULT_CBR_FILES_DIRECTORY_NAME",
    "collect_cbr_files",
    "list_cbr_file_sources",
]
