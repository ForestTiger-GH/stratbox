"""Specialization changes selected graphs while preserving exact contracts."""
import json
import subprocess
import sys

import pytest

from stratbox.capabilities.catalog import (
    CatalogContribution, CatalogError, CatalogSnapshot, MethodDefinition,
    ProcessingGroup, ProfileDefinition, RecipeDefinition,
)
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CascadeDefinition, CollectionMembership,
    CommandDefinition, GraphBody, InputRef, OperationDefinition, OutputRef,
    PortContract, ScenarioDefinition, SemanticPredicate,
)
from stratbox.capabilities.model.reuse import ConsumerEligibility, ReuseContract, WorkIdentity, fingerprint
from stratbox.shared.data.processing import DataContract, DataRole


OBS = PortContract(DataContract("observations", role=DataRole.EXTRACTS), tuple)
RAW = PortContract(value_type=bytes)


def layout_catalog(two_methods=False):
    material = CommandDefinition("read", "example:read", inputs={"material": RAW}, outputs={"value": OBS})
    extract = OperationDefinition("extract", method_slot="layout", inputs={"material": RAW}, outputs={"value": OBS})
    body = GraphBody((Call("read", "read", {"material": InputRef("material")}),), {"value": OutputRef("read")})
    methods = [MethodDefinition("rows", "extract", body)]
    profiles = [ProfileDefinition("rows.v1", {"header": {"row": 1}}, method_id="rows")]
    if two_methods:
        methods.append(MethodDefinition("columns", "extract", body))
        profiles.append(ProfileDefinition("columns.v1", {"header": {"column": 2}}, method_id="columns"))
    return CatalogSnapshot((material, extract), tuple(methods), tuple(profiles))


def test_equal_applicability_is_ambiguous_and_profile_selects_method():
    catalog = layout_catalog(True)
    with pytest.raises(CatalogError, match="ambiguous_method"):
        catalog.resolve("extract")
    rows = catalog.resolve("extract", profile_id="rows.v1")
    columns = catalog.resolve("extract", profile_id="columns.v1")
    assert rows.method.method_id == "rows"
    assert columns.method.method_id == "columns"
    assert rows.identities["profile"] != columns.identities["profile"]
    assert rows.parameters["profile"]["header"]["row"] == 1
    with pytest.raises(TypeError):
        rows.parameters["profile"]["header"]["row"] = 99
    with pytest.raises(CatalogError, match="profile_override"):
        catalog.resolve("extract", profile_id="rows.v1", parameters={"profile": {"header": {"row": 99}}})


def test_fixed_constraints_cannot_be_overridden_or_silently_conflict():
    catalog = layout_catalog()
    constrained = MethodDefinition("constrained", "extract", catalog.methods[0].body, fixed={"currency": "RUB"})
    catalog = CatalogSnapshot(catalog.definitions, (constrained,))
    assert catalog.resolve("extract").parameters["currency"] == "RUB"
    with pytest.raises(CatalogError, match="fixed_parameter_override"):
        catalog.resolve("extract", parameters={"currency": "USD"})


def test_operation_cannot_hide_acquisition_effect_or_scenario():
    acquire = CommandDefinition("acquire", "example:acquire", outputs={"value": OBS}, effects=frozenset({"network.receive"}))
    extract = OperationDefinition("extract", method_slot="layout", outputs={"value": OBS})
    method = MethodDefinition("network", "extract", GraphBody((Call("acquire", "acquire"),), {"value": OutputRef("acquire")}))
    with pytest.raises(CatalogError, match="method_effect_escalation"):
        CatalogSnapshot((acquire, extract), (method,))
    command = CommandDefinition("plain", "example:plain")
    operation = OperationDefinition("op", GraphBody((Call("plain", "plain"),), {"value": OutputRef("plain")}))
    scenario = ScenarioDefinition("scenario", GraphBody((Call("op", "op"),), {"value": OutputRef("op")}))
    invalid = OperationDefinition("bad", GraphBody((Call("nested", "scenario"),), {"value": OutputRef("nested")}))
    with pytest.raises(CatalogError, match="invalid_body_kind"):
        CatalogSnapshot((command, operation, scenario, invalid))


def test_nominal_ports_reject_same_representation_with_different_semantics():
    command = CommandDefinition("rows", "example:rows", outputs={"value": OBS})
    unrelated = PortContract(DataContract("offices", role=DataRole.EXTRACTS), tuple)
    operation = OperationDefinition("wrong", GraphBody((Call("rows", "rows"),), {"value": OutputRef("rows")}), outputs={"value": unrelated})
    with pytest.raises(CatalogError, match="port_contract_mismatch"):
        CatalogSnapshot((command, operation))


