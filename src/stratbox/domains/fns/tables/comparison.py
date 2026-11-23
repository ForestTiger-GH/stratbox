"""Source changes are distinct from comparisons of integrated economic measures."""
from dataclasses import dataclass

from stratbox.shared.identity import ByteIdentity

from .contracts import JsonFlake
from .legal_entities.extraction import WorkbookBundle


@dataclass(frozen=True, slots=True)
class FlakeComparison:
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    state: str
    changed: tuple[str, ...]
    qualifications: tuple[str, ...]


def compare_flakes(before, after):
    if type(before) is not type(after) or not isinstance(before, (JsonFlake, WorkbookBundle)):
        raise ValueError("fns.comparison.flake_type_mismatch")
    identity = lambda value: (value.context.series_id, value.context.issue_id,
        value.context.asset_id, value.context.observation_date, value.profile_id)
    if identity(before) != identity(after):
        return FlakeComparison(before.identity, after.identity, "indeterminate", (), ("comparison.source_issue_mismatch",))
    if isinstance(before, JsonFlake):
        values = lambda value: {f"json:{item.ordinal}:{field.name}": (field.kind, field.raw_token)
                               for item in value.records for field in item.fields}
    else:
        values = lambda value: {f"member:{name}:sheet:{sheet.name}:cell:{cell.coordinate}": cell
            for name, workbook in value.members for sheet in workbook.sheets for cell in sheet.cells}
    left, right = values(before), values(after)
    changed = tuple(sorted(key for key in left.keys() | right.keys() if left.get(key) != right.get(key)))
    if isinstance(before, WorkbookBundle):
        structure = lambda value: (value.inventory, tuple((name, tuple((sheet.name, sheet.rows, sheet.columns,
            sheet.merged_ranges) for sheet in workbook.sheets)) for name, workbook in value.members))
        if structure(before) != structure(after):
            changed = (*changed, "workbook_structure_or_inventory")
    return FlakeComparison(before.identity, after.identity, "revised" if changed else "unchanged", changed,
        ("comparison.literal_source_cells_and_tokens", "comparison.no_economic_interpretation"))
