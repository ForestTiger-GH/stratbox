"""Form 102 published income statement totals."""

from stratbox.macrobanks.cbr_forms.common.formula import FormulaDatasetSpec, plain_account


def _account(value):
    code = plain_account(value)
    return code.zfill(5) if code.isascii() and code.isdecimal() else code.upper()


DEFAULT_SPEC = FormulaDatasetSpec(
    "102", "pnl", {"REGN": ("REGN",), "CODE": ("CODE",), "VALUE": ("SIM_ITOGO", "SIM_ITOG", "SIM_R")},
    "P1", normalize_account=_account,
)
