"""Monthly Bank of Russia office releases by territory."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'CAPTURE': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'COMPARE': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'CompareReleaseRequest': 'stratbox.shared.data.releases',
 'DISCOVER': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'DiscoverOfficesRegRequest': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'OfficesRegCandidates': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'PARSE': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'ParseOfficesRegRequest': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'READ': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'ReadOfficesRegRequest': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'SnapshotOfficesRegRequest': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'SNAPSHOT': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'RESTORE': 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions',
 'snapshot_release': 'stratbox.domains.cbr.operations.service_network.territorial_offices.snapshots',
 'restore_release': 'stratbox.domains.cbr.operations.service_network.territorial_offices.snapshots',
 'ReleaseLink': 'stratbox.shared.data.releases',
 'acquire': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations',
 'capture': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations',
 'compare': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations',
 'discover': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations',
 'parse': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations',
 'read_representation': 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations'}
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
