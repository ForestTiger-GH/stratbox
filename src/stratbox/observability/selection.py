"""Stream-oriented selection, grouping and explicit causal navigation."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Iterator
from .contracts import JournalRecord, require_utc


@dataclass(frozen=True, slots=True)
class RecordFilter:
    record_types: frozenset[str] | None = None
    kinds: frozenset[str] | None = None
    outcomes: frozenset[str] | None = None
    invocation_id: str | None = None
    operation_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    attempt_id: str | None = None
    fact_id: str | None = None
    related_namespace: str | None = None
    related_id: str | None = None
    cause_record_id: str | None = None
    from_utc: datetime | None = None
    until_utc: datetime | None = None
    time_field: str = "occurred"
    diagnostic_code: str | None = None

    def __post_init__(self):
        if self.time_field not in {"occurred", "observed"}:
            raise ValueError("Time field must be occurred or observed")
        if self.from_utc is not None:
            require_utc(self.from_utc)
        if self.until_utc is not None:
            require_utc(self.until_utc)


def select_records(records: Iterable[JournalRecord], criteria: RecordFilter) -> Iterator[JournalRecord]:
    for item in records:
        c = item.correlation
        conditions = (
            criteria.record_types is None or item.record_type in criteria.record_types,
            criteria.kinds is None or item.kind in criteria.kinds,
            criteria.outcomes is None or item.outcome in criteria.outcomes,
            criteria.invocation_id is None or item.invocation_id == criteria.invocation_id,
            criteria.operation_id is None or item.operation_id == criteria.operation_id,
            criteria.run_id is None or c.run_id == criteria.run_id,
            criteria.step_id is None or c.step_id == criteria.step_id,
            criteria.attempt_id is None or c.attempt_id == criteria.attempt_id,
            criteria.fact_id is None or item.fact_id == criteria.fact_id,
            criteria.cause_record_id is None or criteria.cause_record_id in item.cause_record_ids or c.cause_event_id == criteria.cause_record_id,
        )
        if not all(conditions):
            continue
        if criteria.related_id is not None:
            refs = ((item.subject,) if item.subject else ()) + item.references
            if not any(ref.object_id == criteria.related_id and (
                criteria.related_namespace is None or ref.namespace == criteria.related_namespace) for ref in refs):
                continue
        time = item.occurred_at_utc if criteria.time_field == "occurred" else item.observed_at_utc
        if criteria.from_utc is not None and (time is None or time < criteria.from_utc):
            continue
        if criteria.until_utc is not None and (time is None or time >= criteria.until_utc):
            continue
        if criteria.diagnostic_code is not None:
            entries = item.payload.get("diagnostics", ())
            codes = [item.payload.get("diagnostic_code")]
            if isinstance(entries, (list, tuple)):
                codes.extend(x.get("code") for x in entries if isinstance(x, dict))
            if criteria.diagnostic_code not in codes:
                continue
        yield item


def group_records(records: Iterable[JournalRecord], key: Callable[[JournalRecord], str | None]) -> dict[str | None, tuple[JournalRecord, ...]]:
    grouped: dict[str | None, list[JournalRecord]] = {}
    for item in records:
        grouped.setdefault(key(item), []).append(item)
    return {k: tuple(v) for k, v in grouped.items()}


@dataclass(frozen=True, slots=True)
class CausalInspection:
    roots: tuple[JournalRecord, ...]
    missing_parent_ids: tuple[str, ...]


def inspect_causes(records: Iterable[JournalRecord], record_id: str) -> CausalInspection:
    by_id = {item.record_id: item for item in records}
    alias = {f"{item.invocation_id}.{item.sequence}": item.record_id for item in by_id.values()
             if item.record_type == "execution" and item.sequence is not None}
    visited, found, missing = set(), [], set()

    def visit(ident: str):
        if ident in visited:
            return
        visited.add(ident)
        item = by_id.get(alias.get(ident, ident))
        if item is None:
            missing.add(ident)
            return
        found.append(item)
        for parent in item.cause_record_ids:
            visit(parent)
        if item.correlation.cause_event_id:
            visit(item.correlation.cause_event_id)

    visit(record_id)
    return CausalInspection(tuple(found), tuple(sorted(missing)))
