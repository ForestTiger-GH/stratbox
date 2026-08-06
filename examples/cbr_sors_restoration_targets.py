from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCellResolutionConfig,
    SorsCellScope,
    SorsRunConfig,
    SorsSourceFiles,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional='01_05_A_Debt_corp_20260601.xlsx',
    national_okved2='01_02_C_Debt_corp_by_activity.xlsx',
    federal_district_okved2='01_03_C_Loans_corp_by_fd_activity_20260601.xlsx',
    national_traditional='01_02_A_Debt_corp_by_activity.xlsx',
)
config = SorsRunConfig(
    as_of_date='2026-06-01',
    cell_resolution=SorsCellResolutionConfig(
        mode='targets',
        scope=SorsCellScope(
            region_names=('Белгородская область',),
            class_codes=('01',),
            components=('overdue_rub',),
        ),
    ),
)
result = run_sors_restoration(files, config)
print(result.current_component_facts_grid)
print(result.cell_attempts_grid)
print(result.cell_subsystems_grid)
