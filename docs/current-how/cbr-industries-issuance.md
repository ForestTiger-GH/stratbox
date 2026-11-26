# Corporate loan issuance and reference periods

The continuing series `cbr.corporate_lending.issuance_0104a` interprets published `01_04_A_New_loans_corp_YYYYMMDD.xlsx` workbooks as loan flows. The release `20260801` represents issuance during July 2026. Release date and reference interval remain separate; the canonical observation period and rendered month use the actual issuance interval.

Physical workbook decoding precedes source-specific worksheet and geometry validation. The reviewed layout checks 26 published industries and 96 geographic rows. Three currency scopes represent rubles, foreign currency/precious metals and the published total. Issuance contains `new_loans`, with no invented overdue measure. All numerical source cells participate in validation, including when a caller later selects a subset.

Published totals remain source values. APK and LPK are explicit formulas using the five required published components for the same region, period, currency, units and perimeter. A missing or incompatible operand blocks calculation. Source values remain available independently of the derived metrics.

Independently rounded currency-component differences above one million RUB generate warnings without altering source values. Negative observations are scientific errors; blanks remain missing. Geographic labels preserve source perimeter and reviewed aliases.

Invoke `scenario.series.refresh` with the series target for source interpretation, then an explicit calculation target for APK or a product target for presentation. Use [the supplied source CLI](../../examples/source_route.py) and [CBR routes](cbr-data-pipeline.md). Publication requests select actual discovered assets; URLs are not guessed from presumed release dates.
