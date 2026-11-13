"""Select a default provider set supplied by the installed environment."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from importlib.metadata import entry_points
from importlib.util import find_spec
from pathlib import Path
import re
from threading import RLock
from typing import TYPE_CHECKING, Callable

from stratbox.base.capabilities import (
    BindingError as BindingError,
    CapabilityRequirement as CapabilityRequirement,
    ProviderBinding as ProviderBinding,
    probe_provider as probe_provider,
    select_provider as select_provider,
)
from stratbox.base.filestore import FileStore, LocalFileStore
from stratbox.base.net import HttpTransport, RequestsTransport
from stratbox.base.secrets import EnvSecretProvider, SecretProvider

if TYPE_CHECKING:
    from stratbox.base.styles.excel.registry import ExcelStylesRegistry

_FACTORY = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", re.ASCII)
_LOCK = RLock()


class RuntimeProviderError(OSError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Providers:
    filestore: FileStore
    http: HttpTransport
    secrets: SecretProvider
    excel_styles: Callable[[], ExcelStylesRegistry] | None = None


def local_providers(*, root: str | None = None, secret_prefix: str = "STRATBOX_") -> Providers:
    return Providers(LocalFileStore(root), RequestsTransport(), EnvSecretProvider(prefix=secret_prefix))


def active_providers() -> Providers | None:
    """Use wheel entry-point metadata or a factory in a sibling source package."""
    with _LOCK:
        return _discover_providers()


@lru_cache(maxsize=1)
def _discover_providers() -> Providers | None:
    try:
        installed = {}
        for entry in entry_points(group="stratbox.runtime", name="default"):
            if entry.value in installed:
                raise RuntimeProviderError("provider.binding_conflict")
            installed[entry.value] = entry
        candidates = dict.fromkeys(installed)
        root = Path(__file__).resolve().parents[2]
        for marker in root.glob("stratbox_*/_stratbox_runtime.py"):
            package = marker.parent
            candidates[f"{package.name}._stratbox_runtime:create_providers"] = package / "__init__.py"
        if not candidates:
            return None
        if len(candidates) != 1:
            raise RuntimeProviderError("provider.binding_conflict")
        value, origin = next(iter(candidates.items()))
        if not _FACTORY.fullmatch(value):
            raise ValueError("Invalid runtime factory")
        module, name = value.split(":")
        if origin is not None:
            spec = find_spec(module.split(".", 1)[0])
            if spec is None or not spec.origin or Path(spec.origin).resolve() != origin.resolve():
                raise RuntimeProviderError("provider.binding_conflict")
        factory = installed[value].load() if value in installed else getattr(import_module(module), name)
        bundle = factory()
        if not isinstance(bundle, Providers) or any(
            not callable(getattr(adapter, method, None)) for adapter, method in (
                (bundle.filestore, "open_read"), (bundle.filestore, "write_bytes"),
                (bundle.http, "exchange"), (bundle.secrets, "get_secret"),
            )
        ):
            raise TypeError("Invalid provider bundle")
        if bundle.excel_styles is not None and not callable(bundle.excel_styles):
            raise TypeError("Invalid Excel registry factory")
        return bundle
    except RuntimeProviderError:
        raise
    except Exception:
        raise RuntimeProviderError("provider.configuration_invalid") from None


def default_filestore(store: FileStore | None = None) -> FileStore:
    if store is not None:
        return store
    active = active_providers()
    return active.filestore if active is not None else LocalFileStore()


def default_secrets(secrets: SecretProvider | None = None) -> SecretProvider:
    if secrets is not None:
        return secrets
    active = active_providers()
    return active.secrets if active is not None else EnvSecretProvider(prefix="STRATBOX_")
