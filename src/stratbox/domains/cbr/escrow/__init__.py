"""Bank of Russia escrow-account history."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'BuildEscrowViewsRequest': '.contracts',
 'DISCOVER': '.definitions',
 'DiscoverEscrowRequest': '.contracts',
 'EscrowHistoryBuildRequest': '.contracts',
 'EscrowSourceLink': '.contracts',
 'EscrowViewBuildRequest': '.contracts',
 'HISTORY': '.definitions',
 'PARSE': '.definitions',
 'ParseEscrowRequest': '.contracts',
 'RENDER': '.definitions',
 'VIEWS': '.definitions',
 'acquire': '.operations',
 'build_history': '.operations',
 'build_views': '.operations',
 'discover': '.operations',
 'parse': '.operations',
 'render_workbook': '.operations'}
_SYMBOL_MODULES.update({
    **{name: ".contracts" for name in (
        "ParsedEscrowFile", "EscrowDataset", "EscrowPivotPack", "EscrowRelease", "IntegrateEscrowRequest",
        "EscrowFlakeSnapshotRequest", "EscrowDatasetSnapshotRequest", "EscrowViewSnapshotRequest", "ReadEscrowSnapshotRequest",
    )},
    **{name: ".lifecycle" for name in (
        "integrate_flakes", "build_flake_snapshot", "read_flake_snapshot", "build_dataset_snapshot", "read_dataset_snapshot",
        "build_view_snapshot", "read_view_snapshot",
    )},
})
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
