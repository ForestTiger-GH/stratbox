"""Admission separates inert declarations, typed schemas and callable handlers."""
from dataclasses import dataclass, replace
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.operations import OperationCatalog, OperationRef
from stratbox.operations.declarations import validate_request_contract
from stratbox.shared.data.operations import InputPort, OperationSemantics, OutputPort, ProcessingStage, RequestField
from stratbox.shared.data.processing import DataContract
from stratbox.operations import operation_catalog


@dataclass(frozen=True)
class Request:
    value: int
    semantic_option: int = 1


@dataclass(frozen=True)
class Settings:
    factor: float = 2.0
    destination: str = "output.csv"
    progress: str = "quiet"


@dataclass(frozen=True)
class NestedRequest:
    settings: Settings


def test_unclassified_initialized_field_is_rejected_before_handler_import():
    definition = OperationDefinition("test.classification", "multiply", Request, int,
                                    request_fields=(RequestField("value", "parameter"),))
    catalog = OperationCatalog((OperationRef(definition.operation_id, "missing.handler:run", definition=definition),))
    with pytest.raises(ValueError, match="registry.request_field_unclassified:semantic_option"):
        catalog.get(definition.operation_id)


def test_nested_semantic_effect_and_observability_fields_are_covered_exactly():
    definition = OperationDefinition("test.nested", "multiply", NestedRequest, int,
        request_fields=(RequestField("settings.factor", "parameter"),
                        RequestField("settings.destination", "effect"),
                        RequestField("settings.progress", "observability")))
    validate_request_contract(definition, require_classification=True)
    broken = replace(definition, request_fields=definition.request_fields[:-1])
    with pytest.raises(ValueError, match="registry.request_field_unclassified:settings.progress"):
        validate_request_contract(broken, require_classification=True)


def test_nonexistent_typed_port_path_is_not_admitted():
    schema = DataContract("test.value", 1)
    definition = OperationDefinition("test.path", "read", Request, int,
        request_fields=(RequestField("value", "parameter"), RequestField("semantic_option", "parameter")),
        processing=OperationSemantics((ProcessingStage.EXTRACT,),
            inputs=(InputPort("value", schema, path="missing"),),
            outputs=(OutputPort("value", schema),), summary="Read an integer."))
    with pytest.raises(ValueError, match="registry.type_path_unavailable:missing"):
        validate_request_contract(definition)


def test_static_unknown_requirement_source_is_rejected_without_typed_loading(monkeypatch):
    from stratbox.domains.registry import requirements
    catalog = operation_catalog()
    original = requirements.declared_requirements
    known = original("cbr.sors.prepare_inputs")
    changed = (replace(known[0], source_ids=("unknown.publisher.series",)), *known[1:])
    monkeypatch.setattr(requirements, "declared_requirements", lambda operation:
                        changed if operation == "cbr.sors.prepare_inputs" else original(operation))
    with pytest.raises(ValueError, match="registry.source_requirement_source_unknown"):
        catalog.admit(level="metadata", refresh=True)


def test_admission_levels_report_distinct_proofs_and_stable_identities():
    catalog = operation_catalog()
    metadata = catalog.admit(level="metadata")
    typed = catalog.admit(level="typed")
    executable = catalog.admit(level="executable")
    assert metadata.semantic_registry_identity == typed.semantic_registry_identity == executable.semantic_registry_identity
    assert metadata.source_resource_identity == typed.source_resource_identity
    assert metadata.implementation_identity is None
    assert typed.implementation_identity == executable.implementation_identity
    assert len(metadata.source_ids) == 90
    assert len(typed.operation_ids) == len(catalog.references)
    assert any(check.responsibility == "semantic_fixtures" and check.state == "not_run" for check in typed.checks)
    assert any(check.responsibility == "executable_handlers" for check in executable.checks)


def test_relocation_changes_resource_identity_and_preserves_semantic_identity(monkeypatch, tmp_path):
    from stratbox.core import resources
    catalog = operation_catalog()
    before = catalog.admit(level="metadata")
    root = tmp_path / "registry"
    shutil.copytree(Path(str(resources.registry_root())), root)
    original = next(root.rglob("OPERATION_workbook.extract.yaml"))
    moved = original.parent / "physical" / original.name
    moved.parent.mkdir()
    original.rename(moved)
    monkeypatch.setattr(resources, "registry_root", lambda: root)
    after = catalog.admit(level="metadata", refresh=True)
    assert after.source_resource_identity != before.source_resource_identity
    assert after.semantic_registry_identity == before.semantic_registry_identity


