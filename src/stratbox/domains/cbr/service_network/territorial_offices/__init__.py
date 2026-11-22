"""Monthly Bank of Russia office releases by territory."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'CAPTURE': '.definitions',
 'COMPARE': '.definitions',
 'CompareReleaseRequest': 'stratbox.shared.data.releases',
 'DISCOVER': '.definitions',
 'DiscoverOfficesRegRequest': '.definitions',
 'OfficesRegCandidates': '.definitions',
 'PARSE': '.definitions',
 'ParseOfficesRegRequest': '.definitions',
 'READ': '.definitions',
 'ReadOfficesRegRequest': '.definitions',
 'SnapshotOfficesRegRequest': '.definitions',
 'SNAPSHOT': '.definitions',
 'RESTORE': '.definitions',
 'snapshot_release': '.snapshots',
 'restore_release': '.snapshots',
 'ReleaseLink': 'stratbox.shared.data.releases',
 'acquire': '.operations',
 'capture': '.operations',
 'compare': '.operations',
 'discover': '.operations',
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
