"""Canonical content groups and real role-to-request assembly."""
from dataclasses import replace
import pytest

from stratbox.operations import operation_catalog
from stratbox.domains.registry.requirements import bind_requirement_inputs, SourceInstance
from stratbox.domains.registry.declarations import source_group, source_documents
from stratbox.shared.data.sources import ResolvedSourceInstance
from stratbox.shared.evidence import SourcePayload


def test_all_sources_have_resolvable_content_groups_distinct_from_official_table_codes():
    catalog = operation_catalog()
    assert len(catalog.source_catalog().sources) == 90
    for source in catalog.source_catalog().sources:
        assert source.source_groups
        for group in source.source_groups:
            assert source_group(source.series_id, group.group_id) == group
            assert group.contracts and group.grain
    group = source_group("cbr.corporate_lending.debt_0105a", "regional_debt")
    assert group.source_table_code == "01_05_A"
    with pytest.raises(ValueError, match="registry.source_group_unknown"):
        source_group("cbr.corporate_lending.debt_0105a", "01_05_A")


def _actual_roles(catalog):
    result = {}
    for requirement in catalog.requirements("cbr.sors.prepare_inputs"):
        if not requirement.required:
            continue
        payload = SourcePayload((requirement.source_label + "\nfixture material").encode())
        claim = SourceInstance(requirement.source_ids[0], requirement.accepted_contracts[0],
            group_id=requirement.group_id, report_date="2026-10-01", publication_step=1,
            material_identity=payload.identity)
        result[requirement.input_name] = ResolvedSourceInstance(claim, payload, payload)
    return result


def test_sors_10_required_roles_assemble_the_real_typed_input_and_preserve_all_materials():
    catalog = operation_catalog()
    roles = _actual_roles(catalog)
    bound = bind_requirement_inputs(catalog, "cbr.sors.prepare_inputs", roles)
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceInputs
    assert isinstance(bound["sources"].value, SorsSourceInputs)
    assert bound["sources"].value.regional_totals_history is None
    assert len(bound["sources"].used_inputs) == 10
    for role, actual in roles.items():
        assert getattr(bound["sources"].value, role) is actual.value
    changed = dict(roles)
    changed.pop("sme_regional_totals")
    with pytest.raises(ValueError, match="source.required_missing"):
        bind_requirement_inputs(catalog, "cbr.sors.prepare_inputs", changed)


def test_claims_without_material_and_contradictory_role_content_cannot_bind():
    catalog = operation_catalog()
    roles = _actual_roles(catalog)
    claims = {name: value.instance for name, value in roles.items()}
    with pytest.raises(ValueError, match="source.material_unresolved"):
        bind_requirement_inputs(catalog, "cbr.sors.prepare_inputs", claims)
    first = roles["regional_traditional"]
    wrong = replace(first.instance, group_id="national_traditional_debt")
    roles["regional_traditional"] = ResolvedSourceInstance(wrong, first.value, first.material)
    with pytest.raises(ValueError, match="source.group_mismatch"):
        bind_requirement_inputs(catalog, "cbr.sors.prepare_inputs", roles)


def test_selected_format_group_and_unreviewed_edition_explain_the_same_accepted_bindings():
    catalog = operation_catalog()
    sources = catalog.source_catalog()
    selected = sources.selection("frg.regional.issuance", format="xlsx", group_id="reported_metrics")
    assert selected.bindings == sources.bindings("frg.regional.issuance", format="xlsx", group_id="reported_metrics")
    rejected = sources.selection("frg.regional.issuance", format="html", group_id="reported_metrics")
    assert rejected.state == "inapplicable" and not rejected.bindings
    assert "source.format_unavailable" in rejected.reasons
    edition = sources.selection("frg.regional.issuance", format="xlsx", group_id="reported_metrics", edition="unreviewed-layout")
    assert edition.state == "conditional"
    assert all(binding.state == "conditional" for binding in edition.bindings)


def test_named_sors_roles_bind_the_actual_operation_request_and_config_coordinates():
    from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import PrepareSorsRequest
    catalog = operation_catalog()
    roles = _actual_roles(catalog)
    call = catalog.bind("cbr.sors.prepare_inputs", inputs=roles, parameters={"config": SorsRunConfig("2026-10-01")})
    assert isinstance(call.bound.request, PrepareSorsRequest)
    assert call.bound.request.sources.regional_totals_history is None
    assert len(call.bound.inputs[0][1].source_context.uses) == 10
    assert {use.input_role for use in call.bound.inputs[0][1].source_context.uses} == set(roles)
    with pytest.raises(ValueError, match="source.report_date_mismatch"):
        catalog.bind("cbr.sors.prepare_inputs", inputs=roles, parameters={"config": SorsRunConfig("2026-11-01")})


