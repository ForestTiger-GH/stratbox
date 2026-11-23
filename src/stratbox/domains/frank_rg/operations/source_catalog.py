"""All fourteen sources share physical admission; semantic layout evidence is explicit."""
from stratbox.core.execution.source_catalog import SourceCard, SourceOperation, SourceProfile
from ..publications.catalog import families
from .bindings import bind_source


def source_cards():
    result = []
    for family in families():
        for series in family.series:
            bound = bind_source(series.source_id)
            formats = tuple(sorted(bound.parent.identification.admitted_formats))
            profiles = tuple(SourceProfile(getattr(bound.parent, key).profile_id, key,
                str(getattr(bound.parent, key).method_version), formats if key == "identification" else ())
                for key in ("discovery", "identification", "selection", "naming"))
            profiles += (SourceProfile("frg.workbook.cells.v1", "physical_workbook", "1", formats,
                "source-faithful cells; OOXML exact lexemes and qualified decoded binary values"),)
            operations = tuple(SourceOperation("frg." + op) for op in (
                "discover", "inspect", "select", "scan", "acquire", "capture", "prepare_file", "plan_updates", "assess_material",
                "extract", "extract_snapshot", "read_extract", "validate", "compare", "readable"))
            operations += tuple(SourceOperation("frg." + op, state="conditional",
                reason="A caller-supplied byte-bound semantic profile must define coordinates, subject, unit, scale, economic period and perimeter; downstream stages require the admitted result.")
                for op in ("build_flake", "flake_snapshot", "read_flake", "integrate", "align", "build_history", "observation_snapshot",
                           "read_observations", "calculate", "prepare_view", "view_snapshot", "read_view", "render_view"))
            operations += tuple(SourceOperation(op, state="delegated", reason="Caller-selected storage preserves the identified material or complete snapshot.")
                for op in ("source.save_original", "source.read_original", "dataset.write_snapshot", "dataset.read_snapshot", "material.save_artifact", "material.read_artifact"))
            result.append(SourceCard("frank_rg", family.family_id, series.source_id, series.title,
                "month_week_publication" if series.periodicity == "month_week" else "supplier_snapshot_publication",
                formats, profiles, operations, (
                    "No reviewed business-layout profile is claimed without retained publisher workbook fixtures.",
                    "Source names, snapshot labels and Q markers do not establish economic periods, units or reporting perimeters.",
                    "Calculations compare exact matching semantic keys; period growth and forecast models are not inferred.",
                )))
    return tuple(result)
