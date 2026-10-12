#!/usr/bin/env python3
"""Source-executing, offline FRG cleanup fault characterization.
Uses actual current cleanup.py with minimal fake pandas/FileStore/zip dependencies.
Asserts CURRENT hazardous failure behavior, not acceptable future behavior.
"""
from __future__ import annotations
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "src/stratbox/macrobanks/frg/cleanup.py"

def package(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

for name in ("stratbox", "stratbox.base", "stratbox.base.filestore",
             "stratbox.base.ioapi", "stratbox.macrobanks", "stratbox.macrobanks.frg"):
    package(name)

class FakeDataFrame:
    def __init__(self, rows=None, columns=None):
        self.rows = list(rows or [])
    @property
    def empty(self):
        return not self.rows
    def to_dict(self, *, orient):
        assert orient == "records"
        return [dict(row) for row in self.rows]
    def __getitem__(self, columns):
        assert isinstance(columns, list)
        return FakeDataFrame([{name: item.get(name) for name in columns} for item in self.rows])

def module(name, **attrs):
    m = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(m, key, value)
    sys.modules[name] = m
    return m

module("pandas", DataFrame=FakeDataFrame)
module("stratbox.base.filestore", FileStore=object)
module("stratbox.base.runtime", get_filestore=lambda: None)
module("stratbox.base.ioapi.zip", write_zip_from_memory=lambda *a, **kw: None)
module("stratbox.macrobanks.frg.catalog", build_frg_catalog=lambda *a, **kw: None)
module("stratbox.macrobanks.frg.filename_scheme", build_internal_file_name=lambda *a, **kw: "")
module("stratbox.macrobanks.frg.selection", select_latest_frg_files=lambda *a, **kw: None)

spec = importlib.util.spec_from_file_location("stratbox.macrobanks.frg.cleanup", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError("FRG cleanup source unavailable")
cleanup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cleanup
spec.loader.exec_module(cleanup)

class FakeStore:
    def __init__(self, files, *, fail_copy=False, fail_rename=False):
        self.files = dict(files)
        self.fail_copy = fail_copy
        self.fail_rename = fail_rename
        self.removed = []
    def exists(self, path):
        return path in self.files
    def remove(self, path):
        self.removed.append(path)
        del self.files[path]
    def copy(self, src, dest):
        if self.fail_copy:
            raise IOError("injected copy interruption")
        self.files[dest] = self.files[src]
    def rename(self, src, dest):
        if self.fail_rename:
            raise IOError("injected rename interruption")
        self.files[dest] = self.files.pop(src)
    def read_bytes(self, path):
        return self.files[path]

def action(kind, src=None, dst=None, *, enabled=True):
    return {"action_type": kind, "source_path": src, "target_path": dst,
            "family_code": "synthetic", "family_name": "Synthetic",
            "will_execute": enabled}

class CleanupFaults(unittest.TestCase):
    def setUp(self):
        self.original_zip = cleanup.write_zip_from_memory
    def tearDown(self):
        cleanup.write_zip_from_memory = self.original_zip

    def test_copy_replacement_removes_prior_target_before_failed_copy(self):
        fs = FakeStore({"/src.xlsx": b"new", "/target.xlsx": b"old"}, fail_copy=True)
        result = cleanup.apply_frg_cleanup_plan(
            FakeDataFrame([action("copy_latest", "/src.xlsx", "/target.xlsx")]),
            filestore=fs, replace_existing=True,
        )
        self.assertEqual(result.rows[0]["status"], "error")
        self.assertEqual(fs.files["/src.xlsx"], b"new")
        self.assertNotIn("/target.xlsx", fs.files)
        self.assertEqual(fs.removed, ["/target.xlsx"])

    def test_rename_replacement_removes_prior_target_before_failed_rename(self):
        fs = FakeStore({"/src.xlsx": b"new", "/target.xlsx": b"old"}, fail_rename=True)
        result = cleanup.apply_frg_cleanup_plan(
            FakeDataFrame([action("rename_latest", "/src.xlsx", "/target.xlsx")]),
            filestore=fs, replace_existing=True,
        )
        self.assertEqual(result.rows[0]["status"], "error")
        self.assertNotIn("/target.xlsx", fs.files)
        self.assertIn("/src.xlsx", fs.files)

    def test_archive_replacement_removes_old_zip_before_failed_write(self):
        fs = FakeStore({"/latest.xlsx": b"latest", "/old.zip": b"old_archive"})
        def failed_zip(*args, **kwargs):
            raise IOError("injected archive write failure")
        cleanup.write_zip_from_memory = failed_zip
        result = cleanup.apply_frg_cleanup_plan(
            FakeDataFrame([
                action("keep_latest", "/latest.xlsx", "/latest.xlsx", enabled=False),
                action("create_archive", None, "/old.zip"),
            ]),
            filestore=fs,
        )
        self.assertEqual(result.rows[-1]["status"], "error")
        self.assertNotIn("/old.zip", fs.files)
        self.assertIn("/latest.xlsx", fs.files)

    def test_skipped_copy_can_archive_prior_target_instead_of_latest_source(self):
        fs = FakeStore({"/source.xlsx": b"new", "/standard.xlsx": b"old"})
        captured = {}
        def successful_zip(path, members, *, store):
            captured.update(members)
            store.files[path] = b"zip"
        cleanup.write_zip_from_memory = successful_zip
        result = cleanup.apply_frg_cleanup_plan(
            FakeDataFrame([
                action("copy_latest", "/source.xlsx", "/standard.xlsx"),
                action("create_archive", None, "/bundle.zip"),
            ]),
            filestore=fs, replace_existing=False,
        )
        self.assertEqual([r["status"] for r in result.rows], ["skipped", "done"])
        self.assertEqual(captured["standard.xlsx"], b"old")
        self.assertEqual(fs.files["/source.xlsx"], b"new")

    def test_direct_apply_trusts_mutating_plan_rows_not_recognition_policy(self):
        fs = FakeStore({"/protected.txt": b"non_Frg"})
        result = cleanup.apply_frg_cleanup_plan(
            FakeDataFrame([action("delete_source", "/protected.txt")]),
            filestore=fs,
        )
        self.assertEqual(result.rows[0]["status"], "done")
        self.assertNotIn("/protected.txt", fs.files)
        # The normal plan BUILDER applies recognized-file restrictions.
        # Direct APPLY on an externally supplied row does not recheck it.

if __name__ == "__main__":
    unittest.main(verbosity=2)
