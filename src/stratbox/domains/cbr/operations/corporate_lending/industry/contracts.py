"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.snapshots import DatasetSnapshot


@dataclass(frozen=True, slots=True)
class IndustrySnapshotRequest:
    value: object
    dataset_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class ReadIndustrySnapshotRequest:
    snapshot: DatasetSnapshot
