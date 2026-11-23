"""Validated publication-to-profile bindings projected from the operation catalog.

Executable registrations remain the only operation registry. These bindings
select applicable existing operations and qualify their table, format and model
scope; they never execute handlers or infer support from another source family.
"""
from __future__ import annotations

from dataclasses import replace
import re

from stratbox.operations.catalog import OperationCatalog, merge_catalogs
from stratbox.domains.registry.declarations import source_route, profile_document
from stratbox.shared.data.operations import OperationKey, ProcessingStage, compatible_ports
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.publications.catalog import all_sources, families, source
from stratbox.domains.cbr.publications.contracts import ProcessingProfile
from stratbox.domains.cbr.publications.profiles import acquisition_profile
from stratbox.domains.cbr.tables.statistics.contracts import SourceTableProfile, TableVariant
from .catalog.contracts import (BoundOperation, BoundProfile, FamilyDescription, FamilyStage, MethodDependency,
    MethodDescription, ScopedHandoff, ScopedStage, SourceDescription, TableDescription)


def _catalog():
    from stratbox.operations import operation_catalog
    return operation_catalog()


def _key(catalog, operation_id):
    matches = tuple(reference for reference in catalog.references if reference.operation_id == operation_id)
    if len(matches) != 1:
        raise ValueError("cbr.binding.operation_missing" if not matches else "cbr.binding.operation_ambiguous")
    return OperationKey(matches[0].operation_id)


def _definition(catalog, operation_id, *, stage=None):
    key = _key(catalog, operation_id)
    value = catalog.get(key.operation_id)
    if value.processing is None or stage is not None and stage not in value.processing.stages:
        raise ValueError("cbr.binding.operation_stage_mismatch")
    return value


def processing_profile(profile_id, *, catalog=None):
    """Return acquisition-independent processing metadata for a declared profile."""
    catalog = catalog or _catalog()
    try:
        document = profile_document("cbr", profile_id)
    except ValueError:
        raise ValueError("cbr.profile.processing_unknown") from None
    selection = document["declaration"]
    if not {"profile_id", "operation_id", "formats", "scope"} <= set(selection):
        raise ValueError("cbr.profile.processing_unknown")
    operation_id, formats, scope = selection["operation_id"], tuple(selection["formats"]), selection["scope"]
    definition = _definition(catalog, operation_id, stage=ProcessingStage.EXTRACT)
    if not any(port.contract.role is DataRole.EXTRACTS for port in definition.processing.outputs):
        raise ValueError("cbr.binding.extraction_contract_invalid")
    return ProcessingProfile(profile_id, operation_id, formats, scope)


def _models():
    from stratbox.domains.cbr.tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
    from stratbox.domains.cbr.analytics.reporting_forms.registry import MODEL_REGISTRY
    if not set(MODEL_REGISTRY) <= set(LAYOUT_REGISTRY):
        raise ValueError("cbr.binding.form_model_layout_mismatch")
    return frozenset(MODEL_REGISTRY)


