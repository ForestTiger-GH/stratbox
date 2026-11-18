from __future__ import annotations

import importlib

MODULES = [
    'stratbox',
    'stratbox.core.runtime.providers',
    'stratbox.core.formats',
    'stratbox.core.storage.filestore',
    'stratbox.domains.cbr.file_collection',
    'stratbox.domains.cbr.corporate_lending.industries',
    'stratbox.domains.cbr.reporting_forms',
    'stratbox.domains.cbr.escrow',
    'stratbox.domains.frank_rg.retail_banking',
]

def test_core_imports() -> None:
    for module in MODULES:
        importlib.import_module(module)
