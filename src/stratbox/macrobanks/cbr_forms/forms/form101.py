"""Form 101 closing balances and account-side selection."""

from stratbox.macrobanks.cbr_forms.common.formula import FormulaDatasetSpec

DEFAULT_SPEC = FormulaDatasetSpec(
    "101", "balance", {"REGN": ("REGN",), "CODE": ("NUM_SC",), "VALUE": ("IITG",), "PLAN": ("PLAN",)},
    "B1", side_fields=("A_P",), account_plan="А",
)
