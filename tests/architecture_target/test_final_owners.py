"""Architecture acceptance is independent of the existence of old declarations."""
from dataclasses import fields, is_dataclass
from importlib import import_module
import json
from pathlib import Path
from collections.abc import Mapping
import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'src' / 'stratbox'


def identities(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return set()
    seen.add(id(value))
    result = set()
    identity = getattr(value, 'id', None)
    if isinstance(identity, str):
        result.add(identity)
    if is_dataclass(value):
        for item in fields(value):
            result.update(identities(getattr(value, item.name), seen))
    elif isinstance(value, Mapping):
        for item in value.values():
            result.update(identities(item, seen))
    elif isinstance(value, (tuple, list)):
        for item in value:
            result.update(identities(item, seen))
    return result


def test_each_commissioned_source_has_a_final_domain_record():
    from stratbox.capabilities.catalog.domains import load_domains
    domains = load_domains().domains
    expected = json.loads(Path(__file__).with_name('source_scope.json').read_text())
    assert set(domains) == set(expected)
    for domain_id, source_ids in expected.items():
        assert set(source_ids) <= identities(domains[domain_id]), domain_id


def test_retired_runtime_owners_are_removed():
    for name in ('operations', 'composition', 'domains/registry', 'core/operations', 'core/capabilities'):
        assert not (PACKAGE / name).exists(), name
    assert not list((PACKAGE / 'domains').rglob('profiles.py'))
    for domain in (PACKAGE/'domains').iterdir():
        if domain.is_dir():
            for owner in ('operations','capabilities','publications','tables','integration','analytics'):
                assert not (domain/owner).exists(),str(domain/owner)


def test_internal_import_and_owner_rules():
    from scripts.check_internal_imports import check_source
    assert check_source() == []


def test_metadata_imports_do_not_require_optional_numerical_backends():
    import subprocess, sys
    program = '''
import sys
from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.catalog.domains import load_domains
catalog, domains = standard_catalog(), load_domains()
assert catalog.definitions and len(domains.domains) == 5
assert not {'pandas', 'numpy', 'openpyxl', 'highspy'} & sys.modules.keys()
'''
    completed = subprocess.run([sys.executable, '-c', program],cwd=ROOT,capture_output=True,text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_no_component_release_counters_in_authored_public_models():
    from stratbox.capabilities.model.domains import DomainSpec, SeriesSpec, CommandSpec
    from stratbox.capabilities.model.definitions import CommandDefinition
    banned = {'revision','version','schema_version','profile_version','method_version','rules_version'}
    for cls in (DomainSpec,SeriesSpec,CommandSpec,CommandDefinition):
        assert not {field.name for field in fields(cls)} & banned
