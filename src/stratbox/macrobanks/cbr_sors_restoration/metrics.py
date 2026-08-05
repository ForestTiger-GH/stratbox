from __future__ import annotations

from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS

METRIC_COMPONENTS: dict[str, tuple[str, ...]] = {
    'debt_rub': ('performing_rub', 'overdue_rub'),
    'debt_fx': ('performing_fx', 'overdue_fx'),
    'debt_total': COMPONENTS,
    'overdue_rub': ('overdue_rub',),
    'overdue_fx': ('overdue_fx',),
    'overdue_total': ('overdue_rub', 'overdue_fx'),
}


def source_metric(measure: str, currency: str) -> str:
    overdue = measure in {'overdue', 'overdue_debt'}
    if currency in {'rub', 'rubles'}:
        return 'overdue_rub' if overdue else 'debt_rub'
    if currency in {'fx', 'foreign_currency_and_precious_metals'}:
        return 'overdue_fx' if overdue else 'debt_fx'
    if currency == 'total':
        return 'overdue_total' if overdue else 'debt_total'
    raise ValueError(f'Unsupported SORS measure/currency: {measure!r}/{currency!r}')
