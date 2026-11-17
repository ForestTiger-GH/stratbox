"""Historical Git links are evidence locators, not current source aliases."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.check_pinned_source_links import pinned_links, validate_pinned_links


def test_revision_pinned_links_keep_exact_paths():
    revision = "a" * 40
    source = f"Read [source](https://github.com/ForestTiger-GH/stratbox/blob/{revision}/src/stratbox/base/net/http.py#L10-L20) here."
    assert list(pinned_links(source)) == [(revision, "src/stratbox/base/net/http.py", 1)]


def test_missing_historical_path_is_reported(monkeypatch, tmp_path):
    revision = "b" * 40
    document = tmp_path / "current-how.md"
    document.write_text(
        f"[old](https://github.com/ForestTiger-GH/stratbox/blob/{revision}/src/stratbox/system/base/net/http.py)",
        encoding="utf-8",
    )
    checked = []

    def fake_run(args, **kwargs):
        checked.append(args)
        return SimpleNamespace(returncode=1, stdout="", stderr="absent")

    monkeypatch.setattr("scripts.check_pinned_source_links.subprocess.run", fake_run)
    issues = validate_pinned_links([document], repository=tmp_path)
    assert len(issues) == 1
    assert "pinned source absent" in issues[0]
    assert checked[0][-1].endswith(":src/stratbox/system/base/net/http.py")


def test_existing_historical_object_is_accepted(monkeypatch, tmp_path):
    revision = "c" * 40
    document = tmp_path / "sources.md"
    link = f"https://github.com/ForestTiger-GH/stratbox/blob/{revision}/src/stratbox/base/net/http.py"
    document.write_text(f"[first]({link})\n[again]({link})", encoding="utf-8")
    called = []

    def fake_run(args, **kwargs):
        called.append(args)
        return SimpleNamespace(returncode=0, stdout="blob\n", stderr="")

    monkeypatch.setattr("scripts.check_pinned_source_links.subprocess.run", fake_run)
    assert validate_pinned_links([document], repository=tmp_path) == []
    assert len(called) == 1
