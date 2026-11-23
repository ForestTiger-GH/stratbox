"""Source-level registry coverage must not inherit support from another series."""
from dataclasses import replace

import pytest

from stratbox.shared.data.operations import ProcessingStage, OperationKey, OutputPort
from stratbox.domains.cbr.operations import bindings
from stratbox.domains.cbr.operations.catalog import DescribeFamilyRequest, DescribeSourceRequest, describe_family, describe_source
from stratbox.shared.data.processing import DataContract, DataRole


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def stage(value, name):
    return next(item for item in value.stages if item.stage is name)


def test_all_57_publications_bind_to_exact_registered_contracts():
    catalog = bindings._catalog()
    values = bindings.validate_all_profiles(catalog=catalog)
    assert len(values) == 57
    assert len({item.source.family_id for item in values}) == 12
    for item in values:
        assert item.tables and item.source.series_id == item.table_profile.series_id
        for operation in (*item.operations, *item.delegated_operations):
            current = catalog.get(operation.key.operation_id)
            assert operation.method_id == current.method_id
            assert operation.inputs == current.processing.inputs
            assert operation.outputs == current.processing.outputs
        for table in item.tables:
            assert table.edition == item.table_profile.edition
            assert table.table_id.startswith(item.source.series_id + ".")
        for connection in item.handoffs:
            assert connection.producer in {operation.key for operation in (*item.operations, *item.delegated_operations)}
            assert connection.consumer in {operation.key for operation in (*item.operations, *item.delegated_operations)}


def test_forms_without_models_keep_source_processing_but_expose_alignment_gaps():
    for code in ("134", "803"):
        value = checked(describe_source(DescribeSourceRequest("cbr.reporting_forms.f" + code)))
        ids = {operation.key.operation_id for operation in value.operations}
        assert {"cbr.forms.extract", "cbr.forms.flake_snapshot", "cbr.forms.make_readable"} <= ids
        assert {"cbr.forms.align", "cbr.forms.normalize", "cbr.forms.build_data", "cbr.forms.build_views"}.isdisjoint(ids)
        assert stage(value, ProcessingStage.EXTRACT).state == "supported"
        assert stage(value, ProcessingStage.INTEGRATE).state == "missing"
        assert stage(value, ProcessingStage.VIEW).state == "missing"
    family = checked(describe_family(DescribeFamilyRequest("cbr.reporting_forms")))
    integration = stage(family, ProcessingStage.INTEGRATE)
    assert set(integration.missing_sources) == {"cbr.reporting_forms.f134", "cbr.reporting_forms.f803"}
    assert len(integration.conditional_sources) == 6


def test_escrow_html_cannot_inherit_xlsx_extraction_coverage():
    value = checked(describe_source(DescribeSourceRequest("cbr.project_finance.escrow", format="html")))
    assert value.original_only_formats == ("html",)
    assert stage(value, ProcessingStage.EXTRACT).state == "missing"
    assert stage(value, ProcessingStage.INGEST).state == "missing"
    assert not any(operation.key.operation_id == "cbr.escrow.parse" for operation in value.operations)
    xlsx = checked(describe_source(DescribeSourceRequest("cbr.project_finance.escrow", format="xlsx")))
    assert OperationKey("cbr.escrow.parse") in stage(xlsx, ProcessingStage.EXTRACT).operations
    assert any(link.assembly == "explicit_collection" for link in xlsx.handoffs)
    historical = next(table for table in value.tables if table.variant_id == "historical_html")
    assert historical.schema_contracts == ()
    mismatch = describe_source(DescribeSourceRequest("cbr.project_finance.escrow", format="xlsx", table_id=historical.table_id))
    assert mismatch.diagnostics[0].code == "cbr.binding.table_format_mismatch"


def test_table_selection_and_edition_are_explicit_and_unknown_editions_fail():
    value = checked(describe_source(DescribeSourceRequest("cbr.monetary_statistics.monetary_agg")))
    assert len(value.tables) >= 4
    chosen = checked(describe_source(DescribeSourceRequest(value.source.series_id,
        table_id=value.tables[0].table_id, edition=value.table_profile.edition)))
    assert chosen.tables == (value.tables[0],)
    failed = describe_source(DescribeSourceRequest(value.source.series_id, edition="unreviewed-edition"))
    assert failed.diagnostics[0].code == "cbr.binding.table_edition_unsupported"
    failed = describe_source(DescribeSourceRequest(value.source.series_id, table_id="invented"))
    assert failed.diagnostics[0].code == "cbr.binding.table_unknown"


