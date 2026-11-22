"""Read-only machine adapter for a scoped FRG cleanup proposal."""

from __future__ import annotations

from stratbox.core.execution.machine.contracts import (
    DirectoryMaterial, ReadOnlyWireCodec, WireRequestError,
)
from . import housekeeping
from ..publications.cleanup import PlanCleanupRequest

from .machine_contracts import PLAN_CONTRACT



def _plan(data, materials, context):
    directory = materials.directory(data["directory_ref"])
    if not isinstance(directory, DirectoryMaterial):
        raise WireRequestError("material.invalid_directory")
    return housekeeping.plan_cleanup(
        PlanCleanupRequest(directory.directory, data.get("delete_others", False)),
        store=directory.store, context=context,
    )


def _project(result):
    if result.value is None:
        return None
    return {"plan_sha256": result.value.identity.sha256,
            "action_count": len(result.value.actions)}


PLAN_CODEC = ReadOnlyWireCodec(PLAN_CONTRACT, _plan, _project)
