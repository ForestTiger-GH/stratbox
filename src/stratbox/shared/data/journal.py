"""Detached, immutable facts and certified contiguous journal scan values."""
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping
from stratbox.shared.data.values import canonical_tree, restore_tree

def _freeze(value):
    if value is None or type(value) in (str, int, bool, float, bytes) or isinstance(value, (Decimal, date, time, timedelta)):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({_freeze(key): _freeze(part) for key, part in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(part) for part in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(part) for part in value)
    if is_dataclass(value) and not isinstance(value, type) and getattr(type(value), "__dataclass_params__").frozen:
        return replace(value, **{item.name: _freeze(getattr(value, item.name)) for item in fields(value)})
    raise ValueError("journal.data_immutable_metadata_required")


def _snapshot(data):
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ValueError("journal.data_mapping_required")
    # The portable decoder admits a fixed vocabulary; artifacts never import classes.
    return _freeze(restore_tree(canonical_tree(dict(data))))


def _integer(value, code, *, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or maximum is not None and value > maximum:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class JournalFact:
    sequence: int
    kind: str
    run_id: str
    scope_id: str
    command_id: str | None
    output_name: str | None
    physical_work_id: str | None
    attempt_id: str | None
    data: Mapping[str, object]
    occurred_at: datetime
    stream_id: str = ""

    def __post_init__(self):
        _integer(self.sequence, "journal.sequence_invalid", minimum=1)
        if not isinstance(self.kind, str) or not self.kind or not isinstance(self.run_id, str):
            raise ValueError("journal.fact_identity_invalid")
        if not isinstance(self.occurred_at, datetime):
            raise ValueError("journal.fact_time_invalid")
        object.__setattr__(self, "data", _snapshot(self.data))


@dataclass(frozen=True)
class JournalPage:
    """A confirmed contiguous scan; filters may exclude facts inside its range."""
    stream_id: str
    after: int
    scanned_through: int
    facts: tuple[JournalFact, ...]
    tail: int
    retained_after: int = 0
    filters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("journal.page_stream_required")
        if any(type(value) is not int for value in (self.after, self.scanned_through, self.tail, self.retained_after)) or not 0 <= self.retained_after <= self.after <= self.scanned_through <= self.tail:
            raise ValueError("journal.invalid_page_range")
        facts = tuple(self.facts)
        if any(not isinstance(fact, JournalFact) or fact.stream_id != self.stream_id for fact in facts):
            raise ValueError("journal.invalid_page_facts")
        sequences = tuple(fact.sequence for fact in facts)
        if sequences != tuple(sorted(set(sequences))) or any(not self.after < sequence <= self.scanned_through for sequence in sequences):
            raise ValueError("journal.invalid_page_facts")
        filters = _snapshot(self.filters)
        if set(filters) - {"run_id"} or "run_id" in filters and (not isinstance(filters["run_id"], str) or not filters["run_id"]):
            raise ValueError("journal.page_filter_invalid")
        if filters and any(fact.run_id != filters["run_id"] for fact in facts):
            raise ValueError("journal.page_filter_conflict")
        if not filters and sequences != tuple(range(self.after + 1, self.scanned_through + 1)):
            raise ValueError("journal.page_coverage_gap")
        object.__setattr__(self, "facts", facts)
        object.__setattr__(self, "filters", filters)

    @property
    def has_more(self):
        return self.scanned_through < self.tail


@dataclass(frozen=True)
class JournalCheckpoint:
    stream_id: str
    retained_after: int
    archived_through: int
    tail: int
    consumers: Mapping[str, int]

    def __post_init__(self):
        object.__setattr__(self, "consumers", MappingProxyType(dict(self.consumers)))