def test_metadata_pages_and_admission_import_no_domains_or_optional_engines():
    code = '''
import importlib.abc,sys
class RejectImplementation(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("stratbox.domains.","pandas","openpyxl","highspy","requests")) and not fullname.startswith("stratbox.domains.registry"):
            raise AssertionError("Unexpected metadata import: " + fullname)
sys.meta_path.insert(0, RejectImplementation())
from stratbox.operations import operation_catalog
catalog=operation_catalog()
assert catalog.admit(level="metadata").admitted
assert len(catalog.describe()) == len(catalog.references)
assert catalog.page(limit=2).entries
'''
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run([sys.executable, "-B", "-c", code], env=dict(os.environ, PYTHONPATH=str(root / "src")),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@dataclass(frozen=True)
class ContextCarrier:
    value: int
    source_context: tuple[str, ...] = ()


def test_output_context_carrier_paths_are_declared_and_typed():
    schema = DataContract("test.value", 1)
    output = OutputPort("value", schema, path="value", source_policy="primary_source_required",
                        source_context_path="source_context")
    definition = OperationDefinition("test.context_carrier", "read", Request, (ContextCarrier, int),
        request_fields=(RequestField("value", "parameter"), RequestField("semantic_option", "parameter")),
        processing=OperationSemantics((ProcessingStage.EXTRACT,), outputs=(output,), summary="Read a typed carrier."))
    validate_request_contract(definition)
    broken = replace(definition, processing=replace(definition.processing,
        outputs=(replace(output, source_context_path="missing"),)))
    with pytest.raises(ValueError, match="registry.output_context_path_unavailable:value"):
        validate_request_contract(broken)
    with pytest.raises(ValueError, match="processing.invalid_path"):
        replace(output, source_context_path="source_context.__dict__")


def test_inline_prototype_cannot_claim_typed_admission_without_field_classification():
    definition = OperationDefinition("test.inline_prototype", "multiply", Request, int)
    catalog = OperationCatalog((OperationRef(definition.operation_id, "missing.handler:run", definition=definition),))
    assert catalog.get(definition.operation_id) is definition
    assert catalog.admit(level="metadata").admitted
    with pytest.raises(ValueError, match="registry.request_field_unclassified:value"):
        catalog.admit(level="typed")
    with pytest.raises(ValueError, match="registry.request_field_unclassified:value"):
        catalog.admit(level="executable")


@pytest.mark.parametrize("reference,code", [
    ("cbr.missing.operation", "registry.value_context_requirements_unknown"),
    ("invalid reference", "registry.value_context_requirements_invalid"),
    ("cbr.empty.roles", "registry.value_context_requirements_empty"),
    ("other.roles", "registry.value_context_requirements_owner_mismatch"),
])
def test_context_requirement_references_are_bounded_owner_checked_metadata_links(reference, code):
    from stratbox.operations.admission import _context_requirement_links
    records = ({"owner_id": "cbr", "value_contexts": {"types": {
        "example.ContextCarrier": {"requirements_ref": reference}}}},
        {"schema": "stratbox.operation", "owner_id": "cbr",
         "definition": {"operation_id": "cbr.empty.roles"}},
        {"schema": "stratbox.operation", "owner_id": "other",
         "definition": {"operation_id": "other.roles"}, "source_requirements": [{"input_name": "source"}]})
    with pytest.raises(ValueError, match=code):
        _context_requirement_links(records)


def test_core_typed_admission_resolves_global_context_role_owners():
    from stratbox.operations import core_catalog
    admission = core_catalog().admit(level="typed")
    assert admission.level == "typed"
    assert all(operation.startswith(("source.", "material.", "dataset.", "notifications.", "workbook.", "document.", "observations.", "processing."))
               for operation in admission.operation_ids)
    assert any(check.responsibility == "context_requirement_links" and check.count > 0 for check in admission.checks)