def test_closed_membership_does_not_imply_coverage_and_predicate_rejects_empty():
    assert not CollectionMembership(("sheet-a",), True, frozenset({"a", "b"}), frozenset({"a"})).complete
    observed = PortContract(value_type=tuple, predicates=(SemanticPredicate(),))
    with pytest.raises(ValueError, match="semantic_predicate_failed"):
        observed.validate(())
    observed.validate((1,))
    with pytest.raises(ValueError, match="coherent_outputs_missing"):
        AcceptanceContract(coherent_outputs=("data", "findings")).validate({"data": (1,)})


def test_local_overlay_and_generated_index_have_one_admission_boundary():
    catalog = layout_catalog()
    projection = json.loads(json.dumps(catalog.metadata_index()))
    catalog.check_index(projection)
    projection["capabilities"][0]["revision"] = "stale"
    with pytest.raises(CatalogError, match="stale_metadata_index"):
        catalog.check_index(projection)
    with pytest.raises(CatalogError, match="duplicate_identity"):
        catalog.overlay(CatalogContribution(definitions=(catalog.definition("read"),)))
    replacement = CommandDefinition("read", "example:read2", revision="2", inputs={"material": RAW}, outputs={"value": OBS})
    updated = catalog.overlay(CatalogContribution(definitions=(replacement,)), replace_ids=("read",))
    assert updated.fingerprint != catalog.fingerprint
    assert updated.definition("read").implementation_ref == "example:read2"


def test_processing_group_and_goal_selection_are_declarative():
    catalog = layout_catalog()
    group = ProcessingGroup("tables", source_ids=("publisher.series",), representations=("xlsx",), editions=("1",), methods={"extract": "rows"}, profiles={"extract": "rows.v1"})
    recipe = RecipeDefinition("extract-recipe", "observations", "extract", selection={"publisher": "sample"})
    catalog = CatalogSnapshot(catalog.definitions, catalog.methods, catalog.profiles, (group,), (recipe,))
    selected = catalog.resolve("extract", selection={"source_id": "publisher.series", "representation": "xlsx", "edition": "1"})
    assert selected.group.group_id == "tables"
    assert selected.profile.profile_id == "rows.v1"
    assert catalog.resolve_goal("observations", selection={"publisher": "sample"}).capability_id == "extract"
    with pytest.raises(CatalogError, match="group_inapplicable"):
        catalog.resolve("extract", group_id="tables", selection={"source_id": "publisher.series", "representation": "xlsx", "edition": "2"})


def test_work_identity_keeps_access_and_reference_editions_and_rejects_opaque_inputs():
    a = WorkIdentity("decode", "1", (("material", "sha-a"),), fingerprint({"format": "xlsx"}), access_scope="public", freshness="snapshot-1")
    b = WorkIdentity("decode", "1", (("material", "sha-a"),), fingerprint({"format": "xlsx"}), access_scope="public", freshness="snapshot-2")
    assert a.fingerprint != b.fingerprint
    assert ConsumerEligibility(access_scope="public", freshness="snapshot-1").eligible_for(a)
    assert not ConsumerEligibility(allow_network=False, access_scope="public", freshness="snapshot-1").eligible_for(a, frozenset({"network.receive"}))
    assert not ReuseContract(effects=frozenset({"store.write"})).eligible
    with pytest.raises(ValueError, match="opaque_identity"):
        fingerprint(object())


def test_catalog_metadata_does_not_import_execution_or_numerical_backend():
    code = '''import sys
sys.path.insert(0, 'src')
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import CommandDefinition
catalog = CatalogSnapshot((CommandDefinition("decode", "uninstalled_backend:decode"),))
assert catalog.commands.get("decode").kind == "command"
assert catalog.readiness("decode").metadata
assert not catalog.readiness("decode").executable
assert not any(name == "numpy" or name == "pandas" or name.startswith("stratbox.core.execution") for name in sys.modules)
'''
    subprocess.run([sys.executable, "-c", code], check=True)


