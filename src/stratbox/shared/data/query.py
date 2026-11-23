"""Deterministic bounded queries over one pinned typed component."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage, TableSchema, TypedTable, scalar_value
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class TablePredicate:
    column: str
    operator: str
    value: object = None

    def __post_init__(self):
        if not self.column or self.operator not in {"eq", "ne", "lt", "le", "gt", "ge", "is_null", "not_null"}:
            raise ValueError("query.predicate_invalid")
        if self.operator in {"is_null", "not_null"} and self.value is not None:
            raise ValueError("query.predicate_value_invalid")


@dataclass(frozen=True, slots=True)
class TableQuery:
    component: str
    columns: tuple[str, ...] = ()
    predicates: tuple[TablePredicate, ...] = ()
    offset: int = 0
    limit: int = 100
    scan_limit: int = 10_000

    def __post_init__(self):
        if (type(self.component) is not str or not self.component
                or not isinstance(self.columns, tuple) or len(set(self.columns)) != len(self.columns)
                or not isinstance(self.predicates, tuple) or len(self.predicates) > 32
                or any(not isinstance(p, TablePredicate) for p in self.predicates)
                or type(self.offset) is not int or self.offset < 0
                or type(self.limit) is not int or not 1 <= self.limit <= 10_000
                or type(self.scan_limit) is not int or not self.limit <= self.scan_limit <= 1_000_000):
            raise ValueError("query.selection_invalid")


@dataclass(frozen=True, slots=True)
class TablePreview:
    source_identity: ByteIdentity
    component: str
    table: TypedTable
    source_rows: tuple[int, ...]
    scanned_rows: int
    has_more: bool
    next_offset: int | None
    coverage: SnapshotCoverage


def query_snapshot(snapshot: DatasetSnapshot, query: TableQuery, *, expected_identity=None, checkpoint=None):
    if not isinstance(snapshot, DatasetSnapshot) or not isinstance(query, TableQuery):
        raise ValueError("query.typed_input_required")
    if expected_identity is not None and snapshot.identity != expected_identity:
        raise ValueError("query.snapshot_changed")
    table = snapshot.table(query.component)
    names = tuple(c.name for c in table.schema.columns)
    selected = query.columns or names
    if set(selected) - set(names):
        raise ValueError("query.column_unknown")
    columns = tuple(table.schema.columns[names.index(n)] for n in selected)
    checks = []
    for predicate in query.predicates:
        if predicate.column not in names:
            raise ValueError("query.column_unknown")
        index = names.index(predicate.column)
        if predicate.operator not in {"is_null", "not_null"}:
            scalar_value(predicate.value, table.schema.columns[index])
        checks.append((index, predicate))

    def admitted(row):
        for index, p in checks:
            v = row[index]
            if p.operator == "is_null":
                passed = v is None
            elif p.operator == "not_null":
                passed = v is not None
            elif p.operator == "eq":
                passed = v == p.value
            elif p.operator == "ne":
                passed = v != p.value
            elif v is None or p.value is None:
                passed = False
            elif p.operator == "lt":
                passed = v < p.value
            elif p.operator == "le":
                passed = v <= p.value
            elif p.operator == "gt":
                passed = v > p.value
            else:
                passed = v >= p.value
            if not passed:
                return False
        return True

    rows, positions, scanned = [], [], 0
    position = min(query.offset, len(table.rows))
    while position < len(table.rows) and scanned < query.scan_limit and len(rows) < query.limit:
        if checkpoint is not None:
            checkpoint()
        row = table.rows[position]
        scanned += 1
        if admitted(row):
            rows.append(tuple(row[names.index(n)] for n in selected))
            positions.append(position)
        position += 1
    more = position < len(table.rows)
    primary = table.schema.primary_key if set(table.schema.primary_key) <= set(selected) else ()
    result = TypedTable(TableSchema(table.schema.contract, columns, primary), tuple(rows))
    return TablePreview(snapshot.identity, query.component, result, tuple(positions), scanned, more,
        position if more else None, SnapshotCoverage("partial" if more or query.offset else "complete",
            "Bounded filtered component selection; source-wide completeness is not implied."))
