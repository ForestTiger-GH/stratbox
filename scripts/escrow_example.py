"""
Пример запуска домена счетов эскроу.

Сценарий:
- месячные источники ЦБ сохраняются в кэш-папку;
- строится исторический набор данных;
- итоговый workbook выгружается в zip-архив;
- один и тот же код работает с local FileStore и с plugin FileStore.
"""

from stratbox.base import runtime
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    EscrowViewBuildRequest,
    EscrowWorkbookExportRequest,
    build_escrow_history,
    export_escrow_workbook,
)


providers = runtime.get_providers()
print(f"INFO: providers source = {providers.source}")

history = build_escrow_history(
    EscrowHistoryBuildRequest(
        index_url="https://www.cbr.ru/statistics/bank_sector/equity_const_financing/",
        source_cache_dir="cache/escrow",
        show_progress=True,
    )
)

result = export_escrow_workbook(
    history,
    EscrowWorkbookExportRequest(
        out_path="outputs/Escrow Accounts.zip",
        archive=True,
        show_progress=True,
    ),
    view_request=EscrowViewBuildRequest(regions_mode="latest"),
)

print(f"INFO: output path = {result.output_path}")
print(f"INFO: source files = {len(result.source_files)}")
print(f"INFO: dates = {len(result.dates)}")
print(f"INFO: indicators = {len(result.indicators)}")
print(f"INFO: regions = {len(result.regions)}")
print(f"INFO: long rows = {result.rows_long}")
