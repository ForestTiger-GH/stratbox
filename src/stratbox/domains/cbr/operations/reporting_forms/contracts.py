"""Typed values owned by this processing boundary."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormSnapshot
if TYPE_CHECKING:
    from pandas import DataFrame

from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews

@dataclass(frozen=True, slots=True)
class FormResultSnapshotRequest:
    value: FormSnapshot | FormData | FormViews
    dataset_id: str
    version_id: str
