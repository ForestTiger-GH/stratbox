"""Optional shared-reference diagnostics for source geography names."""

def inspect_escrow_region_names(rows, *, resolver=None):
    """Optional downstream diagnostics; no change to parsed rows or order."""
    from stratbox.shared.reference.geography import RegionNameContext, RegionNameResolver

    matcher = resolver or RegionNameResolver()
    return tuple(
        (row, matcher.resolve(row.entity_name, context=RegionNameContext(observed_kind="subject")))
        for row in rows if row.row_kind == "region"
    )
