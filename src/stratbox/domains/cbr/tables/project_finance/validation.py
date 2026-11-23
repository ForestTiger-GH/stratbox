"""Independent source-table validation and qualified revision comparison."""
from dataclasses import dataclass
from stratbox.shared.identity import ByteIdentity
from .snapshots import flake_tables


@dataclass(frozen=True, slots=True)
class EscrowFlakeValidation:
    original_identity: ByteIdentity
    period: str
    cells: int
    mapped_indicators: tuple[str, ...]
    unmapped_headers: tuple[str, ...]
    unresolved_cells: int


@dataclass(frozen=True, slots=True)
class EscrowFlakeComparison:
    before_original: ByteIdentity
    after_original: ByteIdentity
    issue_changed: bool
    bytes_changed: bool
    facts_changed: bool
    layout_changed: bool
    interpretation_changed: bool


def validate_flake(value):
    flake_tables(value)
    return EscrowFlakeValidation(value.original_identity, value.file_date, len(value.df_cells),
        tuple(column.spec.code for column in value.resolved_columns), value.unmapped_headers,
        sum(status in {"unparsed", "formula_unresolved"} for status in value.df_cells["status"]))


def _facts(value):
    facts = []
    for row, column, header, code, token, kind, status, number, row_kind, region, order in value.df_cells.itertuples(index=False, name=None):
        facts.append((region, row_kind, code or f"unknown:{header}", status,
                      str(number.normalize()) if number is not None else token))
    return tuple(sorted(facts, key=repr))


def compare_flakes(before, after):
    flake_tables(before)
    flake_tables(after)
    return EscrowFlakeComparison(before.original_identity, after.original_identity,
        before.file_date != after.file_date, before.original_identity != after.original_identity,
        _facts(before) != _facts(after),
        (tuple((column.source_index, column.source_name, column.spec.code) for column in before.resolved_columns), before.unmapped_headers)
        != (tuple((column.source_index, column.source_name, column.spec.code) for column in after.resolved_columns), after.unmapped_headers),
        (before.method_version, tuple(column.spec for column in before.resolved_columns))
        != (after.method_version, tuple(column.spec for column in after.resolved_columns)))
