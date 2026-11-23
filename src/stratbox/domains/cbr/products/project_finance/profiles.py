"""Workbook titles, ordering and formatting belong only to the product layer."""
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class EscrowProductIndicator:
    code: str
    title: str
    sheet_code: str
    order: int
    number_format: str = "#,##0.##########"

    def __post_init__(self):
        if (not self.code or not self.title or not self.sheet_code or len(self.sheet_code) > 31
                or any(c in self.sheet_code for c in "[]:*?/\\")
                or type(self.order) is not int or self.order < 0 or not self.number_format):
            raise ValueError("escrow.product_indicator_invalid")

@dataclass(frozen=True, slots=True)
class EscrowProductProfile:
    profile_id: str
    version: int
    indicators: tuple[EscrowProductIndicator, ...]

    def __post_init__(self):
        if (not self.profile_id or type(self.version) is not int or self.version < 1 or not self.indicators
                or len({item.code for item in self.indicators}) != len(self.indicators)
                or len({item.sheet_code.casefold() for item in self.indicators}) != len(self.indicators)):
            raise ValueError("escrow.product_profile_invalid")

DEFAULT_PRODUCT_PROFILE = EscrowProductProfile("cbr-escrow-regional-history", 1, (
    EscrowProductIndicator(**{'code': 'active_credit_contracts_count', 'title': 'Кол-во действующих кредитных договоров', 'sheet_code': 'КДКД', 'order': 1, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'active_credit_contracts_amount_mln_rub', 'title': 'Сумма действующих кредитных договоров, млн руб.', 'sheet_code': 'СДКДМР', 'order': 2, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'debt_mln_rub', 'title': 'Задолженность, млн руб.', 'sheet_code': 'ЗМР', 'order': 3, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'escrow_accounts_count', 'title': 'Кол-во счетов эскроу', 'sheet_code': 'КСЭ', 'order': 4, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'escrow_accounts_with_balance_count', 'title': 'Кол-во счетов эскроу, имеющих остатки', 'sheet_code': 'КСЭИО', 'order': 5, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'escrow_balance_mln_rub', 'title': 'Остатки средств на счетах эскроу, млн руб.', 'sheet_code': 'ОСНСЭМР', 'order': 6, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'weighted_rate_federal_district_percent', 'title': 'Средневзвешенная ставка по кредитным договорам по федеральному округу, %', 'sheet_code': 'ССПКДПФО', 'order': 7, 'number_format': '#,##0.00'}),
    EscrowProductIndicator(**{'code': 'average_rate_federal_district_percent', 'title': 'Средняя ставка по кредитным договорам по федеральному округу, %', 'sheet_code': 'СПКДПФО', 'order': 7, 'number_format': '#,##0.00'}),
    EscrowProductIndicator(**{'code': 'revealed_escrow_accounts_count', 'title': 'Кол-во «раскрытых» счетов эскроу', 'sheet_code': 'КРСЭ', 'order': 8, 'number_format': '#,##0.##########'}),
    EscrowProductIndicator(**{'code': 'revealed_escrow_amount_mln_rub', 'title': 'Сумма средств, перечисленных с «раскрытых» счетов эскроу, млн руб.', 'sheet_code': 'ССПСРСЭМР', 'order': 9, 'number_format': '#,##0.##########'}),
))
