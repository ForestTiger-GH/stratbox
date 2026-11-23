"""Semantic admission preserves editions, qualifications and incomplete outcomes."""

from dataclasses import replace
from typing import get_type_hints

import pytest

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution import OperationDefinition
from stratbox.shared.data.operations import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
    StageDeclaration,
    assess_input,
    compatible_ports,
)

SOURCE = DataContract("example.source", 1, DataRole.ORIGINALS)
EXTRACT = DataContract("example.extract", 1, DataRole.EXTRACTS)


def test_definition_type_hints_are_resolvable_for_application_schema_adapters():
    assert (
        get_type_hints(OperationDefinition)["processing"] == OperationSemantics | None
    )


def test_roles_do_not_define_schema_compatibility_or_storage_locations():
    port = InputPort("source", SOURCE)
    assert compatible_ports(OutputPort("original", SOURCE), port)
    assert not compatible_ports(
        OutputPort("original", replace(SOURCE, version=2)), port
    )
    assert not compatible_ports(
        OutputPort("original", replace(SOURCE, schema_id="other.source")), port
    )
    assert not compatible_ports(
        OutputPort("extract", replace(SOURCE, role=DataRole.EXTRACTS)), port
    )


@pytest.mark.parametrize("outcome", ["unknown", "failed", "cancelled", "partial"])
def test_success_qualifications_cannot_promote_an_incomplete_outcome(outcome):
    port = InputPort(
        "dataset",
        EXTRACT,
        qualifications=frozenset({"validated"}),
        coverage=frozenset({"all_regions"}),
    )
    assessment = assess_input(
        port,
        EXTRACT,
        outcome=outcome,
        qualifications=frozenset({"validated"}),
        coverage=frozenset({"all_regions"}),
    )
    assert not assessment.compatible
    assert assessment.reasons == ("processing.outcome_not_accepted",)


def test_explicit_partial_policy_still_requires_the_requested_coverage():
    port = InputPort(
        "dataset",
        EXTRACT,
        outcomes=frozenset({"succeeded", "partial"}),
        qualifications=frozenset({"validated"}),
        coverage=frozenset({"selected_regions"}),
    )
    missing = assess_input(
        port, EXTRACT, outcome="partial", qualifications=frozenset({"validated"})
    )
    assert missing.reasons == ("processing.coverage_missing",)
    assert assess_input(
        port,
        EXTRACT,
        outcome="partial",
        qualifications=frozenset({"validated"}),
        coverage=frozenset({"selected_regions"}),
    ).compatible


def test_explicit_alternative_does_not_create_a_generic_wildcard():
    port = InputPort("dataset", EXTRACT, alternatives=(SOURCE,))
    assert compatible_ports(OutputPort("original", SOURCE), port)
    assert not compatible_ports(
        OutputPort("other", DataContract("unknown", 1, DataRole.ORIGINALS)), port
    )
    with pytest.raises(ValueError, match="processing.invalid_alternatives"):
        replace(port, alternatives=(SOURCE, SOURCE))


def test_qualifications_and_coverage_are_independently_required():
    port = InputPort(
        "dataset",
        EXTRACT,
        qualifications=frozenset({"reported"}),
        coverage=frozenset({"complete"}),
    )
    assessment = assess_input(port, SOURCE, outcome="succeeded")
    assert assessment.reasons == (
        "processing.schema_mismatch",
        "processing.qualification_missing",
        "processing.coverage_missing",
    )


def test_definition_must_admit_every_advertised_output_outcome():
    semantics = OperationSemantics(
        (ProcessingStage.EXTRACT,),
        outputs=(OutputPort("extract", EXTRACT, outcomes=frozenset({"partial"})),),
        summary="Extract selected source data.",
    )
    with pytest.raises(ValueError, match="processing.partial_output_undeclared"):
        OperationDefinition(
            "example.parse", "method-1", str, str, processing=semantics
        )
    assert (
        OperationDefinition(
            "example.parse",
            "method-1",
            str,
            str,
            partial_allowed=True,
            processing=semantics,
        ).processing
        is semantics
    )


def test_invalid_roles_ports_and_stage_claims_are_rejected():
    with pytest.raises(ValueError, match="processing.invalid_role"):
        DataContract("example", 1, "extracts")
    with pytest.raises(ValueError, match="processing.invalid_schema_version"):
        DataContract("example", True, DataRole.EXTRACTS)
    with pytest.raises(ValueError, match="processing.invalid_path"):
        InputPort("source", SOURCE, path="source.__dict__")
    with pytest.raises(ValueError, match="processing.invalid_stages"):
        OperationSemantics(
            (ProcessingStage.EXTRACT, ProcessingStage.EXTRACT),
            summary="Duplicate stage.",
        )
    with pytest.raises(ValueError, match="processing.invalid_ports"):
        OperationSemantics(
            (ProcessingStage.EXTRACT,),
            inputs=(InputPort("source", SOURCE), InputPort("source", SOURCE)),
            summary="Duplicate port.",
        )
    with pytest.raises(ValueError, match="processing.delegation_binding_required"):
        StageDeclaration(ProcessingStage.EXTRACT, "delegated", "test.delegate")
