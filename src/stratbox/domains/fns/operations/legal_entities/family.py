"""The 1-YUR family's concrete layout, archive and interpretation methods."""
from stratbox.core.execution import OperationFailure
from stratbox.shared.data.releases import ReleaseLink
from ...tables.legal_entities.extraction import WorkbookBundle, extract_bundle
from ...tables.legal_entities.projection import project_reported, validate
from ...tables.legal_entities.readable import readable
from ...tables.legal_entities.snapshots import flake_snapshot, flake_from_snapshot
from ...integration.legal_entities.alignment import align
from ..pipeline import FamilyMethods, FamilyOperations


def _extract(payload, release, *, invocation, rar_reader=None):
    if payload.data.startswith(b"Rar!") and invocation.context.profile == "managed":
        invocation.require_provider("archive_decoder", rar_reader)
    return extract_bundle(payload, release, budget=invocation.budget,
                          checkpoint=invocation.check_cancelled, rar_reader=rar_reader)


def _acquire(request, *, invocation, transport):
    from .operations import _acquire as acquire
    if not request.url:
        raise OperationFailure("request.release_link_required")
    return acquire(ReleaseLink(request.release.observation_date, request.url), invocation, transport)


OPERATIONS = FamilyOperations(FamilyMethods(
    "fns.1yur", WorkbookBundle, 30_000_000, _extract, project_reported, validate, readable,
    flake_snapshot, flake_from_snapshot, align, _acquire,
    lambda value: sum(len(sheet.cells) for _, workbook in value.members for sheet in workbook.sheets)))


def admit(requirement, instance, value):
    return OPERATIONS.admit(requirement, instance, value)
