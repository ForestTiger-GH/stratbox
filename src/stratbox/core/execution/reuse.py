"""Qualified reuse of an accessible output admitted by its receiving owner."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Callable

from stratbox.core.execution.contracts import OperationResult
from stratbox.core.execution.handoff import HandoffError, project_output
from stratbox.core.execution.values import argument_identity
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotReference
from stratbox.shared.evidence import MaterialReference, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.materials import MaterialArtifact


@dataclass(frozen=True, slots=True)
class ReuseAssessment:
    eligible: bool
    reasons: tuple[str, ...]
    identity: ByteIdentity | None = None


def _verified_identity(value):
    if isinstance(value, (ByteIdentity, SnapshotReference, MaterialReference)):
        raise ValueError("reuse.material_unresolved")
    if isinstance(value, MaterialArtifact):
        value.__post_init__()
        return _verified_identity(value.representation)
    if isinstance(value, (Representation, SourcePayload)):
        actual = ByteIdentity.of(value.data)
        if actual != value.identity:
            raise ValueError("reuse.material_identity_mismatch")
        return actual
    if isinstance(value, DatasetSnapshot):
        value.__post_init__()
        if not value.complete:
            raise ValueError("reuse.material_incomplete")
        return value.identity
    # Arbitrary user identity properties are claims. A domain may supply its
    # own validator/identity adapter for table-backed scientific result types.
    return argument_identity(value)


def assess_reuse(result: OperationResult, *, expected_computation: ByteIdentity,
                 output_name: str, receiving_owner: Callable[[object], bool] | None,
                 required_qualifications: frozenset[str] = frozenset(),
                 resolve_material: Callable[[ByteIdentity], object] | None = None,
                 verify_identity: Callable[[object], ByteIdentity] | None = None) -> ReuseAssessment:
    """Require computation agreement, real content, qualifications and admission.

    A saved hash or reference alone never proves material availability. The
    resolver and receiving validator are trusted application/domain adapters;
    neither scheduling nor cache ownership belongs to this assessment.
    """
    if not isinstance(result, OperationResult) or not isinstance(expected_computation, ByteIdentity):
        raise ValueError("reuse.request_invalid")
    computation = result.computation
    reasons = []
    if result.outcome not in {"succeeded", "partial"}:
        reasons.append("reuse.outcome_not_qualified")
    if computation is None:
        reasons.append("reuse.computation_missing")
    else:
        if computation.computation_id != expected_computation:
            reasons.append("reuse.computation_mismatch")
        if computation.method_fingerprint is None or not {
            "method_resolved", "signature_complete"
        } <= computation.qualifications:
            reasons.append("reuse.signature_unqualified")
    if reasons:
        return ReuseAssessment(False, tuple(reasons))
    try:
        projected = project_output(result, output_name)
    except HandoffError as error:
        return ReuseAssessment(False, (error.code,))
    qualifications = projected.qualifications | computation.qualifications
    if not required_qualifications <= qualifications:
        return ReuseAssessment(False, ("reuse.qualification_missing",))
    if not callable(receiving_owner):
        return ReuseAssessment(False, ("reuse.owner_admission_required",))
    port = next(port for port in result.definition.processing.outputs if port.name == output_name)
    expected_identity = computation.output if not port.path else projected.identity
    if expected_identity is None:
        return ReuseAssessment(False, ("reuse.output_identity_missing",))
    try:
        material = resolve_material(expected_identity) if resolve_material is not None else projected.value
        identity = (verify_identity or _verified_identity)(material)
        if not isinstance(identity, ByteIdentity) or identity != expected_identity:
            return ReuseAssessment(False, ("reuse.material_identity_mismatch",))
        if not receiving_owner(material):
            return ReuseAssessment(False, ("reuse.owner_rejected",), identity)
    except Exception as error:
        code = str(error)
        if not code.startswith("reuse.") or not all(character.isalnum() or character in "._" for character in code):
            code = "reuse.material_unavailable"
        return ReuseAssessment(False, (code,))
    return ReuseAssessment(True, (), identity)
