"""Logical identities survive directory grouping; every reader sees the same set."""
from pathlib import Path
import json

import pytest

from stratbox.core.registry import resources
from stratbox.core.registry.catalog import OperationCatalog, OperationRef
from stratbox.core.registry.operations import definition, validate_operation_document


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _minimal():
    return {"schema": "stratbox.operation", "owner_id": "core.processing",
            "definition": {"operation_id": "example.normalize", "method_id": "normalization",
                           "request_type": "builtins:str", "value_type": "builtins:str"},
            "implementation": {"handler_ref": "stratbox.core.operations.processing.handlers:extract_workbook"}}


def test_compact_schema_has_explicit_defaults_without_dataclass_field_inventory():
    value = _minimal()
    assert validate_operation_document(value, owner_id="core.processing") == value
    value["definition"]["internal_runtime_state"] = None
    with pytest.raises(ValueError, match="registry.invalid_document"):
        validate_operation_document(value)


def test_grouping_and_relocation_preserve_owner_and_record_identity(tmp_path):
    root = tmp_path / "registry"
    owner = root / "core" / "shared" / "processing"
    _write(owner / "OWNER.yaml", {"owner_id": "core.processing"})
    record = owner / "operations" / "workbooks" / "OPERATION_example.normalize.yaml"
    _write(record, _minimal())
    assert resources.resource_owners(root=root) == ("core.processing",)
    before = resources.iter_resources("core.processing", "operations", root=root)
    assert before == (record,)
    original = resources.read_document(before[0])
    relocated = record.parent / "extraction" / record.name
    relocated.parent.mkdir()
    record.rename(relocated)
    resources._discover.cache_clear()
    after = resources.iter_resources("core.processing", "operations", root=root)
    assert after == (relocated,)
    assert resources.read_document(after[0]) == original
    inventory = resources.resource_inventory(root=root)
    assert {name for name, _, _ in inventory} == {
        "core/shared/processing/OWNER.yaml",
        "core/shared/processing/operations/workbooks/extraction/OPERATION_example.normalize.yaml",
    }


def test_orphan_records_fail_for_both_owner_discovery_and_distribution(tmp_path):
    root = tmp_path / "registry"
    _write(root / "domains" / "orphan" / "operations" / "OPERATION_example.normalize.yaml", _minimal())
    for discover in (resources.resource_owners, resources.resource_inventory):
        with pytest.raises(ValueError, match="registry.unowned_resource"):
            discover(root=root)


def test_duplicate_explicit_owner_is_rejected_across_grouping_paths(tmp_path):
    root = tmp_path / "registry"
    for group in ("first", "second"):
        _write(root / group / "OWNER.yaml", {"owner_id": "core.processing"})
    with pytest.raises(ValueError, match="registry.duplicate_owner"):
        resources.resource_owners(root=root)


def test_canonical_definition_is_independent_of_python_projection_and_handler(monkeypatch):
    from stratbox.core.registry import catalog as catalog_module
    from stratbox.core.operations.processing import definitions as projections
    expected = definition("workbook.extract")
    monkeypatch.setattr(projections, "WORKBOOK", object())
    monkeypatch.setattr(catalog_module, "_load", lambda ref: (_ for _ in ()).throw(AssertionError(ref)))
    catalog_module._definition.cache_clear()
    catalog = OperationCatalog((OperationRef("workbook.extract", "unavailable.engine:extract"),))
    from dataclasses import replace
    assert catalog.get("workbook.extract") == replace(expected, method_refs=("unavailable.engine:extract",))


def test_zip_package_root_and_discovery_are_reused_without_rescanning(monkeypatch, tmp_path):
    from importlib.resources import files as package_files
    import sys
    from zipfile import ZipFile

    package = "stratbox_registry_zip_fixture"
    archive = tmp_path / "registry.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr(package + "/__init__.py", "")
        bundle.writestr(package + "/core/processing/OWNER.yaml",
                        json.dumps({"owner_id": "core.processing"}))
        bundle.writestr(package + "/core/processing/operations/OPERATION_example.normalize.yaml",
                        json.dumps(_minimal()))
    monkeypatch.syspath_prepend(str(archive))
    monkeypatch.setattr(resources, "files", lambda _: package_files(package))
    resources.registry_root.cache_clear()
    resources._discover.cache_clear()
    try:
        root = resources.registry_root()
        assert resources.registry_root() is root
        assert resources.resource_owners() == ("core.processing",)
        assert len(resources.iter_resources("core.processing", "operations")) == 1
        assert len(resources.resource_inventory()) == 2
        assert resources._discover.cache_info().misses == 1
        assert resources._discover.cache_info().hits >= 2
    finally:
        resources.registry_root.cache_clear()
        resources._discover.cache_clear()
        sys.modules.pop(package, None)
