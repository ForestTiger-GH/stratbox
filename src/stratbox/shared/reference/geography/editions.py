"""Supplied, dated territory editions and explicit administrative transitions.

Codes remain strings in their declared namespaces. Hierarchy and transitions
are evidence, not authority to aggregate data or equate statistical perimeters.
No complete official municipal directory is implied by the packaged aliases.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from .models import GEOGRAPHY_KINDS


@dataclass(frozen=True, slots=True)
class TerritoryUnit:
    namespace: str
    code: str
    name: str
    kind: str
    effective_from: date
    effective_to: date | None
    parent_namespace: str | None
    parent_code: str | None
    perimeter_id: str
    evidence_ref: str

    def __post_init__(self):
        if (any(type(v) is not str or not v for v in (self.namespace, self.code, self.name, self.perimeter_id, self.evidence_ref))
                or self.kind not in GEOGRAPHY_KINDS or type(self.effective_from) is not date
                or self.effective_to is not None and (type(self.effective_to) is not date or self.effective_to < self.effective_from)
                or (self.parent_namespace is None) != (self.parent_code is None)
                or self.parent_namespace is not None and (not self.parent_namespace or not self.parent_code)
                or (self.namespace, self.code) == (self.parent_namespace, self.parent_code)):
            raise ValueError("geography.unit_invalid")

    def covers(self, as_of):
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)


@dataclass(frozen=True, slots=True)
class TerritoryTransition:
    predecessor_namespace: str
    predecessor_code: str
    successor_namespace: str
    successor_code: str
    kind: str
    effective_on: date
    evidence_ref: str

    def __post_init__(self):
        if (self.kind not in {"rename", "recode", "split", "merge", "boundary_change"}
                or type(self.effective_on) is not date
                or any(type(v) is not str or not v for v in (self.predecessor_namespace, self.predecessor_code,
                    self.successor_namespace, self.successor_code, self.evidence_ref))):
            raise ValueError("geography.transition_invalid")


@dataclass(frozen=True, slots=True)
class TerritoryEdition:
    reference_id: str
    edition_id: str
    units: tuple[TerritoryUnit, ...]
    transitions: tuple[TerritoryTransition, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage

    def __post_init__(self):
        if (not self.reference_id or not self.edition_id or not isinstance(self.units, tuple)
                or any(not isinstance(u, TerritoryUnit) for u in self.units)
                or not isinstance(self.transitions, tuple) or any(not isinstance(t, TerritoryTransition) for t in self.transitions)
                or not isinstance(self.lineage, tuple) or not self.lineage
                or any(not isinstance(i, UsedInputReceipt) for i in self.lineage)
                or not isinstance(self.coverage, SnapshotCoverage)):
            raise ValueError("geography.edition_invalid")
        groups = {}
        for unit in self.units:
            groups.setdefault((unit.namespace, unit.code), []).append(unit)
        for units in groups.values():
            ordered = sorted(units, key=lambda u: u.effective_from)
            if any(a.effective_to is None or a.effective_to >= b.effective_from for a,b in zip(ordered, ordered[1:])):
                raise ValueError("geography.overlapping_code_validity")

    def resolve(self, namespace: str, code: str, *, as_of: date):
        if type(as_of) is not date:
            raise ValueError("geography.date_required")
        found = tuple(u for u in self.units if (u.namespace, u.code) == (namespace, code) and u.covers(as_of))
        return found[0] if found else None

    def ancestors(self, namespace: str, code: str, *, as_of: date):
        result, seen = [], set()
        while True:
            key = namespace, code
            if key in seen:
                raise ValueError("geography.hierarchy_cycle")
            seen.add(key)
            unit = self.resolve(namespace, code, as_of=as_of)
            if unit is None:
                raise ValueError("geography.hierarchy_gap")
            result.append(unit)
            if unit.parent_code is None:
                return tuple(result)
            namespace, code = unit.parent_namespace, unit.parent_code

    @property
    def identity(self):
        return territory_snapshot(self).identity


_T, _D = ScalarType.TEXT, ScalarType.DATE
_CONTRACT = DataContract("reference.territory_edition", 1)
_META = TableSchema(DataContract("reference.territory_metadata", 1), (
    ColumnSchema("reference_id", _T), ColumnSchema("edition_id", _T)))
_UNITS = TableSchema(DataContract("reference.territory_units", 1), (
    ColumnSchema("namespace", _T), ColumnSchema("code", _T), ColumnSchema("name", _T), ColumnSchema("kind", _T),
    ColumnSchema("effective_from", _D), ColumnSchema("effective_to", _D, True),
    ColumnSchema("parent_namespace", _T, True), ColumnSchema("parent_code", _T, True),
    ColumnSchema("perimeter_id", _T), ColumnSchema("evidence_ref", _T)), ("namespace", "code", "effective_from"))
_TRANSITIONS = TableSchema(DataContract("reference.territory_transitions", 1), (
    *(ColumnSchema(n, _T) for n in ("predecessor_namespace", "predecessor_code", "successor_namespace", "successor_code", "kind")),
    ColumnSchema("effective_on", _D), ColumnSchema("evidence_ref", _T)))


def territory_snapshot(value: TerritoryEdition):
    value.__post_init__()
    rows = tuple((u.namespace,u.code,u.name,u.kind,u.effective_from,u.effective_to,u.parent_namespace,
                  u.parent_code,u.perimeter_id,u.evidence_ref) for u in value.units)
    transitions = tuple((t.predecessor_namespace,t.predecessor_code,t.successor_namespace,t.successor_code,
                         t.kind,t.effective_on,t.evidence_ref) for t in value.transitions)
    return DatasetSnapshot.build(value.reference_id,value.edition_id,_CONTRACT,(
        ("metadata",TypedTable(_META,((value.reference_id,value.edition_id),))),
        ("units",TypedTable(_UNITS,rows)),("transitions",TypedTable(_TRANSITIONS,transitions))),
        coverage=value.coverage,inputs=value.lineage)


def territory_from_snapshot(snapshot: DatasetSnapshot):
    if (not snapshot.complete or snapshot.manifest.contract != _CONTRACT
            or tuple(n for n,_ in snapshot.tables) != ("metadata","units","transitions")
            or snapshot.table("metadata").schema != _META or len(snapshot.table("metadata").rows) != 1
            or snapshot.table("units").schema != _UNITS or snapshot.table("transitions").schema != _TRANSITIONS):
        raise ValueError("geography.snapshot_invalid")
    reference,edition = snapshot.table("metadata").rows[0]
    value = TerritoryEdition(reference,edition,tuple(TerritoryUnit(*r) for r in snapshot.table("units").rows),
        tuple(TerritoryTransition(*r) for r in snapshot.table("transitions").rows),
        snapshot.manifest.inputs,snapshot.manifest.coverage)
    if territory_snapshot(value).identity != snapshot.identity:
        raise ValueError("geography.snapshot_identity_mismatch")
    return value
