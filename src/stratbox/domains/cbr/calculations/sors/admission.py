"""Admission of the complete source vector against exact retained evidence."""
from datetime import date
from math import isfinite
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.calculations.sors.inputs.dependencies import DEPENDENCIES, contract_coordinates
from stratbox.domains.cbr.calculations.sors.identity import validate_content


def validate_bundle_context(value):
    if value.method_fingerprint != __import__("stratbox.domains.cbr.calculations.sors.fingerprints", fromlist=["implementation_fingerprint"]).implementation_fingerprint("inputs"):
        raise ValueError("sors.input_method_changed")
    if value.as_of_date is None or value.publication_step is None:
        raise ValueError("sors.input_source_parameters_required")
    date.fromisoformat(value.as_of_date)
    if not isfinite(value.publication_step) or value.publication_step <= 0:
        raise ValueError("sors.input_source_parameters_invalid")
    # Every declared role is recorded, including the absent optional input.
    # Partial source contexts cannot be advertised as replayable models.
    manifest = value.dependency_manifest_grid
    if manifest.empty:
        raise ValueError("sors.input_dependencies_incomplete")
    else:
        expected = tuple((item.input_name, item.source_series, item.series_id, item.required) for item in DEPENDENCIES)
        if not {"input_name", "source_series", "series_id", "source_role", "method_fingerprint", "accepted_contracts", "compatibility_rule", "required", "status", "as_of_date", "publication_step", "original_sha256", "original_size", "source_id", "input_kind"} <= set(manifest.columns):
            raise ValueError("sors.input_dependencies_invalid")
        actual = tuple(manifest[["input_name", "source_series", "series_id", "required"]].itertuples(index=False, name=None))
        if actual != expected or not manifest["as_of_date"].eq(value.as_of_date).all() or not manifest["publication_step"].eq(value.publication_step).all():
            raise ValueError("sors.input_dependencies_invalid")
        resolved = []
        for declaration, row in zip(DEPENDENCIES, manifest.itertuples(index=False), strict=True):
            if (type(row.required) is not bool or row.method_fingerprint != declaration.method_fingerprint or row.source_role != declaration.source_role
                    or row.accepted_contracts != contract_coordinates(declaration) or row.compatibility_rule != declaration.compatibility_rule):
                raise ValueError("sors.input_dependencies_invalid")
            if row.status not in {"resolved", "not_supplied"} or row.required and row.status != "resolved":
                raise ValueError("sors.input_dependencies_incomplete")
            if row.status == "resolved":
                if type(row.original_size) is not int:
                    raise ValueError("sors.input_dependency_identity_mismatch")
                matching = tuple(receipt for receipt in value.lineage if receipt.role == row.source_series)
                if (len(matching) != 1 or matching[0].identity != ByteIdentity(row.original_sha256, row.original_size)
                        or matching[0].source_id != row.source_id or row.input_kind not in {"original", "flake"}):
                    raise ValueError("sors.input_dependency_identity_mismatch")
                resolved.append(row)
            elif any(item is not None for item in (row.original_sha256, row.original_size, row.source_id, row.input_kind)):
                raise ValueError("sors.input_dependencies_invalid")
        published = value.source_manifest_grid
        if not {"source_series", "sha256", "size_bytes"} <= set(published.columns) or len(published) != len(resolved):
            raise ValueError("sors.input_source_manifest_mismatch")
        for row in resolved:
            matched = published[published["source_series"].eq(row.source_series)]
            if len(matched) != 1 or matched.iloc[0]["sha256"] != row.original_sha256 or matched.iloc[0]["size_bytes"] != row.original_size:
                raise ValueError("sors.input_source_manifest_mismatch")
    validate_content(value)

