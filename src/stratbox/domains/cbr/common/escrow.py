"""Reviewed source meanings and independent column/layout recognition rules."""
from dataclasses import dataclass
from stratbox.domains.cbr.methods.tables.project_finance.contracts import EscrowIndicatorSpec

@dataclass(frozen=True, slots=True)
class EscrowColumnRule:
    indicator_code: str
    required_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...] = ()
    required: bool = True

ESCROW_INDICATOR_SPECS = (
    EscrowIndicatorSpec(**{'code': 'active_credit_contracts_count', 'canonical_name': 'Кол-во действующих кредитных договоров', 'value_kind': 'number', 'unit': 'count', 'scale': '1', 'quantity_kind': 'count'}),
    EscrowIndicatorSpec(**{'code': 'active_credit_contracts_amount_mln_rub', 'canonical_name': 'Сумма действующих кредитных договоров, млн руб.', 'value_kind': 'number', 'unit': 'RUB', 'scale': '1000000', 'quantity_kind': 'stock'}),
    EscrowIndicatorSpec(**{'code': 'debt_mln_rub', 'canonical_name': 'Задолженность, млн руб.', 'value_kind': 'number', 'unit': 'RUB', 'scale': '1000000', 'quantity_kind': 'stock'}),
    EscrowIndicatorSpec(**{'code': 'escrow_accounts_count', 'canonical_name': 'Кол-во счетов эскроу', 'value_kind': 'number', 'unit': 'count', 'scale': '1', 'quantity_kind': 'count'}),
    EscrowIndicatorSpec(**{'code': 'escrow_accounts_with_balance_count', 'canonical_name': 'Кол-во счетов эскроу, имеющих остатки', 'value_kind': 'number', 'unit': 'count', 'scale': '1', 'quantity_kind': 'count'}),
    EscrowIndicatorSpec(**{'code': 'escrow_balance_mln_rub', 'canonical_name': 'Остатки средств на счетах эскроу, млн руб.', 'value_kind': 'number', 'unit': 'RUB', 'scale': '1000000', 'quantity_kind': 'stock'}),
    EscrowIndicatorSpec(**{'code': 'weighted_rate_federal_district_percent', 'canonical_name': 'Средневзвешенная ставка по кредитным договорам по федеральному округу, %', 'value_kind': 'percent', 'unit': 'percent', 'scale': '1', 'quantity_kind': 'ratio'}),
    EscrowIndicatorSpec(**{'code': 'average_rate_federal_district_percent', 'canonical_name': 'Средняя ставка по кредитным договорам по федеральному округу, %', 'value_kind': 'percent', 'unit': 'percent', 'scale': '1', 'quantity_kind': 'ratio'}),
    EscrowIndicatorSpec(**{'code': 'revealed_escrow_accounts_count', 'canonical_name': 'Кол-во «раскрытых» счетов эскроу', 'value_kind': 'number', 'unit': 'count', 'scale': '1', 'quantity_kind': 'count'}),
    EscrowIndicatorSpec(**{'code': 'revealed_escrow_amount_mln_rub', 'canonical_name': 'Сумма средств, перечисленных с «раскрытых» счетов эскроу, млн руб.', 'value_kind': 'number', 'unit': 'RUB', 'scale': '1000000', 'quantity_kind': None}),
)

ESCROW_COLUMN_RULES = (
    EscrowColumnRule(**{'indicator_code': 'active_credit_contracts_count', 'required_tokens': ('кол', 'во', 'действующих', 'кредитных', 'договоров'), 'forbidden_tokens': (), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'active_credit_contracts_amount_mln_rub', 'required_tokens': ('сумма', 'действующих', 'кредитных', 'договоров', 'млн', 'руб'), 'forbidden_tokens': (), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'debt_mln_rub', 'required_tokens': ('задолженность', 'млн', 'руб'), 'forbidden_tokens': (), 'required': False}),
    EscrowColumnRule(**{'indicator_code': 'escrow_accounts_count', 'required_tokens': ('кол', 'во', 'счетов', 'эскроу'), 'forbidden_tokens': ('имеющих', 'остатки'), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'escrow_accounts_with_balance_count', 'required_tokens': ('кол', 'во', 'счетов', 'эскроу', 'имеющих', 'остатки'), 'forbidden_tokens': (), 'required': False}),
    EscrowColumnRule(**{'indicator_code': 'escrow_balance_mln_rub', 'required_tokens': ('остатки', 'средств', 'счетах', 'эскроу', 'млн', 'руб'), 'forbidden_tokens': (), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'weighted_rate_federal_district_percent', 'required_tokens': ('средневзвешенная', 'ставка', 'кредитным', 'договорам', 'федеральному', 'округу', 'процент'), 'forbidden_tokens': (), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'average_rate_federal_district_percent', 'required_tokens': ('средняя', 'ставка', 'кредитным', 'договорам', 'федеральному', 'округу', 'процент'), 'forbidden_tokens': ('средневзвешенная',), 'required': False}),
    EscrowColumnRule(**{'indicator_code': 'revealed_escrow_accounts_count', 'required_tokens': ('кол', 'во', 'раскрытых', 'счетов', 'эскроу'), 'forbidden_tokens': (), 'required': True}),
    EscrowColumnRule(**{'indicator_code': 'revealed_escrow_amount_mln_rub', 'required_tokens': ('сумма', 'средств', 'перечисленных', 'раскрытых', 'счетов', 'эскроу', 'млн', 'руб'), 'forbidden_tokens': (), 'required': True}),
)
INDICATORS = {item.code: item for item in ESCROW_INDICATOR_SPECS}

def required_indicators():
    """Source admission requirements, independent of output selection."""
    return tuple(INDICATORS[item.indicator_code] for item in ESCROW_COLUMN_RULES if item.required)
