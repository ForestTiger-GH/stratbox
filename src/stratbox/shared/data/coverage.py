"""Explicit semantic coverage independent of material format or storage."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SelectedScopeCoverage:
    """A closed requested subset with the parent qualification kept separately."""
    parent_identity: str
    selector_identity: str
    requested: tuple[str, ...]
    selected: tuple[str, ...]
    missing: tuple[str, ...]
    parent_assessment: object
    membership_closed: bool = True

    def __post_init__(self):
        if not self.parent_identity or not self.selector_identity or type(self.membership_closed) is not bool:
            raise ValueError("coverage.selected_scope_invalid")
        for name in ("requested", "selected", "missing"):
            values = tuple(getattr(self, name))
            if len(values) > 1000000 or len(values) != len(set(values)) or any(not isinstance(v, str) or not v for v in values):
                raise ValueError("coverage.selected_members_invalid")
            object.__setattr__(self, name, values)
        if set(self.selected) & set(self.missing) or not set(self.missing) <= set(self.requested):
            raise ValueError("coverage.selected_scope_conflict")

    @property
    def status(self):
        return "complete" if self.membership_closed and not self.missing and set(self.requested) <= set(self.selected) else "partial"

@dataclass(frozen=True, slots=True)
class CoverageDimension:
    """Explicit members of one scope axis; empty sets make no completeness claim."""

    name: str
    requested: tuple[str, ...] = ()
    materialized: tuple[str, ...] = ()
    validated: tuple[str, ...] = ()
    interpreted: tuple[str, ...] = ()
    output: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name or len(self.name) > 128:
            raise ValueError("coverage.axis_name_invalid")
        for name in ("requested", "materialized", "validated", "interpreted", "output", "missing"):
            values = getattr(self, name)
            if (not isinstance(values, tuple) or len(values) != len(set(values))
                    or any(type(value) is not str or not value or len(value) > 1024 for value in values)):
                raise ValueError("dataset.invalid_coverage_dimension")
        if set(self.missing) & set(self.output):
            raise ValueError("dataset.conflicting_coverage")
        if self.requested and (set(self.output) | set(self.missing)) - set(self.requested):
            raise ValueError("dataset.coverage_scope_mismatch")


@dataclass(frozen=True, slots=True)
class SnapshotCoverage:
    """Caller-declared source coverage, independent of selected table membership."""

    status: str
    description: str | None = None
    dimensions: tuple[CoverageDimension, ...] = ()

    def __post_init__(self):
        if self.status not in {"complete", "partial", "unknown"}:
            raise ValueError("dataset.invalid_coverage")
        if self.description is not None and (not isinstance(self.description, str) or not self.description
                                             or len(self.description) > 4096):
            raise ValueError("dataset.invalid_coverage")
        if (not isinstance(self.dimensions, tuple) or any(not isinstance(v, CoverageDimension) for v in self.dimensions)
                or len({v.name for v in self.dimensions}) != len(self.dimensions)
                or self.status == "complete" and any(v.missing for v in self.dimensions)):
            raise ValueError("dataset.invalid_coverage_dimensions")


def coverage_value(coverage: SnapshotCoverage) -> dict:
    return {"status": coverage.status, "description": coverage.description,
            "dimensions": [{"name": v.name, **{n: list(getattr(v, n)) for n in
                ("requested", "materialized", "validated", "interpreted", "output", "missing")}}
                for v in coverage.dimensions]}


def coverage_from(value: dict) -> SnapshotCoverage:
    if not isinstance(value, dict) or set(value) != {"status", "description", "dimensions"} or not isinstance(value["dimensions"], list):
        raise ValueError("dataset.invalid_coverage_encoding")
    dimensions = []
    names = ("requested", "materialized", "validated", "interpreted", "output", "missing")
    for item in value["dimensions"]:
        if not isinstance(item, dict) or set(item) != {"name", *names} or any(not isinstance(item[n], list) for n in names):
            raise ValueError("dataset.invalid_coverage_encoding")
        dimensions.append(CoverageDimension(item["name"], **{n: tuple(item[n]) for n in names}))
    return SnapshotCoverage(value["status"], value["description"], tuple(dimensions))

