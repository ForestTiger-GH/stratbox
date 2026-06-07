"""cbr_archiver — загрузка и сохранение исходных статистических файлов Банка России."""

from stratbox.macrobanks.cbr_archiver.contracts import (
    CbrCollectedFile,
    CbrRegistryItem,
    CbrSourceCollectRequest,
    CbrSourceCollectResult,
    CbrSourceFailure,
)
from stratbox.macrobanks.cbr_archiver.operations import collect_cbr_sources, list_cbr_sources
from stratbox.macrobanks.cbr_archiver.registry import (
    DEFAULT_CBR_SOURCES,
    DEFAULT_CBR_TARGET_ARCHIVE_NAME,
    DEFAULT_CBR_TARGET_DIRECTORY_NAME,
)

__all__ = [
    "CbrCollectedFile",
    "CbrRegistryItem",
    "CbrSourceCollectRequest",
    "CbrSourceCollectResult",
    "CbrSourceFailure",
    "DEFAULT_CBR_SOURCES",
    "DEFAULT_CBR_TARGET_ARCHIVE_NAME",
    "DEFAULT_CBR_TARGET_DIRECTORY_NAME",
    "collect_cbr_sources",
    "list_cbr_sources",
]
