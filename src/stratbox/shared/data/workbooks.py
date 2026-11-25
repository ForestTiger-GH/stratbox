"""Complete, partitioned physical workbook extracts and exact offline replay.

This layer preserves decoder evidence. Publisher-specific table profiles assign
economic meaning in their own domains. Each cell partition has at most 20,000
records so storage can address portions without a monolithic cell component.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.scalars import encode_scalar, decode_scalar
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable, coverage_value
from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells, validate_sheet_cells
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity

WORKBOOK_EXTRACT = DataContract("workbook.cells.extract", 1, DataRole.EXTRACTS)
# The wrapper port describes a DatasetSnapshot; its manifest retains the
# logical extract contract. A live extract and its retained encoding differ.
WORKBOOK_SNAPSHOT = DataContract("workbook.cells.snapshot", 1, DataRole.EXTRACTS)
_T, _I = ScalarType.TEXT, ScalarType.INTEGER
_META = TableSchema(DataContract("workbook.extract.metadata", 1), tuple(ColumnSchema(n, t) for n, t in (
    ("series_id", _T), ("issue_id", _T), ("asset_id", _T), ("sha256", _T), ("size", _I),
    ("format", _T), ("profile_id", _T), ("profile_version", _I), ("qualifications", _T))))
_SHEETS = TableSchema(DataContract("workbook.extract.sheets", 1), tuple(ColumnSchema(n, t) for n, t in (
    ("index", _I), ("name", _T), ("rows", _I), ("columns", _I), ("merged_ranges", _T),
    ("partitions", _I))), ("index",))
_CELLS = TableSchema(DataContract("workbook.extract.cells", 1), (
    ColumnSchema("row", _I), ColumnSchema("column", _I), ColumnSchema("coordinate", _T),
    ColumnSchema("value_type", _T), ColumnSchema("value", _T), ColumnSchema("raw_token", _T, True),
    ColumnSchema("kind", _T), ColumnSchema("formula", _T, True), ColumnSchema("number_format", _T),
    ColumnSchema("indent", _I), ColumnSchema("formula_attributes", _T), ColumnSchema("evidence_kind", _T),
), ("row", "column"))
_PARTITION_ROWS = 20_000
_PARTITION_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class WorkbookExtract:
    series_id: str
    issue_id: str
    asset_id: str
    source_identity: ByteIdentity
    format: str
    profile_id: str
    profile_version: int
    sheets: tuple[SheetCells, ...]
    lineage: tuple[UsedInputReceipt, ...] = ()
    coverage: SnapshotCoverage = SnapshotCoverage("complete", "All worksheets and decoder-visible cells in the supplied workbook.")
    qualifications: tuple[str, ...] = ()

    def __post_init__(self):
        SourceAssetIdentity(self.series_id, self.issue_id, self.asset_id)
        if (not isinstance(self.source_identity, ByteIdentity) or self.source_identity.size == 0
                or self.format not in {"xlsx", "xlsm", "xls", "xlsb"}
                or not isinstance(self.profile_id, str) or not self.profile_id
                or type(self.profile_version) is not int or self.profile_version < 1
                or not isinstance(self.coverage, SnapshotCoverage)
                or not isinstance(self.sheets, tuple) or not self.sheets
                or tuple(s.index for s in self.sheets) != tuple(range(len(self.sheets)))
                or len({s.name for s in self.sheets}) != len(self.sheets)
                or not isinstance(self.qualifications, tuple)
                or any(type(q) is not str or not q for q in self.qualifications)):
            raise ValueError("workbook.extract_invalid")
        if not isinstance(self.lineage, tuple) or not any(
                isinstance(i, UsedInputReceipt) and i.identity == self.source_identity for i in self.lineage):
            raise ValueError("workbook.source_evidence_required")
        for sheet in self.sheets:
            validate_sheet_cells(sheet)

    @property
    def identity(self):
        return workbook_snapshot(self).identity


def _json(value):
    return canonical_manifest_bytes(value).decode("utf-8")


def _array(value):
    decoded = json.loads(value)
    if not isinstance(decoded, list) or _json(decoded) != value:
        raise ValueError("workbook.noncanonical_array")
    return decoded


def _cell_partitions(sheet):
    """Bound both row count and conservative encoded size before table building."""
    current, size = [], 0
    for c in sheet.cells:
        row = (c.row, c.column, c.coordinate, *encode_scalar(c.value), c.raw_token,
               c.kind, c.formula, c.number_format, c.indent, _json(c.formula_attributes), c.evidence_kind)
        # Six bytes per character bounds JSON escapes and UTF-8; scalar fields
        # and separators have a small constant envelope.
        upper = 256 + sum(6 * len(v) for v in row if isinstance(v, str))
        if upper > _PARTITION_BYTES:
            raise ValueError("workbook.cell_serialization_limit")
        if current and (len(current) >= _PARTITION_ROWS or size + upper > _PARTITION_BYTES):
            yield tuple(current)
            current, size = [], 0
        current.append(row)
        size += upper
    if current or not sheet.cells:
        yield tuple(current)


def workbook_snapshot(value: WorkbookExtract, *, dataset_id=None, version_id=None):
    if not isinstance(value, WorkbookExtract):
        raise TypeError("workbook.extract_required")
    value.__post_init__()
    meta = TypedTable(_META, ((value.series_id, value.issue_id, value.asset_id,
        value.source_identity.sha256, value.source_identity.size, value.format,
        value.profile_id, value.profile_version, _json(value.qualifications)),))
    sheet_rows, partitions = [], []
    for sheet in value.sheets:
        count = 0
        for part, rows in enumerate(_cell_partitions(sheet)):
            partitions.append((f"sheet_{sheet.index:04d}_{part:05d}", TypedTable(_CELLS, rows)))
            count += 1
        sheet_rows.append((sheet.index, sheet.name, sheet.rows, sheet.columns, _json(sheet.merged_ranges), count))
    result = DatasetSnapshot.build(dataset_id or value.series_id, version_id or "content", WORKBOOK_EXTRACT,
        (("metadata", meta), ("sheets", TypedTable(_SHEETS, tuple(sheet_rows))), *partitions),
        coverage=value.coverage, inputs=value.lineage)
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def workbook_from_snapshot(snapshot: DatasetSnapshot) -> WorkbookExtract:
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != WORKBOOK_EXTRACT):
        raise ValueError("workbook.snapshot_invalid")
    meta, sheets = snapshot.table("metadata"), snapshot.table("sheets")
    if meta.schema != _META or sheets.schema != _SHEETS or len(meta.rows) != 1:
        raise ValueError("workbook.snapshot_schema_invalid")
    series, issue, asset, sha, size, fmt, profile, version, qualifications = meta.rows[0]
    restored, expected = [], ["metadata", "sheets"]
    for index, name, rows, columns, merges, count in sheets.rows:
        if type(count) is not int or not 1 <= count <= 10_000:
            raise ValueError("workbook.partition_count_invalid")
        cells = []
        for part in range(count):
            key = f"sheet_{index:04d}_{part:05d}"
            expected.append(key)
            table = snapshot.table(key)
            if table.schema != _CELLS or len(table.rows) > _PARTITION_ROWS:
                raise ValueError("workbook.snapshot_cells_invalid")
            for row, column, coordinate, scalar, token, raw, kind, formula, nf, indent, attrs, evidence in table.rows:
                attributes = _array(attrs)
                cells.append(WorkbookCell(row, column, coordinate, decode_scalar(scalar, token), raw,
                    kind, formula, nf, indent, tuple(tuple(p) for p in attributes), evidence))
        restored.append(SheetCells(name, index, rows, columns, tuple(cells), tuple(_array(merges))))
    if tuple(expected) != tuple(n for n, _ in snapshot.tables):
        raise ValueError("workbook.snapshot_components_invalid")
    value = WorkbookExtract(series, issue, asset, ByteIdentity(sha, size), fmt, profile, version,
        tuple(restored), snapshot.manifest.inputs, snapshot.manifest.coverage, tuple(_array(qualifications)))
    if workbook_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                         version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("workbook.snapshot_identity_mismatch")
    return value


def readable_workbook(value: WorkbookExtract, *, max_bytes=32 * 1024 * 1024, checkpoint=None) -> Representation:
    value.__post_init__()
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("workbook.readable_limit_invalid")
    def records():
        yield {"kind": "workbook", "series_id": value.series_id, "issue_id": value.issue_id,
            "asset_id": value.asset_id, "source_sha256": value.source_identity.sha256, "format": value.format,
            "profile_id": value.profile_id, "profile_version": value.profile_version,
            "coverage": coverage_value(value.coverage), "qualifications": value.qualifications}
        for sheet in value.sheets:
            yield {"kind": "sheet", "index": sheet.index, "name": sheet.name,
                "rows": sheet.rows, "columns": sheet.columns, "merged_ranges": sheet.merged_ranges}
            for cell in sheet.cells:
                scalar, text = encode_scalar(cell.value)
                yield {"kind": "cell", "sheet": sheet.name, "coordinate": cell.coordinate,
                    "value_type": scalar, "value": text, "raw_token": cell.raw_token,
                    "source_type": cell.kind, "formula": cell.formula, "formula_attributes": cell.formula_attributes,
                    "number_format": cell.number_format, "indent": cell.indent, "evidence_kind": cell.evidence_kind}
    chunks, size = [], 0
    for record in records():
        if checkpoint is not None:
            checkpoint()
        chunk = canonical_manifest_bytes(record) + b"\n"
        size += len(chunk)
        if size > max_bytes:
            raise ValueError("workbook.readable_size_limit")
        chunks.append(chunk)
    return Representation("workbook.readable.jsonl", 1, "application/x-ndjson", b"".join(chunks), "utf-8")


@dataclass(frozen=True, slots=True)
class WorkbookDifference:
    sheet: str
    coordinate: str
    before: WorkbookCell | None
    after: WorkbookCell | None


@dataclass(frozen=True, slots=True)
class WorkbookComparison:
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    cells: tuple[WorkbookDifference, ...]
    structure_changed: bool
    qualifications: tuple[str, ...]


def compare_workbooks(before: WorkbookExtract, after: WorkbookExtract) -> WorkbookComparison:
    if (before.series_id, before.asset_id) != (after.series_id, after.asset_id):
        raise ValueError("workbook.comparison_source_mismatch")
    left = {(s.name, c.coordinate): c for s in before.sheets for c in s.cells}
    right = {(s.name, c.coordinate): c for s in after.sheets for c in s.cells}
    keys = sorted(left.keys() | right.keys())
    changes = tuple(WorkbookDifference(*key, left.get(key), right.get(key))
                    for key in keys if left.get(key) != right.get(key))
    structure = lambda w: tuple((s.name, s.index, s.rows, s.columns, s.merged_ranges) for s in w.sheets)
    return WorkbookComparison(before.identity, after.identity, changes, structure(before) != structure(after),
        tuple(dict.fromkeys((*before.qualifications, *after.qualifications,
                            "Physical cell differences; economic comparability is a domain decision."))))
