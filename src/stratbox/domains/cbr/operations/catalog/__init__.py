"""Source and family scoped operation discovery."""
from .contracts import DescribeFamilyRequest, DescribeSourceRequest
from importlib import import_module

__all__ = ("DescribeFamilyRequest", "DescribeSourceRequest", "describe_family", "describe_source")


def __getattr__(name):
    if name in {"describe_family", "describe_source"}:
        value = getattr(import_module(__name__ + ".handlers"), name)
        globals()[name] = value
        return value
    raise AttributeError(name)
