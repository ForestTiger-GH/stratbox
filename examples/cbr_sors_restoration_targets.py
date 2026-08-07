from stratbox.macrobanks.cbr_sors_restoration import (
    SorsOptimizationConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional='01_05_A_Debt_corp_20260601.xlsx',
    national_okved2='01_02_C_Debt_corp_by_activity.xlsx',
    federal_district_okved2='01_03_C_Loans_corp_by_fd_activity_20260601.xlsx',
    national_traditional='01_02_A_Debt_corp_by_activity.xlsx',
    sme_national_totals='01_11_Debt_sme.xlsx',
    sme_national_okved2='01_11_F_Debt_sme_by_activity.xlsx',
    sme_ie_national_okved2='01_11_I_Debt_ie_by_activity.xlsx',
    sme_federal_district_okved2='01_12_A_Loans_sme_by_fd_activity_20260601.xlsx',
    sme_regional_totals='01_13_F_Debt_sme_subj.xlsx',
    sme_ie_regional_totals='01_13_I_Debt_sme_subj.xlsx',
)
config = SorsRunConfig(
    as_of_date='2026-06-01',
    optimization=SorsOptimizationConfig(
        mode='targets',
        scope=SorsTargetScope(
            region_names=('Белгородская область',),
            class_codes=('01',),
            metrics=('debt_rub', 'overdue_rub'),
        ),
        max_targets=20,
    ),
)
result = run_sors_restoration(files, config)
print(result.regional_okved2_grid)
print(result.facts_ledger_grid)
print(result.fixed_point_passes_grid)
print(result.target_bounds_grid)
print(result.rounding_profiles_grid)
