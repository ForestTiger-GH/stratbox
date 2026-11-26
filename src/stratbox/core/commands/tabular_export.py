"""Strict physical DBF-to-CSV export with streamed preservation evidence."""
from __future__ import annotations

import csv
import json

from stratbox.core.formats.dbf_lossless import DBFReader
from stratbox.shared.data.dbf import DBFPreservationPolicy
from stratbox.shared.data.values import Assessment, canonical_tree, fingerprint
from ._physical import material_properties, open_material, physical_material, representation_writer
from ._settings import _option


class _Utf8Writer:
    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        self.stream.write(text.encode("utf-8", errors="strict"))
        return len(text)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def dbf_encoding(policy, value):
    properties = material_properties(value)
    metadata = properties["metadata"]
    scope = {"source_id": properties["source_id"], "issue_id": metadata.get("issue_id"),
             "member": metadata.get("member", metadata.get("filename", metadata.get("name", metadata.get("asset_id")))),
             "asset_id": metadata.get("container_asset_id", metadata.get("asset_id"))}
    encoding, basis = policy.resolve(**scope)
    return encoding, basis, scope


def dbf_export_csv(inputs, settings, context):
    """Produce two complete representations; durable retention is a separate step."""
    value = inputs["material"]
    material, properties = physical_material(value), material_properties(value)
    policy = inputs.get("policy", _option(context, settings, "policy", None))
    if not isinstance(policy, DBFPreservationPolicy):
        raise ValueError("dbf.explicit_preservation_policy_required")
    encoding, basis, scope = dbf_encoding(policy, value)
    placement = _option(context, settings, "placement", "staged")
    if placement not in {"buffered", "staged"}:
        raise ValueError("material.placement_invalid")
    max_csv = _option(context, settings, "max_csv_bytes", 64 * 1024**3 if placement == "staged" else 32 * 1024**2)
    max_evidence = _option(context, settings, "max_evidence_bytes", 2 * 1024**3 if placement == "staged" else 8 * 1024**2)
    max_records = _option(context, settings, "max_records", 5_000_000)
    max_cells = _option(context, settings, "max_cells", 50_000_000)
    lineage = (*properties["lineage"], material.identity)
    base = {"source_id": properties["source_id"], "charset": "utf-8", "lineage": lineage,
            "source_uses": properties["source_uses"]}
    metadata = {**properties["metadata"], "source_dbf": material.identity,
                "preservation_policy": fingerprint(policy)}
    with open_material(value, context) as source:
        reader = DBFReader(source, material.identity, encoding=encoding, encoding_basis=basis,
            max_records=max_records, max_cells=max_cells, budget=getattr(context, "budget", None),
            checkpoint=context.checkpoint)
        with representation_writer(context, placement=placement, max_bytes=max_csv,
                media_type="text/csv", metadata={**metadata, "representation": "dbf_csv"}, **base) as csv_output, \
             representation_writer(context, placement=placement, max_bytes=max_evidence,
                media_type="application/json", metadata={**metadata, "representation": "dbf_preservation"}, **base) as evidence_output:
            writer = csv.writer(_Utf8Writer(csv_output.stream), delimiter=",", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            writer.writerow(tuple(field.name for field in reader.fields))
            evidence_output.stream.write(b'{"deleted_record_ordinals":[')
            deleted, written = 0, 0
            for record in reader.records():
                if record.deleted:
                    evidence_output.stream.write((b"," if deleted else b"") + str(record.ordinal).encode("ascii"))
                    deleted += 1
                if policy.include_deleted or not record.deleted:
                    writer.writerow(record.values)
                    written += 1
            csv_material = csv_output.seal()
            header = reader.header
            evidence = {
                "source": {"sha256": material.identity.sha256, "size": material.identity.size},
                "source_context": {"source_id": properties["source_id"],
                    "metadata": canonical_tree(properties["metadata"]),
                    "source_uses": canonical_tree(properties["source_uses"])},
                "header": {"version": header.version, "raw_date_hex": header.header_date.hex(),
                    "header_length": header.header_length, "record_length": header.record_length,
                    "record_count": header.record_count, "language_driver": header.language_driver,
                    "eof_marker": header.eof_marker, "integrity": "complete_original_verified"},
                "fields": [{"name": field.name, "type": field.field_type, "length": field.length,
                    "decimals": field.decimals, "offset": field.offset} for field in reader.fields],
                "encoding": {"effective": encoding, "basis": basis, "scope": scope, "errors": "strict"},
                "preservation": {"policy": canonical_tree(policy), "character_padding": "right_space_nul",
                    "lexical_padding": "both_space_nul", "record_order": "physical",
                    "deleted_records": "included" if policy.include_deleted else "excluded",
                    "deleted_ordinals_basis": "one_based_physical_record"},
                "csv": {"sha256": csv_material.identity.sha256, "size": csv_material.identity.size,
                    "encoding": "utf-8", "delimiter": ",", "quotechar": '"', "quoting": "minimal",
                    "line_terminator": "\n", "header": True, "records": written},
                "counts": {"physical_records": header.record_count, "exported_records": written,
                           "deleted_records": deleted, "fields": len(reader.fields)},
            }
            evidence_output.stream.write(b"]")
            for key, item in evidence.items():
                context.checkpoint()
                evidence_output.stream.write(b"," + _json(key) + b":" + _json(item))
            evidence_output.stream.write(b"}\n")
            evidence_material = evidence_output.seal(lineage=(*lineage, csv_material.identity),
                metadata={**metadata, "representation": "dbf_preservation", "csv_identity": csv_material.identity})
    return {"csv": csv_material, "evidence": evidence_material,
            "assessment": Assessment(qualifications=frozenset({"strict_lexical_dbf", "complete_original_verified"})),
            "summary": {"records": written, "physical_records": header.record_count,
                        "deleted_records": deleted, "fields": len(reader.fields),
                        "encoding": encoding, "encoding_basis": basis}}
