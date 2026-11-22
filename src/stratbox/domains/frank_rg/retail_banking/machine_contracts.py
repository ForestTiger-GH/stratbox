"""Read-only machine schemas, independent of executable adapters."""

from stratbox.core.execution.machine.contracts import ReadOnlyWireContract

REF = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}

INTEGER = {"type": "integer", "minimum": 0}

DIGEST = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}

PLAN_CONTRACT = ReadOnlyWireContract(
    "frg.plan_cleanup",
    1,
    {"directory_ref": REF, "delete_others": {"type": "boolean"}},
    ("directory_ref",),
    {"plan_sha256": DIGEST, "action_count": INTEGER},
)