def test_sors_method_has_full_dependencies_without_marking_all_corporate_sources_as_sors():
    family = checked(describe_family(DescribeFamilyRequest("cbr.corporate_lending")))
    method, = family.methods
    assert method.method_id == "cbr.sors"
    assert sum(item.required for item in method.dependencies) == 10
    assert sum(not item.required for item in method.dependencies) == 1
    for source in family.sources:
        assert not any(item.key.operation_id.startswith("cbr.sors.") for item in source.operations)
    source = next(item for item in family.sources if item.source.series_id.endswith(".sme_debt"))
    assert any(item.key.operation_id == "cbr.corporate_lending.extract_observations" for item in source.operations)
    source = next(item for item in family.sources if item.source.series_id.endswith(".sme_borrowers_info"))
    assert not any(item.key.operation_id == "cbr.corporate_lending.extract_observations" for item in source.operations)


def test_binding_validation_rejects_profile_scope_format_and_table_series_mismatch(monkeypatch):
    item = bindings.source("cbr.funding.funds_all")
    original = bindings.source
    for mutated, expected in (
        (replace(item, formats=("html",)), "profile_format_mismatch"),
        (replace(item, table_profile="cbr.tables.funds_clients"), "table_series_mismatch"),
        (replace(item, integration_profile="cbr.service_network.alignment"), "integration_scope_mismatch"),
        (replace(item, product_profile="cbr.project_finance.views"), "product_scope_mismatch"),
        (replace(item, extraction_profile="cbr.invented.profile"), "processing_unknown"),
    ):
        monkeypatch.setattr(bindings, "source", lambda key, value=mutated: value)
        with pytest.raises(ValueError, match=expected):
            bindings.bind_source(item.series_id)
    monkeypatch.setattr(bindings, "source", original)


def test_binding_validation_detects_a_broken_declared_handoff():
    actual = bindings._catalog()
    class ChangedCatalog:
        references = actual.references
        def get(self, operation_id):
            result = actual.get(operation_id)
            if operation_id == "cbr.statistics.align":
                return replace(result, processing=replace(result.processing,
                    outputs=(OutputPort("wrong", DataContract("different.dataset", 1, DataRole.INTEGRATED)),)))
            return result
    with pytest.raises(ValueError, match="handoff_contract_mismatch"):
        bindings.bind_source("cbr.funding.funds_all", catalog=ChangedCatalog())


def test_descriptions_load_metadata_without_resolving_or_executing_handlers(monkeypatch):
    catalog = bindings._catalog()
    def forbidden(*args, **kwargs):
        raise AssertionError("Description must not resolve executable handlers")
    monkeypatch.setattr(type(catalog), "resolve", forbidden)
    value = bindings.bind_source("cbr.reporting_forms.f101", catalog=catalog)
    assert any(profile.kind == "financial_model" and profile.profile_id == "cbr.forms.model.101" for profile in value.profiles)


def test_publication_lifecycle_and_neutral_archive_receive_exact_scoped_ports():
    value = bindings.bind_source("cbr.monetary_statistics.balance_odc")
    ids = {operation.key.operation_id for operation in value.operations}
    assert {"cbr.publications.select", "cbr.publications.acquire", "cbr.publications.assess_updates"} <= ids
    edges = {(link.producer.operation_id, link.output, link.consumer.operation_id, link.input) for link in value.handoffs}
    assert ("cbr.publications.discover", "inventory", "cbr.publications.select", "inventory") in edges
    assert ("cbr.publications.select", "asset", "cbr.publications.acquire", "asset") in edges
    assert ("cbr.publications.acquire", "original", "cbr.tables.extract", "original") in edges
    assert ("cbr.file_collector.collect_materials", "archive_members", "material.archive", "members") in edges
    assert ("cbr.file_collector.collect_materials", "manifest", "material.archive", "manifest") in edges
    assert OperationKey("material.archive") in {operation.key for operation in value.delegated_operations}
    assert {table.unit_anchor for table in value.tables if table.variant_id in {"table_2", "table_3", "table_4"}} == {"A2"}


def test_reviewed_form_models_offer_a_standalone_route_from_retained_observations():
    value = bindings.bind_source("cbr.reporting_forms.f101")
    edges = {(link.producer.operation_id, link.consumer.operation_id) for link in value.handoffs}
    assert ("cbr.forms.align", "cbr.forms.prepare_model_inputs") in edges
    assert ("cbr.forms.prepare_model_inputs", "cbr.forms.calculate") in edges
    assert ("cbr.forms.calculate", "cbr.forms.build_views") in edges
    model = next(profile for profile in value.profiles if profile.kind == "financial_model")
    assert OperationKey("cbr.forms.calculate") in model.operations
    for code in ("134", "803"):
        unsupported = bindings.bind_source("cbr.reporting_forms.f" + code)
        assert {"cbr.forms.prepare_model_inputs", "cbr.forms.calculate"}.isdisjoint(
            operation.key.operation_id for operation in unsupported.operations)
