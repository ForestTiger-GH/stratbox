"""Form 101 closing balances and account-side selection."""

from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import FormulaDatasetSpec

DEFAULT_SPEC = FormulaDatasetSpec(
    "101", "balance", {"REGN": ("REGN",), "CODE": ("NUM_SC",), "VALUE": ("IITG",), "PLAN": ("PLAN",)},
    "B1", side_fields=("A_P",), account_plan="А",
)
