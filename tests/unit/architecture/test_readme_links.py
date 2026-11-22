"""Offline, path-sensitive README link checks."""

from pathlib import Path
import runpy


def _checker():
    script = Path(__file__).resolve().parents[3] / "scripts/check_readme_links.py"
    return runpy.run_path(str(script))


def test_maintained_package_readme_links_resolve():
    checker = _checker()
    assert checker["check_links"]() == []


def test_broken_link_at_nested_depth_is_detected(tmp_path):
    checker = _checker()
    package = tmp_path / "src/stratbox/domains/cbr/series"
    package.mkdir(parents=True)
    (package / "README.md").write_text(
        "# Series\n\n[missing](../../../../../docs/missing.md)\n",
        encoding="utf-8",
    )
    issues = checker["check_links"](tmp_path / "src/stratbox", repository=tmp_path)
    assert len(issues) == 1 and "missing link" in issues[0]


def test_external_and_fragment_links_are_ignored(tmp_path):
    checker = _checker()
    package = tmp_path / "src/stratbox"
    package.mkdir(parents=True)
    (package / "README.md").write_text(
        "[web](https://example.org/x) [section](#part) [email](mailto:a@b.org)\n",
        encoding="utf-8",
    )
    assert checker["check_links"](package, repository=tmp_path) == []


def test_relative_parent_link_and_url_encoding(tmp_path):
    checker = _checker()
    package = tmp_path / "src/stratbox"
    package.mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs"/"A B.md").write_text("test", encoding="utf-8")
    (package / "README.md").write_text("[file](../../docs/A%20B.md)", encoding="utf-8")
    assert checker["check_links"](package, repository=tmp_path) == []


def test_broken_maintained_document_link_is_detected(tmp_path):
    checker = _checker()
    readmes = tmp_path / "src" / "stratbox"
    readmes.mkdir(parents=True)
    docs = tmp_path / "docs" / "current-how"
    docs.mkdir(parents=True)
    (docs / "README.md").write_text("[broken](missing.md)", encoding="utf-8")
    failures = checker["check_links"](
        readmes, repository=tmp_path, documentation_roots=(docs,)
    )
    assert len(failures) == 1 and "missing link" in failures[0]


def test_archived_documents_are_outside_current_navigation(tmp_path):
    checker = _checker()
    readmes = tmp_path / "src" / "stratbox"
    readmes.mkdir(parents=True)
    archive = tmp_path / "docs_old"
    archive.mkdir()
    (archive / "README.md").write_text("[archive](old-link.md)", encoding="utf-8")
    assert checker["check_links"](readmes, repository=tmp_path) == []
