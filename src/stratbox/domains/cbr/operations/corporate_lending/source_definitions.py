"""Independent source-observation operations for corporate publications."""
from dataclasses import dataclass
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

_LIMITS = ExecutionBudget(cells=80_000_000, output_bytes=256 * 1024 * 1024)
SOURCE = DataContract("cbr.corporate_lending.source_observations", 1, DataRole.EXTRACTS)
SNAPSHOT = DataContract("cbr.corporate_lending.source_observations.snapshot", 1, DataRole.EXTRACTS)


@dataclass(frozen=True, slots=True)
class ExtractCorporateObservationsRequest:
    flake: WorkbookFlake
    periods: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class CorporateObservationSnapshotRequest:
    value: CorporateSourceDataset
    dataset_id: str = "cbr.corporate_lending.source_observations"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadCorporateObservationSnapshotRequest:
    snapshot: DatasetSnapshot


EXTRACT = OperationDefinition("cbr.corporate_lending.extract_observations", 1,
    "cbr-corporate-source-observations-1", ExtractCorporateObservationsRequest, CorporateSourceDataset,
    limits=_LIMITS, processing=OperationSemantics(stages=(ProcessingStage.EXTRACT,),
        summary="Extract every selected source period with exact values, missingness and cell evidence.",
        inputs=(InputPort("flake", DataContract("cbr.workbook.flake", 1, DataRole.EXTRACTS), path="flake"),),
        outputs=(OutputPort("observations", SOURCE),), parameters=("periods",)))

ENCODE = OperationDefinition("cbr.corporate_lending.observation_snapshot", 1,
    "cbr-corporate-observation-snapshot-1", CorporateObservationSnapshotRequest, DatasetSnapshot,
    limits=_LIMITS, processing=OperationSemantics(stages=(ProcessingStage.RENDER,),
        summary="Encode a complete source observation result for independent retention.",
        inputs=(InputPort("value", SOURCE, path="value"),),
        outputs=(OutputPort("snapshot", SNAPSHOT), OutputPort("dataset", DataContract("dataset.snapshot"))),
        parameters=("dataset_id", "version_id",)))

DECODE = OperationDefinition("cbr.corporate_lending.read_observation_snapshot", 1,
    "cbr-corporate-observation-snapshot-1", ReadCorporateObservationSnapshotRequest, CorporateSourceDataset,
    limits=_LIMITS, processing=OperationSemantics(stages=(ProcessingStage.READ_EXTRACT,),
        summary="Restore qualified source observations without reading a workbook or running a model.",
        inputs=(InputPort("snapshot", SNAPSHOT, path="snapshot", alternatives=(DataContract("dataset.snapshot"),)),),
        outputs=(OutputPort("observations", SOURCE),)))
