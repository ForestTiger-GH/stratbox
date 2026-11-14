"""Reconstruct bounded operation history without inventing missing lifecycle events."""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from typing import Iterable, Literal
from .contracts import JournalRecord

Coverage = Literal["complete", "incomplete", "indeterminate"]


@dataclass(frozen=True, slots=True)
class OperationHistory:
    invocation_id: str
    records: tuple[JournalRecord, ...]
    outcome: str | None
    duration_ms: int | None
    coverage: Coverage
    missing_sequences: tuple[int, ...]
    problems: tuple[str, ...]
    missing_causes: tuple[str, ...]


def build_operation_history(records: Iterable[JournalRecord], invocation_id: str, *,
                            known_dropped: int = 0, capture_complete: bool = False) -> OperationHistory:
    selected = [r for r in records if r.invocation_id == invocation_id]
    seen = {}
    problems = set()
    for r in selected:
        old = seen.get(r.record_id)
        if old is not None and old != r:
            problems.add("journal.record_identity_conflict")
        else:
            seen[r.record_id] = r
    selected = list(seen.values())
    execution = sorted((r for r in selected if r.record_type == "execution"),
                       key=lambda x: (x.sequence or 0, x.record_id))
    seqs = [r.sequence for r in execution if r.sequence is not None]
    counts = Counter(seqs)
    if any(n > 1 for n in counts.values()):
        problems.add("journal.sequence_conflict")
    missing = tuple(set(range(1, max(seqs) + 1)) - set(seqs)) if seqs else ()
    missing = tuple(sorted(missing))
    if missing:
        problems.add("journal.sequence_gap")
    starts = [r for r in execution if r.kind == "operation.started"]
    finishes = [r for r in execution if r.kind == "operation.finished"]
    if not starts:
        problems.add("journal.start_missing")
    if not finishes:
        problems.add("journal.finish_missing")
    if len(starts) > 1 or len(finishes) > 1:
        problems.add("journal.lifecycle_conflict")
    ids = {r.record_id for r in selected}
    missing_causes = tuple(sorted({cause for r in selected for cause in r.cause_record_ids if cause not in ids}))
    if missing_causes:
        problems.add("journal.causal_parent_missing")
    if known_dropped > 0:
        problems.add("journal.capture_loss")
    if not capture_complete:
        problems.add("journal.coverage_unverified")
    if not selected:
        coverage = "indeterminate"
    elif problems - {"journal.coverage_unverified"}:
        coverage = "incomplete"
    elif capture_complete:
        coverage = "complete"
    else:
        coverage = "indeterminate"
    finish = finishes[0] if len(finishes) == 1 else None
    return OperationHistory(invocation_id, tuple(execution + [r for r in selected if r.record_type != "execution"]),
                            finish.outcome if finish else None,
                            finish.payload.get("duration_ms") if finish else None,
                            coverage, missing, tuple(sorted(problems)), missing_causes)


@dataclass(frozen=True, slots=True)
class OperationStatistics:
    total: int
    outcomes: dict[str, int]
    diagnostic_codes: dict[str, int]
    durations_ms: tuple[int, ...]
    incomplete: int
    indeterminate: int
    coverage: str


def summarize_operations(histories: Iterable[OperationHistory]) -> OperationStatistics:
    items = tuple(histories)
    outcomes: Counter[str] = Counter()
    diagnostics: Counter[str] = Counter()
    durations: list[int] = []
    for h in items:
        if h.outcome is not None:
            outcomes[h.outcome] += 1
        if h.duration_ms is not None:
            durations.append(h.duration_ms)
        for r in h.records:
            if r.record_type == "result_summary":
                diagnostics.update(d["code"] for d in r.payload.get("diagnostics", ()) if isinstance(d, dict))
    incomplete = sum(x.coverage == "incomplete" for x in items)
    indeterminate = sum(x.coverage == "indeterminate" for x in items)
    return OperationStatistics(len(items), dict(outcomes), dict(diagnostics), tuple(durations),
                               incomplete, indeterminate,
                               "complete" if not incomplete and not indeterminate and items else "qualified")
