"""Physical fields and source identity for Bank of Russia Form 135."""


from __future__ import annotations


from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import (
    DirectDatasetSpec,
    normalize_code_metric,
)


FORM = "135"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="section3",
    bank_fields=("REGN",),
    code_fields=("C1_3",),
    measure_fields={"actual": ("C2_3",)},
    prefer_stem_contains="135_3",
    code_normalizer=normalize_code_metric,
)
