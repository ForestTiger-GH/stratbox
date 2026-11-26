"""Publication coordinates carried by the admitted industry stream schema."""
from __future__ import annotations

from dataclasses import replace

from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, source_use_value
from stratbox.shared.identity import canonical_manifest_bytes


# These identifiers belong to the two admitted publisher schemas. A filename,
# binding expectation or arbitrary dataframe attribute never establishes them.
_SERIES = {
    "01_05_A_Debt_corp": ("cbr.corporate_lending.debt_0105a", "regional_debt"),
    "01_04_A_New_loans_corp": ("cbr.corporate_lending.issuance_0104a", "published_statistics"),
}


def merge_source_uses(*collections):
    uses = {}
    for collection in collections:
        for use in collection:
            if not isinstance(use, SourceUse):
                raise ValueError("industry.source_context_invalid")
            uses[canonical_manifest_bytes(source_use_value(use))] = use
    return tuple(uses[key] for key in sorted(uses))


def industry_source_uses(value, *, frame=None, carriers=(), source_uses=()):
    """Read source/issue/asset pairs from actual consumed stream records.

    Existing typed carrier coordinates and matching original byte receipts can
    enrich a pair. Unknown series remain unqualified; their names are never
    promoted to a logical publisher source by spelling or path conventions.
    """
    import pandas as pd

    frame = frame if frame is not None else value if isinstance(value, pd.DataFrame) else getattr(value, "df_stream", None)
    if frame is None or not {"series_code", "report_date"} <= set(frame.columns):
        return ()
    roots = (value, *carriers)
    known, materials, seen = list(source_uses), {}, set()

    def evidence(receipt):
        if receipt is None or id(receipt) in seen:
            return
        seen.add(id(receipt))
        for item in receipt.inputs:
            materials[item.identity.sha256] = item.identity
        for _, parent in getattr(receipt, "parents", ()):
            evidence(parent)

    for carrier in roots:
        if carrier is None:
            continue
        known.extend(getattr(carrier, "source_uses", ()))
        evidence(getattr(carrier, "evidence", None))
        for parsed in getattr(carrier, "parsed_files", ()):
            known.extend(getattr(parsed, "source_uses", ()))
            evidence(getattr(parsed, "evidence", None))
    columns = ["series_code", "report_date", *(name for name in ("source_id", "source_sha256") if name in frame.columns)]
    result = []
    for record in frame[columns].drop_duplicates().itertuples(index=False, name=None):
        fields = dict(zip(columns, record))
        if pd.isna(fields["series_code"]) or pd.isna(fields["report_date"]):
            continue
        source = _SERIES.get(str(fields["series_code"]))
        if source is None:
            continue
        source_id, group = source
        issue = str(fields["report_date"])
        asset = fields.get("source_id")
        asset = None if asset is None or pd.isna(asset) else str(asset)
        digest = fields.get("source_sha256")
        digest = None if digest is None or pd.isna(digest) else str(digest)
        existing = next((use for use in known if use.coordinate.source_id == source_id
            and use.coordinate.issue_id == issue
            and use.coordinate.asset_id in {None, asset}), None)
        coordinate = SourceCoordinate(source_id=source_id, family_id="cbr.corporate_lending",
            source_group_id=group, issue_id=issue, asset_id=asset,
            material_identity=materials.get(digest))
        if existing is not None:
            if (existing.coordinate.material_identity is not None and digest is not None
                    and existing.coordinate.material_identity.sha256 != digest):
                raise ValueError("industry.source_material_mismatch")
            coordinate = replace(coordinate,
                material_identity=coordinate.material_identity or existing.coordinate.material_identity,
                layout_identity=existing.coordinate.layout_identity,
                semantic_identity=existing.coordinate.semantic_identity)
        result.append(SourceUse(coordinate, existing.input_role if existing is not None else "source",
            existing.qualification if existing is not None else "typed",
            existing.evidence_ref if existing is not None else digest))
    return merge_source_uses(result)
