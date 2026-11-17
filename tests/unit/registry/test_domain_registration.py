"""Check domain registration, identity and read-only admission."""

from dataclasses import replace
import json
from pathlib import Path
from pkgutil import ModuleInfo
from types import SimpleNamespace

import pytest

from stratbox.domains import registry as domain_registry
from stratbox.domains.registry import domain_catalog, operation_catalog
from stratbox.core.execution.catalog import OperationRegistration, OperationCatalog, OperationRef, RegistryError
from stratbox.core.registry import core_catalog


def test_published_contracts_remain_discoverable_and_machine_admission_is_explicit():
    domains = domain_catalog()
    core = core_catalog()
    all_ops = operation_catalog()
    domain_refs = set(domains.references)
    core_refs = set(core.references)
    assert domain_refs.isdisjoint(core_refs)
    assert domain_refs | core_refs == set(all_ops.references)
    identities = {(ref.operation_id, ref.contract_version) for ref in all_ops.references}
    assert len(identities) == len(all_ops.references)

    baseline_path = Path(__file__).resolve().parents[2] / "fixtures" / "operation_contracts_0_14.json"
    baseline = {tuple(item) for item in json.loads(baseline_path.read_text(encoding="utf-8"))}
    assert baseline <= identities, f"Published contracts removed: {sorted(baseline - identities)}"

    admitted = {(ref.operation_id, ref.contract_version) for ref in all_ops.references if ref.wire_codec_ref}
    assert {('cbr.offices.parse', 1), ('cbr.offices.compare', 2), ('frg.plan_cleanup', 1)} <= admitted


def test_all_references_resolve_to_matching_definitions_and_handlers():
    catalog = operation_catalog()
    for ref in catalog.list_refs():
        definition, handler, codec = catalog.resolve(ref.operation_id, ref.contract_version)
        assert definition.operation_id == ref.operation_id
        assert definition.contract_version == ref.contract_version
        assert callable(handler)
        assert (codec is not None) == (ref.wire_codec_ref is not None)
    assert len(catalog.describe()) == len(catalog.references)


def test_invalid_registrations_fail_explicitly():
    ref = domain_catalog().references[0]
    with pytest.raises(RegistryError, match='Duplicate operation contract'):
        OperationCatalog((ref, ref))
    with pytest.raises(RegistryError, match='registry.duplicate_contract'):
        OperationRegistration('test', (ref, ref))
    wrong = replace(ref, operation_id='wrong.contract')
    with pytest.raises(RegistryError, match='registry.contract_mismatch'):
        OperationCatalog((wrong,)).get(wrong.operation_id, wrong.contract_version)
    invalid_handler = replace(ref, handler_ref=ref.definition_ref)
    with pytest.raises(RegistryError, match='registry.invalid_handler'):
        OperationCatalog((invalid_handler,)).resolve(ref.operation_id, ref.contract_version)


def test_new_domain_is_discovered_without_a_central_list(monkeypatch):
    original_modules = domain_registry.iter_modules
    original_import = domain_registry.import_module
    name = 'new_business_domain'
    added = OperationRef('test.new_domain', 1,
        'stratbox.domains.new_business_domain.operations:TEST',
        'stratbox.domains.new_business_domain.operations:handle')
    registration = OperationRegistration(name, (added,))

    def modules(path):
        yield from original_modules(path)
        yield ModuleInfo(None, name, True)

    def importer(path):
        if path == f'stratbox.domains.{name}.registration':
            return SimpleNamespace(REGISTRATION=registration)
        return original_import(path)

    monkeypatch.setattr(domain_registry, 'iter_modules', modules)
    monkeypatch.setattr(domain_registry, 'import_module', importer)
    assert added in domain_registry.domain_catalog().list_refs()
