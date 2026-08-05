from __future__ import annotations

from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS, TARGET_METRICS

METRIC_COMPONENTS: dict[str, tuple[str, ...]] = {
    'debt_rub': ('performing_rub', 'overdue_rub'),
    'debt_fx': ('performing_fx', 'overdue_fx'),
    'debt_total': COMPONENTS,
    'overdue_rub': ('overdue_rub',),
    'overdue_fx': ('overdue_fx',),
    'overdue_total': ('overdue_rub', 'overdue_fx'),
}

METRIC_NAMES_RU = {
    'debt_rub': 'Задолженность в рублях',
    'debt_fx': 'Задолженность в иностранной валюте и драгоценных металлах',
    'debt_total': 'Задолженность, итого',
    'overdue_rub': 'Просроченная задолженность в рублях',
    'overdue_fx': 'Просроченная задолженность в иностранной валюте и драгоценных металлах',
    'overdue_total': 'Просроченная задолженность, итого',
}
METRIC_ORDER = {metric: i + 1 for i, metric in enumerate(TARGET_METRICS)}


def source_metric(measure: str, currency: str) -> str:
    overdue = measure in {'overdue', 'overdue_debt'}
    if currency in {'rub', 'rubles'}:
        return 'overdue_rub' if overdue else 'debt_rub'
    if currency in {'fx', 'foreign_currency_and_precious_metals'}:
        return 'overdue_fx' if overdue else 'debt_fx'
    if currency == 'total':
        return 'overdue_total' if overdue else 'debt_total'
    raise ValueError(f'Unsupported SORS measure/currency: {measure!r}/{currency!r}')
