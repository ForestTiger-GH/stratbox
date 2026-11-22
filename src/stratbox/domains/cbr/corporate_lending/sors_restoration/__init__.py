"""Evidence-preserving regional OKVED2 reconstruction from CBR SORS tables."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'CROSSWALK': '.definitions',
 'CrosswalkSorsRequest': '.definitions',
 'LOAD': '.definitions',
 'LoadSorsRequest': '.definitions',
 'PIVOT': '.definitions',
 'PivotSorsRequest': '.definitions',
 'READ': '.definitions',
 'RENDER': '.definitions',
 'RESTORE': '.definitions',
 'RenderSorsRequest': '.definitions',
 'RestoreSorsRequest': '.definitions',
 'SorsCrosswalkConfig': '.contracts',
 'SorsCrosswalkResult': '.results',
 'SorsDeterministicConfig': '.contracts',
 'SorsOptimizationConfig': '.contracts',
 'SorsPivotRequest': '.contracts',
 'SorsPivotResult': '.results',
 'SorsRestorationResult': '.results',
 'SorsRunConfig': '.contracts',
 'SorsRunSummary': '.results',
 'SorsSelectionPolicy': '.contracts',
 'SorsSourceBundle': '.contracts',
 'SorsSourceFiles': '.contracts',
 'SorsSourceInputs': '.contracts',
 'SorsTargetScope': '.contracts',
 'SorsWorkbookRequest': '.contracts',
 'SorsWorkbookResult': '.results',
 'build_pivot': '.api',
 'load_sources': '.api',
 'read_source_files': '.api',
 'render_workbook': '.api',
 'restore': '.api',
 'run_crosswalk': '.api'}
_SYMBOL_MODULES.update({
    **{name: ".definitions" for name in ("SorsBundleSnapshotRequest", "SorsRestorationSnapshotRequest", "SorsCrosswalkSnapshotRequest", "ReadSorsSnapshotRequest")},
    **{name: ".snapshot_operations" for name in ("build_bundle_snapshot", "read_bundle_snapshot", "build_restoration_snapshot", "read_restoration_snapshot", "build_crosswalk_snapshot", "read_crosswalk_snapshot")},
    "DEPENDENCIES": ".dependencies", "SorsDependency": ".dependencies",
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
