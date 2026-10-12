#!/usr/bin/env python3
"""Execute bounded current LocalFileStore semantics in disposable temp directories.
Source-loaded, no external providers/network, never writes outside an owned test temp.
These are CURRENT behavior tests, not a security/host acceptance suite.
"""
from __future__ import annotations
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "src/stratbox/base/filestore"
for name in ("stratbox", "stratbox.base", "stratbox.base.filestore"):
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod

def load(part):
    name = "stratbox.base.filestore." + part
    spec = importlib.util.spec_from_file_location(name, SOURCE / (part + ".py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Source missing " + part)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

types_module = load("types")
base_module = load("base")
local_module = load("local")
tmp_module = load("tmp")

class FileStoreBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sb-fs-proof-")
        self.addCleanup(self.temp.cleanup)
        self.top = Path(self.temp.name)
        self.allowed = self.top / "assigned"
        self.allowed.mkdir()
        self.store = local_module.LocalFileStore(root=str(self.allowed))

    def test_parent_traversal_not_confined_by_root(self):
        outside = self.top / "outside.bin"
        outside.write_bytes(b"prior")
        self.store.write_bytes("../outside.bin", b"replacement")
        self.assertEqual(outside.read_bytes(), b"replacement")

    def test_absolute_path_bypasses_root(self):
        outside = self.top / "absolute.bin"
        outside.write_bytes(b"prior")
        self.store.write_bytes(str(outside), b"absolute")
        self.assertEqual(outside.read_bytes(), b"absolute")

    def test_symlink_from_root_follows_outside_target(self):
        destination = self.top / "other-dir"
        destination.mkdir()
        (self.allowed / "link").symlink_to(destination, target_is_directory=True)
        self.store.write_bytes("link/outside.bin", b"through-link")
        self.assertEqual((destination / "outside.bin").read_bytes(), b"through-link")

    def test_missing_empty_and_wrong_type_listdir_are_identical(self):
        (self.allowed / "empty").mkdir()
        (self.allowed / "file").write_bytes(b"body")
        self.assertEqual(self.store.listdir("missing"), [])
        self.assertEqual(self.store.listdir("empty"), [])
        self.assertEqual(self.store.listdir("file"), [])
        self.assertEqual(list(self.store.walk("missing")), [])
        self.assertEqual(list(self.store.walk("file")), [])

    def test_writer_interruption_leaves_truncated_partial_target(self):
        prior = self.allowed / "report.xlsx"
        prior.write_bytes(b"original complete historical bytes")
        with self.assertRaisesRegex(OSError, "injected"):
            with self.store.open_write("report.xlsx") as handle:
                handle.write(b"incomplete")
                raise OSError("injected writer interruption")
        self.assertEqual(prior.read_bytes(), b"incomplete")

if __name__ == "__main__":
    unittest.main(verbosity=2)
