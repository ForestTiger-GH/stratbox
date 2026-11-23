"""Ordered document evidence with explicit extraction scope and cold replay."""
from __future__ import annotations

from dataclasses import dataclass, replace
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable, coverage_value
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity

DOCUMENT_EXTRACT = DataContract("document.blocks.extract", 1, DataRole.EXTRACTS)
DOCUMENT_SNAPSHOT = DataContract("document.blocks.snapshot", 1, DataRole.EXTRACTS)
_T, _I = ScalarType.TEXT, ScalarType.INTEGER
_META = TableSchema(DataContract("document.extract.metadata", 1), tuple(ColumnSchema(n, t) for n, t in (
    ("series_id", _T), ("issue_id", _T), ("asset_id", _T), ("sha256", _T), ("size", _I),
    ("format", _T), ("profile_id", _T), ("profile_version", _I), ("qualifications", _T))))
_BLOCKS = TableSchema(DataContract("document.extract.blocks", 1), (
    ColumnSchema("ordinal", _I), ColumnSchema("kind", _T), ColumnSchema("text", _T),
    ColumnSchema("page", _I, True), ColumnSchema("rows", _T), ColumnSchema("locator", _T)), ("ordinal",))


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    ordinal: int
    kind: str
    text: str
    page: int | None = None
    rows: tuple[tuple[str, ...], ...] = ()
    locator: str = ""

    def __post_init__(self):
        if (type(self.ordinal) is not int or self.ordinal < 0 or self.kind not in {"paragraph", "table", "page", "error"}
                or not isinstance(self.text, str) or not isinstance(self.locator, str)
                or self.page is not None and (type(self.page) is not int or self.page < 1)
                or not isinstance(self.rows, tuple) or any(not isinstance(r, tuple)
                    or any(type(c) is not str for c in r) for r in self.rows)
                or self.rows and self.kind != "table"):
            raise ValueError("document.block_invalid")


@dataclass(frozen=True, slots=True)
class DocumentExtract:
    series_id: str
    issue_id: str
    asset_id: str
    source_identity: ByteIdentity
    format: str
    profile_id: str
    profile_version: int
    blocks: tuple[DocumentBlock, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...] = ()

    def __post_init__(self):
        SourceAssetIdentity(self.series_id, self.issue_id, self.asset_id)
        if (not isinstance(self.source_identity, ByteIdentity) or not self.source_identity.size
                or self.format not in {"pdf", "docx", "txt"} or not self.profile_id
                or type(self.profile_version) is not int or self.profile_version < 1
                or not isinstance(self.blocks, tuple) or any(not isinstance(b, DocumentBlock) for b in self.blocks)
                or tuple(b.ordinal for b in self.blocks) != tuple(range(len(self.blocks)))
                or not isinstance(self.lineage, tuple) or not any(i.identity == self.source_identity for i in self.lineage)
                or not isinstance(self.coverage, SnapshotCoverage)
                or not isinstance(self.qualifications, tuple) or any(type(q) is not str or not q for q in self.qualifications)):
            raise ValueError("document.extract_invalid")

    @property
    def identity(self):
        return document_snapshot(self).identity


def _json(value):
    return canonical_manifest_bytes(value).decode("utf-8")


def document_snapshot(value: DocumentExtract, *, dataset_id=None, version_id=None):
    value.__post_init__()
    meta = TypedTable(_META, ((value.series_id, value.issue_id, value.asset_id,
        value.source_identity.sha256, value.source_identity.size, value.format, value.profile_id,
        value.profile_version, _json(value.qualifications)),))
    parts = tuple((f"blocks_{i // 1000:05d}", TypedTable(_BLOCKS, tuple(
        (b.ordinal, b.kind, b.text, b.page, _json(b.rows), b.locator) for b in value.blocks[i:i+1000])))
        for i in range(0, max(1, len(value.blocks)), 1000))
    result = DatasetSnapshot.build(dataset_id or value.series_id, version_id or "content", DOCUMENT_EXTRACT,
        (("metadata", meta), *parts), coverage=value.coverage, inputs=value.lineage)
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def document_from_snapshot(snapshot: DatasetSnapshot):
    if not snapshot.complete or snapshot.manifest.contract != DOCUMENT_EXTRACT:
        raise ValueError("document.snapshot_invalid")
    meta = snapshot.table("metadata")
    if meta.schema != _META or len(meta.rows) != 1:
        raise ValueError("document.snapshot_metadata_invalid")
    series, issue, asset, sha, size, fmt, profile, version, quals = meta.rows[0]
    blocks = []
    for index, (name, table) in enumerate(snapshot.tables[1:]):
        if name != f"blocks_{index:05d}" or table.schema != _BLOCKS or len(table.rows) > 1000:
            raise ValueError("document.snapshot_partition_invalid")
        for ordinal, kind, text, page, rows, locator in table.rows:
            decoded = json.loads(rows)
            blocks.append(DocumentBlock(ordinal, kind, text, page, tuple(tuple(r) for r in decoded), locator))
    value = DocumentExtract(series, issue, asset, ByteIdentity(sha, size), fmt, profile, version,
        tuple(blocks), snapshot.manifest.inputs, snapshot.manifest.coverage, tuple(json.loads(quals)))
    if document_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                         version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("document.snapshot_identity_mismatch")
    return value


def readable_document(value: DocumentExtract):
    value.__post_init__()
    records = [{"kind": "document", "series_id": value.series_id, "issue_id": value.issue_id,
        "asset_id": value.asset_id, "source_sha256": value.source_identity.sha256, "format": value.format,
        "profile_id": value.profile_id, "profile_version": value.profile_version,
        "coverage": coverage_value(value.coverage), "qualifications": value.qualifications}]
    records.extend({"ordinal": b.ordinal, "kind": b.kind, "text": b.text, "page": b.page,
                    "rows": b.rows, "locator": b.locator} for b in value.blocks)
    return Representation("document.readable.jsonl", 1, "application/x-ndjson",
        b"\n".join(canonical_manifest_bytes(r) for r in records) + b"\n", "utf-8")
