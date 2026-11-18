"""Monthly corporate loan issuance by industry and region (01_04_A)."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {
    "IndustrySelection": "stratbox.domains.cbr.corporate_lending.industries.contracts",
    "BuildIssuanceStreamRequest": ".contracts",
    "CalculateIssuanceApkRequest": ".contracts",
    "DiscoverIssuanceRequest": ".contracts",
    "IssuanceSourceLink": ".contracts",
    "IssuanceStreamResult": ".contracts",
    "IssuanceWorkbookRequest": ".contracts",
    "RenderIssuanceIndustriesRequest": ".contracts",
    "IssuanceWorkbooksResult": ".contracts",
    "ParseIssuanceRequest": ".contracts",
    "PivotIssuanceRequest": ".contracts",
    "ACQUIRE": ".operations",
    "BUILD_STREAM": ".operations",
    "CALCULATE_APK": ".operations",
    "DISCOVER": ".operations",
    "PARSE": ".operations",
    "PIVOT": ".operations",
    "RENDER_INDUSTRY": ".operations",
    "RENDER_INDUSTRIES": ".operations",
    "acquire": ".operations",
    "build_pivots": ".operations",
    "build_stream": ".operations",
    "calculate_apk": ".operations",
    "discover": ".operations",
    "parse": ".operations",
    "render_industry": ".operations",
    "render_industries": ".operations",
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
