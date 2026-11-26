"""Fiscal table settings and row-specific economic meaning."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RowRule:
    code: str
    metric: str
    label: str
    basis: str
    unit: str = "RUB"
    scale: Decimal = Decimal("1e9")


@dataclass(frozen=True)
class TableRules:
    source_id: str
    family_id: str
    frequency: str
    basis: str
    perimeter: str
    rows: tuple[RowRule, ...]
    code_column: int = 1
    label_column: int = 2
    first_period_column: int = 3
    max_header_rows: int = 12
    minimum_periods: int = 2
    max_rows: int = 200_000
    scope: str = "reviewed_rows"


BUDGET_ROWS = (
    RowRule("1", "budget.revenue", "Доходы, всего", "source"),
    RowRule("2", "budget.expenditure", "Расходы, всего", "source"),
    RowRule("3", "budget.balance", "Дефицит (-)/Профицит (+)", "source"),
)
FUND_ROWS = (
    RowRule("2", "nwf.total", "Объем на конец периода", "stock"),
    RowRule("5", "nwf.other_assets", "Размещено в иные разрешенные активы на конец периода", "stock"),
)


@dataclass(frozen=True)
class DocumentField:
    block: int
    row: int
    column: int
    metric: str
    unit: str
    scale: Decimal
    as_of: str
    row_label: str
    label_column: int = 0
    subject: str = "RU"
    measure_kind: str = "stock"
    perimeter: str = "russian_national_wealth_fund"


@dataclass(frozen=True)
class DocumentRules:
    source_id: str
    fields: tuple[DocumentField, ...] = ()
    required_text: tuple[str, ...] = ()
    format: str = "docx"
    scope: str = "reviewed_fields_required"
