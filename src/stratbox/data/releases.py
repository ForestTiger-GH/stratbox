"""Contracts shared by date-keyed source releases."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Literal, Mapping

from .comparison import BaselineState
from .evidence import AcquisitionReceipt, ByteIdentity, SourcePayload
from .identity import canonical_manifest_bytes
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
class ReleaseQualification:
    provenance: Literal["offline_bytes", "literal_replay", "provider_reported", "tls_host", "peer_bound"]
    analysis: Literal["qualified", "literal_only"]
    scope: str
    row_count: int


@dataclass(frozen=True, slots=True)
class ParsedRelease:
    as_of: date
    batch: ObservationBatch | None
    representation: Representation
    dataset_version: DatasetVersion
    row_count: int
    acquisition: AcquisitionReceipt | None = None
    source_details: Mapping[str, object] | None = None
    qualification: ReleaseQualification | None = None
    facts_identity: ByteIdentity | None = None


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
    provenance = (
        acquisition.origin_assurance if acquisition is not None
        else "literal_replay" if any(item.role == "csv_representation" for item in lineage)
        else "offline_bytes"
    )
    qualification = ReleaseQualification(
        provenance, "qualified" if batch is not None else "literal_only", dataset_id, row_count,
    )
    facts_identity = None
    if observations is not None:
        facts = []
        for item in observations:
            value = item.value
            if isinstance(value, (int, Decimal)):
                number = format(value, "f")
                if "." in number:
                    number = number.rstrip("0").rstrip(".")
                value = ("number", "0" if number == "-0" else number)
            facts.append(canonical_manifest_bytes({
                "subject": (item.subject.namespace, item.subject.id),
                "metric": (item.metric.id, item.metric.unit),
                "period": (item.period.kind, item.period.as_of, item.period.start, item.period.end),
                "dimensions": sorted(item.dimensions), "perimeter": item.perimeter,
                "status": item.value_status, "value": value,
            }))
        facts_identity = ByteIdentity.of(b"\n".join(sorted(facts)))
    return ParsedRelease(
        as_of, batch, representation, version, row_count, acquisition, source_details,
        qualification, facts_identity,
    )
