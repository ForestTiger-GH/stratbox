"""Google Colab example for SORS Restoration 0.3.1.

Use a clean runtime. Different SORS implementations must never be installed under
one version in the same Colab session.

Recommended installation cell for a wheel uploaded to /content:

    !pip uninstall -y stratbox
    !rm -rf /usr/local/lib/python3.12/dist-packages/stratbox
    !rm -rf /usr/local/lib/python3.12/dist-packages/stratbox-*.dist-info
    !pip install --no-cache-dir "highspy>=1.11,<2"
    !pip install --no-cache-dir --force-reinstall --no-deps \
        /content/stratbox-0.3.1-py3-none-any.whl

Then restart the session before importing:

    from google.colab import runtime
    runtime.restart_session()

facts_grid contains only published and STRICT reconstructed values.
estimates_grid contains conditional minimum-reclassification bridge results.
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
display(result.estimates_grid)
display(result.bridge_bounds_grid)

export_sors_restoration_xlsx(
    result,
    '/content/SORS_Restored_20260601.xlsx',
)
