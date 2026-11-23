"""One executable registry with uniform source-scoped metadata across publishers."""
from collections import Counter

from stratbox.domains.registry import operation_catalog
from stratbox.core.execution.semantics import ProcessingFunction


def test_all_publisher_cards_resolve_actual_operations_without_duplicate_sources():
    catalog=operation_catalog()
    sources=catalog.source_catalog()
    assert Counter(c.publisher_id for c in sources.sources)=={"cbr":57,"fns":2,"frank_rg":14,"minfin":13,"rosstat":4}
    assert len(sources.families)==26
    for source in sources.sources:
        for binding in source.operations:
            catalog.get(binding.operation_id,binding.contract_version)
        assert sources.describe(source.series_id,operations=catalog)["source"]==source


def test_cleanup_and_durable_replay_do_not_claim_economic_processing_stages():
    catalog=operation_catalog()
    for op,version,function in (
        ("frg.apply_cleanup",1,ProcessingFunction.MAINTAIN),
        ("cbr.tables.flake_snapshot",1,ProcessingFunction.ENCODE),
        ("cbr.escrow.read_view_snapshot",2,ProcessingFunction.REPLAY),
        ("material.read_artifact",1,ProcessingFunction.REPLAY),
    ):
        definition=catalog.get(op,version)
        assert definition.processing.function is function
        assert definition.processing.stages==()