def test_map_collection_admission_preserves_element_schema_and_membership():
    from stratbox.capabilities.model import MapCall, CollectCall
    number = PortContract(DataContract("number"), int)
    numbers = PortContract(DataContract("numbers"), tuple, collection=True)
    command = CommandDefinition("identity", "example:identity", inputs={"item": number}, outputs={"value": number})
    operation = OperationDefinition("identity.op", GraphBody((Call("leaf", "identity", {"item": InputRef("item")}),), {"value": OutputRef("leaf")}), inputs={"item": number}, outputs={"value": number})
    scenario = ScenarioDefinition("identity.scenario", GraphBody((Call("op", "identity.op", {"item": InputRef("item")}),), {"value": OutputRef("op")}), inputs={"item": number}, outputs={"value": number})
    cascade = CascadeDefinition("mapped", GraphBody((
        MapCall("items", "identity.scenario", InputRef("items"), contract=PortContract(number.schema, collection=True), max_items=10),
        CollectCall("values", (OutputRef("items"),), numbers, number),
    ), {"value": OutputRef("values")}), inputs={"items": PortContract(value_type=tuple)}, outputs={"value": numbers},
        membership=CollectionMembership(("items",), closed=True, expected_coverage=frozenset({"all"})))
    catalog = CatalogSnapshot((command, operation, scenario, cascade))
    assert catalog.cascades.get("mapped").membership.closed
    assert not catalog.cascades.get("mapped").membership.complete
    assert catalog.resolve("mapped").body.steps[0].max_items == 10
    broken = PortContract(DataContract("unrelated"), int)
    from dataclasses import replace
    bad_collect = replace(cascade.body.steps[1], element_contract=broken)
    invalid = replace(cascade, body=replace(cascade.body, steps=(cascade.body.steps[0], bad_collect)))
    with pytest.raises(CatalogError, match="collection_element_contract_mismatch"):
        CatalogSnapshot((command, operation, scenario, invalid))


def test_inferred_profile_group_gets_the_same_applicability_checks():
    catalog = layout_catalog()
    group = ProcessingGroup("sheets", source_ids=("allowed.series",), representations=("xlsx",), methods={"extract": "rows"})
    profile = ProfileDefinition("restricted", {"header": 1}, method_id="rows", group_id="sheets")
    catalog = CatalogSnapshot(catalog.definitions, catalog.methods, (*catalog.profiles, profile), (group,))
    with pytest.raises(CatalogError, match="group_inapplicable"):
        catalog.resolve("extract", profile_id="restricted", selection={"source_id": "wrong.series", "representation": "csv"})
    assert catalog.resolve("extract", profile_id="restricted",
        selection={"source_id": "allowed.series", "representation": "xlsx"}).group == group


def test_unknown_semantic_parameter_is_rejected_at_selected_binding():
    catalog = layout_catalog()
    with pytest.raises(CatalogError, match="parameter_unknown"):
        catalog.resolve("extract", parameters={"curreny": "RUB"})
    with pytest.raises(CatalogError, match="parameter_unknown"):
        catalog.resolve("read", parameters={"unused": 99})


def test_required_effect_root_must_reach_an_effectful_command():
    command = CommandDefinition("pure", "example:pure")
    scope = OperationDefinition("false.save", GraphBody((Call("pure", "pure"),),
        {"value": OutputRef("pure")}, required_effects=("pure",)))
    with pytest.raises(CatalogError, match="required_effect_without_effect"):
        CatalogSnapshot((command, scope))
    # Giving the intermediate operation an effect label cannot fabricate a
    # physical effect in a parent's required-effect closure.
    intermediate = OperationDefinition("labelled", GraphBody((Call("pure", "pure"),),
        {"value": OutputRef("pure")}), effects=frozenset({"storage.write"}))
    scenario = ScenarioDefinition("false.delivery", GraphBody((Call("save", "labelled"),),
        {"value": OutputRef("save")}, required_effects=("save",)))
    with pytest.raises(CatalogError, match="required_effect_without_effect"):
        CatalogSnapshot((command, intermediate, scenario))


