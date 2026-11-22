"""Monthly corporate loan issuance by industry and region (01_04_A)."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'BUILD_STREAM': '.definitions',
 'BuildIssuanceStreamRequest': '.contracts',
 'CALCULATE_APK': '.definitions',
 'CalculateIssuanceApkRequest': '.contracts',
 'DISCOVER': '.definitions',
 'DiscoverIssuanceRequest': '.contracts',
 'IndustrySelection': 'stratbox.domains.cbr.corporate_lending.industries.common.contracts',
 'IssuanceSourceLink': '.contracts',
 'IssuanceStreamResult': '.contracts',
 'IssuanceWorkbookRequest': '.contracts',
 'IssuanceWorkbooksResult': '.contracts',
 'PARSE': '.definitions',
 'PIVOT': '.definitions',
 'ParseIssuanceRequest': '.contracts',
 'PivotIssuanceRequest': '.contracts',
 'RENDER_INDUSTRIES': '.definitions',
 'RENDER_INDUSTRY': '.definitions',
 'RenderIssuanceIndustriesRequest': '.contracts',
 'acquire': '.operations',
 'build_pivots': '.operations',
 'build_stream': '.operations',
 'calculate_apk': '.operations',
 'discover': '.operations',
 'parse': '.operations',
 'render_industries': '.operations',
 'render_industry': '.operations'}
_SYMBOL_MODULES.update({'IntegrateIssuanceFlakesRequest': '.contracts', 'IndustrySnapshotRequest': 'stratbox.domains.cbr.corporate_lending.industries.common.contracts', 'ReadIndustrySnapshotRequest': 'stratbox.domains.cbr.corporate_lending.industries.common.contracts', 'integrate_flakes': '.snapshot_operations', 'INTEGRATE_FLAKES': '.definitions', 'build_flake_snapshot': '.snapshot_operations', 'read_flake_snapshot': '.snapshot_operations', 'FLAKE_SNAPSHOT': '.definitions', 'READ_FLAKE_SNAPSHOT': '.definitions', 'build_stream_snapshot': '.snapshot_operations', 'read_stream_snapshot': '.snapshot_operations', 'STREAM_SNAPSHOT': '.definitions', 'READ_STREAM_SNAPSHOT': '.definitions', 'build_calculation_snapshot': '.snapshot_operations', 'read_calculation_snapshot': '.snapshot_operations', 'CALCULATION_SNAPSHOT': '.definitions', 'READ_CALCULATION_SNAPSHOT': '.definitions', 'build_view_snapshot': '.snapshot_operations', 'read_view_snapshot': '.snapshot_operations', 'VIEW_SNAPSHOT': '.definitions', 'READ_VIEW_SNAPSHOT': '.definitions'})
_SYMBOL_MODULES.update({"RenderIssuancePivotsRequest": ".contracts", "render_pivots": ".operations", "RENDER_PIVOTS": ".definitions"})
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