def _table_profile(item, primary):
    key = item.series_id.rsplit(".", 1)[1]
    if item.extraction_profile == "cbr.workbook.flake":
        from stratbox.domains.cbr.tables.statistics.profiles import table_profile
        profile = table_profile(item.table_profile)
        if profile.series_id != item.series_id or profile.version != 1:
            raise ValueError("cbr.binding.table_series_mismatch")
        return profile
    version = 2 if item.family_id == "cbr.project_finance" else 1
    if item.table_profile != f"cbr.tables.{key}":
        raise ValueError("cbr.binding.table_profile_unknown")
    if item.family_id == "cbr.reporting_forms":
        variants = [TableVariant("members", r".*", "physical_members", None, "source_report_date",
            ("archive_member", "record", "field", "deletion_flag"), "Published DBF descriptors; no inferred economic unit.",
            "Dynamic archive member schemas and every supported physical record are retained; unsupported members remain exact originals.")]
        if key[1:] in _models():
            variants.append(TableVariant("model_projection", r"reviewed_form_table", "model_input", None,
                "explicit_form_period", ("reporting_subject", "published_row_code", "section", "column"),
                "Reviewed physical layout and explicit metric mapping.",
                "Projection covers the reviewed model input table; other archive tables remain available in the all-member flake."))
    elif item.family_id == "cbr.project_finance":
        variants = [TableVariant("regional", r"recognized_subject_header", "statistics", None, "as_of",
            ("source_geography", "published_indicator"), "Metric-specific RUB scale, count or percent from the source metric registry.",
            "Average and weighted rates have distinct identities; cumulative start dates remain unspecified where unpublished."),
            TableVariant("historical_html", r"historical_html", "original_only", None, "unreviewed",
            (), "Unreviewed source layout.", "Historical HTML is retained; no reviewed table parser is declared.")]
    elif item.family_id == "cbr.service_network":
        bank = key == "bank_offices"
        variants = [TableVariant("office_counts", r"reviewed_office_table", "statistics", "count",
            "capture_or_qualified_official_as_of" if bank else "official_as_of",
            ("credit_institution", "source_geography", "office_type") if bank else ("source_geography", "office_type"),
            "Published office counts; no conversion to individual office identities.",
            "Explicit block selection and versioned subject, geography and metric mappings; capture date alone never establishes a new official release.")]
    elif key in {"debt_0105a", "issuance_0104a"}:
        variants = [TableVariant("regional_industry", r"reviewed_currency_measure_sheets", "statistics",
            "stock" if key == "debt_0105a" else "flow", "as_of" if key == "debt_0105a" else "preceding_calendar_month",
            ("published_industry", "source_geography", "currency", "measure"), "Published million RUB; currency denomination is separate.",
            "Reviewed 26-industry/96-geography layout with explicit selection; older or structurally different editions require admission.")]
    else:
        raise ValueError("cbr.binding.table_profile_unknown")
    return SourceTableProfile(item.table_profile, item.series_id, version, primary.method_id, tuple(variants),
        "Reviewed source-local layout with complete admitted scope and explicit source limitations.",
        "Source identities remain distinct until an explicit reviewed mapping is supplied.")


def _scope(item):
    return source_route(item.series_id).qualifications


def _operation_ids(item, catalog, *, original_only=False):
    route = source_route(item.series_id)
    selected_formats = set(item.formats)
    if original_only:
        primary = processing_profile(item.extraction_profile, catalog=catalog)
        selected_formats -= set(primary.formats)
    return {binding.operation_id for binding in route.operations
            if binding.state != "delegated" and (not binding.formats or selected_formats & set(binding.formats))}


def _bound_operation(catalog, operation_id, qualifications=()):
    op = _definition(catalog, operation_id)
    p = op.processing
    return BoundOperation(_key(catalog, operation_id), op.method_id, p.stages, p.inputs, p.outputs,
                          p.parameters, p.summary, p.composition, qualifications)


def _validate_semantic_profiles(item, catalog):
    family = item.family_id
    if item.normalization_profile is not None:
        if family != "cbr.reporting_forms" or item.normalization_profile != item.series_id.replace("cbr.reporting_forms.", "cbr.forms.") + ".normalization":
            raise ValueError("cbr.binding.normalization_series_mismatch")
        processing_profile(item.normalization_profile, catalog=catalog)
    expected = ("cbr.statistics.observations" if item.extraction_profile == "cbr.workbook.flake" else
        "cbr.project_finance.alignment" if family == "cbr.project_finance" else
        "cbr.service_network.alignment" if family == "cbr.service_network" else
        "cbr.corporate_lending.alignment" if family == "cbr.corporate_lending" else
        "cbr.reporting_forms.alignment" if family == "cbr.reporting_forms" and item.series_id.rsplit(".f", 1)[1] in _models() else None)
    if item.integration_profile != expected:
        raise ValueError("cbr.binding.integration_scope_mismatch")
    if expected is None:
        if item.product_profile is not None:
            raise ValueError("cbr.binding.product_scope_mismatch")
        return
    metadata = profile_document("cbr", expected)["declaration"]
    alignment, product, view = (metadata["alignment_operation"], metadata["product_profile"], metadata["view_operation"])
    if item.product_profile != product:
        raise ValueError("cbr.binding.product_scope_mismatch")
    if alignment is None:
        prefix = "cbr.industries.0105a" if item.series_id.endswith(".debt_0105a") else "cbr.industries.0104a"
        alignment, view = prefix + ".integrate_flakes", prefix + ".build_pivots"
    _definition(catalog, alignment, stage=ProcessingStage.INTEGRATE)
    _definition(catalog, view, stage=ProcessingStage.VIEW)


