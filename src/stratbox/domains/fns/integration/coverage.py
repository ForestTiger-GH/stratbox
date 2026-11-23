"""Keep interpreted/output coverage synchronized with the retained observations."""
from dataclasses import replace

from stratbox.shared.data.snapshots import CoverageDimension


def observation_coverage(coverage, observations):
    fields, kinds, levels, semantic_fields = set(), set(), set(), set()
    for item in observations:
        dimensions = dict(item.dimensions)
        if "source_field" in dimensions:
            fields.add(dimensions["source_field"])
        if "source_indicator" in dimensions and "source_legal_kind" in dimensions:
            fields.add(dimensions["source_indicator"] + "_" + dimensions["source_legal_kind"])
        if "source_legal_kind" in dimensions:
            kinds.add(dimensions["source_legal_kind"])
        if "geographic_level" in dimensions:
            levels.add(dimensions["geographic_level"])
        semantic_fields.add("le_" + item.metric.id + "__" + dimensions["legal_kind"]
                            if "legal_kind" in dimensions else item.metric.id)
    axes = {"counter_fields": fields, "source_fields": fields, "legal_kinds": kinds,
            "geographic_levels": levels, "semantic_fields": semantic_fields}
    dimensions = []
    for dimension in coverage.dimensions:
        if dimension.name not in axes:
            dimensions.append(dimension)
            continue
        present = axes[dimension.name]
        output = tuple(value for value in dimension.requested if value in present) if dimension.requested else tuple(sorted(present))
        missing = tuple(value for value in dimension.requested if value not in present)
        dimensions.append(replace(dimension, interpreted=output, output=output, missing=missing))
    if not any(dimension.name == "semantic_fields" for dimension in dimensions):
        interpreted = tuple(sorted(semantic_fields))
        dimensions.append(CoverageDimension("semantic_fields", requested=interpreted,
            materialized=interpreted, validated=interpreted, interpreted=interpreted, output=interpreted))
    status = "partial" if any(dimension.missing for dimension in dimensions) else coverage.status
    return replace(coverage, status=status, dimensions=tuple(dimensions))
