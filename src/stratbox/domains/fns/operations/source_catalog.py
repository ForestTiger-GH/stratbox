"""FNS source cards bind real operations and retain each reviewed profile's scope."""
from stratbox.core.execution.source_catalog import SourceCard, SourceOperation, SourceProfile

from ..publications.catalog import all_sources


def source_cards():
    result = []
    stages = ("discover", "acquire", "extract", "readable", "validate", "compare_flakes", "project", "align",
        "compare_datasets", "calculate_changes", "calculate_shares", "view", "render", "process", "capture_full",
        "render_artifact", "readable_artifact", "flake_snapshot", "read_flake_snapshot", "projection_snapshot",
        "read_projection_snapshot", "dataset_snapshot", "read_dataset_snapshot", "calculation_snapshot",
        "read_calculation_snapshot", "view_snapshot", "read_view_snapshot")
    for source in all_sources():
        operations = []
        for name in stages:
            conditional = name in {"project", "align", "calculate_changes", "calculate_shares", "process", "capture_full"}
            operations.append(SourceOperation(source.series_id + "." + name,
                state="conditional" if conditional else "supported",
                reason=("Requires the declared reviewed source profile; calculation inputs also require matching metric definitions, scopes and periods."
                        if conditional else "")))
        for name, version in (("parse", 1), ("capture", 1), ("read_representation", 1), ("compare", 2)):
            operations.append(SourceOperation(source.series_id + "." + name, version, "conditional",
                "Explicit regional CSV product convenience; full source retention uses extract/process/capture_full."))
        for name in ("source.save_original", "source.read_original", "dataset.write_snapshot", "dataset.read_snapshot",
                     "material.save_artifact", "material.read_artifact"):
            operations.append(SourceOperation(name, state="delegated", reason="A caller-selected neutral store retains exact bytes, snapshots or artifact descriptors."))
        result.append(SourceCard("fns", source.family_id, source.series_id, source.title,
            "Independent issue key, published observation date, optional publication date and timezone-aware capture timestamp.",
            source.formats, (
                SourceProfile(source.acquisition_profile, "acquisition", "1", source.formats, "Publisher-owned index or dated official link."),
                SourceProfile(source.extract_profile, "physical_extract", "1", source.formats,
                    "Every JSON record/field or every admitted workbook member/cell precedes semantic projection."),
                SourceProfile(source.integration_profile, "integration", "1", (),
                    "Versioned identity-only mappings; qualified source subsets and historical omissions remain explicit."),
            ), tuple(operations), (
                "FNS geographic codes and labels remain in source namespaces; canonical geography requires an explicit external crosswalk.",
                "Net stock changes do not measure registration entries, business births or exits.",
                "File storage is independent of source acquisition, database snapshots and prepared views.",
            )))
    return tuple(result)