def _handoffs(operations):
    """Project exact compatible ports; collection assembly is separately explicit."""
    result = []
    for producer in operations:
        for consumer in operations:
            if producer.key == consumer.key:
                continue
            for output in producer.outputs:
                for input in consumer.inputs:
                    if compatible_ports(output, input):
                        result.append(ScopedHandoff(producer.key, output.name, consumer.key, input.name,
                            "direct", output.contract, input.contract,
                            tuple(sorted(input.qualifications - output.qualifications)) + tuple(sorted(input.coverage - output.coverage))))
    return tuple(result)



def _required_handoffs(item, operations, catalog, *, original_only):
    _require_direct(catalog, (("cbr.publications.discover", "cbr.publications.select"),
        ("cbr.publications.select", "cbr.publications.acquire"),
        ("cbr.publications.acquire", "cbr.publications.assess_updates"),
        ("cbr.publications.identify", "cbr.publications.assess_updates")))
    if original_only:
        return ()
    direct, collections = [], []
    if item.extraction_profile == "cbr.workbook.flake":
        direct = [("cbr.publications.identify", "cbr.tables.extract"),
                  ("cbr.publications.acquire", "cbr.tables.extract"),
                  ("cbr.statistics.align", "cbr.statistics.build_view"),
                  ("cbr.statistics.build_view", "cbr.statistics.render_view"),
                  ("cbr.tables.extract", "cbr.tables.flake_snapshot"),
                  ("cbr.tables.flake_snapshot", "cbr.tables.read_flake_snapshot")]
        collections = [("cbr.tables.extract", "flake", "cbr.statistics.align", "flakes",
            DataContract("cbr.workbook.flake", 1, DataRole.EXTRACTS), DataContract("cbr.workbook.flake_collection", 1, DataRole.EXTRACTS))]
        for name in ("validate", "compare", "readable"):
            _definition(catalog, "cbr.tables." + name)
        for name in ("calculate_change", "calculate_share", "dataset_snapshot", "read_dataset_snapshot", "view_snapshot", "read_view_snapshot"):
            _definition(catalog, "cbr.statistics." + name)
    elif item.family_id == "cbr.reporting_forms":
        direct = [("cbr.forms.extract", "cbr.forms.flake_snapshot"),
                  ("cbr.forms.flake_snapshot", "cbr.forms.restore_flakes"),
                  ("cbr.forms.extract", "cbr.forms.make_readable"),
                  ("cbr.forms.extract", "cbr.forms.render_flakes")]
        if item.normalization_profile:
            direct += [("cbr.forms.extract", "cbr.forms.normalize"),
                       ("cbr.forms.align", "cbr.forms.prepare_model_inputs"),
                       ("cbr.forms.prepare_model_inputs", "cbr.forms.calculate"),
                       ("cbr.forms.calculate", "cbr.forms.build_views"),
                       ("cbr.forms.build_data", "cbr.forms.build_views"),
                       ("cbr.forms.build_views", "cbr.forms.render_workbook")]
            collections += [("cbr.forms.normalize", "snapshot", "cbr.forms.align", "snapshots",
                             DataContract("cbr.forms.snapshot", 1, DataRole.EXTRACTS), DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS)),
                            ("cbr.forms.normalize", "snapshot", "cbr.forms.build_data", "snapshots",
                             DataContract("cbr.forms.snapshot", 1, DataRole.EXTRACTS), DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS))]
    elif item.family_id == "cbr.project_finance":
        direct = [("cbr.escrow.integrate_flakes", "cbr.escrow.build_views"),
                  ("cbr.escrow.build_views", "cbr.escrow.render_workbook"),
                  ("cbr.escrow.build_views", "cbr.escrow.view_snapshot"),
                  ("cbr.escrow.view_snapshot", "cbr.escrow.read_view_snapshot"),
                  ("cbr.escrow.read_view_snapshot", "cbr.escrow.render_workbook")]
        collections = [("cbr.escrow.parse", "file", "cbr.escrow.integrate_flakes", "flakes",
                        DataContract("cbr.escrow.parsed_file", 3, DataRole.EXTRACTS), DataContract("cbr.escrow.flakes", 2, DataRole.EXTRACTS))]
    elif item.family_id == "cbr.service_network":
        prefix = "cbr.offices" if item.series_id.endswith(".bank_offices") else "cbr.offices_reg"
        direct = [(prefix + ".parse", "cbr.service_network.align"),
                  ("cbr.service_network.align", "cbr.service_network.build_view"),
                  ("cbr.service_network.build_view", "cbr.service_network.render")]
    else:
        prefix = "cbr.industries.0105a" if item.series_id.endswith(".debt_0105a") else "cbr.industries.0104a"
        direct = [(prefix + ".integrate_flakes", prefix + ".calculate_apk"),
                  (prefix + ".integrate_flakes", prefix + ".build_pivots"),
                  (prefix + ".build_pivots", prefix + ".render_pivots")]
        collections = [(prefix + ".parse", "file", prefix + ".integrate_flakes", "flakes",
            DataContract(prefix + ".parsed_file", 1, DataRole.EXTRACTS), DataContract(prefix + ".parsed_files", 1, DataRole.EXTRACTS))]
    _require_direct(catalog, direct)
    links = []
    for producer, output_name, consumer, input_name, element_contract, collection_contract in collections:
        before, after = _definition(catalog, producer), _definition(catalog, consumer)
        output = next((port for port in before.processing.outputs if port.name == output_name), None)
        input = next((port for port in after.processing.inputs if port.name == input_name), None)
        if output is None or input is None or output.contract != element_contract or input.contract != collection_contract:
            raise ValueError("cbr.binding.collection_contract_mismatch")
        links.append(ScopedHandoff(_key(catalog, producer), output_name, _key(catalog, consumer), input_name,
            "explicit_collection", element_contract, collection_contract,
            ("Assemble the selected admitted values into the request tuple; resolve duplicate releases and coverage explicitly.",)))
    return tuple(links)


