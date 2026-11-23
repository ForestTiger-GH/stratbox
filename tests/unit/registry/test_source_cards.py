"""One executable registry with uniform source-scoped metadata across publishers."""
from collections import Counter

from stratbox.domains.registry import operation_catalog
from stratbox.core.execution.semantics import ProcessingFunction, compatible_ports


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


def test_common_snapshot_ports_separate_values_codecs_and_storage():
    catalog = operation_catalog()

    def connected(producer, consumer):
        before = catalog.get(producer, 1).processing.outputs
        after = catalog.get(consumer, 1).processing.inputs
        return any(compatible_ports(out, inp) for out in before for inp in after)

    for encode, replay in (
        ("workbook.snapshot", "workbook.replay"),
        ("document.snapshot", "document.replay"),
        ("observations.view_snapshot", "observations.replay_view"),
        ("frg.extract_snapshot", "workbook.replay"),
        ("frg.view_snapshot", "observations.replay_view"),
        ("minfin.view_snapshot", "observations.replay_view"),
    ):
        assert connected(encode, replay)
        assert connected(encode, "dataset.write_snapshot")

    for producer, consumer in (
        ("workbook.snapshot", "document.replay"),
        ("document.snapshot", "observations.replay_view"),
        ("observations.view_snapshot", "workbook.replay"),
        ("workbook.extract", "workbook.replay"),
        ("frg.extract", "frg.read_extract"),
        ("minfin.prepare_view", "minfin.read_view"),
        ("frg.prepare_view", "frg.read_view"),
    ):
        assert not connected(producer, consumer)
