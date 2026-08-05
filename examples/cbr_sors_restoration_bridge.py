from stratbox.macrobanks.cbr_sors_restoration import (
    SorsBridgeConfig,
    SorsRunConfig,
    SorsSourceFiles,
    run_sors_bridge,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional="01_05_A.xlsx",
    national_okved2="01_02_C.xlsx",
    federal_district_okved2="01_03_C.xlsx",
    national_traditional="01_02_A.xlsx",
)
strict = run_sors_restoration(files, SorsRunConfig(as_of_date="2026-06-01"))
bridge = run_sors_bridge(strict, SorsBridgeConfig(mode="optimum_only"))
print(bridge.status)
print(bridge.diagnostics_grid)
