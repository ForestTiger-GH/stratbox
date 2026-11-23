"""Physical fields and source identity for Bank of Russia Form 802."""


from __future__ import annotations


from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import (
    DirectDatasetSpec,
)


FORM = "802"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="main",
    bank_fields=("REGN_GKO",),
    code_fields=("STR",),
    measure_fields={
        "total": ("VSEGO",),
    },
    optional_measure_fields={
        "consolidation_plus": ("KORR_P",),
        "consolidation_minus": ("KORR_M",),
        "intragroup_adjustment": ("KORR_GR",),
    },
    prefer_stem_contains="PK802",
)
