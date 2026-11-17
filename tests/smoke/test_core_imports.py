from __future__ import annotations

import importlib

MODULES = [
    'stratbox',
    'stratbox.system.base.runtime',
    'stratbox.system.base.ioapi',
    'stratbox.system.base.filestore',
    'stratbox.domains.cbr_file_collector',
    'stratbox.domains.cbr_industries',
    'stratbox.domains.cbr_forms',
    'stratbox.domains.escrow',
    'stratbox.domains.frg',
]

def test_core_imports() -> None:
    for module in MODULES:
        importlib.import_module(module)
