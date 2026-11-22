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
