"""CBR corporate lending by industry: publication-family grouping.

Stock (01_05_A) and monthly issuance (01_04_A) are independent operation
owners. Statistical source layouts shared by the series are under common.
"""

from importlib import import_module as _import_module

__all__ = ("common", "debt_0105a", "issuance_0104")


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = _import_module("." + name, __name__)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