def test_binding_projection_pins_group_recipe_and_only_used_semantics():
    from dataclasses import replace
    from stratbox.capabilities.catalog import ReferenceDefinition, SchemaDefinition
    from stratbox.capabilities.model import declaration_fingerprint
    source = PortContract(DataContract("source.table"), bytes)
    result = PortContract(DataContract("result.table"), tuple)
    command = CommandDefinition("decode.bound", "example:decode", inputs={"source": source}, outputs={"value": result})
    operation = OperationDefinition("extract.bound", method_slot="layout", inputs={"source": source}, outputs={"value": result}, parameters={"profile": {}})
    body = GraphBody((Call("decode", command.capability_id, {"source": InputRef("source")}),), {"value": OutputRef("decode")})
    method = MethodDefinition("decode.csv", operation.capability_id, body,
        selection={"representation": "csv"}, group_ids=("publisher.table",), reference_ids=("units",))
    profile = ProfileDefinition("layout.v1", {"columns": 2}, method_id=method.method_id, group_id="publisher.table")
    group = ProcessingGroup("publisher.table", source_ids=("source.series",), representations=("csv",),
        editions=("1",), methods={operation.capability_id: method.method_id}, profiles={operation.capability_id: profile.profile_id})
    recipe = RecipeDefinition("extract.recipe", "extract.goal", operation.capability_id, selection={"edition": "1"})
    schema = SchemaDefinition("result.table", data={"columns": 2})
    unused_schema = SchemaDefinition("unused.schema", data={"ignored": True})
    units = ReferenceDefinition("units", "1", "units-content")
    unused_ref = ReferenceDefinition("unused.reference", "1", "irrelevant")
    catalog = CatalogSnapshot((command, operation), (method,), (profile,), (group,), (recipe,),
        (schema, unused_schema), (units, unused_ref))
    selection = {"source_id": "source.series", "representation": "csv", "edition": "1"}
    resolved = catalog.resolve(operation.capability_id, selection=selection, recipe_id=recipe.recipe_id)
    assert resolved.identities["group"] == group.fingerprint
    assert resolved.identities["recipe"] == recipe.fingerprint
    assert resolved.identities["reference:units"] == declaration_fingerprint(units)
    assert "reference:unused.reference" not in resolved.identities
    assert "schema:unused.schema" not in resolved.identities
    projection = resolved.projection()
    assert catalog.validate_binding(projection) == resolved
    with pytest.raises(TypeError):
        projection["resolve_inputs"]["selection"]["edition"] = "2"
    for changed in (
        replace(catalog, groups=(replace(group, fixed={"profile": {"columns": 3}}),)),
        replace(catalog, recipes=(replace(recipe, revision="2"),)),
        replace(catalog, references=(replace(units, revision="2"), unused_ref)),
        replace(catalog, schemas=(replace(schema, revision="2"), unused_schema)),
    ):
        with pytest.raises(CatalogError, match="binding_changed"):
            changed.validate_binding(projection)
    unrelated = replace(catalog, schemas=(schema, replace(unused_schema, revision="2")),
        references=(units, replace(unused_ref, revision="2")))
    assert unrelated.validate_binding(projection) == resolved


def test_authoring_reference_types_participate_in_definition_identity():
    from dataclasses import replace
    from stratbox.capabilities.model import declaration_fingerprint, ParameterRef
    assert declaration_fingerprint(InputRef("source")) != declaration_fingerprint(ParameterRef("source"))
    call = Call("extract", "extract", selection={"edition": {"name": "first"}})
    with pytest.raises(TypeError):
        call.selection["edition"]["name"] = "second"
    assert declaration_fingerprint(call) != declaration_fingerprint(replace(call, selection={"edition": "second"}))


def test_per_output_predicates_and_coherent_groups_reject_only_owned_outputs():
    acceptance = AcceptanceContract(predicates=(SemanticPredicate("left", "minimum", 10),))
    assert dict(acceptance.output_errors({"left": 2, "right": 20})) == {
        "left": ("acceptance.semantic_predicate_failed",)}
    coherent = AcceptanceContract(coherent_outputs=("left", "findings"),
        predicates=(SemanticPredicate("left", "minimum", 10),))
    assert set(coherent.output_errors({"left": 2, "right": 20, "findings": ()})) == {"left", "findings"}
    errors = coherent.output_errors({"right": 20}, names=("left", "findings", "right"))
    assert set(errors) == {"left", "findings"}


def test_global_acceptance_predicates_wait_for_all_dependencies():
    acceptance = AcceptanceContract(predicates=(SemanticPredicate("", "equals", {"left": 1}),))
    errors, pending = acceptance.assess_outputs({"left": 1}, names=("left", "right"))
    assert not errors and pending == {"left", "right"}
    errors, pending = acceptance.assess_outputs({"left": 1, "right": 2}, names=("left", "right"))
    assert set(errors) == {"left", "right"} and not pending
    named = AcceptanceContract(predicates=(SemanticPredicate("left", "minimum", 1),))
    errors, pending = named.assess_outputs({"left": 1}, names=("left", "right"))
    assert not errors and not pending
    coherent = AcceptanceContract(coherent_outputs=("left", "right"))
    errors, pending = coherent.assess_outputs({"left": 1}, names=("left", "right"))
    assert not errors and pending == {"left", "right"}
    errors, pending = coherent.assess_outputs({"left": 1}, names=("left", "right"), settled=("right",))
    assert set(errors) == {"left", "right"} and not pending
