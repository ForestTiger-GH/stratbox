"""Trusted typed conditions evaluated inside the operation execution boundary.

Policies are supplied by trusted Python bindings. Registry declarations describe
their meaning and never supply executable postcondition callbacks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from stratbox.core.execution.contracts import Diagnostic, OperationDefinition, Outcome

AdmissionPhase = Literal["result", "precommit"]


class ResultAdmission(ABC):
    """A trusted result condition, independent of a concrete source or storage.

    An empty diagnostic tuple admits the value. A rejection supplies classified
    diagnostics; the runner retains every effect receipt and resolves uncertainty.
    The ``precommit`` phase sees prepared data, which may have a different type
    from the final storage receipt. Its outcome is pending (``None``). The final
    phase receives the actual work outcome so alternative output obligations can
    be selected without treating a valid partial value as a complete release.
    """

    policy_id: str

    @abstractmethod
    def assess(
        self, definition: OperationDefinition, value: object, *, phase: AdmissionPhase,
        outcome: Outcome | None = None,
    ) -> tuple[Diagnostic, ...]:
        """Return bounded reasons for rejecting this prepared or final value."""
        raise NotImplementedError


def assess_result(definition, value, policies, *, phase: AdmissionPhase, outcome=None):
    """Validate policy decisions without admitting arbitrary callables."""
    from stratbox.core.execution.contracts import Diagnostic

    if phase not in {"result", "precommit"}:
        raise ValueError("result.admission_phase_invalid")
    if outcome not in {None, "succeeded", "partial", "failed", "cancelled", "unknown"}:
        raise ValueError("result.admission_outcome_invalid")
    diagnostics = []
    for policy in policies:
        if not isinstance(policy, ResultAdmission):
            raise TypeError("result.admission_policy_invalid")
        decision = policy.assess(definition, value, phase=phase, outcome=outcome)
        if (not isinstance(decision, tuple) or len(decision) > 32
                or any(not isinstance(item, Diagnostic) for item in decision)):
            raise ValueError("result.admission_decision_invalid")
        diagnostics.extend(decision)
    return tuple(dict.fromkeys(diagnostics))
