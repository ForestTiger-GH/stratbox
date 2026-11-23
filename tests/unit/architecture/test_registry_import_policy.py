"""YAML declarations obey the same implementation ownership as Python imports."""

import copy
import json
from pathlib import Path
import runpy

import pytest


def _checker(tmp_path):
    root = Path(__file__).resolve().parents[3]
    tool = runpy.run_path(str(root / "scripts/check_internal_imports.py"))
    check = tool["check_registry_declarations"]
    package = tmp_path / "src/stratbox"
    check.__globals__["PACKAGE"] = package
    sample = root / "src/stratbox/operations/specifications/domains/cbr/operations/OPERATION_cbr.describe_source.yaml"
    return check, package, json.loads(sample.read_bytes())


def _owner(package, name):
    directory = package / "operations" / "specifications" / name
    directory.mkdir(parents=True)
    (directory / "OWNER.yaml").write_text(json.dumps({"owner_id": name}), encoding="utf-8")
    domain = package / "domains"
    for part in name.split("."):
        domain = domain / part
        domain.mkdir(parents=True, exist_ok=True)
        (domain / "__init__.py").write_text("", encoding="utf-8")
    return directory


def _operation(owner, value):
    operations = owner / "operations"
    operations.mkdir()
    (operations / "OPERATION_example.yaml").write_text(json.dumps(value), encoding="utf-8")


@pytest.mark.parametrize("role", ["handler_ref", "request_type", "value_type"])
def test_declaration_cannot_escape_its_domain_owner(tmp_path, role):
    check, package, sample = _checker(tmp_path)
    owner = _owner(package, "cbr")
    document = copy.deepcopy(sample)
    container = document["implementation"] if role == "handler_ref" else document["definition"]
    container[role] = "stratbox.domains.fns.operations:Foreign"
    _operation(owner, document)
    assert any("reference_ownership" in failure for failure in check())


def test_yaml_handler_belongs_to_the_nearest_registered_owner(tmp_path):
    check, package, sample = _checker(tmp_path)
    owner = _owner(package, "cbr")
    _owner(package, "cbr.family")
    document = copy.deepcopy(sample)
    document["implementation"]["handler_ref"] = "stratbox.domains.cbr.family.operations:handle"
    _operation(owner, document)
    assert any("nearest operation owner mismatch" in failure for failure in check())


def test_duplicate_json_keys_are_not_accepted_as_registry_metadata(tmp_path):
    check, package, _ = _checker(tmp_path)
    owner = _owner(package, "cbr")
    operations = owner / "operations"
    operations.mkdir()
    (operations / "OPERATION_invalid.yaml").write_text('{"owner_id":"cbr","owner_id":"fns"}',
                                                       encoding="utf-8")
    assert any("invalid registry declaration" in failure for failure in check())
