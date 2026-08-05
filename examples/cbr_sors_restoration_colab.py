"""Google Colab example for SORS Restoration V2.

Run in a clean Colab runtime. SORS V2 uses highspy directly and does not require
SciPy, avoiding NumPy/SciPy binary conflicts from the previous prototype.

Installation from a Git branch:
    !pip install --no-cache-dir highspy
    !pip install --no-cache-dir "git+https://github.com/ForestTiger-GH/stratbox.git@YOUR_BRANCH"

The first example certifies one target deliberately. Expand the target scope only
after the smoke run succeeds: each non-singleton metric requires strict and bridge
min/max solves.
"""

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    export_sors_restoration_xlsx,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional='/content/01_05_A_Debt_corp_20260601 (1).xlsx',
    national_traditional='/content/01_02_A_Debt_corp_by_activity.xlsx',
    national_okved2='/content/01_02_C_Debt_corp_by_activity.xlsx',
    fd_okved2='/content/01_03_C_Loans_corp_by_fd_activity_20260601 (1).xlsx',
)

config = SorsRunConfig(
    as_of_date='2026-06-01',
    target_scope=SorsTargetScope(
        region_names=('г. Москва',),
        class_codes=('16',),
        metrics=('debt_total',),
        max_targets=10,
    ),
)

result = run_sors_restoration(files, config)
print(result.audit)
display(result.facts_grid.query('is_reconstructed == True'))
display(result.bounds_grid)

export_sors_restoration_xlsx(
    result,
    '/content/SORS_Restored_20260601.xlsx',
)
