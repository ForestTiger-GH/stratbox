"""Form 123 capital indicators and historical numeric account identifiers."""

from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import FormulaDatasetSpec, integer_account

DEFAULT_SPEC = FormulaDatasetSpec(
    "123", "capital", {"REGN": ("REGN",), "CODE": ("C1",), "VALUE": ("C3",)},
    "123D", normalize_account=integer_account,
)
