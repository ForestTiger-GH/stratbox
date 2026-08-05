"""Strict SORS restoration example for Colab or a local notebook."""

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsPivotRequest,
    SorsRunConfig,
    SorsSourceFiles,
    SorsWorkbookRequest,
    build_sors_pivot,
    export_sors_workbook,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional="01_05_A_Debt_corp_20260601.xlsx",
    national_okved2="01_02_C_Debt_corp_by_activity.xlsx",
    federal_district_okved2="01_03_C_Loans_corp_by_fd_activity_20260601.xlsx",
    national_traditional="01_02_A_Debt_corp_by_activity.xlsx",
    regional_totals_history="01_05_D_Debt_subj.xlsx",
)
result = run_sors_restoration(files, SorsRunConfig(as_of_date="2026-06-01"))

moscow = build_sors_pivot(
    result,
    SorsPivotRequest(region_name="г. Москва", include_bounds=True),
)
class_16 = build_sors_pivot(result, SorsPivotRequest(class_code="16"))

export_sors_workbook(
    result,
    SorsWorkbookRequest(
        output_path="sors_restoration.xlsx",
        overwrite=True,
        pivots=(
            SorsPivotRequest(region_name="г. Москва", include_bounds=True),
            SorsPivotRequest(class_code="16"),
        ),
    ),
)
