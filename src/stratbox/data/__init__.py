"""Shared data, byte evidence and representation contracts."""

from .comparison import BaselineState, Comparison, compare_releases
from .evidence import (
    AcquiredSource, AcquisitionReceipt, ByteIdentity, PublicationReceipt,
    SourcePayload, StoredBytesReceipt, UsedInputReceipt,
)
from .identity import DatasetVersion, build_dataset_version, canonical_manifest_bytes
from .observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef, ValueStatus
from .representation import Representation
