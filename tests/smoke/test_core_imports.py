from __future__ import annotations

import importlib

MODULES = [
    'stratbox',
    'stratbox.base.runtime',
    'stratbox.base.ioapi',
    'stratbox.base.filestore',
    'stratbox.macrobanks.cbr_file_collector',
    'stratbox.macrobanks.cbr_forms',
    'stratbox.macrobanks.escrow',
    'stratbox.macrobanks.frg',
]

def test_core_imports() -> None:
    for module in MODULES:
        importlib.import_module(module)