def test_source_profile_refs_resolve_canonically_or_through_explicit_owned_factories():
    from stratbox.domains.registry.declarations import validate_publication_profiles
    raw = next(value for value in source_documents("cbr") if value["series_id"] == "cbr.corporate_lending.corp_debt_a")
    validate_publication_profiles(raw, typed=True)
    raw["publication"]["acquisition_profile"] = "cbr.route.undefined"
    with pytest.raises(ValueError, match="registry.source_profile_unknown"):
        validate_publication_profiles(raw)
    raw["domain_profiles"] = {"cbr.route.undefined": {"kind": "acquisition",
        "implementation_ref": "stratbox.domains.cbr.publications.profiles:acquisition_profile",
        "implementation_parameters": {"profile_id": "cbr.route.undefined"}}}
    validate_publication_profiles(raw)
    with pytest.raises(ValueError, match="cbr.profile.acquisition_unknown"):
        validate_publication_profiles(raw, typed=True)
    raw["domain_profiles"]["cbr.route.undefined"]["implementation_ref"] = "stratbox.domains.frank_rg.profiles:admit"
    with pytest.raises(ValueError, match="registry.source_profile_pointer_owner_mismatch"):
        validate_publication_profiles(raw)


def test_requirement_group_contract_and_grain_must_match_canonical_source(monkeypatch):
    from stratbox.domains.registry import requirements, declarations as sources
    catalog = operation_catalog()
    declared = catalog.requirements("cbr.sors.prepare_inputs")
    original = requirements.declared_requirements
    monkeypatch.setattr(requirements, "declared_requirements", lambda operation: (replace(declared[0], group_id="missing"),))
    with pytest.raises(ValueError, match="registry.source_group_unknown"):
        catalog.requirements("cbr.sors.prepare_inputs")
    monkeypatch.setattr(requirements, "declared_requirements", lambda operation: (replace(declared[0], grain=("incompatible",)),))
    with pytest.raises(ValueError, match="registry.source_requirement_grain_mismatch"):
        catalog.requirements("cbr.sors.prepare_inputs")


def test_single_role_named_like_its_input_port_uses_the_same_checked_bridge(monkeypatch):
    from stratbox.domains.registry import requirements
    from stratbox.domains.registry.requirements import SourceRequirement
    from stratbox.shared.data.processing import DataContract, DataRole
    catalog = operation_catalog()
    contract = DataContract("source.payload", role=DataRole.ORIGINALS)
    requirement = SourceRequirement("source", ("cbr.corporate_lending.debt_0105a",), (contract,), "published", "source", group_id="regional_debt")
    original = requirements.operation_requirements
    monkeypatch.setattr(requirements, "operation_requirements", lambda c, identity: (requirement,) if identity == "workbook.extract" else original(c, identity))
    payload = SourcePayload(b"actual material")
    claim = SourceInstance(requirement.source_ids[0], contract, group_id=requirement.group_id, material_identity=payload.identity)
    call = catalog.bind("workbook.extract", inputs={"source": ResolvedSourceInstance(claim, payload, payload)},
        parameters={"series_id": claim.source_id, "issue_id": "2026-10"})
    assert call.bound.request.payload is payload
    assert call.bound.inputs[0][1].source_context.uses[0].coordinate.source_group_id == "regional_debt"


def test_declared_existing_profile_factory_resolves_new_profile_parameters_without_an_allowlist(monkeypatch):
    from stratbox.domains.registry import declarations as sources
    raw = next(value for value in source_documents("cbr") if value["series_id"] == "cbr.corporate_lending.corp_debt_a")
    reference = "cbr.route.declarative_future"
    raw["publication"]["acquisition_profile"] = reference
    raw["domain_profiles"] = {reference: {"kind": "acquisition",
        "implementation_ref": "stratbox.domains.cbr.publications.contracts:AcquisitionProfile",
        "implementation_parameters": {"profile_id": reference, "kind": "fixed",
            "default_url": "https://www.cbr.ru/statistics/declared_future.xlsx"}}}
    sources.validate_publication_profiles(raw, typed=True)
    monkeypatch.setattr(sources, "source_documents", lambda owner: (raw,))
    profile = sources.resolve_domain_profile("cbr", reference)
    assert profile.profile_id == reference
    assert profile.default_url == "https://www.cbr.ru/statistics/declared_future.xlsx"
    from stratbox.domains.cbr.publications.profiles import acquisition_profile
    assert acquisition_profile(reference) == profile



def test_missing_optional_roles_build_a_typed_empty_bundle_without_invented_guarantees(monkeypatch):
    from dataclasses import dataclass
    from types import SimpleNamespace
    from stratbox.domains.registry import requirements
    from stratbox.shared.data.operations import InputPort
    from stratbox.shared.data.processing import DataContract
    @dataclass(frozen=True)
    class OptionalBundle:
        payload: SourcePayload | None = None
    requirement = requirements.SourceRequirement("history", ("cbr.corporate_lending.debt_0105a",),
        (DataContract("source.payload"),), "validation", "source", required=False, minimum=0)
    policy = SimpleNamespace(processing=SimpleNamespace(inputs=(InputPort("source", DataContract("example.optional.bundle")),)))
    catalog = SimpleNamespace(get=lambda identity: policy)
    monkeypatch.setattr(requirements, "operation_requirements", lambda *args: (requirement,))
    monkeypatch.setattr(requirements, "_assembly_types", lambda *args: {"source": (OptionalBundle, {"history": "payload"}, {"payload": SourcePayload | None})})
    bound = requirements.bind_requirement_inputs(catalog, "workbook.extract", {})
    assert bound["source"].value == OptionalBundle()
    assert not bound["source"].qualifications and not bound["source"].coverage
    assert not bound["source"].used_inputs and not bound["source"].source_context.uses
