"""Discovery cannot acquire executable implementations or mutable schemas."""

from dataclasses import replace

import pytest

from stratbox.operations.catalog import OperationCatalog, RegistryError
from stratbox.core.execution.machine import wire_schemas
from stratbox.operations import operation_catalog


def test_definition_and_schemas_remain_inspectable_with_an_unavailable_handler():
    ref = operation_catalog().reference("cbr.offices.parse")
    catalog = OperationCatalog((replace(ref, handler_ref="uninstalled_engine:parse"),))
    assert catalog.get(ref.operation_id).operation_id == ref.operation_id
    assert catalog.describe()[0]["machine_read_only"]
    assert wire_schemas(ref.operation_id, catalog=catalog)[0]["required"]
    with pytest.raises(RegistryError, match="registry.unresolvable_reference"):
        catalog.resolve(ref.operation_id)


def test_wire_contract_and_schema_results_have_no_shared_mutable_state():
    catalog = operation_catalog()
    contract = catalog.wire_contract("cbr.offices.parse")
    contract.input_fields["capture_date"]["type"] = "boolean"
    assert contract.input_fields["capture_date"]["type"] == "string"
    request, _ = wire_schemas("cbr.offices.parse", catalog=catalog)
    request["properties"]["input"]["properties"].clear()
    assert wire_schemas("cbr.offices.parse", catalog=catalog)[0]["properties"][
        "input"
    ]["properties"]


def test_machine_contract_and_codec_must_be_registered_together():
    ref = operation_catalog().reference("cbr.offices.parse")
    with pytest.raises(RegistryError, match="registry.wire_contract_required"):
        replace(ref, wire_contract_ref=None)


def test_read_only_contract_cannot_advertise_effectful_work(monkeypatch):
    from stratbox.operations import catalog as implementation

    catalog = operation_catalog()
    parse = catalog.reference("cbr.offices.parse")
    definition = replace(catalog.get(parse.operation_id), possible_effects=frozenset({"storage.write"}))
    forged = replace(parse, definition=definition)
    with pytest.raises(RegistryError, match="registry.read_only_effects"):
        OperationCatalog((forged,)).describe()


def test_codec_drift_is_rejected_even_when_its_identity_is_unchanged(monkeypatch):
    from stratbox.operations import catalog as implementation
    from stratbox.core.execution.machine import ReadOnlyWireContract

    catalog = operation_catalog()
    ref = catalog.reference("cbr.offices.parse")
    _, _, codec = catalog.resolve(ref.operation_id)
    contract = codec.contract
    changed = ReadOnlyWireContract(
        contract.operation_id,
        contract.input_fields,
        contract.required_fields,
        {"different_result": {"type": "string"}},
    )
    original_load = implementation._load
    monkeypatch.setattr(
        implementation,
        "_load",
        lambda link: (
            replace(codec, contract=changed)
            if link == "hypothetical.codec:PARSE"
            else original_load(link)
        ),
    )
    drifted = OperationCatalog(
        (replace(ref, wire_codec_ref="hypothetical.codec:PARSE"),)
    )
    assert drifted.describe()[0]["machine_read_only"]
    with pytest.raises(RegistryError, match="registry.codec_mismatch"):
        drifted.resolve(ref.operation_id)
