"""Retain and restore aligned data through the shared observation codec."""
from stratbox.core.execution import OperationFailure
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.operations.service_network.observation_definitions import SNAPSHOT, RESTORE

def snapshot_observations(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('encode_observations')
        try:
            result = observation_snapshot(req.batch, dataset_id=req.dataset_id, version_id=req.version_id)
        except (ValueError, TypeError) as error:
            raise OperationFailure(str(error)) from None
        for receipt in req.batch.lineage:
            invocation.use(receipt)
        invocation.record(result.identity)
        return result
    return work(request, invocation)

def restore_observations(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('restore_observations')
        try:
            result = observations_from_snapshot(req)
        except (ValueError, TypeError) as error:
            raise OperationFailure(str(error)) from None
        invocation.use(UsedInputReceipt('retained_observations', req.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.manifest.dataset_id))
        for receipt in result.lineage:
            invocation.use(receipt)
        return result
    return work(request, invocation)


def capability_snapshot_observations(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.observations_snapshot', snapshot_observations)


def capability_restore_observations(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.restore_observations', restore_observations)
