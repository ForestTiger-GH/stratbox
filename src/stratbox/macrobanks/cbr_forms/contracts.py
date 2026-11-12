"""Public contracts for exact CBR form inputs, data and presentations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, TYPE_CHECKING

from stratbox.data import SourcePayload, UsedInputReceipt

if TYPE_CHECKING:
    from pandas import DataFrame


@dataclass(frozen=True, slots=True)
class FormKey:
    code: str
    as_of: date


@dataclass(frozen=True, slots=True)
class SelectFormSourcesRequest:
    keys: tuple[FormKey, ...]


@dataclass(frozen=True, slots=True)
class FormSource:
    key: FormKey
    url: str


@dataclass(frozen=True, slots=True)
class ParseFormRequest:
    key: FormKey
    payload: SourcePayload


@dataclass(frozen=True, slots=True)
class FormSnapshot:
    key: FormKey
    physical_fields: Mapping[str, str]
    rows: DataFrame
    lineage: tuple[UsedInputReceipt, ...]


@dataclass(frozen=True, slots=True)
class BankSelection:
    regn: str
    label: str


@dataclass(frozen=True, slots=True)
class BuildFormDataRequest:
    snapshots: tuple[FormSnapshot, ...]
    banks: tuple[BankSelection, ...] | None = None
    model: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class FormData:
    form: str
    long: DataFrame
    banks: DataFrame
    model: DataFrame
    indicator_order: Mapping[str, int]
    lineage: tuple[UsedInputReceipt, ...]


@dataclass(frozen=True, slots=True)
class FormViews:
    form: str
    profile: str
    sheets: Mapping[str, DataFrame]
    lineage: tuple[UsedInputReceipt, ...]
