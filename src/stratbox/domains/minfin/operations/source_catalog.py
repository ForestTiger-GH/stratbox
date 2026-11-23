"""Per-series source cards bind domain semantics to the shared operation catalog."""
from stratbox.core.execution.source_catalog import SourceCard, SourceOperation, SourceProfile
from ..publications.catalog import families
from .bindings import bind_series


def source_cards():
    cards = []
    storage = tuple(SourceOperation(op, state="delegated", reason=reason) for op, reason in (
        ("source.save_original", "Preserve supplied original bytes in caller-selected storage."),
        ("source.read_original", "Read exact retained originals using their confirmed source reference."),
        ("dataset.write_snapshot", "Store a complete domain snapshot through the caller's dataset adapter."),
        ("dataset.read_snapshot", "Read a pinned complete domain snapshot through the caller's dataset adapter."),
        ("material.save_artifact", "Wrap a rendered representation as a typed material artifact and select its destination."),
        ("material.read_artifact", "Replay a retained representation and its semantic descriptor."),
    ))
    for family in families():
        for series in family.series:
            bound = bind_series(family.family_id, series.source_id)
            rule = bound.parent.identification.rule(series.slot)
            profiles = (
                SourceProfile(bound.parent.acquisition.profile_id, "acquisition", str(bound.parent.acquisition.method_version), scope="official publisher landing page"),
                SourceProfile(bound.parent.publication.profile_id, "publication", str(bound.parent.publication.method_version), ("html",), "publisher document cards"),
                SourceProfile(bound.parent.identification.profile_id, "identification", str(bound.parent.identification.method_version), (rule.format,), series.slot),
            )
            operations = tuple(SourceOperation("minfin." + op) for op in ("discover", "inspect", "acquire", "plan_updates"))
            if series.kind == "table":
                profiles += (SourceProfile(bound.table.profile_id, "table", bound.table.method_version,
                    tuple(sorted(bound.table.admitted_formats)), "source-local periods and per-row units"),
                    SourceProfile(bound.metrics.profile_id, "calculation", str(bound.metrics.method_version), scope="reviewed headline rows"))
                operations += tuple(SourceOperation("minfin." + op) for op in (
                    "capture", "extract", "validate", "compare", "serialize", "read_representation", "render_csv",
                    "build_flake", "render_flake", "serialize_flake", "read_flake", "flake_snapshot", "read_flake_snapshot",
                    "summarize", "summary_snapshot", "read_summary", "prepare_notice", "prepare_view", "view_snapshot", "read_view", "render_view",
                    "observation_snapshot", "read_observations"))
                operations += (SourceOperation("minfin.integrate", state="conditional",
                    reason="Reviewed headline rows are built in; other rows require explicit metric, unit, basis and perimeter bindings."),)
                qualifications = (
                    "Publication dates are release evidence; reporting periods come from source columns.",
                    "Monthly and quarterly budget values remain cumulative YTD; NWF units and basis are row-specific.",
                )
            else:
                profiles += (SourceProfile("minfin.document.blocks.v1", "document", "1", ("pdf", "docx"), "ordered text and table blocks"),)
                operations += tuple(SourceOperation("minfin." + op, state="conditional",
                    reason="PDF or DOCX bytes and explicit publication context are required; legacy DOC remains an original-only asset.")
                    for op in ("readable", "extract_document", "document_snapshot", "read_document", "render_document"))
                qualifications = ("Historical document branch retains ordered blocks with explicit coverage; no automatic economic table interpretation.",
                                  "Legacy DOC decoding is not supplied; exact source bytes remain retainable.")
            cards.append(SourceCard("minfin", family.family_id, series.source_id, series.title,
                "publisher_document_release", (rule.format,), profiles, (*operations, *storage), qualifications))
    return tuple(cards)
