"""Source-role metadata and resolved material admission through the common catalog."""
from dataclasses import replace

import pytest

from stratbox.operations import operation_catalog
from stratbox.domains.registry.requirements import (
    SourceInstance, SourceRequirement, assess_requirements, decode_requirement,
)
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.identity import ByteIdentity


def _resolved(requirement, *, report_date="2026-10-01", step=1.0):
    return SourceInstance(requirement.source_ids[0], requirement.accepted_contracts[0],
        group_id=requirement.group_id, report_date=report_date, publication_step=step,
        issue_id="2026-10", material_identity=ByteIdentity.of(requirement.input_name.encode()), revision="release-2")


def test_sors_roles_are_projected_into_the_common_catalog_and_domain():
    catalog = operation_catalog()
    requirements = catalog.requirements("cbr.sors.prepare_inputs")
    assert len(requirements) == 11
    assert sum(item.required for item in requirements) == 10
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES
    assert tuple((item.input_name, item.series_id, item.accepted_contracts) for item in DEPENDENCIES) == tuple(
        (item.input_name, item.source_ids[0], item.accepted_contracts) for item in requirements)
    described = next(value for value in catalog.describe() if value["operation_id"] == "cbr.sors.prepare_inputs")
    assert len(described["source_requirements"]) == 11


def test_readiness_counts_missing_roles_and_retains_selected_release_and_material():
    catalog = operation_catalog()
    requirements = catalog.requirements("cbr.sors.prepare_inputs")
    available = {item.input_name: _resolved(item) for item in requirements[:8]}
    result = catalog.readiness("cbr.sors.prepare_inputs", available, report_date="2026-10-01", publication_step=1.0)
    assert result.state == "blocked"
    assert (result.supplied_count, result.required_count) == (8, 10)
    assert result.ready_count == 0
    assert result.layers.material == "unverified"
    assert sum(item.state == "missing" for item in result.requirements) == 2
    selected = result.requirements[0].instances[0]
    assert selected.issue_id == "2026-10"
    assert selected.revision == "release-2"
    assert selected.material_identity == available[requirements[0].input_name].material_identity
    available.update({item.input_name: _resolved(item) for item in requirements[8:] if item.required})
    assert catalog.readiness("cbr.sors.prepare_inputs", available).state == "conditional"


def test_same_date_step_and_perimeter_conflicts_are_explained_per_role():
    contract = DataContract("source.payload", role=DataRole.ORIGINALS)
    roles = tuple(SourceRequirement(name, ("demo.source",), (contract,), name, "sources",
                    compatibility=("report_date", "publication_step", "perimeter")) for name in ("national", "regional"))
    first = SourceInstance("demo.source", contract, report_date="2026-10-01", publication_step=1,
                           perimeter="resident", material_identity=ByteIdentity.of(b"a"))
    second = replace(first, report_date="2026-11-01", publication_step=2, perimeter="all")
    result = assess_requirements("demo.operation", roles, {"national": first, "regional": second})
    assert result.state == "blocked"
    assert all(item.state == "incompatible" for item in result.requirements)
    assert all({"source.report_date_mismatch", "source.publication_step_mismatch", "source.perimeter_mismatch"} <= set(item.reasons)
               for item in result.requirements)


def test_unresolved_evidence_is_conditional_and_collection_cardinality_is_checked():
    contract = DataContract("source.payload")
    requirement = SourceRequirement("history", ("demo.source",), (contract,), "validation", "sources", required=False, minimum=0, maximum=2)
    unresolved = SourceInstance("demo.source", contract)
    result = assess_requirements("demo.operation", (requirement,), {"history": unresolved})
    assert result.state == "conditional"
    assert "source.material_unverified" in result.requirements[0].reasons
    assert assess_requirements("demo.operation", (requirement,), {"history": (unresolved,) * 3}).state == "blocked"
    assert assess_requirements("demo.operation", (requirement,), {}).state == "inputs_verified"


def test_wrong_source_contract_and_unexpected_roles_are_not_reported_ready():
    contract = DataContract("source.payload")
    requirement = SourceRequirement("source", ("demo.source",), (contract,), "national", "sources")
    wrong = SourceInstance("demo.other", DataContract("demo.wrong"), material_identity=ByteIdentity.of(b"x"))
    result = assess_requirements("demo.operation", (requirement,), {"source": wrong, "typo": wrong})
    assert result.state == "blocked"
    assert result.unexpected_inputs == ("typo",)
    assert {"source.identity_mismatch", "source.contract_mismatch"} <= set(result.requirements[0].reasons)


def test_requirement_declarations_reject_unknown_fields_and_contradictory_multiplicity():
    with pytest.raises(ValueError, match="registry.source_requirement_invalid"):
        decode_requirement({"input_name": "source", "source_ids": ["demo.source"],
            "accepted_contracts": [{"schema_id": "source.payload"}], "role": "national", "port": "sources", "revision": "v1"})
    with pytest.raises(ValueError, match="registry.source_requirement_invalid"):
        SourceRequirement("source", ("demo.source",), (DataContract("source.payload"),), "national", "sources", minimum=2, maximum=1)


def test_inline_extension_descriptions_and_readiness_do_not_require_packaged_records():
    from stratbox.core.execution.contracts import OperationDefinition
    from stratbox.operations.catalog import OperationCatalog, OperationRef
    definition = OperationDefinition("extension.inspect", "extension-inspect", object, object)
    catalog = OperationCatalog((OperationRef("extension.inspect", "extension.handlers:inspect", definition=definition),))
    assert catalog.describe()[0]["source_requirements"] == ()
    assert catalog.page().entries[0]["operation_id"] == "extension.inspect"
    assert catalog.requirements("extension.inspect") == ()
    assert catalog.readiness("extension.inspect", {}).state == "requirements_satisfied"
