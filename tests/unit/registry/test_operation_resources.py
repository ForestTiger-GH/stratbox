"""Canonical metadata remains inert, complete and isolated from caller mutations."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from stratbox.operations.catalog import RegistryError
from stratbox.operations.declarations import (
    definition, operation_documents, owner_registration, validate_operation_document,
)


def _document():
    return next(item for item in operation_documents("core.processing")
                if item["definition"]["operation_id"] == "workbook.extract")


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(unrecognized=True),
    lambda d: d.update(schema_version=True),
    lambda d: d["definition"].update(contract_version=True),
    lambda d: d["definition"].update(required_capabilities=["http", "http"]),
    lambda d: d["definition"]["processing"]["inputs"][0].update(required="false"),
    lambda d: d["definition"]["processing"]["outputs"][0].update(outcomes=["failed"]),
    lambda d: d["definition"]["limits"].update(cells=1.5),
    lambda d: d["implementation"].update(handler_ref="stratbox.domains.cbr.operations.handlers:extract"),
    lambda d: d["definition"].update(request_type="stratbox.domains.fns.operations.contracts:ExtractRequest"),
])
def test_malformed_operation_metadata_fails_before_reference_resolution(mutate):
    document = _document()
    mutate(document)
    with pytest.raises(RegistryError):
        validate_operation_document(document, owner_id="core.processing")


def test_documents_cannot_change_admitted_contract_or_registration():
    expected = definition("workbook.extract")
    refs = owner_registration("core.processing").operations
    document = _document()
    document["definition"]["processing"]["inputs"][0]["path"] = "invented"
    document["definition"]["limits"]["cells"] = 0
    document["implementation"]["handler_ref"] = "invented.module:handler"
    assert definition("workbook.extract") == expected
    assert owner_registration("core.processing").operations == refs
    assert _document()["definition"]["processing"]["inputs"][0]["path"] == "payload"


def test_operation_document_preserves_named_role_contract_and_runtime_policy():
    document = _document()
    value = definition("workbook.extract")
    assert value.processing.inputs[0].name == "source"
    assert value.processing.inputs[0].path == "payload"
    assert value.processing.parameters == ("series_id", "issue_id", "asset_id")
    assert value.limits.cells == 80_000_000
    assert document["definition"]["request_type"].endswith(":ExtractRequest")


def test_declarative_discovery_never_loads_implementation_or_optional_engines():
    code = '''
import sys
from stratbox.operations.declarations import owner_ids, owner_registration
for owner in owner_ids():
    owner_registration(owner)
assert not any(name.startswith(("pandas", "openpyxl", "highspy", "requests")) for name in sys.modules)
assert not any(".handlers" in name for name in sys.modules)
assert not any((name.startswith("stratbox.domains.") and not name.startswith("stratbox.domains.registry")) for name in sys.modules)
'''
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[3] / "src"))
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
