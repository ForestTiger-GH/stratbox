"""Snapshot wrapper ports prevent false replay edges while preserving generic storage."""
import pytest

from stratbox.shared.data.operations import compatible_ports
from stratbox.core.storage.datasets.definitions import WRITE
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.workbooks import WORKBOOK_EXTRACT,WORKBOOK_SNAPSHOT
from stratbox.shared.data.documents import DOCUMENT_EXTRACT,DOCUMENT_SNAPSHOT
from stratbox.shared.data.views import OBSERVATION_VIEW,OBSERVATION_VIEW_SNAPSHOT
from stratbox.domains.rosstat.tables.snapshots import FLAKE_CONTRACT,FLAKE_SNAPSHOT_CONTRACT
from stratbox.domains.rosstat.integration.datasets import DATASET_CONTRACT,DATASET_SNAPSHOT_CONTRACT
from stratbox.domains.rosstat.operations import definitions as D

_ROUTES=(
    (D.WORKBOOK_SNAPSHOT,D.READ_WORKBOOK,WORKBOOK_EXTRACT,WORKBOOK_SNAPSHOT),
    (D.DOCUMENT_SNAPSHOT,D.READ_DOCUMENT,DOCUMENT_EXTRACT,DOCUMENT_SNAPSHOT),
    (D.FLAKE_SNAPSHOT,D.READ_FLAKE,FLAKE_CONTRACT,FLAKE_SNAPSHOT_CONTRACT),
    (D.DATASET_SNAPSHOT,D.READ_DATASET,DATASET_CONTRACT,DATASET_SNAPSHOT_CONTRACT),
    (D.VIEW_SNAPSHOT,D.READ_VIEW,OBSERVATION_VIEW,OBSERVATION_VIEW_SNAPSHOT),
)


@pytest.mark.parametrize("producer",_ROUTES,ids=lambda route:route[0].operation_id)
@pytest.mark.parametrize("consumer",_ROUTES,ids=lambda route:route[1].operation_id)
def test_snapshot_types_connect_only_to_their_own_replay(producer,consumer):
    encode,_,_,wrapper=producer
    _,decode,_,expected=consumer
    input_port,=decode.processing.inputs
    assert input_port.contract==expected
    assert not input_port.alternatives
    matches=[output for output in encode.processing.outputs if compatible_ports(output,input_port)]
    assert bool(matches)==(wrapper==expected)
    if matches:
        assert [output.name for output in matches]==["snapshot"]


@pytest.mark.parametrize("route",_ROUTES,ids=lambda route:route[0].operation_id)
def test_encode_exposes_distinct_wrapper_and_generic_storage_contracts(route):
    encode,decode,value_contract,wrapper=route
    outputs={output.name:output for output in encode.processing.outputs}
    assert outputs["snapshot"].contract==wrapper
    assert wrapper!=value_contract
    assert wrapper.role==value_contract.role and wrapper.version==1
    assert outputs["storage_snapshot"].contract==DataContract("dataset.snapshot",1)
    assert outputs["snapshot"].path==outputs["storage_snapshot"].path==""
    storage_input=next(port for port in WRITE.processing.inputs if port.name=="snapshot")
    assert compatible_ports(outputs["storage_snapshot"],storage_input)
    assert compatible_ports(outputs["snapshot"],decode.processing.inputs[0])
    assert not compatible_ports(outputs["storage_snapshot"],decode.processing.inputs[0])
