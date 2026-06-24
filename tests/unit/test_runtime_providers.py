from __future__ import annotations

from stratbox.base.runtime import get_providers


def test_runtime_providers_local_default() -> None:
    providers = get_providers(force_reload=True)
    assert providers.source in {'local', 'plugin'}
    assert providers.filestore is not None
    assert providers.secrets is not None
