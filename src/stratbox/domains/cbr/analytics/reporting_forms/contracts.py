"""Typed values owned by this processing boundary."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Mapping, TYPE_CHECKING
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.data.observations import ObservationBatch, PeriodRef
from stratbox.shared.data.source_context import SourceUse
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormSnapshot
if TYPE_CHECKING:
    from pandas import DataFrame

@dataclass(frozen=True, slots=True)
class BankSelection:
    regn: str
    label: str


@dataclass(frozen=True, slots=True)
class BuildFormDataRequest:
    snapshots: tuple[FormSnapshot, ...]
    banks: tuple[BankSelection, ...] | None = None
    model: SourcePayload | None = None
    selection_profile: str = "all_admitted"
    periods: tuple[tuple[date, PeriodRef], ...] = ()


@dataclass(frozen=True, slots=True)
class PrepareFormModelInputsRequest:
    batch: ObservationBatch


@dataclass(frozen=True, slots=True)
class FormModelInputs:
    form: str
    layout_edition: str
    batch: ObservationBatch
    preparation_version: str = "cbr.forms.model_inputs.v1"


@dataclass(frozen=True, slots=True)
class CalculateFormRequest:
    inputs: FormModelInputs
    banks: tuple[BankSelection, ...] | None = None
    model: SourcePayload | None = None
    selection_profile: str = "all_admitted"


@dataclass(frozen=True, slots=True)
class FormData:
    form: str
    long: DataFrame
    banks: DataFrame
    model: DataFrame
    indicator_order: Mapping[str, int]
    lineage: tuple[UsedInputReceipt, ...]
    evidence: ComputationReceipt | None = None
    source_uses: tuple[SourceUse, ...] = ()
