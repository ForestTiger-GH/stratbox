"""Daily Bank of Russia office observations."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'AcquireOfficesRequest': 'stratbox.domains.cbr.tables.service_network.bank_offices.contracts',
 'AcquiredOffices': 'stratbox.domains.cbr.tables.service_network.bank_offices.contracts',
 'CAPTURE': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'COMPARE': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'CompareReleaseRequest': 'stratbox.shared.data.releases',
 'PARSE': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'ParseOfficesRequest': 'stratbox.domains.cbr.tables.service_network.bank_offices.contracts',
 'READ': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'ReadOfficesRequest': 'stratbox.domains.cbr.tables.service_network.bank_offices.contracts',
 'SnapshotOfficesRequest': 'stratbox.domains.cbr.tables.service_network.bank_offices.contracts',
 'SNAPSHOT': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'RESTORE': 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions',
 'snapshot_release': 'stratbox.domains.cbr.operations.service_network.bank_offices.snapshots',
 'restore_release': 'stratbox.domains.cbr.operations.service_network.bank_offices.snapshots',
 'acquire': 'stratbox.domains.cbr.operations.service_network.bank_offices.operations',
 'capture': 'stratbox.domains.cbr.operations.service_network.bank_offices.operations',
 'compare': 'stratbox.domains.cbr.operations.service_network.bank_offices.operations',
 'parse': 'stratbox.domains.cbr.operations.service_network.bank_offices.operations',
 'read_representation': 'stratbox.domains.cbr.operations.service_network.bank_offices.operations'}
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
