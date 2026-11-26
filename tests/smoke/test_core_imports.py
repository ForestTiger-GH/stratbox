"""Final public owner metadata is importable without opening providers."""
import importlib


def test_core_imports():
    for module in (
        'stratbox', 'stratbox.sdk', 'stratbox.capabilities.catalog',
        'stratbox.capabilities.catalog.domains', 'stratbox.capabilities.preparation',
        'stratbox.core.execution', 'stratbox.core.observability',
        'stratbox.core.notifications', 'stratbox.core.storage.filestore',
        'stratbox.domains.cbr.domain', 'stratbox.domains.fns.domain',
        'stratbox.domains.minfin.domain', 'stratbox.domains.frank_rg.domain',
        'stratbox.domains.rosstat.domain',
    ):
        importlib.import_module(module)
