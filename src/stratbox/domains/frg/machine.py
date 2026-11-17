"""Read-only machine adapter for a scoped FRG cleanup proposal."""

from __future__ import annotations

from stratbox.system.execution.machine.contracts import (
    DirectoryMaterial, ReadOnlyWireCodec, WireRequestError,
)
from . import api
from .cleanup import PlanCleanupRequest

REF = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
INTEGER = {"type": "integer", "minimum": 0}
DIGEST = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}


def _plan(data, materials, context):
    directory = materials.directory(data["directory_ref"])
    if not isinstance(directory, DirectoryMaterial):
        raise WireRequestError("material.invalid_directory")
    return api.plan_cleanup(
        PlanCleanupRequest(directory.directory, data.get("delete_others", False)),
        store=directory.store, context=context,
    )


def _project(result):
    if result.value is None:
        return None
    return {"plan_sha256": result.value.identity.sha256,
            "action_count": len(result.value.actions)}


PLAN_CODEC = ReadOnlyWireCodec(
    "frg.plan_cleanup", 1,
    {"directory_ref": REF, "delete_others": {"type": "boolean"}},
    ("directory_ref",),
    {"plan_sha256": DIGEST, "action_count": INTEGER},
    _plan, _project,
)
