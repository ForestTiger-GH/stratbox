"""Distribution completeness follows real manifests and packaged source bytes."""

from pathlib import Path
import runpy

import pytest


def _inspector():
    root = Path(__file__).resolve().parents[3]
    return runpy.run_path(str(root / "scripts" / "inspect_reference_wheel.py"))


def _real_members(source: Path):
    return {
        "stratbox/domains/" + entry.relative_to(source).as_posix()
        for entry in source.rglob("*") if entry.is_file()
    }


def _read_from_source(source: Path):
    def read(member: str) -> bytes:
        return (source / member.removeprefix("stratbox/domains/")).read_bytes()
    return read


def test_every_packaged_domain_manifest_and_data_asset_is_verified():
    check = _inspector()
    source = check["DOMAIN_SOURCE"]
    expected = _real_members(source)
    report = check["_verify_domain_members"](expected, "", _read_from_source(source))
    assert report["owners"] > 0
    assert report["data_files"] >= 1


def test_omitted_registration_is_rejected():
    check = _inspector()
    source = check["DOMAIN_SOURCE"]
    members = _real_members(source)
    manifest = next(name for name in members if name.endswith("/_registration.py"))
    members.remove(manifest)
    with pytest.raises(ValueError, match="missing_owners"):
        check["_verify_domain_members"](members, "", _read_from_source(source))


def test_every_sors_csv_is_required_not_just_any_one():
    check = _inspector()
    source = check["DOMAIN_SOURCE"]
    files = _real_members(source)
    names = sorted(name for name in files if "/sors_restoration/crosswalk/_resources/" in name
                   and name.endswith(".csv"))
    assert len(names) >= 3
    for missing in names:
        with pytest.raises(ValueError, match="missing_data"):
            check["_verify_domain_members"](files - {missing}, "", _read_from_source(source))


def test_corrupted_domain_model_is_rejected_by_hash():
    check = _inspector()
    source = check["DOMAIN_SOURCE"]
    files = _real_members(source)
    victim = next(name for name in files if "/reporting_forms/models/form" in name
                  and name.endswith(".csv"))

    def corrupted(member: str) -> bytes:
        if member == victim:
            return b"corrupted"
        return _read_from_source(source)(member)

    with pytest.raises(ValueError, match="changed_data"):
        check["_verify_domain_members"](files, "", corrupted)


def test_new_owner_is_automatically_required_from_source(tmp_path):
    check = _inspector()
    source = tmp_path / "domains"
    source.mkdir()
    (source / "__init__.py").write_text("", encoding="utf-8")
    parent = source / "another_publisher" / "family" / "series"
    parent.mkdir(parents=True)
    for current in (source / "another_publisher",
                    source / "another_publisher" / "family", parent):
        (current / "__init__.py").write_text("", encoding="utf-8")
    (parent / "_registration.py").write_text("", encoding="utf-8")
    check["_verify_domain_members"].__globals__["DOMAIN_SOURCE"] = source
    with pytest.raises(ValueError, match="missing_owners"):
        check["_verify_domain_members"](
            {"stratbox/domains/__init__.py"}, "", _read_from_source(source)
        )


def test_new_non_csv_domain_asset_is_included_automatically(tmp_path):
    check = _inspector()
    source = tmp_path / "domains"
    source.mkdir()
    (source / "__init__.py").write_text("", encoding="utf-8")
    owner = source / "publisher" / "survey"
    owner.mkdir(parents=True)
    (source / "publisher" / "__init__.py").write_text("", encoding="utf-8")
    (owner / "__init__.py").write_text("", encoding="utf-8")
    (owner / "_registration.py").write_text("", encoding="utf-8")
    data = owner / "raw-series.parquet"
    data.write_bytes(b"future domain binary asset")
    check["_verify_domain_members"].__globals__["DOMAIN_SOURCE"] = source
    files = _real_members(source)
    member = "stratbox/domains/publisher/survey/raw-series.parquet"
    with pytest.raises(ValueError, match="missing_data"):
        check["_verify_domain_members"](
            files - {member}, "", _read_from_source(source)
        )
    actual = check["_verify_domain_members"](
        files, "", _read_from_source(source)
    )
    assert actual["data_files"] == 1


def test_changed_owner_manifest_content_is_rejected():
    check = _inspector()
    source = check["DOMAIN_SOURCE"]
    files = _real_members(source)
    victim = next(name for name in files if name.endswith("/_registration.py"))

    def corrupted(member: str) -> bytes:
        if member == victim:
            return b"REGISTRATION = None\n"
        return _read_from_source(source)(member)

    with pytest.raises(ValueError, match="changed_owners"):
        check["_verify_domain_members"](files, "", corrupted)


def test_generated_hidden_cache_files_are_excluded_from_domain_inventory():
    check = _inspector()
    assert not check["_domain_asset"](".pytest_cache/v/cache/nodeids")
    assert not check["_domain_asset"]("publisher/.hidden/CACHEDIR.TAG")
    assert not check["_domain_asset"]("publisher/__pycache__/module.pyc")
    assert check["_domain_asset"]("publisher/data/model.yml")
    assert check["_domain_asset"]("publisher/data/raw-source.parquet")
