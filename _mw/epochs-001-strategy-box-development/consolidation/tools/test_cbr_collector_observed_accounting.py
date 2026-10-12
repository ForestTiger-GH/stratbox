#!/usr/bin/env python3
"""Isolated executable characterization of the frozen public CBR collector.
No network, credentials, installed third-party libraries or deployment dependencies.
Tests record CURRENT behavior, including limitations; they are not acceptance tests.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PKG = ROOT / "src/stratbox/macrobanks/cbr_file_collector"
N = "stratbox.macrobanks.cbr_file_collector"


def package(name: str) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


for n in ("stratbox", "stratbox.base", "stratbox.macrobanks", N):
    package(n)

network = types.ModuleType("stratbox.base.net")
network.download_bytes = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("Network forbidden"))
sys.modules[network.__name__] = network

file_store = types.ModuleType("stratbox.base.filestore")
file_store.FileStore = object
sys.modules[file_store.__name__] = file_store

runtime = types.ModuleType("stratbox.base.runtime")
runtime.get_filestore = lambda: object()
sys.modules[runtime.__name__] = runtime

save = types.ModuleType(N + ".save")
save.save_downloaded_sources = lambda downloaded, *, target_path, save_mode, store, overwrite: (
    target_path, (target_path,), tuple(downloaded),
)
sys.modules[save.__name__] = save


def load(name: str):
    fullname = N + "." + name
    spec = importlib.util.spec_from_file_location(fullname, PKG / (name + ".py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Collector module missing " + name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = mod
    spec.loader.exec_module(mod)
    return mod


contracts = load("contracts")
registry = load("registry")
filenames = load("file_names")
downloader = load("downloader")
operations = load("operations")


class CollectorObservedTests(unittest.TestCase):
    def setUp(self):
        self.calls: list[str] = []
        self.original_downloader = downloader.download_bytes

    def tearDown(self):
        downloader.download_bytes = self.original_downloader

    def response(self, ok=False, content=None, url="", headers=None):
        return types.SimpleNamespace(
            ok=ok, content=content, error=None if ok else "synthetic unavailable",
            status_code=200 if ok else 503, final_url=url,
            headers=headers or {},
        )

    def test_empty_registry_returns_success_without_any_result_file(self):
        downloader.download_bytes = lambda *a, **kw: self.fail("unexpected network")
        result = operations.collect_cbr_files(
            contracts.CbrFileCollectRequest(
                target_path="unused.zip", show_progress=False,
            ),
            registry=(),
            filestore=object(),
        )
        self.assertEqual((result.requested_count, result.success_count, result.failure_count), (0, 0, 0))
        self.assertTrue(result.ok)
        self.assertEqual(result.saved_paths, ())

    def test_stop_on_first_failure_leaves_unattempted_sources_out_of_failure_list(self):
        def fake(url, **kwargs):
            self.calls.append(url)
            return self.response(url=url)
        downloader.download_bytes = fake
        sources = tuple(contracts.CbrFileRegistryItem(f"source-{i}", f"https://example.invalid/{i}.xlsx") for i in range(3))
        result = operations.collect_cbr_files(
            contracts.CbrFileCollectRequest(
                target_path="unused.zip", continue_on_error=False,
                retry_attempts=1, try_case_variants=False, show_progress=False,
            ),
            registry=sources,
            filestore=object(),
        )
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((result.requested_count, result.success_count, result.failure_count), (3, 0, 1))
        self.assertEqual([f.source_id for f in result.failures], ["source-0"])
        self.assertEqual(result.requested_count - result.success_count - result.failure_count, 2)

    def test_outer_retry_counter_is_not_count_of_variant_http_calls(self):
        def fake(url, **kwargs):
            self.calls.append(url)
            return self.response(url=url)
        downloader.download_bytes = fake
        source = contracts.CbrFileRegistryItem(
            "variants", "https://example.invalid/BankSector/Mortgage/Loans_to_corporations/a.xlsx"
        )
        result = downloader.download_one_source(
            source, retry_attempts=2, retry_backoff_sec=0, try_case_variants=True,
        )
        self.assertIsInstance(result, contracts.CbrFileCollectFailure)
        self.assertEqual(result.attempts_used, 2)
        self.assertEqual(len(downloader.build_cbr_url_variants(source.url)), 8)
        self.assertEqual(len(self.calls), 16)

    def test_non_html_response_is_not_verified_spreadsheet(self):
        body = b'{"error":"synthetic"}' + b" " * 600
        downloader.download_bytes = lambda url, **kw: self.response(
            ok=True, content=body, url=url, headers={"Content-Type": "application/json"}
        )
        source = contracts.CbrFileRegistryItem("json-response", "https://example.invalid/file.xlsx")
        result = downloader.download_one_source(source, retry_attempts=1, try_case_variants=False)
        self.assertIsInstance(result, contracts.CbrDownloadedFileSource)
        self.assertEqual(result.content, body)
        self.assertEqual(result.size_bytes, len(body))


if __name__ == "__main__":
    unittest.main(verbosity=2)
