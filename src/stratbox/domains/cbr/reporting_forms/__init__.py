"""CBR reporting forms, physical source records and semantic form models."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'BUILD': '.definitions',
 'BankSelection': '.contracts',
 'BuildFormDataRequest': '.contracts',
 'FormData': '.contracts',
 'FormKey': '.contracts',
 'FormSnapshot': '.contracts',
 'FormSource': '.contracts',
 'FormViews': '.contracts',
 'PARSE': '.definitions',
 'ParseFormRequest': '.contracts',
 'RENDER': '.definitions',
 'SELECT': '.definitions',
 'SelectFormSourcesRequest': '.contracts',
 'VIEWS': '.definitions',
 'acquire': '.operations',
 'build_form_data': '.operations',
 'build_form_views': '.operations',
 'parse_form': '.operations',
 'render_workbook': '.operations',
 'select_sources': '.operations'}
_SYMBOL_MODULES.update({'ExtractFormRequest': '.contracts', 'FormMember': '.contracts', 'FormFlakes': '.contracts', 'NormalizeFormRequest': '.contracts', 'FormFlakeSnapshotRequest': '.contracts', 'DiscoverFormsRequest': '.contracts', 'FormInventory': '.contracts', 'IntegrateFormsRequest': '.contracts', 'FormResultSnapshotRequest': '.contracts', 'discover_sources': '.source_operations', 'extract_forms': '.source_operations', 'normalize_form': '.source_operations', 'flake_snapshot': '.source_operations', 'restore_flakes': '.source_operations', 'snapshot_result': '.source_operations', 'restore_normalized': '.source_operations', 'restore_data': '.source_operations', 'restore_views': '.source_operations', 'integrate_forms': '.source_operations', 'restore_history': '.source_operations'})
_SYMBOL_MODULES.update({"RenderFormFlakesRequest": ".contracts", "FormFlakeExport": ".contracts", "render_flakes": ".flake_export"})
_SYMBOL_MODULES.update({"ReadFormFlakeExportRequest": ".contracts", "read_flake_export": ".flake_export"})
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
