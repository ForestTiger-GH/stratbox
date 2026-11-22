"""Discovery cannot acquire executable implementations or mutable schemas."""

from dataclasses import replace

import pytest

from stratbox.core.execution.catalog import OperationCatalog, RegistryError
from stratbox.core.execution.machine import wire_schemas
from stratbox.domains.registry import operation_catalog


def test_definition_and_schemas_remain_inspectable_with_an_unavailable_handler():
    ref = operation_catalog().reference("cbr.offices.parse", 1)
    catalog = OperationCatalog((replace(ref, handler_ref="uninstalled_engine:parse"),))
    assert catalog.get(ref.operation_id, 1).operation_id == ref.operation_id
    assert catalog.describe()[0]["machine_read_only"]
    assert wire_schemas(ref.operation_id, 1, catalog=catalog)[0]["required"]
    with pytest.raises(RegistryError, match="registry.unresolvable_reference"):
        catalog.resolve(ref.operation_id, 1)


def test_wire_contract_and_schema_results_have_no_shared_mutable_state():
    catalog = operation_catalog()
    contract = catalog.wire_contract("cbr.offices.parse", 1)
    contract.input_fields["capture_date"]["type"] = "boolean"
    assert contract.input_fields["capture_date"]["type"] == "string"
    request, _ = wire_schemas("cbr.offices.parse", 1, catalog=catalog)
    request["properties"]["input"]["properties"].clear()
    assert wire_schemas("cbr.offices.parse", 1, catalog=catalog)[0]["properties"]["input"]["properties"]


def test_machine_contract_and_codec_must_be_registered_together():
    ref = operation_catalog().reference("cbr.offices.parse", 1)
    with pytest.raises(RegistryError, match="registry.wire_contract_required"):
        replace(ref, wire_contract_ref=None)


def test_read_only_contract_cannot_advertise_effectful_work(monkeypatch):
    from stratbox.core.execution import catalog as implementation
    catalog = operation_catalog()
    parse = catalog.reference("cbr.offices.parse", 1)
    original_load = implementation._load
    definition = replace(catalog.get(parse.operation_id, 1), possible_effects=frozenset({"storage.write"}))
    monkeypatch.setattr(implementation, "_load", lambda ref: (
        definition if ref == "hypothetical.definitions:PARSE" else original_load(ref)
    ))
    forged = replace(parse, definition_ref="hypothetical.definitions:PARSE")
    with pytest.raises(RegistryError, match="registry.read_only_effects"):
        OperationCatalog((forged,)).describe()
