"""Поток, pivot set и Excel-книга Банка России 01_05_A_Debt_corp."""

from stratbox.macrobanks.cbr_industries import (
    CBR_SORS_INDEX_URL,
    Cbr0105ADebtCorpPivotRequest,
    Cbr0105ADebtCorpPivotWorkbookRequest,
    Cbr0105ADebtCorpStreamBuildRequest,
    build_cbr_0105a_debt_corp_pivot_set,
    build_cbr_0105a_debt_corp_stream,
    save_cbr_0105a_debt_corp_pivot_workbook,
)


stream_result = build_cbr_0105a_debt_corp_stream(
    Cbr0105ADebtCorpStreamBuildRequest(
        index_url=CBR_SORS_INDEX_URL,
        date_from="2026-04-01",
        date_to="2026-06-01",
        source_cache_dir="cache/cbr_industries/01_05_A_Debt_corp",
    )
)

# Фильтр выполняется до pivot: здесь выбирается отраслевой итог.
filtered_stream = stream_result.df_stream.loc[
    stream_result.df_stream["industry_code"].astype("object") == "total"
].copy()

pivot_set = build_cbr_0105a_debt_corp_pivot_set(
    filtered_stream,
    Cbr0105ADebtCorpPivotRequest(
        row_dimension="region_code",
        column_dimension="report_date",
        value_columns=("value",),
        sheet_dimensions=("measure", "currency_scope"),
    ),
    stream_result=stream_result,
)

saved = save_cbr_0105a_debt_corp_pivot_workbook(
    pivot_set,
    Cbr0105ADebtCorpPivotWorkbookRequest(
        out_path="output/01_05_A_Debt_corp_total_by_regions.xlsx",
        overwrite=True,
    ),
)

print(saved.output_path)
print(saved.sheet_names)
