from __future__ import annotations

import importlib

MODULES = [
    'stratbox',
    'stratbox.core.runtime.providers',
    'stratbox.core.formats',
    'stratbox.core.storage.filestore',
    'stratbox.domains.cbr.operations.collection',
    'stratbox.domains.cbr.operations.corporate_lending.debt',
    'stratbox.domains.cbr.operations.reporting_forms',
    'stratbox.domains.cbr.operations.project_finance',
    'stratbox.domains.frank_rg',
]

def test_core_imports() -> None:
    for module in MODULES:
        importlib.import_module(module)
