"""Project finance operation entry points and typed request contracts."""
from importlib import import_module
_SYMBOL_MODULES = {'ACQUIRE': '.definitions', 'DISCOVER': '.definitions', 'HISTORY': '.definitions', 'PARSE': '.definitions', 'RENDER': '.definitions', 'VIEWS': '.definitions', 'INTEGRATE': '.definitions', 'FLAKE_SNAPSHOT': '.definitions', 'READ_FLAKE_SNAPSHOT': '.definitions', 'DATASET_SNAPSHOT': '.definitions', 'READ_DATASET_SNAPSHOT': '.definitions', 'VIEW_SNAPSHOT': '.definitions', 'READ_VIEW_SNAPSHOT': '.definitions', 'BuildEscrowViewsRequest': '.contracts', 'DiscoverEscrowRequest': '.contracts', 'EscrowHistoryBuildRequest': '.contracts', 'EscrowSourceLink': '.contracts', 'ParseEscrowRequest': '.contracts', 'IntegrateEscrowRequest': '.contracts', 'EscrowFlakeSnapshotRequest': '.contracts', 'EscrowDatasetSnapshotRequest': '.contracts', 'EscrowViewSnapshotRequest': '.contracts', 'ReadEscrowSnapshotRequest': '.contracts', 'CompareEscrowFlakesRequest': '.contracts', 'ParsedEscrowFile': 'stratbox.domains.cbr.tables.project_finance.contracts', 'EscrowDataset': 'stratbox.domains.cbr.integration.project_finance.contracts', 'EscrowRelease': 'stratbox.domains.cbr.integration.project_finance.contracts', 'EscrowPivotPack': 'stratbox.domains.cbr.products.project_finance.contracts', 'EscrowViewBuildRequest': 'stratbox.domains.cbr.products.project_finance.contracts', 'EscrowProductProfile': 'stratbox.domains.cbr.products.project_finance.profiles', 'EscrowProductIndicator': 'stratbox.domains.cbr.products.project_finance.profiles', 'DEFAULT_PRODUCT_PROFILE': 'stratbox.domains.cbr.products.project_finance.profiles', 'discover': '.handlers', 'acquire': '.handlers', 'parse': '.handlers', 'build_history': '.handlers', 'build_views': '.handlers', 'render_workbook': '.handlers', 'integrate_flakes': '.lifecycle', 'build_flake_snapshot': '.lifecycle', 'read_flake_snapshot': '.lifecycle', 'build_dataset_snapshot': '.lifecycle', 'read_dataset_snapshot': '.lifecycle', 'build_view_snapshot': '.lifecycle', 'read_view_snapshot': '.lifecycle'}
_SYMBOL_MODULES.update({
    "AlignEscrowObservationsRequest": ".contracts",
    "EscrowGeographyRule": "stratbox.domains.cbr.integration.project_finance.mapping",
    **{name: ".inspection" for name in ("validate", "compare", "readable", "align_observations")},
    **{name: ".definitions" for name in ("VALIDATE", "COMPARE", "READABLE", "ALIGN")},
})
__all__ = tuple(_SYMBOL_MODULES)

def __getattr__(name):
    module = _SYMBOL_MODULES.get(name)
    if module is None:
        raise AttributeError(name)
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value

def __dir__():
    return sorted(set(globals()) | set(__all__))
