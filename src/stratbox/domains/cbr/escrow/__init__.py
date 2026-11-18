"""Bank of Russia escrow-account history."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {
    "BuildEscrowViewsRequest": ".contracts",
    "DiscoverEscrowRequest": ".contracts",
    "EscrowHistoryBuildRequest": ".contracts",
    "EscrowSourceLink": ".contracts",
    "EscrowViewBuildRequest": ".contracts",
    "ParseEscrowRequest": ".contracts",
    "ACQUIRE": ".operations",
    "DISCOVER": ".operations",
    "HISTORY": ".operations",
    "PARSE": ".operations",
    "RENDER": ".operations",
    "VIEWS": ".operations",
    "acquire": ".operations",
    "build_history": ".operations",
    "build_views": ".operations",
    "discover": ".operations",
    "parse": ".operations",
    "render_workbook": ".operations",
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
