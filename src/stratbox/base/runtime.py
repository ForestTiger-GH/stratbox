"""Explicit construction of the standard local adapters."""

from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class Providers:
    filestore: FileStore
    http: HttpTransport
    secrets: SecretProvider


def local_providers(
    *, root: str | None = None, secret_prefix: str = "STRATBOX_"
) -> Providers:
    return Providers(
        LocalFileStore(root),
        RequestsTransport(),
        EnvSecretProvider(prefix=secret_prefix),
    )
