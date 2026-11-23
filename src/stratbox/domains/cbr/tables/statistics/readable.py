"""Source-readable JSONL retains physical cells independently of interpretation."""
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.data.scalars import encode_scalar


def readable_workbook(flake):
    rows = [canonical_manifest_bytes({"kind": "workbook", "series_id": flake.series_id,
        "issue_id": flake.issue_id, "asset_id": flake.asset_id, "source_sha256": flake.source_identity.sha256,
        "profile_id": flake.profile_id, "profile_version": flake.profile_version})]
    for sheet in flake.sheets:
        rows.append(canonical_manifest_bytes({"kind": "sheet", "name": sheet.name,
            "rows": sheet.rows, "columns": sheet.columns, "merged_ranges": sheet.merged_ranges}))
        for cell in sheet.cells:
            scalar, token = encode_scalar(cell.value)
            rows.append(canonical_manifest_bytes({"kind": "cell", "sheet": sheet.name,
                "coordinate": cell.coordinate, "value_type": scalar, "value": token,
                "raw_token": cell.raw_token, "source_type": cell.kind, "formula": cell.formula,
                "formula_attributes": cell.formula_attributes, "number_format": cell.number_format,
                "indent": cell.indent}))
    return Representation("cbr.workbook.readable.jsonl", 1, "application/x-ndjson", b"\n".join(rows) + b"\n", "utf-8")
