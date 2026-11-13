from types import SimpleNamespace

import pytest

from stratbox.base import runtime
from stratbox.base.ioapi import bytes as files
from stratbox.base.runtime import local_providers


@pytest.fixture
def provider_environment(monkeypatch, tmp_path):
    package = tmp_path / "src/stratbox/base/runtime.py"
    package.parent.mkdir(parents=True)
    monkeypatch.setattr(runtime, "__file__", str(package))
    runtime._discover_providers.cache_clear()
    yield tmp_path / "src"
    runtime._discover_providers.cache_clear()


def test_local_providers_have_independent_configuration(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    one = local_providers(root=str(left))
    two = local_providers(root=str(right))
    one.filestore.write_bytes("source.bin", b"one")
    two.filestore.write_bytes("source.bin", b"two")
    assert one.filestore.read_bytes("source.bin") == b"one"
    assert two.filestore.read_bytes("source.bin") == b"two"
    assert one.http is not two.http


def test_discovered_default_is_cached_and_explicit_store_overrides_it(monkeypatch, provider_environment, tmp_path):
    bundle = local_providers(root=str(tmp_path / "default"))
    explicit = local_providers(root=str(tmp_path / "explicit"))
    calls = []

    def create():
        calls.append(True)
        return bundle

    entry = SimpleNamespace(value="example.runtime:create", load=lambda: create)
    monkeypatch.setattr(runtime, "entry_points", lambda **filters: [entry])
    assert files.write_bytes("report.bin", b"default").status == "stored"
    assert files.write_bytes("report.bin", b"explicit", store=explicit.filestore).status == "stored"
    assert files.read_bytes("report.bin") == b"default"
    assert explicit.filestore.read_bytes("report.bin") == b"explicit"
    assert len(calls) == 1


def test_conflicting_defaults_fail_before_any_write(monkeypatch, provider_environment, tmp_path):
    monkeypatch.chdir(tmp_path)
    entries = [SimpleNamespace(value=f"{module}:create") for module in ("example.one", "example.two")]
    monkeypatch.setattr(runtime, "entry_points", lambda **filters: entries)
    with pytest.raises(runtime.RuntimeProviderError, match="provider.binding_conflict"):
        files.write_bytes("report.bin", b"unexpected")
    assert not (tmp_path / "report.bin").exists()


@pytest.mark.parametrize("path", [
    r'"F:\Reports\example.xlsm"',
    r"\\?\F:\Reports\example.xlsm",
    "file:///F:/Reports/example%2Exlsm",
    "smb://files.example/Reports/example.XLSM",
])
def test_excel_selects_the_format_for_copied_file_paths(path):
    from stratbox.base.ioapi.excel import _ext

    assert _ext(path) == ".xlsm"
