"""Shared FNS observation-grain and count validation."""
def validate(inputs, settings, context):
    dataset = inputs["dataset"]
    if dataset.source_id != settings.source_id:
        raise ValueError("fns.source_mismatch")
    seen = set()
    for row in dataset.rows:
        key = tuple(row.get(name) for name in ("subject_namespace", "subject", "metric", "period", "perimeter", "legal_kind"))
        if key in seen:
            raise ValueError("fns.duplicate_semantic_grain")
        seen.add(key)
        if row["unit"] != "count" or type(row["value"]) is not int or row["value"] < 0:
            raise ValueError("fns.count_invalid")
    return {"dataset": dataset, "assessment": dataset.assessment}
