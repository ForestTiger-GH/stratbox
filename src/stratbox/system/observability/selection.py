"""Lazy selection, bounded grouping and iterative, qualified causal traversal."""
from __future__ import annotations
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

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
            raise ValueError("Invalid time selection")
        for item in (self.from_utc, self.until_utc):
            if item is not None:
                require_utc(item)


def select_records(records: Iterable[JournalRecord], criteria: RecordFilter) -> Iterator[JournalRecord]:
    for record in records:
        c = record.correlation
        if not all((
            criteria.record_types is None or record.record_type in criteria.record_types,
            criteria.kinds is None or record.kind in criteria.kinds,
            criteria.outcomes is None or record.outcome in criteria.outcomes,
            criteria.invocation_id is None or record.invocation_id == criteria.invocation_id,
            criteria.operation_id is None or record.operation_id == criteria.operation_id,
            criteria.run_id is None or c.run_id == criteria.run_id,
            criteria.step_id is None or c.step_id == criteria.step_id,
            criteria.attempt_id is None or c.attempt_id == criteria.attempt_id,
            criteria.fact_id is None or record.fact_id == criteria.fact_id,
            criteria.cause_record_id is None or criteria.cause_record_id in record.cause_record_ids
            or c.cause_event_id == criteria.cause_record_id,
        )):
            continue
        if criteria.related_id is not None:
            refs = ((record.subject,) if record.subject else ()) + record.references
            if not any(ref.object_id == criteria.related_id and (
                criteria.related_namespace is None or ref.namespace == criteria.related_namespace) for ref in refs):
                continue
        instant = record.occurred_at_utc if criteria.time_field == "occurred" else record.observed_at_utc
        if criteria.from_utc is not None and (instant is None or instant < criteria.from_utc):
            continue
        if criteria.until_utc is not None and (instant is None or instant >= criteria.until_utc):
            continue
        if criteria.diagnostic_code is not None:
            diagnostics = record.payload.get("diagnostics", ())
            codes = [record.payload.get("diagnostic_code")]
            if isinstance(diagnostics, (tuple, list)):
                codes.extend(x.get("code") for x in diagnostics if isinstance(x, Mapping))
            if criteria.diagnostic_code not in codes:
                continue
        yield record


def group_records(records: Iterable[JournalRecord], key: Callable[[JournalRecord], str | None], *,
                  max_records: int = 100_000, max_groups: int = 10_000) -> dict[str | None, tuple[JournalRecord, ...]]:
    """Materializes groups, unlike select_records; callers can bound input."""
    result: dict[str | None, list[JournalRecord]] = {}
    for i, record in enumerate(records, 1):
        if i > max_records:
            raise ValueError("journal.group_record_limit")
        group = key(record)
        if group not in result and len(result) >= max_groups:
            raise ValueError("journal.group_limit")
        result.setdefault(group, []).append(record)
    return {k: tuple(v) for k, v in result.items()}


@dataclass(frozen=True, slots=True)
class CausalInspection:
    roots: tuple[JournalRecord, ...]
    missing_parent_ids: tuple[str, ...]
    conflicts: tuple[str, ...] = ()
    truncated: bool = False
    reason: str | None = None


def inspect_causes(records: Iterable[JournalRecord], record_id: str, *,
                   max_nodes: int = 10_000, max_depth: int = 1000,
                   max_input_records: int = 100_000) -> CausalInspection:
    if not 1 <= max_nodes <= 100_000 or not 1 <= max_depth <= 100_000:
        raise ValueError("Invalid causal traversal budget")
    by_id: dict[str, JournalRecord] = {}
    aliases: dict[str, str] = {}
    conflicts: set[str] = set()
    truncated = False
    for n, item in enumerate(records, 1):
        if n > max_input_records:
            truncated = True
            break
        prev = by_id.get(item.record_id)
        if prev is not None and prev != item:
            conflicts.add(item.record_id)
        else:
            by_id[item.record_id] = item
        if item.record_type == "execution" and item.sequence is not None:
            alias = f"{item.invocation_id}.{item.sequence}"
            prior = aliases.get(alias)
            if prior is not None and prior != item.record_id:
                conflicts.add(alias)
            else:
                aliases[alias] = item.record_id
    seen: set[str] = set()
    found: list[JournalRecord] = []
    missing: set[str] = set()
    stack = [(record_id, 0)]
    reason = "journal.input_limit" if truncated else None
    while stack:
        ident, depth = stack.pop()
        if ident in seen:
            continue
        if len(seen) >= max_nodes or depth > max_depth:
            truncated, reason = True, "journal.causes_limit"
            break
        seen.add(ident)
        if ident in conflicts:
            continue
        target = aliases.get(ident, ident)
        if target in conflicts:
            continue
        item = by_id.get(target)
        if item is None:
            missing.add(ident)
            continue
        found.append(item)
        parents = list(item.cause_record_ids)
        if item.correlation.cause_event_id:
            parents.append(item.correlation.cause_event_id)
        stack.extend((parent, depth + 1) for parent in reversed(parents))
    return CausalInspection(tuple(found), tuple(sorted(missing)), tuple(sorted(conflicts)), truncated, reason)
