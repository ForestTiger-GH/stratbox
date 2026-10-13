#!/usr/bin/env python3
"""Execute the REAL current FRG API module via a direct hostless Python call.

Dependencies are explicit synthetic domain collaborators. This is a bounded
current-source import/call witness, NOT verified banking data/host/browser/
Windows installation or an implementation of the LCD offering compiler.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "src/stratbox/macrobanks/frg/api.py"
assert SOURCE.is_file(), "actual public Python domain API is missing"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
imports = [n.module for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom) and n.level == 0]
assert imports
assert all(name in {
    "__future__", "stratbox.base.filestore",
    "stratbox.macrobanks.frg.catalog", "stratbox.macrobanks.frg.cleanup",
    "stratbox.macrobanks.frg.dispatch", "stratbox.macrobanks.frg.selection",
} for name in imports), "current FRG module gained an unexamined dependency"


def package(name: str) -> None:
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module


def module(name: str, **values: object) -> None:
    mod = types.ModuleType(name)
    for attr, value in values.items():
        setattr(mod, attr, value)
    sys.modules[name] = mod


for pkg in ("stratbox", "stratbox.base", "stratbox.macrobanks",
            "stratbox.macrobanks.frg"):
    package(pkg)

class SyntheticStore:
    pass

store = SyntheticStore()
catalog, latest, dispatched = object(), object(), object()
calls: list[tuple[str, object]] = []


def catalog_builder(root_dir, *, recursive, filestore):
    calls.append(("catalog", (root_dir, recursive, filestore)))
    return catalog


def latest_selector(incoming):
    calls.append(("latest", incoming))
    assert incoming is catalog
    return latest


def dispatcher(incoming):
    calls.append(("dispatch", incoming))
    assert incoming is latest
    return dispatched


module("stratbox.base.filestore", FileStore=SyntheticStore)
module("stratbox.macrobanks.frg.catalog", build_frg_catalog=catalog_builder)
module("stratbox.macrobanks.frg.selection",
       select_latest_frg_files=latest_selector)
module("stratbox.macrobanks.frg.dispatch",
       dispatch_latest_frg_files=dispatcher)
module(
    "stratbox.macrobanks.frg.cleanup",
    apply_frg_cleanup_plan=lambda *args, **kw: None,
    build_frg_actuals_archive_name=lambda *args, **kw: None,
    build_frg_cleanup_plan=lambda *args, **kw: None,
    build_frg_latest_file_name=lambda *args, **kw: None,
    run_frg_cleanup=lambda *args, **kw: None,
)
spec = importlib.util.spec_from_file_location(
    "stratbox.macrobanks.frg.api", SOURCE)
assert spec is not None and spec.loader is not None
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)
sig = inspect.signature(api.run_frg_stage1)
assert list(sig.parameters) == ["root_dir", "recursive", "filestore"]
assert sig.parameters["recursive"].kind is inspect.Parameter.KEYWORD_ONLY
assert sig.parameters["filestore"].kind is inspect.Parameter.KEYWORD_ONLY
assert sig.parameters["recursive"].default is False
assert sig.parameters["filestore"].default is None
assert "run_frg_stage1" in api.__all__

# Notebook-style direct call, no application/host/client object created.
result = api.run_frg_stage1(
    "/synthetic/current-frg-data", recursive=True, filestore=store)
assert isinstance(result, dict) and set(result) == {
    "catalog", "latest", "dispatch"}
assert result["catalog"] is catalog
assert result["latest"] is latest
assert result["dispatch"] is dispatched
assert calls == [
    ("catalog", ("/synthetic/current-frg-data", True, store)),
    ("latest", catalog),
    ("dispatch", latest),
]
assert not any(name.startswith(("stratbox_windows", "stratbox_application",
                                 "appdock")) for name in sys.modules)

print(json.dumps({
    "verdict": "ACTUAL_CORE_FRG_API_DIRECT_PYTHON_CALL_WITH_SYNTHETIC_COLLABORATORS",
    "actual_executed_source": str(SOURCE.relative_to(ROOT)),
    "module_imports_under_test": imports,
    "direct_call_without_host_or_client": True,
    "ordered_domain_stage_contracts": 3,
    "return_keys": list(result),
    "domain_numeric_semantics": "NOT_TESTED_FAKE_TABLES",
    "real_filestore_pandas_parsers": "NOT_TESTED",
    "real_product_offering_or_host": "NOT_TESTED",
    "independent_assurance": "NOT_PERFORMED",
}, ensure_ascii=False))
