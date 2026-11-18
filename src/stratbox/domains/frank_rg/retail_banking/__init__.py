"""FRG catalog, latest-file selection and conditional directory effects."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {
    "APPLY": ".api",
    "ARCHIVE": ".api",
    "PLAN": ".api",
    "SCAN": ".api",
    "STREAM_ARCHIVE": ".api",
    "Catalog": ".api",
    "ScanRequest": ".api",
    "StreamArchiveRequest": ".api",
    "apply_cleanup": ".api",
    "plan_cleanup": ".api",
    "prepare_archive": ".api",
    "prepare_archive_to_store": ".api",
    "scan": ".api",
    "ApplyCleanupRequest": ".cleanup",
    "CleanupAction": ".cleanup",
    "CleanupPlan": ".cleanup",
    "CleanupReceipt": ".cleanup",
    "PlanCleanupRequest": ".cleanup",
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
