"""Bank of Russia original-file catalog and acquisition."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ARCHIVE': '.definitions',
 'ARCHIVE_TO_STORE': '.definitions',
 'COLLECT': '.definitions',
 'COLLECT_TO_STORE': '.definitions',
 'CbrFileRegistryItem': '.contracts',
 'CollectFailure': '.contracts',
 'CollectFilesRequest': '.contracts',
 'CollectToStoreRequest': '.contracts',
 'CollectedFile': '.contracts',
 'Collection': '.contracts',
 'DISCOVER': '.definitions',
 'DiscoverFilesRequest': '.contracts',
 'PrepareArchiveRequest': '.contracts',
 'StoreArchiveRequest': '.contracts',
 'StoredCollectedFile': '.contracts',
 'archive_to_store': '.operations',
 'collect_raw': '.operations',
 'collect_to_store': '.operations',
 'discover': '.operations',
 'prepare_archive': '.operations'}
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
