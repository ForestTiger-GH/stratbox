"""Reviewed external debt workbook variants and interpretation boundaries."""
from stratbox.domains.cbr.tables.statistics.contracts import SourceTableProfile, TableVariant

_DECLARATIONS = (('cbr.tables.debt_new',
  'cbr.external_debt.debt_new',
  (('table_1',
    '\\d{4}-\\d{4}',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'layout_vintage', 'maturity_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain '
    'independent until explicitly reconciled.'),)),
 ('cbr.tables.debt_maturity',
  'cbr.external_debt.debt_maturity',
  (('table_1',
    '\\d{4}-\\d{4}',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'layout_vintage', 'maturity_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain '
    'independent until explicitly reconciled.'),)),
 ('cbr.tables.debt_cur-mat_new',
  'cbr.external_debt.debt_cur-mat_new',
  (('table_1',
    '\\d{4}-\\d{4}',
    'statistics',
    'stock',
    'as_of',
    ('source_hierarchy', 'layout_vintage', 'maturity_basis'),
    'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.',
    'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain '
    'independent until explicitly reconciled.'),)))

PROFILES = tuple(SourceTableProfile(profile, series, 1, "published_matrix_v1",
    tuple(TableVariant(*variant) for variant in variants),
    "All worksheets and physical cells, including notes and unknown variants.",
    'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.') for profile, series, variants in _DECLARATIONS)
