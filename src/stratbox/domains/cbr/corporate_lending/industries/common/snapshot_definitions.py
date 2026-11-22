"""Identical snapshot transport semantics with independent family contracts."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

from .contracts import IndustrySnapshotRequest, ReadIndustrySnapshotRequest
from .limits import TABLE_LIMITS
from .snapshots import snapshot_contract


def snapshot_definitions(family, kind, value_type):
    prefix = f"cbr.industries.{family}"
    contracts = {
        "flake": DataContract(f"{prefix}.parsed_file", 1, DataRole.EXTRACTS),
        "stream": DataContract(f"{prefix}.stream_result", 1, DataRole.INTEGRATED),
        "calculation": DataContract(f"{prefix}.calculation", 1, DataRole.INTEGRATED),
        "view": DataContract(f"{prefix}.pivots", 1, DataRole.PRODUCTS),
    }
    value_contract = contracts[kind]
    snapshot = snapshot_contract(family, kind)
    generic = DataContract("dataset.snapshot", 1, None)
    return (
        OperationDefinition(f"{prefix}.{kind}_snapshot", 1, "cbr-industry-snapshot-1", IndustrySnapshotRequest,
            DatasetSnapshot, limits=TABLE_LIMITS, processing=OperationSemantics(
                stages=(ProcessingStage.RENDER,), summary=f"Encode a complete {kind} with table schemas and domain context.",
                inputs=(InputPort("value", value_contract, path="value"),),
                outputs=(OutputPort("snapshot", snapshot), OutputPort("dataset", generic)),
                parameters=("dataset_id", "version_id"))),
        OperationDefinition(f"{prefix}.read_{kind}_snapshot", 1, "cbr-industry-snapshot-1", ReadIndustrySnapshotRequest,
            value_type, limits=TABLE_LIMITS, processing=OperationSemantics(
                stages=(ProcessingStage.READ_EXTRACT,), summary=f"Restore a complete {kind} and validate its original table identities.",
                inputs=(InputPort("snapshot", snapshot, path="snapshot", alternatives=(generic,)),),
                outputs=(OutputPort("value", value_contract),))),
    )