def _require_direct(catalog, pairs):
    for producer, consumer in pairs:
        before, after = _definition(catalog, producer), _definition(catalog, consumer)
        if not any(compatible_ports(output, input) for output in before.processing.outputs for input in after.processing.inputs):
            raise ValueError("cbr.binding.handoff_contract_mismatch")


def _delegated_handoffs(operations, delegated, catalog):
    _require_direct(catalog, (("cbr.file_collector.collect_materials", "material.archive"),))
    own = {item.key for item in operations}
    links = _handoffs((*operations, *delegated))
    return tuple(link for link in links if (link.producer in own) != (link.consumer in own))


def _stages(item, operations, *, original_only, catalog):
    result = []
    delegated = {}
    for stage in (ProcessingStage.PRESERVE, ProcessingStage.INGEST):
        keys = tuple(OperationKey(binding.operation_id)
                     for binding in source_route(item.series_id).operations
                     if binding.state == "delegated" and
                     stage in _definition(catalog, binding.operation_id).processing.stages)
        if keys:
            delegated[stage] = keys
    for stage in ProcessingStage:
        keys = tuple(operation.key for operation in operations if stage in operation.stages)
        if stage is ProcessingStage.INGEST and original_only:
            result.append(ScopedStage(stage, "missing", (), "No reviewed dataset encoding is declared for this original-only format."))
        elif stage in delegated:
            result.append(ScopedStage(stage, "delegated", delegated[stage],
                "Caller-selected neutral storage; encode a complete typed value before ingestion."))
        elif stage is ProcessingStage.PUBLISH:
            result.append(ScopedStage(stage, "missing", (), "Destination publication is owned by the receiving application; saving bytes is not remote publication."))
        elif not keys:
            reason = "No standalone operation is declared for this source and stage."
            if original_only and stage not in {ProcessingStage.DISCOVER, ProcessingStage.INSPECT, ProcessingStage.ACQUIRE}:
                reason = "The selected source format has no reviewed extraction layout."
            result.append(ScopedStage(stage, "missing", (), reason))
        else:
            conditional = stage in {ProcessingStage.INTEGRATE, ProcessingStage.CALCULATE, ProcessingStage.VIEW}
            if stage is ProcessingStage.EXTRACT and (original_only or len(item.formats) > 1 and "html" in item.formats):
                conditional = True
            if all(operation.composition for operation in operations if operation.key in keys):
                conditional = True
            result.append(ScopedStage(stage, "conditional" if conditional else "supported", keys,
                "Available within the bound source/table edition and explicit input qualifications.",
                _scope(item) if conditional else ()))
    return tuple(result)


