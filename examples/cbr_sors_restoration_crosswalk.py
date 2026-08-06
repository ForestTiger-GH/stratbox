from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCrosswalkConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_crosswalk,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional='01_05_A.xlsx',
    national_okved2='01_02_C.xlsx',
    federal_district_okved2='01_03_C.xlsx',
    national_traditional='01_02_A.xlsx',
)
strict = run_sors_restoration(
    files,
    SorsRunConfig(as_of_date='2026-06-01'),
)
crosswalk = run_sors_crosswalk(
    strict,
    SorsCrosswalkConfig(
        mode='targets',
        scenario_ids=('core',),
        scope=SorsTargetScope(
            region_names=('Белгородская область',),
            class_codes=('01', '02'),
        ),
    ),
)
print(crosswalk.status)
print(crosswalk.crosswalk_facts_grid)
print(crosswalk.crosswalk_bounds_grid)
