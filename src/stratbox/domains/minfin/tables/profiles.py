"""Registered source-table shape rules, independent of operations and YAML."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TableProfile:
    profile_id: str
    code_column: int
    indicator_column: int
    first_period_column: int
    max_header_rows: int
    minimum_periods: int
    max_rows: int
    admitted_formats: frozenset[str]
    method_version: str
    unit_hint: str
    code_pattern: str = r"\d+(?:\.\d+)*\.?"
    notes_pattern: str = r"\s*(?:\*+|[¹²³⁴⁵⁶⁷⁸⁹]+)\s*$"

    def __post_init__(self):
        if not (0 < self.code_column < self.first_period_column and
                0 < self.indicator_column < self.first_period_column and
                1 <= self.max_header_rows <= 100 and self.minimum_periods >= 1 and
                self.admitted_formats and self.method_version):
            raise ValueError("minfin.profile.invalid_table")


_TABLES = {
    "minfin.budget_table": TableProfile("minfin.budget_table", 1, 2, 3, 12, 2,
        200_000, frozenset({"xlsx", "xls", "xlsm"}), "minfin.flake.budget.v2", "billion_rub"),
    "minfin.nwf_table": TableProfile("minfin.nwf_table", 1, 2, 3, 12, 2,
        200_000, frozenset({"xlsx", "xls", "xlsm"}), "minfin.flake.nwf.v2", "mixed"),
}


def table_profile(profile_id: str) -> TableProfile:
    try:
        return _TABLES[profile_id]
    except (KeyError, TypeError):
        raise ValueError("minfin.profile.table_unknown") from None


__all__ = ("TableProfile", "table_profile")