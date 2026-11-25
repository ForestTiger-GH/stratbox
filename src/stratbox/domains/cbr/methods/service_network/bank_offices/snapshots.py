"""Persist and restore the complete daily-office release boundary."""
from collections.abc import Mapping
from datetime import date
from stratbox.core.execution import OperationFailure
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.releases import csv_rows
from stratbox.domains.cbr.tables.service_network.snapshots import release_from_snapshot, release_snapshot
from stratbox.domains.cbr.operations.service_network.bank_offices.definitions import DATASET, RESTORE, SNAPSHOT
from stratbox.domains.cbr.tables.service_network.bank_offices.parser import CaptureError
from stratbox.domains.cbr.tables.service_network.bank_offices.representation import validate_csv_bytes
from stratbox.domains.cbr.tables.service_network.bank_offices.observations import _observations
_PROFILE = 'cbr.offices.wide-csv'

def _validate(value):
    count, _ = validate_csv_bytes(value.representation.data)
    details = value.source_details
    if count != value.row_count or not isinstance(details, Mapping) or details.get('captured_on') != value.as_of:
        raise ValueError('cbr.offices.capture_metadata_invalid')
    official = details.get('official_as_of')
    basis = details.get('period_basis', 'as_of' if official is not None else 'capture')
    if official is not None and type(official) is not date or basis not in {'capture', 'as_of', 'unknown'}:
        raise ValueError('cbr.offices.observation_period_invalid')
    if (basis == 'as_of') != (official is not None):
        raise ValueError('cbr.offices.observation_period_invalid')
    if basis == 'unknown':
        if value.batch is not None:
            raise ValueError('cbr.offices.observation_period_invalid')
    elif value.batch is not None:
        expected = _observations(csv_rows(value.representation.data), value.as_of, official)
        if value.batch.observations != expected:
            raise ValueError('cbr.offices.observation_period_invalid')

def snapshot_release(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('encode_release')
        try:
            value = release_snapshot(req.release, dataset=DATASET, profile=_PROFILE, dataset_id=req.dataset_id, version_id=req.version_id, checkpoint=invocation.check_cancelled)
            _validate(req.release)
        except (ValueError, TypeError, KeyError, CaptureError):
            raise OperationFailure('cbr.offices.snapshot_invalid') from None
        for receipt in req.release.inputs:
            invocation.use(receipt)
        invocation.record(value.identity)
        return value
    return work(request, invocation)

def restore_release(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('restore_release')
        try:
            value = release_from_snapshot(req, dataset=DATASET, profile=_PROFILE, checkpoint=invocation.check_cancelled)
            _validate(value)
        except (ValueError, TypeError, KeyError, CaptureError):
            raise OperationFailure('cbr.offices.snapshot_invalid') from None
        invocation.use(UsedInputReceipt('retained_snapshot', req.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.manifest.dataset_id))
        for receipt in value.inputs:
            invocation.use(receipt)
        return value
    return work(request, invocation)


def capability_restore_release(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.offices.restore', restore_release)


def capability_snapshot_release(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.offices.snapshot', snapshot_release)
