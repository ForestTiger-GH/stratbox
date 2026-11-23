"""Selected source-flake comparison and validation, before integration."""
from dataclasses import dataclass,replace
from stratbox.shared.data.snapshots import SnapshotCoverage
from .contracts import RosstatSourceFlake,SourceValue

@dataclass(frozen=True,slots=True)
class FlakeChange:
    key: tuple
    before: SourceValue | None
    after: SourceValue | None

@dataclass(frozen=True,slots=True)
class FlakeComparison:
    state: str
    changes: tuple[FlakeChange,...]
    reason: str

@dataclass(frozen=True,slots=True)
class FlakeValidation:
    coverage: SnapshotCoverage
    values: int
    reported_values: int
    missing_values: int
    diagnostics: tuple[str,...]


def validate_flake(flake: RosstatSourceFlake) -> FlakeValidation:
    flake.__post_init__()
    diagnostics=list(flake.diagnostics)
    for row in flake.values:
        row.__post_init__()
        if row.value_status=="unparsed":
            diagnostics.append("rosstat.validation.unparsed:"+row.source_locator)
        if row.unit is None or row.quantity_kind is None:
            diagnostics.append("rosstat.validation.semantics_unresolved:"+row.source_locator)
    coverage=replace(flake.coverage,status="partial") if diagnostics else flake.coverage
    reported=sum(row.value_status=="reported" for row in flake.values)
    return FlakeValidation(coverage,len(flake.values),reported,len(flake.values)-reported,tuple(dict.fromkeys(diagnostics)))


def compare_flakes(before: RosstatSourceFlake, after: RosstatSourceFlake) -> FlakeComparison:
    if (before.series_id,before.asset_id)!=(after.series_id,after.asset_id):
        raise ValueError("rosstat.flake_comparison_source_mismatch")
    old={row.key:row for row in before.values}
    new={row.key:row for row in after.values}
    changes=[]
    for key in sorted(old.keys()|new.keys(),key=repr):
        a,b=old.get(key),new.get(key)
        if a is not None and b is not None:
            # Source coordinates are provenance and may move between issues.
            comparable=replace(b,source_locator=a.source_locator,source_sheet=a.source_sheet,
                source_row=a.source_row,source_column=a.source_column)
            if a==comparable:
                continue
        changes.append(FlakeChange(key,a,b))
    if ((before.profile_id,before.profile_version)!=(after.profile_id,after.profile_version)
            or before.coverage!=after.coverage):
        return FlakeComparison("indeterminate",tuple(changes),"rosstat.flake_scope_or_profile_changed")
    return FlakeComparison("changed" if changes else "unchanged",tuple(changes),"rosstat.selected_source_values_compared")
