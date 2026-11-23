"""One FNS operation owner; families and processing stages remain explicit."""
from stratbox.core.execution.catalog import OperationRef, OperationRegistration
from stratbox.core.execution.semantics import OperationKey, ProcessingStage, StageDeclaration

_BASE = "stratbox.domains.fns.operations"
_OPERATIONS = []
for _family, _series in (("sme", "fns.sme"), ("legal_entities", "fns.1yur")):
    for _name, _definition, _version in (('discover', 'DISCOVER', 1), ('acquire', 'ACQUIRE', 1), ('parse', 'PARSE', 1), ('capture', 'CAPTURE', 1), ('read_representation', 'READ', 1), ('compare', 'COMPARE', 2)):
        _OPERATIONS.append(OperationRef(_series + "." + _name, _version,
            _BASE + "." + _family + ".definitions:" + _definition,
            _BASE + "." + _family + ".operations:" + _name))
    for _name in ('extract', 'readable', 'validate', 'compare_flakes', 'project', 'align', 'compare_datasets', 'calculate_changes', 'calculate_shares', 'view', 'render', 'flake_snapshot', 'read_flake_snapshot', 'projection_snapshot', 'read_projection_snapshot', 'dataset_snapshot', 'read_dataset_snapshot', 'calculation_snapshot', 'read_calculation_snapshot', 'view_snapshot', 'read_view_snapshot', 'process', 'capture_full', 'render_artifact', 'readable_artifact'):
        _OPERATIONS.append(OperationRef(_series + "." + _name, 1,
            _BASE + "." + _family + ".definitions:" + _name.upper(),
            _BASE + "." + _family + ".pipeline:" + _name))

REGISTRATION = OperationRegistration(
    owner_id="fns", operations=tuple(_OPERATIONS),
    source_catalog_ref="stratbox.domains.fns.operations.source_catalog:source_cards",
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "fns.neutral_storage",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
             OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1),
             OperationKey("material.save_artifact", 1)),
            "Bind acquired payloads to neutral original storage; encode any flake, projection, integrated dataset, calculation or view as a snapshot and retain it with the selected dataset adapter."),
        StageDeclaration(ProcessingStage.INGEST, "delegated", "fns.neutral_dataset_ingestion",
            (OperationKey("dataset.write_snapshot", 1),),
            "Pass a domain snapshot to WriteSnapshotRequest.snapshot and choose the consumer-owned dataset adapter; source and interpretation identities remain in the manifest."),
        StageDeclaration(ProcessingStage.PUBLISH, "inapplicable", "fns.publication_policy_owned_by_consumer"),
    ),
)
