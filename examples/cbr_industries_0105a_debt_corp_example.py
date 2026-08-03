"""Пример построения потока Банка России 01_05_A_Debt_corp."""

from stratbox.macrobanks.cbr_industries import (
    CBR_SORS_INDEX_URL,
    Cbr0105ADebtCorpStreamBuildRequest,
    build_cbr_0105a_debt_corp_stream,
)


result = build_cbr_0105a_debt_corp_stream(
    Cbr0105ADebtCorpStreamBuildRequest(
        index_url=CBR_SORS_INDEX_URL,
        date_from="2026-04-01",
        date_to="2026-06-01",
        source_cache_dir="cache/cbr_industries/01_05_A_Debt_corp",
    )
)

print(result.dates)
print(result.df_stream.head())
