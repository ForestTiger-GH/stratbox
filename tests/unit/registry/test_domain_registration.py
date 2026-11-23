"""Check domain registration, identity and read-only admission."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from stratbox.domains import registry as domain_registry
from stratbox.domains.registry import domain_catalog, operation_catalog, domain_registration_inventory
from stratbox.domains._structure import DomainLayoutError, discover_operation_owners
from stratbox.core.registry.catalog import OperationRegistration, OperationCatalog, OperationRef, RegistryError
from stratbox.core.registry import core_catalog


def test_published_contracts_remain_discoverable_and_machine_admission_is_explicit():
    domains = domain_catalog()
    core = core_catalog()
    all_ops = operation_catalog()
    domain_refs = set(domains.references)
    core_refs = set(core.references)
    assert domain_refs.isdisjoint(core_refs)
    assert domain_refs | core_refs == set(all_ops.references)
    identities = {ref.operation_id for ref in all_ops.references}
    assert len(identities) == len(all_ops.references)
    baseline_path = Path(__file__).resolve().parents[2] / "fixtures" / "operation_ids.json"
    baseline = set(json.loads(baseline_path.read_text(encoding="utf-8")))
    replacements = {
        "cbr.sors.load_sources": "cbr.sors.prepare_from_originals",
        "cbr.sors.render_workbook": "cbr.sors.render_views",
    }
    expected = {replacements.get(name, name) for name in baseline}
    assert expected <= identities
    assert not set(replacements) & identities
    admitted = {ref.operation_id for ref in all_ops.references if ref.wire_codec_ref}
    assert {'cbr.offices.parse', 'cbr.offices.compare', 'frg.plan_cleanup'} <= admitted


def test_all_references_resolve_to_matching_definitions_and_handlers():
    catalog = operation_catalog()
    for ref in catalog.list_refs():
        definition, handler, codec = catalog.resolve(ref.operation_id)
        assert definition.operation_id == ref.operation_id
        assert callable(handler)
        assert (codec is not None) == (ref.wire_codec_ref is not None)
    assert len(catalog.describe()) == len(catalog.references)


def test_invalid_registrations_fail_explicitly():
    ref = domain_catalog().references[0]
    with pytest.raises(RegistryError, match='registry.duplicate_operation'):
        OperationCatalog((ref, ref))
    with pytest.raises(RegistryError, match='registry.duplicate_operation'):
        OperationRegistration('test', (ref, ref))
    wrong = replace(ref, operation_id='wrong.contract')
    with pytest.raises(RegistryError, match='registry.operation_unavailable'):
        OperationCatalog((wrong,)).get(wrong.operation_id)
    invalid_handler = replace(ref, handler_ref="stratbox.core.registry.resources:_KINDS")
    with pytest.raises(RegistryError, match='registry.invalid_handler'):
        OperationCatalog((invalid_handler,)).resolve(ref.operation_id)


def _synthetic_package(root: Path, owner: str, *, manifest: bool = True) -> None:
    current = root
    for component in owner.split("."):
        current = current / component
        current.mkdir(exist_ok=True)
        (current / "__init__.py").write_text("", encoding="utf-8")
    if manifest:
        (current / "_registration.py").write_text("", encoding="utf-8")


def _synthetic_ref(owner: str, name: str) -> OperationRef:
    module = f"stratbox.domains.{owner}.operations"
    return OperationRef(name, f"{module}:handle")


def _synthetic_catalog(monkeypatch, tmp_path, declarations):
    root = tmp_path / "domains"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    for owner in declarations:
        _synthetic_package(root, owner)
    monkeypatch.setattr(domain_registry, "owner_ids", lambda: tuple(sorted(declarations)))
    monkeypatch.setattr(domain_registry, "owner_registration", lambda owner: declarations[owner])
    return domain_registry.domain_catalog


def test_new_nested_domain_is_discovered_without_a_central_list(monkeypatch, tmp_path):
    owner = "new_publisher.statistics.annual_series"
    ref = _synthetic_ref(owner, "example.new_series")
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path, {owner: OperationRegistration(owner, (ref,))}
    )
    assert catalog().list_refs() == (ref,)
    assert catalog().list_refs() == (ref,)


def test_grouping_and_private_helpers_are_not_registrations(monkeypatch, tmp_path):
    owner = "publisher.family.publication"
    ref = _synthetic_ref(owner, "example.grouped")
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path, {owner: OperationRegistration(owner, (ref,))}
    )
    root = tmp_path / "domains"
    _synthetic_package(root, "publisher.no_operations.utility", manifest=False)
    (root / "publisher" / "_source.py").write_text("unexpected = True\n", encoding="utf-8")
    assert catalog().list_refs() == (ref,)


def test_nearest_owner_prevents_parent_from_claiming_nested_series(monkeypatch, tmp_path):
    parent = "cbr.corporate_lending.industries"
    child = parent + ".issuance_0104"
    misplaced = _synthetic_ref(child, "example.owned_by_child")
    registered = {
        parent: OperationRegistration(parent, (misplaced,)),
        child: OperationRegistration(child, (_synthetic_ref(child, "example.child"),)),
    }
    catalog = _synthetic_catalog(monkeypatch, tmp_path, registered)
    with pytest.raises(RegistryError, match="registry.nearest_owner"):
        catalog()


def test_full_dotted_owner_identity_is_required(monkeypatch, tmp_path):
    owner = "fns.legal_entities"
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {owner: OperationRegistration("legal_entities", (_synthetic_ref(owner, "test.owner"),))},
    )
    with pytest.raises(RegistryError, match="registry.invalid_owner"):
        catalog()


def test_outside_owner_reference_is_rejected(monkeypatch, tmp_path):
    owner = "cbr.publication"
    original = _synthetic_ref(owner, "test.boundary")
    foreign = replace(original, handler_ref="stratbox.domains.fns.somewhere.operations:handle")
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path, {owner: OperationRegistration(owner, (foreign,))}
    )
    with pytest.raises(RegistryError, match="registry.domain_ownership"):
        catalog()


def test_same_named_prefix_does_not_match_other_owner(monkeypatch, tmp_path):
    left = "publisher.annual"
    right = "publisher.annually"
    confused = replace(
        _synthetic_ref(left, "test.segment_boundary"),
        handler_ref=f"stratbox.domains.{right}.operations:handle",
    )
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {
            left: OperationRegistration(left, (confused,)),
            right: OperationRegistration(right, (_synthetic_ref(right, "test.right"),)),
        },
    )
    with pytest.raises(RegistryError, match="registry.nearest_owner"):
        catalog()


def test_duplicate_contract_across_nested_owners_is_rejected(monkeypatch, tmp_path):
    first, second = "a.source_one", "b.source_two"
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {
            first: OperationRegistration(first, (_synthetic_ref(first, "same.operation"),)),
            second: OperationRegistration(second, (_synthetic_ref(second, "same.operation"),)),
        },
    )
    with pytest.raises(RegistryError, match="registry.logical_owner:same.operation"):
        catalog()


def test_broken_existing_manifest_fails_instead_of_being_skipped(monkeypatch, tmp_path):
    owner = "publisher.broken"
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {owner: OperationRegistration(owner, (_synthetic_ref(owner, "test.broken"),))},
    )

    def failing_registration(name):
        raise RegistryError("registry.invalid_manifest")

    monkeypatch.setattr(domain_registry, "owner_registration", failing_registration)
    with pytest.raises(RegistryError, match="registry.invalid_manifest"):
        catalog()


def test_discovered_owner_contracts_are_complete_and_extensible():
    owners = tuple(owner for owner in domain_registry.owner_ids() if not owner.startswith("core."))
    catalog = domain_catalog()
    rows = domain_registration_inventory()
    assert owners == tuple(sorted(owners))
    assert set(owners) == {owner for owner, _ in rows}
    assert len(rows) == len(catalog.references)
    assert len(rows) == len(set(rows))
    assert {operation_id for _, operation_id in rows} == {ref.operation_id for ref in catalog.references}
    assert ("cbr", "cbr.industries.0105a.parse") in rows
    assert ("cbr", "cbr.industries.0104a.parse") in rows
    assert {owner for owner in owners if owner == "cbr" or owner.startswith("cbr.")} == {"cbr"}
    assert all(not hasattr(ref, "definition_ref") for ref in catalog.references)


def test_invalid_intermediate_package_rejects_manifest(monkeypatch, tmp_path):
    root = tmp_path / "domains"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    broken = root / "publisher" / "family" / "series"
    broken.mkdir(parents=True)
    (root / "publisher" / "__init__.py").write_text("", encoding="utf-8")
    # The intervening family is not importable as a regular package.
    (broken / "__init__.py").write_text("", encoding="utf-8")
    (broken / "_registration.py").write_text("", encoding="utf-8")
    with pytest.raises(DomainLayoutError, match="domain.unreachable_manifest"):
        discover_operation_owners(root)


def test_dynamic_new_owner_and_extra_operation_have_no_count_ceiling(monkeypatch, tmp_path):
    owner = "future_publisher.family.series"
    first = _synthetic_ref(owner, "future.series.first")
    second = _synthetic_ref(owner, "future.series.second")
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path, {owner: OperationRegistration(owner, (first, second))}
    )
    assert {ref.operation_id for ref in catalog().references} == {
        "future.series.first", "future.series.second"
    }


def test_empty_manifest_owner_is_rejected_in_favor_of_grouping_packages(monkeypatch, tmp_path):
    owner = "publisher.empty_family"
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {owner: OperationRegistration(owner, ())},
    )
    with pytest.raises(RegistryError, match="registry.empty_owner"):
        catalog()


def test_logical_operation_identity_has_one_owner(monkeypatch, tmp_path):
    first, second = "publisher.series_a", "publisher.series_b"
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {
            first: OperationRegistration(
                first, (_synthetic_ref(first, "example.same_operation"),)
            ),
            second: OperationRegistration(
                second, (replace(
                    _synthetic_ref(second, "example.same_operation"),
                ),)
            ),
        },
    )
    with pytest.raises(RegistryError, match="registry.logical_owner"):
        catalog()


def test_invalid_reference_member_is_a_registry_error():
    with pytest.raises(RegistryError, match="registry.invalid_reference"):
        OperationRegistration("publisher.series", (object(),))
    with pytest.raises(RegistryError, match="registry.invalid_reference"):
        OperationCatalog((object(),))


def test_inventory_and_catalog_are_views_of_one_validated_snapshot(monkeypatch, tmp_path):
    owner = "another_publisher.family.series"
    reference = _synthetic_ref(owner, "example.new_series")
    catalog = _synthetic_catalog(
        monkeypatch, tmp_path,
        {owner: OperationRegistration(owner, (reference,))},
    )
    assert catalog().list_refs() == (reference,)
    assert domain_registry.domain_registration_inventory() == (
        (owner, "example.new_series"),
    )
