"""Supplied, dated territory records and explicit administrative transitions.

Codes remain strings in their declared namespaces. Hierarchy and transitions
are evidence, not authority to aggregate data or equate statistical perimeters.
No complete official municipal directory is implied by the packaged aliases.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from stratbox.shared.data.coverage import SnapshotCoverage, coverage_value, coverage_from
from stratbox.shared.data.lineage import input_value, input_from
from stratbox.shared.identity import canonical_manifest_bytes
import json
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
        if any((type(v) is not str or not v for v in (self.namespace, self.code, self.name, self.perimeter_id, self.evidence_ref))) or self.kind not in GEOGRAPHY_KINDS or type(self.effective_from) is not date or (self.effective_to is not None and (type(self.effective_to) is not date or self.effective_to < self.effective_from)) or ((self.parent_namespace is None) != (self.parent_code is None)) or (self.parent_namespace is not None and (not self.parent_namespace or not self.parent_code)) or ((self.namespace, self.code) == (self.parent_namespace, self.parent_code)):
            raise ValueError('geography.unit_invalid')

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
        if self.kind not in {'rename', 'recode', 'split', 'merge', 'boundary_change'} or type(self.effective_on) is not date or any((type(v) is not str or not v for v in (self.predecessor_namespace, self.predecessor_code, self.successor_namespace, self.successor_code, self.evidence_ref))):
            raise ValueError('geography.transition_invalid')

@dataclass(frozen=True, slots=True)
class TerritoryDataset:
    reference_id: str
    issue_id: str
    units: tuple[TerritoryUnit, ...]
    transitions: tuple[TerritoryTransition, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage

    def __post_init__(self):
        if not self.reference_id or not self.issue_id or (not isinstance(self.units, tuple)) or any((not isinstance(u, TerritoryUnit) for u in self.units)) or (not isinstance(self.transitions, tuple)) or any((not isinstance(t, TerritoryTransition) for t in self.transitions)) or (not isinstance(self.lineage, tuple)) or (not self.lineage) or any((not isinstance(i, UsedInputReceipt) for i in self.lineage)) or (not isinstance(self.coverage, SnapshotCoverage)):
            raise ValueError('geography.dataset_invalid')
        groups = {}
        for unit in self.units:
            groups.setdefault((unit.namespace, unit.code), []).append(unit)
        for units in groups.values():
            ordered = sorted(units, key=lambda u: u.effective_from)
            if any((a.effective_to is None or a.effective_to >= b.effective_from for a, b in zip(ordered, ordered[1:]))):
                raise ValueError('geography.overlapping_code_validity')

    def resolve(self, namespace: str, code: str, *, as_of: date):
        if type(as_of) is not date:
            raise ValueError('geography.date_required')
        found = tuple((u for u in self.units if (u.namespace, u.code) == (namespace, code) and u.covers(as_of)))
        return found[0] if found else None

    def ancestors(self, namespace: str, code: str, *, as_of: date):
        result, seen = ([], set())
        while True:
            key = (namespace, code)
            if key in seen:
                raise ValueError('geography.hierarchy_cycle')
            seen.add(key)
            unit = self.resolve(namespace, code, as_of=as_of)
            if unit is None:
                raise ValueError('geography.hierarchy_gap')
            result.append(unit)
            if unit.parent_code is None:
                return tuple(result)
            namespace, code = (unit.parent_namespace, unit.parent_code)

    @property
    def identity(self):
        return territory_snapshot(self).identity

@dataclass(frozen=True, slots=True)
class TerritorySnapshot:
    data: bytes

    @property
    def identity(self):
        return ByteIdentity.of(self.data)


def territory_snapshot(value: TerritoryDataset):
    value.__post_init__()
    units=[(u.namespace,u.code,u.name,u.kind,u.effective_from.isoformat(),
        u.effective_to.isoformat() if u.effective_to else None,u.parent_namespace,u.parent_code,
        u.perimeter_id,u.evidence_ref) for u in value.units]
    transitions=[(t.predecessor_namespace,t.predecessor_code,t.successor_namespace,t.successor_code,
        t.kind,t.effective_on.isoformat(),t.evidence_ref) for t in value.transitions]
    document={'reference_id':value.reference_id,'issue_id':value.issue_id,'units':units,
        'transitions':transitions,'lineage':[input_value(item) for item in value.lineage],
        'coverage':coverage_value(value.coverage)}
    return TerritorySnapshot(canonical_manifest_bytes(document))


def territory_from_snapshot(snapshot):
    if not isinstance(snapshot,TerritorySnapshot):raise TypeError('geography.snapshot_required')
    try:
        doc=json.loads(snapshot.data)
        if set(doc)!={'reference_id','issue_id','units','transitions','lineage','coverage'}:
            raise ValueError('geography.snapshot_fields')
        units=tuple(TerritoryUnit(*row[:4],date.fromisoformat(row[4]),date.fromisoformat(row[5]) if row[5] else None,*row[6:]) for row in doc['units'])
        transitions=tuple(TerritoryTransition(*row[:5],date.fromisoformat(row[5]),row[6]) for row in doc['transitions'])
        value=TerritoryDataset(doc['reference_id'],doc['issue_id'],units,transitions,
            tuple(input_from(item) for item in doc['lineage']),coverage_from(doc['coverage']))
        if territory_snapshot(value).identity!=snapshot.identity:
            raise ValueError('geography.snapshot_identity_mismatch')
        return value
    except (KeyError,TypeError,IndexError,json.JSONDecodeError) as error:
        raise ValueError('geography.snapshot_invalid') from error
