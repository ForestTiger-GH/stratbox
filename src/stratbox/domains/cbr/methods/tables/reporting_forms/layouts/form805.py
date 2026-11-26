"""Physical fields and source identity for Bank of Russia Form 805."""


from __future__ import annotations


from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import (
    DirectDatasetSpec,
    normalize_code_metric,
)


FORM = "805"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="normatives",
    bank_fields=("REGN_GKO", "REGN"),
    code_fields=("NAME_NORM", "C1_3"),
    measure_fields={"actual": ("FAKT_ZN", "C2_3")},
    prefer_stem_contains="PN805",
    code_normalizer=normalize_code_metric,
    code_aliases={
        "H20.2": "H20_2",
        "H20.4": "H20_4",
        "Н20.2": "H20_2",
        "Н20.4": "H20_4",
    },
)
