"""Retain the complete ordered document and all publisher release metadata."""
import json
from stratbox.shared.data.documents import document_snapshot, document_from_snapshot, DOCUMENT_EXTRACT
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, TableSchema, TypedTable
from stratbox.shared.identity import canonical_manifest_bytes
from ..publications.context import context_document, context_from_document
from .contracts import PublisherDocument

DOCUMENT_SNAPSHOT = DataContract("minfin.document.snapshot", 1, DataRole.EXTRACTS)
_SOURCE = TableSchema(DataContract("minfin.document.publication", 1, DataRole.EXTRACTS),
    (ColumnSchema("family_id", ScalarType.TEXT), ColumnSchema("publication", ScalarType.TEXT)))


def snapshot_document(value, *, dataset_id=None, version_id=None):
    if (not isinstance(value, PublisherDocument) or value.document.series_id != value.publication.series_id
            or value.document.issue_id != value.publication.issue_id or value.document.asset_id != value.publication.asset_id
            or not value.document.series_id.startswith(value.family_id + ".")):
        raise ValueError("minfin.document.context_mismatch")
    retained = document_snapshot(value.document)
    source = TypedTable(_SOURCE, ((value.family_id, canonical_manifest_bytes(context_document(value.publication)).decode()),))
    return DatasetSnapshot.build(dataset_id or retained.manifest.dataset_id, version_id or retained.manifest.version_id,
        DOCUMENT_SNAPSHOT, (("publication", source), *retained.tables),
        coverage=retained.manifest.coverage, inputs=retained.manifest.inputs)


def document_from_dataset(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != DOCUMENT_SNAPSHOT
            or not snapshot.tables or snapshot.tables[0][0] != "publication"
            or snapshot.table("publication").schema != _SOURCE or len(snapshot.table("publication").rows) != 1):
        raise ValueError("minfin.document.snapshot_invalid")
    family_id, document = snapshot.table("publication").rows[0]
    source = DatasetSnapshot.build(snapshot.manifest.dataset_id, snapshot.manifest.version_id, DOCUMENT_EXTRACT,
        snapshot.tables[1:], coverage=snapshot.manifest.coverage, inputs=snapshot.manifest.inputs)
    value = PublisherDocument(family_id, document_from_snapshot(source), context_from_document(json.loads(document)))
    if snapshot_document(value, dataset_id=snapshot.manifest.dataset_id, version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("minfin.document.snapshot_invalid")
    return value
