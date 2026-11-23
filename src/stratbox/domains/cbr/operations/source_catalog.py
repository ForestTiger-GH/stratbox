"""Project CBR's source-scoped bindings into the neutral source metadata envelope."""
from stratbox.core.execution.source_catalog import SourceCard, SourceOperation, SourceProfile
from stratbox.domains.cbr.publications.catalog import all_sources
from .bindings import bind_source


def source_cards():
    cards = []
    for source in all_sources():
        bound = bind_source(source.series_id)
        operations = []
        for operation in bound.operations:
            conditional = any(stage.state == "conditional" and operation.key in stage.operations for stage in bound.stages)
            operations.append(SourceOperation(operation.key.operation_id, operation.key.contract_version,
                "conditional" if conditional else "supported",
                "Requires the declared CBR source/table edition and qualified inputs." if conditional else "",
                (("series_id", source.series_id),)))
        existing = {(o.operation_id, o.contract_version) for o in operations}
        for operation in bound.delegated_operations:
            if (operation.key.operation_id, operation.key.contract_version) not in existing:
                operations.append(SourceOperation(operation.key.operation_id, operation.key.contract_version,
                    "delegated", "Choose an admitted destination and supply the exact typed value or retained artifact."))
        profiles = tuple(SourceProfile(p.profile_id, p.kind, p.edition, p.formats, p.scope) for p in bound.profiles)
        cards.append(SourceCard("cbr", source.family_id, source.series_id, source.title,
            source.issue_model, source.formats, profiles, tuple(operations), bound.qualifications))
    return tuple(cards)
