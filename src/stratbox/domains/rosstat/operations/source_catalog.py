"""Four honest source routes bound to the single executable Rosstat catalog."""
from stratbox.core.execution.source_catalog import SourceCard,SourceProfile,SourceOperation
from ..publications.catalog import list_rosstat_sources
from ..publications.discovery.profiles import profile_for


def source_cards():
    cards=[]
    for source in list_rosstat_sources():
        family=source.series_id.rsplit(".",1)[1]
        discovery=profile_for(source.series_id)
        operations=[
            SourceOperation("rosstat.publications.discover",state="conditional",reason="Publisher HTML is candidate evidence; complete inventory requires review of the exact acquired page.",parameters=(("series_id",source.series_id),)),
            SourceOperation("rosstat.publications.select"),SourceOperation("rosstat.publications.review_index",state="conditional",reason="Requires reviewed exact-index scope evidence."),
            SourceOperation("rosstat.publications.plan_updates"),SourceOperation("rosstat.publications.acquire"),
            SourceOperation("rosstat.publications.acquire_to_store"),
        ]
        profiles=[SourceProfile(discovery.profile_id,"discovery",discovery.profile_version,tuple(sorted(source.accepted_formats)),"Provisional recognition; exact issue/asset identity and independently reviewed coverage.")]
        if family in {"short_term_indicators","population_municipalities","socioeconomic_regions"}:
            reason="Regional archive member and container lineage are required." if family=="socioeconomic_regions" else ""
            operations.append(SourceOperation("rosstat.tables.extract_workbook",state="conditional" if reason else "supported",reason=reason,parameters=(("series_id",source.series_id),)))
            operations.extend(SourceOperation("rosstat.tables."+name) for name in ("workbook_snapshot","read_workbook","readable_workbook","compare_workbooks"))
        if family in {"socioeconomic_russia","socioeconomic_regions"}:
            operations.append(SourceOperation("rosstat.tables.extract_document",parameters=(("series_id",source.series_id),)))
            operations.extend(SourceOperation("rosstat.tables."+name) for name in ("document_snapshot","read_document","readable_document"))
            operations.append(SourceOperation("rosstat.tables.structure_document",state="conditional",reason="An exact-original reviewed line/column layout supplies document table structure; PDF page text alone is insufficient."))
        if family=="socioeconomic_regions":
            operations.extend((SourceOperation("rosstat.publications.inspect_archive"),SourceOperation("rosstat.publications.extract_members")))
        if family=="short_term_indicators":
            profiles.append(SourceProfile("rosstat.kep2.v1","table","1",("xlsx",),"Eleven notebook indicators; reviewed A:R period layout, source units, full annual/quarter/month selection; KEP2 2026-08 validated."))
            operations.extend((SourceOperation("rosstat.tables.extract_kep2",state="conditional",reason="Admits the reviewed contents, section markers and period-header layout; unresolved selections remain partial."),
                SourceOperation("rosstat.products.prepare_kep2_monthly"),SourceOperation("rosstat.products.render_kep2_xlsx"),
                SourceOperation("rosstat.analytics.derive_index_growth",state="conditional",reason="Applies only to explicitly identified published percentage-of-baseline index measures.")))
        profiles.append(SourceProfile("rosstat.reviewed_cells.v1","mapping","1",tuple(sorted(source.accepted_formats)),"Caller-supplied coordinates and metric/period/unit/geography meanings pinned to the exact original digest."))
        operations.append(SourceOperation("rosstat.tables.map_reviewed_cells",state="conditional",reason="Requires an exact-original reviewed profile; population also requires a stock date and geographic code edition."))
        operations.extend(SourceOperation("rosstat."+name) for name in (
            "tables.flake_snapshot","tables.read_flake","tables.readable_flake","tables.validate_flake","tables.compare_flakes","integration.integrate",
            "integration.dataset_snapshot","integration.read_dataset","analytics.compare_datasets",
            "products.prepare_view","products.view_snapshot","products.read_view","products.render_view"))
        operations.extend(SourceOperation(name,state="delegated",reason=reason) for name,reason in (
            ("source.save_original","Preserve exact original bytes at a caller-selected destination."),
            ("source.read_original","Restore confirmed source bytes for offline extraction."),
            ("dataset.write_snapshot","Persist a complete physical/source/integrated/view snapshot through the selected dataset adapter."),
            ("dataset.read_snapshot","Restore a pinned complete snapshot for the corresponding Rosstat replay operation."),
            ("material.save_artifact","Preserve rendered bytes together with their MaterialArtifact descriptor and lineage."),
            ("material.read_artifact","Replay the complete retained representation and descriptor."),
        ))
        cards.append(SourceCard("rosstat",source.series_id,source.series_id,source.title,
            "publisher_issue_and_asset:"+source.frequency_hint,tuple(sorted(source.accepted_formats)),tuple(profiles),tuple(operations),
            ("Publisher issue dates and statistical observation periods are separate identities.",
             "Full physical source evidence, selected source flakes, integrated datasets and presentation products are distinct values.")))
    return tuple(cards)
