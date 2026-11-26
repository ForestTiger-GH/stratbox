"""Static content choices for separately prepared and rendered CBR products."""
from dataclasses import dataclass
from types import MappingProxyType

from stratbox.capabilities.model.domains import ProductSpec, CommandSpec
from stratbox.capabilities.model.methods import MethodRef


@dataclass(frozen=True, slots=True)
class Sheet:
    metric: str
    title: str
    name: str
    number_format: str = "#,##0.##########"


@dataclass(frozen=True, slots=True)
class ProductSettings:
    kind: str
    sheets: tuple[Sheet, ...] = ()
    default_metrics: tuple[str, ...] = ()


ESCROW_CONTENT = ProductSettings("escrow", (
    Sheet("active_credit_contracts_count", "Кол-во действующих кредитных договоров", "КДКД"),
    Sheet("active_credit_contracts_amount_mln_rub", "Сумма действующих кредитных договоров, млн руб.", "СДКДМР"),
    Sheet("debt_mln_rub", "Задолженность, млн руб.", "ЗМР"),
    Sheet("escrow_accounts_count", "Кол-во счетов эскроу", "КСЭ"),
    Sheet("escrow_accounts_with_balance_count", "Кол-во счетов эскроу с остатками", "КСЭИО"),
    Sheet("escrow_balance_mln_rub", "Остатки средств на счетах эскроу, млн руб.", "ОСНСЭМР"),
    Sheet("weighted_rate_federal_district_percent", "Средневзвешенная ставка по договорам, %", "ССПКДПФО", "#,##0.00"),
    Sheet("average_rate_federal_district_percent", "Средняя ставка по договорам, %", "СПКДПФО", "#,##0.00"),
    Sheet("revealed_escrow_accounts_count", "Кол-во раскрытых счетов эскроу", "КРСЭ"),
    Sheet("revealed_escrow_amount_mln_rub", "Средства с раскрытых счетов эскроу, млн руб.", "ССПСРСЭМР"),
))

ESCROW_HISTORY = ProductSpec("cbr.escrow.history", MappingProxyType({
    "command.view.prepare": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:prepare"), ESCROW_CONTENT),
    "command.product.render": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:render"), ESCROW_CONTENT),
}))
FORM_WORKBOOK = ProductSpec("cbr.forms.workbook", MappingProxyType({
    "command.view.prepare": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:prepare"), ProductSettings("forms")),
    "command.product.render": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:render"), ProductSettings("forms")),
}))
INDUSTRY_WORKBOOK = ProductSpec("cbr.industries.workbook", MappingProxyType({
    "command.view.prepare": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:prepare"), ProductSettings("industries", default_metrics=("apk",))),
    "command.product.render": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:render"), ProductSettings("industries")),
}))
OFFICE_TABLE = ProductSpec("cbr.offices.table", MappingProxyType({
    "command.view.prepare": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:prepare"), ProductSettings("offices")),
    "command.product.render": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:render"), ProductSettings("offices")),
}))
STATISTICAL_TABLE = ProductSpec("cbr.statistics.table", MappingProxyType({
    "command.view.prepare": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:prepare"), ProductSettings("statistics")),
    "command.product.render": CommandSpec(MethodRef("stratbox.domains.cbr.products.actions:render"), ProductSettings("statistics")),
}))
