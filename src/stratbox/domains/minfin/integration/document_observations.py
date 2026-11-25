"""Reviewed document-cell semantics, independent of PDF text extraction."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse

from ..documents.contracts import PublisherDocument


@dataclass(frozen=True, slots=True)
class DocumentField:
    block: int
    row: int
    column: int
    metric: MetricRef
    period: PeriodRef
    subject: SubjectRef
    perimeter: str
    expected_row_label: str
    label_column: int = 0
    dimensions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if (any(type(n) is not int or n < 0 for n in (self.block, self.row, self.column, self.label_column))
                or not isinstance(self.metric, MetricRef) or not self.metric.definition_version or self.metric.scale is None
                or not isinstance(self.period, PeriodRef) or self.period.kind == "capture"
                or not isinstance(self.subject, SubjectRef) or not self.perimeter or not self.expected_row_label
                or self.metric.quantity_kind == "stock" and self.period.kind != "as_of"
                or self.metric.quantity_kind == "flow" and self.period.kind != "interval"):
            raise ValueError("minfin.document.field_semantics_invalid")


@dataclass(frozen=True, slots=True)
class DocumentInterpretationProfile:
    profile_id: str
    revision: str
    source_id: str
    fields: tuple[DocumentField, ...]
    required_text: tuple[str, ...]
    format: str = "docx"

    def __post_init__(self):
        if (not self.profile_id or not self.revision or not self.source_id.startswith("minfin.nwf.")
                or self.format != "docx" or not isinstance(self.fields, tuple) or not self.fields
                or any(not isinstance(f, DocumentField) for f in self.fields)
                or not isinstance(self.required_text, tuple) or not self.required_text
                or any(not isinstance(t, str) or not t for t in self.required_text)):
            raise ValueError("minfin.document.reviewed_profile_required")


def interpret_document(value, profile, *, dataset_id, release_id):
    if not isinstance(value, PublisherDocument) or not isinstance(profile, DocumentInterpretationProfile):
        raise ValueError("minfin.document.reviewed_profile_required")
    profile.__post_init__()
    document = value.document
    if document.series_id != profile.source_id or document.format != profile.format:
        raise ValueError("minfin.document.profile_source_mismatch")
    # PDF page text has no admitted table geometry. A PDF table provider must
    # contribute its own qualified layout interpretation rather than pass here.
    complete_text = "\n".join(b.text if b.kind != "table" else "\n".join(" | ".join(r) for r in b.rows) for b in document.blocks)
    if not all(anchor in complete_text for anchor in profile.required_text):
        raise ValueError("minfin.document.layout_unsupported")
    from ..tables.numbers import numeric_value
    rows, keys = [], set()
    for field in profile.fields:
        field.__post_init__()
        try:
            block = document.blocks[field.block]
            if block.kind != "table":
                raise ValueError("minfin.document.table_geometry_required")
            cells = block.rows[field.row]
            if " ".join(cells[field.label_column].split()) != " ".join(field.expected_row_label.split()):
                raise ValueError("minfin.document.layout_unsupported")
            literal = cells[field.column]
        except IndexError:
            raise ValueError("minfin.document.layout_unsupported") from None
        number, status = numeric_value(literal)
        dimensions = (*field.dimensions, ("source_series", document.series_id))
        key = (field.subject, field.metric, field.period, dimensions, field.perimeter)
        if key in keys:
            raise ValueError("minfin.document.duplicate_semantic_key")
        keys.add(key)
        evidence = f"sha256:{document.source_identity.sha256}#block={field.block}&row={field.row}&column={field.column}&issue={quote(document.issue_id,safe='')}&asset={quote(document.asset_id,safe='')}"
        rows.append(Observation(field.subject, field.metric, field.period, dimensions, field.perimeter,
            number, status, evidence, literal))
    return ObservationBatch(dataset_id, 1, release_id, tuple(rows), document.lineage,
        (SourceUse(SourceCoordinate(document.series_id, value.family_id, "fund_assets_document",
            issue_id=document.issue_id, asset_id=document.asset_id, material_identity=document.source_identity,
            semantic_profile_edition=profile.profile_id+"@"+profile.revision), "document", "reviewed_field_projection"),))
