"""Credit-institution office source, integration, calculation and product operations."""
from importlib import import_module
_SYMBOLS = {
    "make_readable": ".lifecycle", "build_source_history": ".lifecycle", "restore_history": ".lifecycle",
    "align_offices": ".lifecycle", "calculate_changes": ".lifecycle", "build_view": ".lifecycle", "render": ".lifecycle",
    "ReadableOfficesRequest": "stratbox.domains.cbr.tables.service_network.readable",
    "OfficeHistoryRequest": "stratbox.domains.cbr.tables.service_network.history",
    "AlignOfficesRequest": "stratbox.domains.cbr.integration.service_network.contracts",
    "OfficeSubjectMapping": "stratbox.domains.cbr.integration.service_network.contracts",
    "OfficeRegionMapping": "stratbox.domains.cbr.integration.service_network.contracts",
    "OfficeMetricMapping": "stratbox.domains.cbr.integration.service_network.contracts",
    "OfficeChangesRequest": "stratbox.domains.cbr.analytics.service_network.changes",
    "OfficeViewRequest": "stratbox.domains.cbr.products.service_network.views",
    "RenderOfficeViewRequest": "stratbox.domains.cbr.products.service_network.views",
}
_SYMBOLS.update({"snapshot_observations": 'stratbox.domains.cbr.operations.service_network.observation_operations', "restore_observations": 'stratbox.domains.cbr.operations.service_network.observation_operations', 'SnapshotOfficeObservationsRequest': 'stratbox.domains.cbr.operations.service_network.observation_definitions'})
__all__ = tuple(_SYMBOLS)
def __getattr__(name):
    if name not in _SYMBOLS:
        raise AttributeError(name)
    value = getattr(import_module(_SYMBOLS[name], __name__), name)
    globals()[name] = value
    return value