def bind_source(series_id, *, format=None, table_id=None, edition=None, catalog=None):
    catalog = catalog or _catalog()
    item = source(series_id)
    acquisition_profile(item.acquisition_profile)
    if format is not None and format not in item.formats:
        raise ValueError("cbr.binding.format_unknown")
    primary_profile = processing_profile(item.extraction_profile, catalog=catalog)
    if not set(primary_profile.formats) <= set(item.formats):
        raise ValueError("cbr.binding.profile_format_mismatch")
    primary = _definition(catalog, primary_profile.operation_id, stage=ProcessingStage.EXTRACT)
    profile = _table_profile(item, primary)
    if profile.series_id != item.series_id or not profile.variants or len({variant.variant_id for variant in profile.variants}) != len(profile.variants):
        raise ValueError("cbr.binding.table_series_mismatch")
    if edition is not None and edition != profile.edition:
        raise ValueError("cbr.binding.table_edition_unsupported")
    for variant in profile.variants:
        re.compile(variant.sheet_pattern)
    _validate_semantic_profiles(item, catalog)
    original_only_formats = tuple(value for value in item.formats if value not in primary_profile.formats)
    original_only = format in original_only_formats or table_id == item.series_id + ".historical_html"
    ids = _operation_ids(item, catalog, original_only=original_only)
    qualifications = _scope(item)
    operations = tuple(_bound_operation(catalog, operation_id, qualifications) for operation_id in sorted(ids))
    schemas = tuple(dict.fromkeys(port.contract for port in primary.processing.outputs if port.contract.role is DataRole.EXTRACTS))
    tables = tuple(TableDescription(item.series_id + "." + variant.variant_id, variant.variant_id,
        profile.edition, () if variant.role == "original_only" else schemas, variant.sheet_pattern, variant.role,
        variant.quantity_kind, variant.period_basis, variant.dimensions, variant.unit_policy, variant.qualification, variant.unit_anchor)
        for variant in profile.variants)
    if table_id is not None:
        tables = tuple(table for table in tables if table.table_id == table_id)
        if not tables:
            raise ValueError("cbr.binding.table_unknown")
        if format is not None and (format in original_only_formats) != (tables[0].role == "original_only"):
            raise ValueError("cbr.binding.table_format_mismatch")
    selection = tuple((key, value) for key, value in (("format", format), ("table_id", table_id), ("edition", edition)) if value is not None)
    collection_handoffs = _required_handoffs(item, operations, catalog, original_only=original_only)
    delegated = tuple(_bound_operation(catalog, operation_id,
        ("Caller-selected neutral infrastructure; this operation does not implement CBR semantics.",)) for operation_id in (binding.operation_id for binding in source_route(item.series_id).operations if binding.state == "delegated"))
    return SourceDescription(item, profile, tables, operations, _stages(item, operations, original_only=original_only, catalog=catalog),
        _handoffs(operations) + collection_handoffs + _delegated_handoffs(operations, delegated, catalog),
        primary_profile.formats, original_only_formats, selection, qualifications,
        _profile_descriptions(item, profile, operations, catalog), delegated)



