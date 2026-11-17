"""Shared data, byte evidence and representation contracts."""

from .comparison import BaselineState, Comparison, ComparisonCoverage, ComparisonLayers, compare_releases
from .evidence import (
    AcquiredSource, AcquisitionReceipt, ByteIdentity, MaterialReference, PublicationReceipt,
    SourcePayload, StoredBytesReceipt, UsedInputReceipt,
)
from .identity import DatasetVersion, build_dataset_version, canonical_manifest_bytes, computation_identity
from .observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef, ValueStatus
from .representation import Representation
from .releases import ReleaseQualification
from .tables import ComputationReceipt, table_identity
