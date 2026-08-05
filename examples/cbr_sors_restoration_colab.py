"""Minimal Google Colab / notebook example for one SORS reporting date.

In Colab, install Strategy Box from your repository/branch first, e.g.:
    !pip install "git+https://github.com/ForestTiger-GH/stratbox.git@YOUR_BRANCH"
Then upload/download the four SORS workbooks and point FILES to them.
"""

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsRestorationConfig,
    SorsRestorationFiles,
    export_sors_restoration_xlsx,
    run_sors_restoration,
)

FILES = SorsRestorationFiles(
    regional_traditional='/content/01_05_A_Debt_corp_20260601.xlsx',
    national_okved2='/content/01_02_C_Debt_corp_by_activity.xlsx',
    fd_okved2='/content/01_03_C_Loans_corp_by_fd_activity_20260601.xlsx',
    national_traditional='/content/01_02_A_Debt_corp_by_activity.xlsx',  # diagnostics only
)

CONFIG = SorsRestorationConfig(
    as_of_date='2026-06-01',
    certify_mode='targets',
    # Examples: certify all components of selected region/class combinations.
    target_region_names=('г. Москва', 'Брянская область', 'Краснодарский край'),
    target_class_codes=('01', '10', '35'),
    max_lp_targets=100,
)

result = run_sors_restoration(FILES, CONFIG)
print(result.audit)
display(result.facts_grid.head(50))
display(result.bounds_grid.query("region_name == 'г. Москва' and class_code in ['01','10','35']"))
export_sors_restoration_xlsx(result, '/content/SORS_Restored_20260601.xlsx')
