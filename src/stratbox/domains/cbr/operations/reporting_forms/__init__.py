"""CBR reporting forms, physical source records and semantic form models."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'BUILD': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'BankSelection': 'stratbox.domains.cbr.analytics.reporting_forms.contracts',
 'BuildFormDataRequest': 'stratbox.domains.cbr.analytics.reporting_forms.contracts',
 'FormData': 'stratbox.domains.cbr.analytics.reporting_forms.contracts',
 'FormKey': 'stratbox.domains.cbr.tables.reporting_forms.contracts',
 'FormSnapshot': 'stratbox.domains.cbr.tables.reporting_forms.contracts',
 'FormSource': 'stratbox.domains.cbr.tables.reporting_forms.contracts',
 'FormViews': 'stratbox.domains.cbr.products.reporting_forms.contracts',
 'PARSE': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'ParseFormRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts',
 'RENDER': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'SELECT': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'SelectFormSourcesRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts',
 'VIEWS': 'stratbox.domains.cbr.operations.reporting_forms.definitions',
 'acquire': 'stratbox.domains.cbr.operations.reporting_forms.acquisition',
 'build_form_data': 'stratbox.domains.cbr.operations.reporting_forms.calculation',
 'build_form_views': 'stratbox.domains.cbr.operations.reporting_forms.products',
 'parse_form': 'stratbox.domains.cbr.operations.reporting_forms.extracts',
 'render_workbook': 'stratbox.domains.cbr.operations.reporting_forms.products',
 'select_sources': 'stratbox.domains.cbr.operations.reporting_forms.acquisition'}
_SYMBOL_MODULES.update({'ExtractFormRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormMember': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormFlakes': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'NormalizeFormRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormFlakeSnapshotRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'DiscoverFormsRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormInventory': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormHistoryRequest': 'stratbox.domains.cbr.tables.reporting_forms.contracts', 'FormResultSnapshotRequest': 'stratbox.domains.cbr.operations.reporting_forms.contracts', 'discover_sources': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'extract_forms': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'normalize_form': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'flake_snapshot': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'restore_flakes': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'snapshot_result': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'restore_normalized': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'restore_data': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'restore_views': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'build_source_history': 'stratbox.domains.cbr.operations.reporting_forms.extracts', 'restore_history': 'stratbox.domains.cbr.operations.reporting_forms.extracts'})
_SYMBOL_MODULES.update({"RenderFormFlakesRequest": 'stratbox.domains.cbr.tables.reporting_forms.contracts', "FormFlakeExport": 'stratbox.domains.cbr.tables.reporting_forms.contracts', "render_flakes": 'stratbox.domains.cbr.operations.reporting_forms.flake_export'})
_SYMBOL_MODULES.update({"ReadFormFlakeExportRequest": 'stratbox.domains.cbr.tables.reporting_forms.contracts', "read_flake_export": 'stratbox.domains.cbr.operations.reporting_forms.flake_export'})
_SYMBOL_MODULES.update({"align_forms": "stratbox.domains.cbr.operations.reporting_forms.integration", "AlignFormRequest": "stratbox.domains.cbr.integration.reporting_forms.contracts", "FormSubjectMapping": "stratbox.domains.cbr.integration.reporting_forms.contracts"})
_SYMBOL_MODULES.update({"compare_sources": "stratbox.domains.cbr.operations.reporting_forms.source_products", "make_readable": "stratbox.domains.cbr.operations.reporting_forms.source_products", "CompareFormFlakesRequest": "stratbox.domains.cbr.tables.reporting_forms.comparison"})
_SYMBOL_MODULES.update({"snapshot_observations": 'stratbox.domains.cbr.operations.reporting_forms.observation_operations', "restore_observations": 'stratbox.domains.cbr.operations.reporting_forms.observation_operations', 'SnapshotFormObservationsRequest': 'stratbox.domains.cbr.operations.reporting_forms.observation_definitions'})
_SYMBOL_MODULES.update({"prepare_model_inputs": "stratbox.domains.cbr.operations.reporting_forms.calculation", "calculate": "stratbox.domains.cbr.operations.reporting_forms.calculation"})
_SYMBOL_MODULES.update({name: "stratbox.domains.cbr.analytics.reporting_forms.contracts" for name in ("PrepareFormModelInputsRequest", "FormModelInputs", "CalculateFormRequest")})
__all__ = tuple(_SYMBOL_MODULES)


def __getattr__(name: str):
    module_name = _SYMBOL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = _import_module(module_name, __name__)
    value = module if module_name == "." + name else getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
