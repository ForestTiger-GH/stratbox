"""Publisher-neutral, pure source-check health assessment.

A failed publisher check cannot be silently interpreted as an unchanged file.
Consumers independently choose alert thresholds and durable check history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from stratbox.core.execution.contracts import OperationResult
from stratbox.shared.source_publications import _utc

CheckState = Literal["observed", "verified", "unverified", "unavailable", "rejected", "failed", "unknown"]


@dataclass(frozen=True, slots=True)
class SourceCheckAssessment:
    operation_id: str
    checked_at_utc: datetime
    state: CheckState
    reason: str
    diagnostics: tuple[str, ...] = ()

    @property
    def confirms_no_change(self) -> bool:
        # This object is a health report, not a verified comparison of bytes.
        return False


def assess_source_check(
    result: OperationResult, *, checked_at_utc: datetime,
    qualified_source_index: bool | None = None,
) -> SourceCheckAssessment:
    if not isinstance(result, OperationResult):
        raise TypeError("source.check_result_invalid")
    _utc(checked_at_utc)
    codes = tuple(d.code for d in result.diagnostics)
    if result.outcome == "succeeded":
        state = (
            "verified" if qualified_source_index is True
            else "unverified" if qualified_source_index is False
            else "observed"
        )
        reason = "source.check_succeeded"
    elif result.outcome == "unknown":
        state, reason = "unknown", "source.check_uncertain"
    elif any(code.startswith(("http.timeout", "http.connection_error", "http.truncated",
                              "http.status_5", "http.status_404", "http.status_403"))
             for code in codes):
        state, reason = "unavailable", "source.publisher_unavailable"
    elif any(code.endswith(("url_forbidden", "destination_forbidden", "identity_unverified",
                            "source_mismatch", "profile_mismatch")) for code in codes):
        state, reason = "rejected", "source.check_rejected"
    else:
        state, reason = "failed", "source.check_failed"
    return SourceCheckAssessment(result.operation_id, checked_at_utc, state, reason, codes)