def _profile_descriptions(item, table_profile, operations, catalog):
    primary = processing_profile(item.extraction_profile, catalog=catalog)
    extract_definition = _definition(catalog, primary.operation_id)
    profiles = [BoundProfile(item.extraction_profile, "extraction",
        (_key(catalog, primary.operation_id),), primary.formats, primary.scope),
        BoundProfile(item.table_profile, "source_table",
        (_key(catalog, primary.operation_id),), primary.formats, table_profile.extraction_scope)]
    if item.normalization_profile:
        normalized = processing_profile(item.normalization_profile, catalog=catalog)
        definition = _definition(catalog, normalized.operation_id)
        profiles.append(BoundProfile(normalized.profile_id, "source_projection",
            (_key(catalog, normalized.operation_id),), normalized.formats, normalized.scope))
        from stratbox.domains.cbr.analytics.reporting_forms.registry import MODEL_REGISTRY
        from stratbox.domains.cbr.tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
        code = item.series_id.rsplit(".f", 1)[1]
        model, layout = MODEL_REGISTRY[code], LAYOUT_REGISTRY[code]
        profiles.append(BoundProfile(f"cbr.forms.model.{code}", "financial_model",
            tuple(_key(catalog, name) for name in ("cbr.forms.prepare_model_inputs", "cbr.forms.calculate", "cbr.forms.build_data")), primary.formats,
            f"Form {code} model with reviewed layout {layout.edition}; all admitted subjects or an explicit bank selection."))
    for name, kind, stage in ((item.integration_profile, "integration", ProcessingStage.INTEGRATE),
                              (item.product_profile, "product", ProcessingStage.VIEW)):
        if name:
            selected = tuple(operation.key for operation in operations if stage in operation.stages and not operation.composition)
            profiles.append(BoundProfile(name, kind, selected, primary.formats,
                table_profile.integration_scope if kind == "integration" else "Prepared selections can be retained and rendered independently of source parsing."))
    return tuple(profiles)


def _methods(family_id, catalog):
    if family_id != "cbr.corporate_lending":
        return ()
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import dependencies
    inputs = tuple(MethodDependency(item.input_name, item.series_id, item.required, item.accepted_contracts,
                                    item.compatibility_rule) for item in dependencies())
    operations = tuple(_bound_operation(catalog, ref.operation_id) for ref in catalog.references
                       if ref.operation_id.startswith("cbr.sors."))
    return (MethodDescription("cbr.sors", operations, inputs, (
        "Ten required publications and one optional validation history are selected for a common reporting date and compatible publication step.",
        "A narrow output selection does not narrow the full constraint input scope.",
        "Source extraction remains independent of reconstruction; restore consumes a prepared bundle and render_views consumes a prepared product.",
    )),)


def bind_family(family_id, *, catalog=None):
    catalog = catalog or _catalog()
    if family_id not in families():
        raise ValueError("cbr.registry.family_unknown")
    items = all_sources(family_id)
    descriptions = tuple(bind_source(item.series_id, catalog=catalog) for item in items)
    stages = tuple(FamilyStage(stage,
        *(tuple(value.source.series_id for value in descriptions
                if next(scope for scope in value.stages if scope.stage is stage).state == state)
          for state in ("supported", "conditional", "missing", "delegated"))) for stage in ProcessingStage)
    return FamilyDescription(family_id, descriptions, stages, _methods(family_id, catalog))


def validate_all_profiles(*, catalog=None):
    """Validate every series binding, exact metadata reference and declared scope."""
    catalog = catalog or _catalog()
    values = tuple(bind_source(item.series_id, catalog=catalog) for item in all_sources())
    for family_id in families():
        _methods(family_id, catalog)
    return values
