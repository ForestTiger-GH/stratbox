from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

ComparisonState = Literal[
    "first_seen", "new_release", "revised", "unchanged", "indeterminate"
]
BaselineState = Literal["available", "confirmed_absent", "unavailable"]


@dataclass(frozen=True, slots=True)
class Comparison:
    state: ComparisonState
    reason: str
    changed_subjects: tuple[str, ...] = ()

    @property
    def changed_count(self) -> int:
        return len(self.changed_subjects)


def compare_releases(
    previous: date | None,
    candidate: date,
    baseline_state: BaselineState,
) -> Comparison | None:
    if baseline_state not in {"available", "confirmed_absent", "unavailable"}:
        raise ValueError("Invalid baseline state")
    if previous is None:
        if baseline_state == "confirmed_absent":
            return Comparison("first_seen", "baseline.confirmed_absent")
        return Comparison("indeterminate", "baseline.unavailable")
    if baseline_state != "available":
        return Comparison("indeterminate", "baseline.unqualified")
    if previous != candidate:
        return Comparison("new_release", "release.date_changed")
    return None
