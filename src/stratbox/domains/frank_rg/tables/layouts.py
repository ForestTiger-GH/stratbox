"""Reusable explicitly reviewed workbook layouts with fail-closed geometry.

These types carry review evidence supplied by a caller. They do not certify a
publisher layout or infer economic meaning from the report filename. A layout
binds a fresh exact-byte semantic profile after its anchors and scope pass.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Mapping

from stratbox.shared.data.observations import PeriodRef
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .contracts import CellBinding, SemanticProfile
from .flakes import _validate_binding


@dataclass(frozen=True, slots=True)
class CellAnchor:
    sheet: str
    row: int
    column: int
    value: object
    formula: str | None = None


@dataclass(frozen=True, slots=True)
class LayoutBinding:
    cell: CellBinding
    period_key: str


@dataclass(frozen=True, slots=True)
class LayoutProfile:
    source_id: str
    profile_id: str
    version: int
    formats: tuple[str, ...]
    sheet_shapes: tuple[tuple[str, int, int], ...]
    anchors: tuple[CellAnchor, ...]
    bindings: tuple[LayoutBinding, ...]
    reviewed_originals: tuple[ByteIdentity, ...]
    review_qualification: str

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes(asdict(self)))

    def __post_init__(self):
        from ..publications.catalog import source
        source(self.source_id)
        if (not self.profile_id or type(self.version) is not int or self.version < 1
                or not isinstance(self.formats, tuple) or not self.formats
                or not set(self.formats) <= {"xlsx", "xlsm", "xls", "xlsb"}
                or len(set(self.formats)) != len(self.formats)
                or not isinstance(self.sheet_shapes, tuple) or not self.sheet_shapes
                or any(not isinstance(shape, tuple) or len(shape) != 3 or not isinstance(shape[0], str) or not shape[0]
                    or type(shape[1]) is not int or type(shape[2]) is not int
                    or min(shape[1:]) < 1 for shape in self.sheet_shapes)
                or len({shape[0] for shape in self.sheet_shapes}) != len(self.sheet_shapes)
                or not isinstance(self.anchors, tuple) or not self.anchors
                or not isinstance(self.bindings, tuple) or not self.bindings
                or not isinstance(self.reviewed_originals, tuple) or not self.reviewed_originals
                or any(not isinstance(item, ByteIdentity) or item.size < 1 for item in self.reviewed_originals)
                or not isinstance(self.review_qualification, str) or not self.review_qualification):
            raise ValueError("frg.layout.scope_required")
        shapes = {name: (rows, columns) for name, rows, columns in self.sheet_shapes}
        positions = set()
        for anchor in self.anchors:
            if (not isinstance(anchor, CellAnchor) or anchor.sheet not in shapes
                    or type(anchor.row) is not int or type(anchor.column) is not int
                    or min(anchor.row, anchor.column) < 1
                    or anchor.row > shapes[anchor.sheet][0] or anchor.column > shapes[anchor.sheet][1]
                    or (anchor.sheet, anchor.row, anchor.column) in positions):
                raise ValueError("frg.layout.anchor_invalid")
            canonical_manifest_bytes({"value": anchor.value, "formula": anchor.formula})
            positions.add((anchor.sheet, anchor.row, anchor.column))
        bound_positions = set()
        for binding in self.bindings:
            if (not isinstance(binding, LayoutBinding) or not isinstance(binding.period_key, str)
                    or not binding.period_key or not isinstance(binding.cell, CellBinding)
                    or binding.cell.sheet not in shapes):
                raise ValueError("frg.layout.binding_invalid")
            _validate_binding(binding.cell)
            cell = binding.cell
            position = (cell.sheet, cell.row, cell.column)
            if (position in bound_positions or cell.row > shapes[cell.sheet][0]
                    or cell.column > shapes[cell.sheet][1]):
                raise ValueError("frg.layout.binding_invalid")
            bound_positions.add(position)


def bind_layout(extract: WorkbookExtract, layout: LayoutProfile, *, periods: Mapping[str, PeriodRef]) -> SemanticProfile:
    """Validate a known shape and explicit economic periods before interpretation."""
    if not isinstance(extract, WorkbookExtract) or not isinstance(layout, LayoutProfile):
        raise ValueError("frg.layout.required")
    layout.__post_init__()
    extract.__post_init__()
    if extract.series_id != layout.source_id or extract.format not in layout.formats:
        raise ValueError("frg.layout.scope_mismatch")
    if tuple((sheet.name, sheet.rows, sheet.columns) for sheet in extract.sheets) != layout.sheet_shapes:
        raise ValueError("frg.layout.geometry_unsupported")
    cells = {(sheet.name, cell.row, cell.column): cell for sheet in extract.sheets for cell in sheet.cells}
    for anchor in layout.anchors:
        cell = cells.get((anchor.sheet, anchor.row, anchor.column))
        if (cell is None or type(cell.value) is not type(anchor.value)
                or cell.value != anchor.value or cell.formula != anchor.formula):
            raise ValueError("frg.layout.anchor_mismatch")
    required = {binding.period_key for binding in layout.bindings}
    if not isinstance(periods, Mapping) or set(periods) != required:
        raise ValueError("frg.layout.periods_required")
    bindings = []
    for item in layout.bindings:
        period = periods[item.period_key]
        if not isinstance(period, PeriodRef):
            raise ValueError("frg.layout.periods_required")
        binding = replace(item.cell, period=period)
        _validate_binding(binding)
        bindings.append(binding)
    return SemanticProfile(layout.source_id, layout.profile_id, layout.version,
        extract.source_identity, tuple(bindings), layout.identity,
        layout.reviewed_originals, layout.review_qualification)

