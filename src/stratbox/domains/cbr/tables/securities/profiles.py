"""Reviewed securities workbook variants and interpretation boundaries."""
from stratbox.domains.cbr.tables.statistics.contracts import SourceTableProfile, TableVariant

_DECLARATIONS = (('cbr.tables.debt_securities.v1',
  'cbr.securities.debt_securities',
  (('table_1',
    'Квартал\\ \\(номинальная\\ стоимость\\)',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'valuation_basis', 'frequency'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Debt securities issued on the domestic market, separate nominal and market valuations and '
    'monthly/quarterly tables.'),
   ('table_2',
    'Месяц\\ \\(номинальная\\ стоимость\\)',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'valuation_basis', 'frequency'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Debt securities issued on the domestic market, separate nominal and market valuations and '
    'monthly/quarterly tables.'),
   ('table_3',
    'Квартал\\ \\(рыночная\\ стоимость\\)',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'valuation_basis', 'frequency'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Debt securities issued on the domestic market, separate nominal and market valuations and '
    'monthly/quarterly tables.'),
   ('table_4',
    'Месяц\\ \\(рыночная\\ стоимость\\)',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'valuation_basis', 'frequency'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Debt securities issued on the domestic market, separate nominal and market valuations and '
    'monthly/quarterly tables.'))),)

PROFILES = tuple(SourceTableProfile(profile, series, 1, "published_matrix_v1",
    tuple(TableVariant(*variant) for variant in variants),
    "All worksheets and physical cells, including notes and unknown variants.",
    'Debt securities issued on the domestic market, separate nominal and market valuations and monthly/quarterly tables.') for profile, series, variants in _DECLARATIONS)
