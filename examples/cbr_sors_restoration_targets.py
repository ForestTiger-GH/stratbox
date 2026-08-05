from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCertificationConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional="01_05_A.xlsx",
    national_okved2="01_02_C.xlsx",
    federal_district_okved2="01_03_C.xlsx",
    national_traditional="01_02_A.xlsx",
)
config = SorsRunConfig(
    as_of_date="2026-06-01",
    strict_certification=SorsCertificationConfig(
        mode="targets",
        scope=SorsTargetScope(
            region_names=("г. Москва",),
            class_codes=("01", "16", "35"),
        ),
        batch_size=25,
        max_targets=100,
    ),
)
result = run_sors_restoration(files, config)
print(result.summary)
