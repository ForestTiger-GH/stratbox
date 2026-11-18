"""Evidence-preserving regional OKVED2 reconstruction from CBR SORS tables."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {
    "CROSSWALK": ".api",
    "LOAD": ".api",
    "PIVOT": ".api",
    "READ": ".api",
    "RENDER": ".api",
    "RESTORE": ".api",
    "CrosswalkSorsRequest": ".api",
    "LoadSorsRequest": ".api",
    "PivotSorsRequest": ".api",
    "RenderSorsRequest": ".api",
    "RestoreSorsRequest": ".api",
    "build_pivot": ".api",
    "load_sources": ".api",
    "read_source_files": ".api",
    "render_workbook": ".api",
    "restore": ".api",
    "run_crosswalk": ".api",
    "SorsCrosswalkConfig": ".contracts",
    "SorsDeterministicConfig": ".contracts",
    "SorsOptimizationConfig": ".contracts",
    "SorsPivotRequest": ".contracts",
    "SorsRunConfig": ".contracts",
    "SorsSelectionPolicy": ".contracts",
    "SorsSourceBundle": ".contracts",
    "SorsSourceFiles": ".contracts",
    "SorsSourceInputs": ".contracts",
    "SorsTargetScope": ".contracts",
    "SorsWorkbookRequest": ".contracts",
    "SorsCrosswalkResult": ".results",
    "SorsPivotResult": ".results",
    "SorsRestorationResult": ".results",
    "SorsRunSummary": ".results",
    "SorsWorkbookResult": ".results",
}
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
