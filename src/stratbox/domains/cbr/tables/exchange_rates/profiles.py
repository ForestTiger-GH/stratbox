"""Reviewed exchange rates workbook variants and interpretation boundaries."""
from stratbox.domains.cbr.tables.statistics.contracts import SourceTableProfile, TableVariant

_DECLARATIONS = (('cbr.tables.exchange_rate',
  'cbr.exchange_rates.exchange_rate',
  (('table_1',
    'Ежемесячные',
    'statistics',
    None,
    'month',
    ('source_measure_or_country', 'frequency', 'reference_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Nominal rates, averages, published indices and trade weights retain separate metric identities and '
    'reference bases.'),
   ('table_2',
    'Ежеквартальные',
    'statistics',
    None,
    'quarter',
    ('source_measure_or_country', 'frequency', 'reference_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Nominal rates, averages, published indices and trade weights retain separate metric identities and '
    'reference bases.'),
   ('table_3',
    'Доли',
    'statistics',
    'ratio',
    'year',
    ('source_measure_or_country', 'frequency', 'reference_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'Nominal rates, averages, published indices and trade weights retain separate metric identities and '
    'reference bases.'))),)

PROFILES = tuple(SourceTableProfile(profile, series, 1, "published_matrix_v1",
    tuple(TableVariant(*variant) for variant in variants),
    "All worksheets and physical cells, including notes and unknown variants.",
    'Nominal rates, averages, published indices and trade weights retain separate metric identities and reference bases.') for profile, series, variants in _DECLARATIONS)
