"""Contracts shared by date-keyed source releases."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Mapping

from .comparison import BaselineState
from .evidence import AcquisitionReceipt, SourcePayload
from .identity import DatasetVersion, build_dataset_version
from .observations import Observation, ObservationBatch
from .representation import CSV, Representation


@dataclass(frozen=True, slots=True)
class ReleaseLink:
    as_of: date
    url: str


@dataclass(frozen=True, slots=True)
class ReadReleaseRequest:
    payload: SourcePayload
    as_of: date


@dataclass(frozen=True, slots=True)
class ParsedRelease:
    as_of: date
    batch: ObservationBatch | None
    representation: Representation
    dataset_version: DatasetVersion
    row_count: int
    acquisition: AcquisitionReceipt | None = None
    source_details: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CompareReleaseRequest:
    candidate: ParsedRelease
    baseline: ParsedRelease | None = None
    baseline_state: BaselineState = "available"


def csv_rows(data: bytes) -> tuple[tuple[str, ...], ...]:
    with StringIO(data.decode("utf-8"), newline="") as stream:
        return tuple(tuple(row) for row in csv.reader(stream, strict=True))


def build_release(
    dataset_id: str,
    profile: str,
    method: str,
    as_of: date,
    data: bytes,
    row_count: int,
    inputs,
    *,
    observations: tuple[Observation, ...] | None = None,
    parameters=None,
    resources=None,
    acquisition=None,
    source_details=None,
) -> ParsedRelease:
    representation = Representation(profile, 1, CSV, data, "utf-8")
    release_id = as_of.isoformat()
    lineage = tuple(inputs)
    batch = (
        ObservationBatch(dataset_id, 1, release_id, observations, lineage)
        if observations is not None
        else None
    )
    version = build_dataset_version(
        dataset_id,
        release_id,
        method,
        lineage,
        representation.identity,
        parameters=parameters,
        resources=resources,
    )
    return ParsedRelease(
        as_of, batch, representation, version, row_count, acquisition, source_details
    )
