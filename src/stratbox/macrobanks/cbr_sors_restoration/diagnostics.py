from __future__ import annotations

import pandas as pd

# These are candidates, not strict monetary identities.  They are deliberately
# kept out of the LP unless a future version attaches documentary HARD evidence.
SEMANTIC_BRIDGE_CANDIDATES: dict[str, tuple[str, ...]] = {
    'agriculture_hunting_services': ('01',),
    'agriculture_hunting_forestry': ('01', '02'),
    'manufacturing_food_beverages_tobacco': ('10', '11', '12'),
    'manufacturing_wood_products': ('16',),
    'manufacturing_non_metallic_mineral_products': ('23',),
    'construction': ('41', '42', '43'),
    'wholesale_retail_trade_motor_vehicles_household_goods': ('45', '46', '47'),
}


def build_mapping_diagnostics(regional_grid: pd.DataFrame, national_okved2_grid: pd.DataFrame) -> pd.DataFrame:
    """Numerical proximity report for human review; never creates strict facts."""
    rf = regional_grid[(regional_grid['region_kind'].astype(str) == 'country_total')]
    records: list[dict[str, object]] = []
    for old_code, classes in SEMANTIC_BRIDGE_CANDIDATES.items():
        for measure, currency_scope, new_currency in (
            ('debt', 'rubles', 'rub'),
            ('debt', 'foreign_currency_and_precious_metals', 'fx'),
            ('overdue_debt', 'rubles', 'rub'),
            ('overdue_debt', 'foreign_currency_and_precious_metals', 'fx'),
        ):
            old = rf[(rf['industry_code'].astype(str) == old_code) & (rf['measure'].astype(str) == measure) & (rf['currency_scope'].astype(str) == currency_scope)]
            if old.empty:
                continue
            new_measure = 'overdue' if measure == 'overdue_debt' else 'debt'
            new = national_okved2_grid[(national_okved2_grid['class_code'].isin(classes)) & (national_okved2_grid['measure'] == new_measure) & (national_okved2_grid['currency'] == new_currency)]
            if new.empty:
                continue
            old_value = float(old.iloc[0]['value'])
            new_value = float(new['value'].sum())
            records.append({
                'traditional_code': old_code,
                'okved2_classes': '+'.join(classes),
                'measure': new_measure,
                'currency': new_currency,
                'traditional_rf_value': old_value,
                'okved2_rf_value': new_value,
                'difference': new_value - old_value,
                'difference_pct_of_okved2': (new_value - old_value) / new_value if new_value else None,
                'hardness': 'SOFT_DIAGNOSTIC_ONLY',
            })
    return pd.DataFrame(records)
