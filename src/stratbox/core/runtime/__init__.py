"""Provider composition, capability selection and optional dependencies.

Importing this package performs no provider discovery.
"""

from importlib import import_module

_SYMBOLS = {
    "Providers": "providers", "RuntimeProviderError": "providers",
    "local_providers": "providers", "active_providers": "providers",
    "default_filestore": "providers", "default_secrets": "providers",
    "CapabilityRequirement": "capabilities", "ProviderBinding": "capabilities",
    "ProviderSelection": "capabilities",
    "Readiness": "capabilities", "BindingError": "capabilities",
    "probe_provider": "capabilities", "select_provider": "capabilities",
    "MissingExtra": "dependencies", "require_extra": "dependencies",
}
__all__ = tuple(_SYMBOLS)


def __getattr__(name: str):
    module = _SYMBOLS.get(name)
    if module is None:
        raise AttributeError(name)
    result = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = result
    return result
