"""
Пример запуска домена счетов эскроу.

Сценарий:
- месячные источники ЦБ сохраняются в кэш-папку;
- итоговый файл выгружается в zip-архив;
- один и тот же код работает с local FileStore и с plugin FileStore.
"""

from stratbox.base import runtime
from stratbox.macrobanks.escrow import run_escrow_to_xlsx


providers = runtime.get_providers()
print(f"INFO: providers source = {providers.source}")

result = run_escrow_to_xlsx(
    out_path="outputs/Escrow Accounts.zip",
    archive=True,
    source_cache_dir="cache/escrow",
    show_progress=True,
)

print(f"INFO: output path = {result.output_path}")
print(f"INFO: source files = {len(result.source_files)}")
print(f"INFO: dates = {len(result.dates)}")
print(f"INFO: indicators = {len(result.indicators)}")
print(f"INFO: regions = {len(result.regions)}")
print(f"INFO: long rows = {result.rows_long}")
