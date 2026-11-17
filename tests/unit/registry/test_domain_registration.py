"""Check domain registration, identity and read-only admission."""

from dataclasses import replace
from pkgutil import ModuleInfo
from types import SimpleNamespace

import pytest

from stratbox.domains import registry as domain_registry
from stratbox.domains.registry import domain_catalog, operation_catalog
from stratbox.system.execution.registry import DomainRegistration, OperationCatalog, OperationRef, RegistryError
from stratbox.system.registry import system_catalog


def test_baseline_registry_size_and_machine_admission():
    domains = domain_catalog()
    system = system_catalog()
    all_ops = operation_catalog()
    assert len(domains.references) == 68
    assert len(system.references) == 9
    assert len(all_ops.references) == 77
    assert len({(r.operation_id, r.contract_version) for r in all_ops.references}) == 77
    assert {(r.operation_id, r.contract_version) for r in all_ops.references if r.wire_codec_ref} == {
        ('cbr.offices.parse', 1), ('cbr.offices.compare', 2), ('frg.plan_cleanup', 1),
    }


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
        DomainRegistration('test', (ref, ref))
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
    registration = DomainRegistration(name, (added,))

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
