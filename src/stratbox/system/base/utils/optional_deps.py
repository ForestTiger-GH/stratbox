"""Use optional dependencies from the installed environment."""

from importlib import import_module
from types import ModuleType


class MissingExtra(ImportError):
    def __init__(self, module: str, extra: str):
        self.extra = extra
        super().__init__(f"{module} is unavailable. Install stratbox[{extra}].")


def require_extra(module: str, extra: str) -> ModuleType:
    try:
        return import_module(module)
    except ImportError as error:
        raise MissingExtra(module, extra) from error
