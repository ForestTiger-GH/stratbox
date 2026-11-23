"""Evidence admission for immutable logical escrow values."""
from dataclasses import asdict, replace
from stratbox.core.operations.tables import record_tables, use_tables
from . import snapshots

def dataset_evidence(value):
    return (("observations", value.observations), ("rows", value.rows)), {
        "releases": [asdict(release) for release in value.releases],
        "indicators": [asdict(spec) for spec in value.indicator_specs],
        "coverage": asdict(value.coverage), "selection_complete": value.selection_complete,
        "failures": value.failures, "stop_reason": value.stop_reason, "integration_profile": value.integration_profile,
    }


def seal_dataset(value, invocation, *, checkpoint=None):
    snapshots.dataset_tables(value)
    tables, metadata = dataset_evidence(value)
    return replace(value, evidence=record_tables(invocation, tables, metadata=metadata, checkpoint=checkpoint))


def use_dataset(value, invocation):
    tables, metadata = dataset_evidence(value)
    observations, rows = use_tables(invocation, tables, receipt=value.evidence, metadata=metadata, role="escrow_dataset")
    copied = replace(value, observations=observations, rows=rows)
    snapshots.dataset_tables(copied)
    return copied
