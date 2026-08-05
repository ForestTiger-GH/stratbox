"""Полные книги АПК и опубликованного ВСЕГО с февраля 2019 года."""

from stratbox.macrobanks.cbr_industries import (
    CBR_SORS_INDEX_URL,
    Cbr0105ADebtCorpIndustryWorkbookRequest,
    Cbr0105ADebtCorpStreamBuildRequest,
    build_cbr_0105a_debt_corp_stream,
    export_cbr_0105a_debt_corp_industry_workbook,
)


stream_result = build_cbr_0105a_debt_corp_stream(
    Cbr0105ADebtCorpStreamBuildRequest(
        index_url=CBR_SORS_INDEX_URL,
        date_from="2019-02-01",
        date_to=None,
        source_cache_dir="/content/stratbox_cache/01_05_A_Debt_corp",
        plugin_only=False,
        show_progress=True,
        source_error_policy="fail_fast",
    )
)

if not stream_result.ok:
    raise RuntimeError(
        "Поток не прошел проверку: "
        f"failures={stream_result.failures}, "
        f"validation_issues={stream_result.validation_issues}"
    )

apk_workbook = export_cbr_0105a_debt_corp_industry_workbook(
    stream_result,
    Cbr0105ADebtCorpIndustryWorkbookRequest(
        out_path="/content/01_05_A_Debt_corp_АПК_по_регионам.xlsx",
        industry_code="apk",
        overwrite=True,
    ),
)

total_workbook = export_cbr_0105a_debt_corp_industry_workbook(
    stream_result,
    Cbr0105ADebtCorpIndustryWorkbookRequest(
        out_path="/content/01_05_A_Debt_corp_ВСЕГО_по_регионам.xlsx",
        industry_code="total",
        overwrite=True,
    ),
)

print(apk_workbook.output_path)
print(total_workbook.output_path)
