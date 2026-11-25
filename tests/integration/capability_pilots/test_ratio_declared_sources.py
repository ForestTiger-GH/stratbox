"""An admitted cross-source pair checks qualified source uses per operand."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import json

import pytest

from stratbox.capabilities.commands import OBSERVATIONS
from stratbox.core.execution.values.codec import encode_value, decode_value
from stratbox.core.execution.value_context import value_context, validate_retained_context
from stratbox.sdk import StrategyBox
from stratbox.shared.data.observation_snapshots import (
    observation_snapshot, observations_from_snapshot, observations_from_components,
)
from stratbox.shared.data.observations import ObservationBatch, Observation, SubjectRef, MetricRef, PeriodRef
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .conftest import ratio_pair


@pytest.fixture
def declared_pair_inputs():
    def operand(dataset, source, group, values):
        identity = ByteIdentity.of(source.encode())
        use = SourceUse(SourceCoordinate(source, family_id=source + ".family", source_group_id=group,
            issue_id="2026-10-01", material_identity=identity, layout_edition="layout.1",
            semantic_profile_edition="mapping.1"), "primary", "observed", "receipt." + source)
        observations = tuple(Observation(SubjectRef("region", subject),
            MetricRef(dataset, "RUB", "stock", "fixture.v1", Decimal(1)),
            PeriodRef("as_of", as_of=date(2026, 10, 1)), (), "banking", value, "reported", identity.sha256)
            for subject, value in zip(("A", "B"), values))
        return ObservationBatch(dataset, 1, "2026-10-01", observations,
            (UsedInputReceipt("source", identity, "application/octet-stream", "reference_only", source),), (use,))
    left = operand("fixture.debt", "publisher.bank", "loans", (10, 20))
    right = operand("fixture.total", "publisher.statistics", "macro", (100, 400))
    pair = ratio_pair(origin_policy="declared_sources")
    for role, batch in (("numerator", left), ("denominator", right)):
        use, = batch.source_uses
        pair[role] = {**pair[role], "source_requirements": ({"source_id": use.coordinate.source_id,
            "source_group_id": use.coordinate.source_group_id, "input_role": "primary",
            "qualifications": ("observed",)},)}
    return left, right, pair


def invoke(box, left, right, pair):
    return box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right},
        parameters={"pair": pair}, timeout=10)


def rejected(result, code):
    assert result.outcome == "failed"
    assert "observations" not in result.outputs
    assert any(item.code == "calculation." + code for value in result.results.values() for item in value.diagnostics)
    assert all(value.value is None for value in result.results.values() if value.outcome == "failed")


def test_declared_cross_source_pair_preserves_qualified_operand_basis_portably(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    with StrategyBox() as box:
        result = invoke(box, left, right, pair)
        assert result.outcome == "succeeded", result.diagnostics
        batch = result.output("observations")
        assert [item.value for item in batch.observations] == [Decimal("0.1"), Decimal("0.05")]
        assert "calculation.admitted" in batch.evidence.qualifications
        basis, = batch.evidence.calculations
        assert basis.source_uses == (("numerator", left.source_uses[0]), ("denominator", right.source_uses[0]))
        assert basis.origin_policy == "declared_sources"
        assert batch.source_uses == (*left.source_uses, *right.source_uses)
        restored = decode_value(encode_value(batch, OBSERVATIONS.schema)).value
        assert restored.evidence.calculations == batch.evidence.calculations
        assert restored.source_uses == batch.source_uses


def test_calculation_source_basis_has_an_exact_metadata_edition_and_context_route(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    with StrategyBox() as box:
        result = invoke(box, left, right, pair)
        assert result.outcome == "succeeded", result.diagnostics
        batch = result.output("observations")
        snapshot = observation_snapshot(batch)
        metadata = snapshot.table("metadata")
        assert metadata.schema.contract == DataContract("observations.batch.metadata", 4)
        restored = observations_from_snapshot(snapshot)
        assert restored == batch
        assert restored.evidence.calculations[0].source_uses == (
            ("numerator", left.source_uses[0]), ("denominator", right.source_uses[0]))
        assert value_context(batch) == value_context(snapshot) == value_context(restored)
        assert value_context(snapshot).uses == (*left.source_uses, *right.source_uses)
        validate_retained_context(snapshot)

        legacy_schema = replace(metadata.schema, contract=replace(metadata.schema.contract, version=3))
        row = list(metadata.rows[0])
        encoded = json.loads(row[-1])
        del encoded["evidence"]["calculations"][0]["source_uses"]
        row[-1] = canonical_manifest_bytes(encoded).decode("utf-8")
        legacy_metadata = TypedTable(legacy_schema, (tuple(row),))
        legacy = DatasetSnapshot.build(snapshot.manifest.dataset_id, snapshot.manifest.version_id,
            snapshot.manifest.contract, (("metadata", legacy_metadata),
                ("observations", snapshot.table("observations"))),
            coverage=snapshot.manifest.coverage, inputs=snapshot.manifest.inputs)
        with pytest.raises(ValueError, match="^observations.snapshot_invalid$"):
            observations_from_snapshot(legacy)
        with pytest.raises(ValueError, match="^observations.metadata_invalid$"):
            observations_from_components(legacy_metadata, snapshot.table("observations"),
                inputs=snapshot.manifest.inputs)
        with pytest.raises(ValueError, match="^source.context_schema_mismatch$"):
            validate_retained_context(legacy)


@pytest.mark.parametrize("role", ("numerator", "denominator"))
def test_each_operand_requires_its_own_source_requirements(declared_pair_inputs, role):
    left, right, pair = declared_pair_inputs
    pair[role] = {key: value for key, value in pair[role].items() if key != "source_requirements"}
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_source_requirements_required")


@pytest.mark.parametrize("role", ("numerator", "denominator"))
def test_matching_dataset_and_metric_do_not_hide_wrong_actual_source(declared_pair_inputs, role):
    left, right, pair = declared_pair_inputs
    batch = left if role == "numerator" else right
    use = batch.source_uses[0]
    changed = replace(batch, source_uses=(replace(use, coordinate=replace(use.coordinate, source_id="unexpected.publisher")),))
    left, right = (changed, right) if role == "numerator" else (left, changed)
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_mismatch")


@pytest.mark.parametrize("change, code", (
    ({"qualification": "declared"}, "pair_origin_qualification_mismatch"),
    ({"input_role": "reference"}, "pair_origin_mismatch"),
))
def test_source_qualification_and_role_are_checked_without_upgrading_evidence(declared_pair_inputs, change, code):
    left, right, pair = declared_pair_inputs
    original = right.source_uses[0]
    right = replace(right, source_uses=(replace(original, **change),))
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), code)
    assert right.source_uses[0] == replace(original, **change)


def test_source_and_group_must_match_the_same_relational_use(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    original = left.source_uses[0]
    wrong_group = replace(original, coordinate=replace(original.coordinate, source_group_id="other"))
    matching_group_elsewhere = replace(original, coordinate=replace(original.coordinate, source_id="another.publisher"))
    left = replace(left, source_uses=(wrong_group, matching_group_elsewhere))
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_mismatch")


def test_lineage_source_id_does_not_substitute_for_missing_qualified_source_use(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    left = replace(left, source_uses=())
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_unavailable")


def test_required_source_evidence_is_not_inferred_from_an_observed_label_alone(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    use = replace(left.source_uses[0], coordinate=replace(left.source_uses[0].coordinate, material_identity=None), evidence_ref=None)
    left = replace(left, source_uses=(use,))
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_evidence_required")


def test_source_requirement_must_declare_acceptable_qualification(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    declared = dict(pair["numerator"]["source_requirements"][0])
    declared.pop("qualifications")
    pair["numerator"]["source_requirements"] = (declared,)
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_source_requirement_invalid")


def test_explicit_coordinate_material_and_profile_pins_match_the_actual_use(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    for role, batch in (("numerator", left), ("denominator", right)):
        use = batch.source_uses[0]
        pair[role]["source_requirements"] = ({**pair[role]["source_requirements"][0],
            "family_id": use.coordinate.family_id, "issue_id": use.coordinate.issue_id,
            "layout_edition": use.coordinate.layout_edition,
            "semantic_profile_edition": use.coordinate.semantic_profile_edition,
            "material_identity": {"sha256": use.coordinate.material_identity.sha256, "size": use.coordinate.material_identity.size},
            "evidence_ref": use.evidence_ref},)
    with StrategyBox() as box:
        assert invoke(box, left, right, pair).outcome == "succeeded"
        altered = replace(right.source_uses[0], coordinate=replace(right.source_uses[0].coordinate,
            semantic_profile_edition="different.mapping"))
        rejected(invoke(box, left, replace(right, source_uses=(altered,)), pair), "pair_origin_mismatch")


def test_undeclared_additional_origin_rejects_the_pair(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    additional = replace(left.source_uses[0], coordinate=replace(left.source_uses[0].coordinate, source_id="undeclared.publisher"))
    left = replace(left, source_uses=(*left.source_uses, additional))
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_mismatch")


def test_missing_required_auxiliary_origin_is_not_covered_by_primary_source(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    primary, = pair["numerator"]["source_requirements"]
    pair["numerator"]["source_requirements"] = (primary,
        {"source_id": "publisher.reference", "qualifications": ("reviewed",), "input_role": "reference"})
    with StrategyBox() as box:
        rejected(invoke(box, left, right, pair), "pair_origin_missing")


@pytest.mark.parametrize("present", (False, True))
def test_optional_reference_allowance_records_only_actual_uses(declared_pair_inputs, present):
    left, right, pair = declared_pair_inputs
    primary, = pair["numerator"]["source_requirements"]
    pair["numerator"]["source_requirements"] = (primary,
        {"source_id": "publisher.reference", "qualifications": ("reviewed",), "input_role": "reference", "required": False})
    if present:
        reference = SourceUse(SourceCoordinate("publisher.reference"), "reference", "reviewed", "reference.edition.1")
        left = replace(left, source_uses=(*left.source_uses, reference))
    with StrategyBox() as box:
        result = invoke(box, left, right, pair)
        assert result.outcome == "succeeded"
        basis, = result.output("observations").evidence.calculations
        assert len(basis.source_uses) == (3 if present else 2)
        assert tuple(use for role, use in basis.source_uses if role == "numerator") == left.source_uses


def test_explicitly_allowed_declared_source_remains_declared_in_the_basis(declared_pair_inputs):
    left, right, pair = declared_pair_inputs
    use = replace(left.source_uses[0], qualification="declared", evidence_ref=None,
        coordinate=replace(left.source_uses[0].coordinate, material_identity=None))
    left = replace(left, source_uses=(use,))
    declared = dict(pair["numerator"]["source_requirements"][0])
    declared.update(qualifications=("declared",), require_evidence=False)
    pair["numerator"]["source_requirements"] = (declared,)
    with StrategyBox() as box:
        result = invoke(box, left, right, pair)
        assert result.outcome == "succeeded"
        basis, = result.output("observations").evidence.calculations
        assert basis.source_uses[0] == ("numerator", use)
        assert basis.source_uses[0][1].qualification == "declared"


@pytest.mark.parametrize("policy", ("same_source", "common_material"))
def test_other_origin_policies_keep_their_existing_contract(declared_pair_inputs, policy):
    left, right, pair = declared_pair_inputs
    pair["origin_policy"] = policy
    for role in ("numerator", "denominator"):
        pair[role].pop("source_requirements")
    if policy == "same_source":
        right = replace(right, source_uses=(replace(right.source_uses[0],
            coordinate=replace(right.source_uses[0].coordinate, source_id=left.source_uses[0].coordinate.source_id)),))
    else:
        right = replace(right, lineage=left.lineage, source_uses=(replace(right.source_uses[0],
            coordinate=replace(right.source_uses[0].coordinate, material_identity=left.lineage[0].identity)),))
    with StrategyBox() as box:
        assert invoke(box, left, right, pair).outcome == "succeeded"
