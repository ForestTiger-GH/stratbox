"""The published SME population family's concrete scientific methods."""
from stratbox.core.execution import OperationFailure
from ...tables.contracts import JsonFlake
from ...tables.sme.extraction import extract_json
from ...tables.sme.projection import project_counts, validate
from ...tables.sme.readable import readable
from ...tables.sme.snapshots import flake_snapshot, flake_from_snapshot
from ...integration.sme.alignment import align
from ..pipeline import FamilyMethods, FamilyOperations


def _extract(payload, release, *, invocation, rar_reader=None):
    return extract_json(payload, release, budget=invocation.budget, checkpoint=invocation.check_cancelled)


def _acquire(request, *, invocation, transport):
    from .definitions import AcquireSmeRequest
    from .operations import _acquire as acquire
    if request.url is not None:
        raise OperationFailure("fns.sme.fixed_endpoint_required")
    return acquire(AcquireSmeRequest(request.release.observation_date), invocation, transport)


OPERATIONS = FamilyOperations(FamilyMethods(
    "fns.sme", JsonFlake, 4_000_000, _extract, project_counts, validate, readable,
    flake_snapshot, flake_from_snapshot, align, _acquire,
    lambda value: sum(len(record.fields) for record in value.records)))


def admit(requirement, instance, value):
    return OPERATIONS.admit(requirement, instance, value)
