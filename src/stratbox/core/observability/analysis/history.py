"""Bounded operation reconstruction; proof of collection is explicit evidence."""
from __future__ import annotations
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.assessment.coverage import (CaptureCoverage, CoverageStatus, SequenceRange, count_ranges, find_gaps)
from stratbox.core.observability.assessment.lifecycle import assess_invocation_lifecycle


@dataclass(frozen=True, slots=True)
class OperationHistory:
    invocation_id: str
    records: tuple[JournalRecord, ...]
    outcome: str | None
    duration_ms: int | None
    coverage: CoverageStatus
    missing_sequence_ranges: tuple[SequenceRange, ...]
    missing_sequence_count: int
    problems: tuple[str, ...]
    missing_causes: tuple[str, ...]
    causal_coverage: str = "indeterminate"
    summary_record_id: str | None = None

    def sample_missing_sequences(self, limit: int = 20) -> tuple[int, ...]:
        if not 0 <= limit <= 1000:
            raise ValueError("Invalid sample size")
        result: list[int] = []
        for interval in self.missing_sequence_ranges:
            for number in range(interval.first, min(interval.last + 1, interval.first + limit - len(result))):
                result.append(number)
            if len(result) >= limit:
                break
        return tuple(result)


def build_operation_history(records: Iterable[JournalRecord], invocation_id: str, *,
                            coverage: CaptureCoverage | None = None,
                            max_records: int = 100_000) -> OperationHistory:
    if not 1 <= max_records <= 1_000_000:
        raise ValueError("Invalid history limit")
    # Only target-invocation records are retained. Unrelated record IDs are
    # sampled for causal membership without retaining foreign payloads.
    selected: dict[str, JournalRecord] = {}
    all_ids: set[str] = set()
    aliases: dict[str, str] = {}
    problems: set[str] = set()
    count = 0
    for rec in records:
        count += 1
        if count > max_records:
            problems.add("journal.history_truncated")
            break
        all_ids.add(rec.record_id)
        if rec.record_type == "execution" and rec.sequence is not None:
            alias = f"{rec.invocation_id}.{rec.sequence}"
            prev = aliases.get(alias)
            if prev is not None and prev != rec.record_id:
                problems.add("journal.sequence_conflict")
            aliases[alias] = rec.record_id
        if rec.invocation_id == invocation_id:
            prior = selected.get(rec.record_id)
            if prior is not None and prior != rec:
                problems.add("journal.record_identity_conflict")
            else:
                selected[rec.record_id] = rec
    ordered = list(selected.values())
    execution = sorted((rec for rec in ordered if rec.record_type == "execution"),
                       key=lambda x: (x.sequence or 0, x.record_id))
    if coverage is not None and coverage.invocation_id != invocation_id:
        raise ValueError("Coverage invocation does not match")
    lifecycle, assessment, state = assess_invocation_lifecycle(execution, invocation_id, coverage)
    problems.update(lifecycle.problems)
    problems.update(assessment.reasons)
    missing = find_gaps(lifecycle.accepted_sequences,
                        expected_last=coverage.producer_last_sequence if coverage else None)
    finishes = [rec for rec in execution if rec.kind == "operation.finished"]
    causes = {cause for rec in selected.values() for cause in
              (*rec.cause_record_ids, *((rec.correlation.cause_event_id,)
                                       if rec.correlation.cause_event_id else ()))
              if cause not in all_ids and cause not in aliases}
    if causes:
        problems.add("journal.causal_parent_outside_scope")
    if "journal.history_truncated" in problems or "journal.record_identity_conflict" in problems:
        state = "incomplete"
    finished = finishes[0] if len(finishes) == 1 else None
    summaries = [record for record in ordered if record.record_type == "result_summary" and
                 record.kind == "operation.result"]
    if finished is not None:
        finished_summaries = [
            record for record in summaries if record.payload.get("time_basis") == "producer_finished_event"
            and record.outcome == finished.outcome and record.operation_id == finished.operation_id
            and record.occurred_at_utc == finished.occurred_at_utc
            and record.payload.get("contract_version") == finished.payload.get("contract_version")
            and record.payload.get("method_version") == finished.payload.get("method_version")
            and (record.payload.get("data_version", 1) == 1 or finished.record_id in record.cause_record_ids)
        ]
        if finished_summaries:
            summaries = finished_summaries
        else:
            summaries = [record for record in summaries if record.payload.get("time_basis") == "observation"
                         and record.outcome == finished.outcome and record.operation_id == finished.operation_id]
    by_preference = sorted(summaries, key=lambda record:
                           (-record.payload.get("data_version", 1), record.record_id)
                           if type(record.payload.get("data_version", 1)) is int else (0, record.record_id))
    summary_id = None
    if by_preference:
        chosen = by_preference[0]
        assertion = {key: value for key, value in chosen.payload.items() if key not in {"data_version", "time_basis"}}
        if all((record.operation_id, record.outcome) == (chosen.operation_id, chosen.outcome)
               and assertion == {key: value for key, value in record.payload.items()
                                 if key not in {"data_version", "time_basis"}} for record in summaries):
            summary_id = chosen.record_id
        else:
            problems.add("journal.result_summary_conflict")
    order = tuple(execution + [r for r in ordered if r.record_type != "execution"])
    duration = finished.payload.get("duration_ms") if finished else None
    return OperationHistory(invocation_id, order, finished.outcome if finished else None,
                            duration if type(duration) is int else None,
                            state, missing, count_ranges(missing), tuple(sorted(problems)),
                            tuple(sorted(causes)), "incomplete" if causes else "indeterminate", summary_id)


@dataclass(frozen=True, slots=True)
class OperationStatistics:
    total: int
    outcomes: dict[str, int]
    diagnostic_codes: dict[str, int]
    durations_ms: tuple[int, ...]
    incomplete: int
    indeterminate: int
    coverage: str


def summarize_operations(histories: Iterable[OperationHistory], *, max_histories: int = 100_000) -> OperationStatistics:
    outcomes: Counter[str] = Counter()
    diagnostics: Counter[str] = Counter()
    durations: list[int] = []
    total = incomplete = indeterminate = 0
    seen = set()
    for read, history in enumerate(histories, 1):
        if read > max_histories:
            raise ValueError("journal.summary_limit")
        if history.invocation_id in seen:
            continue
        seen.add(history.invocation_id)
        total += 1
        if history.outcome is not None:
            outcomes[history.outcome] += 1
        if history.duration_ms is not None:
            durations.append(history.duration_ms)
        if history.coverage == "incomplete":
            incomplete += 1
        elif history.coverage == "indeterminate":
            indeterminate += 1
        for rec in history.records:
            if rec.record_id == history.summary_record_id:
                entries = rec.payload.get("diagnostics", ())
                if isinstance(entries, (tuple, list)):
                    diagnostics.update(item["code"] for item in entries if isinstance(item, Mapping)
                                       and type(item.get("code")) is str)
    return OperationStatistics(total, dict(outcomes), dict(diagnostics), tuple(durations),
                               incomplete, indeterminate,
                               "complete" if total and not incomplete and not indeterminate else "qualified")
