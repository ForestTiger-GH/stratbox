"""Daily Bank of Russia office observations."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'AcquireOfficesRequest': '.contracts',
 'AcquiredOffices': '.contracts',
 'CAPTURE': '.definitions',
 'COMPARE': '.definitions',
 'CompareReleaseRequest': 'stratbox.shared.data.releases',
 'PARSE': '.definitions',
 'ParseOfficesRequest': '.contracts',
 'READ': '.definitions',
 'ReadReleaseRequest': 'stratbox.shared.data.releases',
 'acquire': '.operations',
 'capture': '.operations',
 'compare': '.operations',
 'parse': '.operations',
 'read_representation': '.operations'}
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
