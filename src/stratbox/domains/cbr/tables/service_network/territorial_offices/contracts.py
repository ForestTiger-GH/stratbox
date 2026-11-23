"""Explicit source selection and result contracts for territorial office publications."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Mapping
from stratbox.shared.data.releases import ParsedRelease
from stratbox.shared.evidence import AcquisitionReceipt, SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

@dataclass(frozen=True, slots=True)
class DiscoverOfficesRegRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ParseOfficesRegRequest:
    payload: SourcePayload
    as_of: date
    sheet: str | None = None
    national_row: int | None = None
    last_row: int | None = None


@dataclass(frozen=True, slots=True)
class OfficesRegCandidates:
    source_identity: ByteIdentity
    blocks: tuple[tuple[str, int, int], ...]
    as_of: date | None = None
    requested_sheet: str | None = None
    requested_national_row: int | None = None
    requested_last_row: int | None = None
    inputs: tuple[UsedInputReceipt, ...] = ()
    acquisition: AcquisitionReceipt | None = None


@dataclass(frozen=True, slots=True)
class ReadOfficesRegRequest:
    payload: SourcePayload
    as_of: date
    source_details: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class SnapshotOfficesRegRequest:
    release: ParsedRelease | OfficesRegCandidates
    dataset_id: str
    version_id: str
