"""Data-only SORS snapshots including the inputs needed for continuation.

A strict result owns its source bundle and run configuration. A crosswalk result
owns its strict result and mapping configuration. Solver sessions and matrices
are rebuilt by the computational operations; snapshots never serialize them.
"""
from __future__ import annotations

from dataclasses import asdict, fields, replace
from datetime import date
import json
from math import isfinite

from stratbox.core.formats.dataframes import frame_from_table, frame_to_table
from stratbox.shared.data.lineage import computation_from, computation_value, input_from, input_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.source_context import source_use_value, source_use_from
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable, coverage_from
from stratbox.shared.data.tables import TABLE_ENCODING, table_identity
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsCrosswalkConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsDeterministicConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsOptimizationConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsSelectionPolicy
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsTargetScope
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import contract_coordinates
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsCrosswalkResult
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsRestorationResult
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsRunSummary

BUNDLE = DataContract("cbr.sors.bundle.snapshot", 1, DataRole.INTEGRATED)
RESTORATION = DataContract("cbr.sors.restoration.snapshot", 1, DataRole.INTEGRATED)
CROSSWALK = DataContract("cbr.sors.crosswalk.snapshot", 1, DataRole.INTEGRATED)
CONTEXT = TableSchema(DataContract("cbr.sors.snapshot.context", 1), (ColumnSchema("context", ScalarType.TEXT),))
DESCRIPTORS = TableSchema(DataContract("cbr.sors.snapshot.frames", 1),
    (ColumnSchema("component", ScalarType.TEXT), ColumnSchema("descriptor", ScalarType.TEXT)), ("component",))
_PROFILE = "sors-replay-context-1"
_KINDS = {SorsSourceBundle: "bundle", SorsRestorationResult: "restoration", SorsCrosswalkResult: "crosswalk"}
_CONTRACTS = {"bundle": BUNDLE, "restoration": RESTORATION, "crosswalk": CROSSWALK}
_TYPES = {kind: cls for cls, kind in _KINDS.items()}
_MAX_CELLS = 80_000_000


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _parse_json(text):
    value = json.loads(text)
    if _json(value) != text:
        raise ValueError("sors.snapshot_noncanonical_metadata")
    return value


def _dependency_values():
    return _parse_json(_json([asdict(item) for item in DEPENDENCIES]))


def _exact_keys(value, cls):
    if not isinstance(value, dict) or set(value) != {field.name for field in fields(cls)}:
        raise ValueError("sors.snapshot_config_invalid")
    return dict(value)


def _scope(value):
    mapping = _exact_keys(value, SorsTargetScope)
    for key in mapping:
        if not isinstance(mapping[key], list) or any(type(item) is not str for item in mapping[key]):
            raise ValueError("sors.snapshot_scope_invalid")
        mapping[key] = tuple(mapping[key])
    return SorsTargetScope(**mapping)


def run_config_from(value):
    mapping = _exact_keys(value, SorsRunConfig)
    mapping["deterministic"] = SorsDeterministicConfig(**_exact_keys(mapping["deterministic"], SorsDeterministicConfig))
    optimization = _exact_keys(mapping["optimization"], SorsOptimizationConfig)
    optimization["scope"] = _scope(optimization["scope"])
    optimization["selection"] = SorsSelectionPolicy(**_exact_keys(optimization["selection"], SorsSelectionPolicy))
    mapping["optimization"] = SorsOptimizationConfig(**optimization)
    config = SorsRunConfig(**mapping)
    date.fromisoformat(config.as_of_date)
    return config


def crosswalk_config_from(value):
    mapping = _exact_keys(value, SorsCrosswalkConfig)
    mapping["scope"] = _scope(mapping["scope"])
    if not isinstance(mapping["scenario_ids"], list) or any(type(item) is not str for item in mapping["scenario_ids"]):
        raise ValueError("sors.snapshot_scope_invalid")
    mapping["scenario_ids"] = tuple(mapping["scenario_ids"])
    return SorsCrosswalkConfig(**mapping)


def _summary(value):
    mapping = _exact_keys(value, SorsRunSummary)
    if not isinstance(mapping["portfolio_scopes"], list):
        raise ValueError("sors.snapshot_summary_invalid")
    mapping["portfolio_scopes"] = tuple(mapping["portfolio_scopes"])
    result = SorsRunSummary(**mapping)
    date.fromisoformat(result.as_of_date)
    return result


def _grid_names(cls):
    return tuple(field.name for field in fields(cls) if field.name.endswith("_grid"))


def grid_identity(value):
    from .identity import grid_metadata as _grid_metadata
    from .identity import grid_tables as _grid_tables
    identity = table_identity(_grid_tables(value), allow_infinite=True)
    metadata = _grid_metadata(value)
    return ByteIdentity.of(canonical_manifest_bytes({"encoding": TABLE_ENCODING,
        "tables": [identity.sha256, identity.size], "metadata": metadata})) if metadata is not None else identity


def validate_seal(value):
    if value.evidence is None:
        raise ValueError("sors.snapshot_unsealed")
    if grid_identity(value) != value.evidence.output:
        raise ValueError("sors.snapshot_evidence_mismatch")


def _validate_bundle(value):
    if value.method_version != "sors-source-bundle-2":
        raise ValueError("sors.snapshot_bundle_profile_unsupported")
    if value.as_of_date is None or value.publication_step is None:
        raise ValueError("sors.snapshot_source_parameters_required")
    date.fromisoformat(value.as_of_date)
    if not isfinite(value.publication_step) or value.publication_step <= 0:
        raise ValueError("sors.snapshot_source_parameters_invalid")
    # Every declared role is recorded, including the absent optional input.
    # Partial source contexts cannot be advertised as replayable models.
    manifest = value.dependency_manifest_grid
    if manifest.empty:
        raise ValueError("sors.snapshot_dependencies_incomplete")
    else:
        expected = tuple((item.input_name, item.source_series, item.series_id, item.required) for item in DEPENDENCIES)
        if not {"input_name", "source_series", "series_id", "source_role", "method_version", "accepted_contracts", "compatibility_rule", "required", "status", "as_of_date", "publication_step", "original_sha256", "original_size", "source_id", "input_kind"} <= set(manifest.columns):
            raise ValueError("sors.snapshot_dependencies_invalid")
        actual = tuple(manifest[["input_name", "source_series", "series_id", "required"]].itertuples(index=False, name=None))
        if actual != expected or not manifest["as_of_date"].eq(value.as_of_date).all() or not manifest["publication_step"].eq(value.publication_step).all():
            raise ValueError("sors.snapshot_dependencies_invalid")
        resolved = []
        for declaration, row in zip(DEPENDENCIES, manifest.itertuples(index=False), strict=True):
            if (type(row.required) is not bool or row.method_version != declaration.method_version or row.source_role != declaration.source_role
                    or row.accepted_contracts != contract_coordinates(declaration) or row.compatibility_rule != declaration.compatibility_rule):
                raise ValueError("sors.snapshot_dependencies_invalid")
            if row.status not in {"resolved", "not_supplied"} or row.required and row.status != "resolved":
                raise ValueError("sors.snapshot_dependencies_incomplete")
            if row.status == "resolved":
                if type(row.original_size) is not int:
                    raise ValueError("sors.snapshot_dependency_identity_mismatch")
                matching = tuple(receipt for receipt in value.lineage if receipt.role == row.source_series)
                if (len(matching) != 1 or matching[0].identity != ByteIdentity(row.original_sha256, row.original_size)
                        or matching[0].source_id != row.source_id or row.input_kind not in {"original", "flake"}):
                    raise ValueError("sors.snapshot_dependency_identity_mismatch")
                resolved.append(row)
            elif any(item is not None for item in (row.original_sha256, row.original_size, row.source_id, row.input_kind)):
                raise ValueError("sors.snapshot_dependencies_invalid")
        published = value.source_manifest_grid
        if not {"source_series", "sha256", "size_bytes"} <= set(published.columns) or len(published) != len(resolved):
            raise ValueError("sors.snapshot_source_manifest_mismatch")
        for row in resolved:
            matched = published[published["source_series"].eq(row.source_series)]
            if len(matched) != 1 or matched.iloc[0]["sha256"] != row.original_sha256 or matched.iloc[0]["size_bytes"] != row.original_size:
                raise ValueError("sors.snapshot_source_manifest_mismatch")
    validate_seal(value)


def _validate_restoration(value):
    if not isinstance(value.source_bundle, SorsSourceBundle) or not isinstance(value.run_config, SorsRunConfig):
        raise ValueError("sors.snapshot_context_required")
    _validate_bundle(value.source_bundle)
    if (value.summary.as_of_date != value.run_config.as_of_date or value.summary.publication_step != value.run_config.publication_step
            or value.source_bundle.as_of_date != value.run_config.as_of_date or value.source_bundle.publication_step != value.run_config.publication_step):
        raise ValueError("sors.snapshot_context_parameters_mismatch")
    for name in ("source_grid", "source_manifest_grid", "validation_grid"):
        if table_identity(((name, getattr(value, name)),), allow_infinite=True) != table_identity(((name, getattr(value.source_bundle, name)),), allow_infinite=True):
            raise ValueError("sors.snapshot_source_context_mismatch")
    validate_seal(value)


def validate_context(value):
    if isinstance(value, SorsSourceBundle):
        _validate_bundle(value)
    elif isinstance(value, SorsRestorationResult):
        _validate_restoration(value)
    elif isinstance(value, SorsCrosswalkResult):
        if not isinstance(value.strict_result, SorsRestorationResult) or not isinstance(value.crosswalk_config, SorsCrosswalkConfig):
            raise ValueError("sors.snapshot_context_required")
        _validate_restoration(value.strict_result)
        validate_seal(value)
    else:
        raise ValueError("sors.snapshot_kind_invalid")


def _owners(value):
    if isinstance(value, SorsSourceBundle):
        return (("bundle", value),)
    if isinstance(value, SorsRestorationResult):
        return (("bundle", value.source_bundle), ("restoration", value))
    return (("bundle", value.strict_result.source_bundle), ("restoration", value.strict_result), ("crosswalk", value))


def _context(value):
    common = {"kind": _KINDS[type(value)], "evidence": computation_value(value.evidence)}
    if isinstance(value, SorsSourceBundle):
        return {**common, "as_of_date": value.as_of_date, "publication_step": value.publication_step,
                "lineage": [input_value(item) for item in value.lineage], "coverage": asdict(value.coverage), "method_version": value.method_version,
                "source_uses": [source_use_value(use) for use in value.source_uses]}
    if isinstance(value, SorsRestorationResult):
        return {**common, "summary": asdict(value.summary), "run_config": asdict(value.run_config)}
    return {**common, "crosswalk_run_id": value.crosswalk_run_id, "status": value.status, "crosswalk_config": asdict(value.crosswalk_config)}


def snapshot(value, *, dataset_id=None, version_id=None, checkpoint=None):
    validate_context(value)
    owners = _owners(value)
    kind = _KINDS[type(value)]
    context = {"profile": _PROFILE, "kind": kind,
               "dependencies": _dependency_values(),
               "owners": {name: _context(owner) for name, owner in owners}}
    tables, descriptors = [], []
    for name, owner in owners:
        for grid in _grid_names(type(owner)):
            if checkpoint is not None:
                checkpoint()
            component = f"{name}.{grid}"
            table, descriptor = frame_to_table(getattr(owner, grid), contract=DataContract(f"cbr.sors.frame.{grid}", 1, DataRole.INTEGRATED),
                                               max_cells=_MAX_CELLS, checkpoint=checkpoint)
            tables.append((component, table))
            descriptors.append((component, _json(descriptor)))
    tables = (("context", TypedTable(CONTEXT, ((_json(context),),))), ("frames", TypedTable(DESCRIPTORS, tuple(descriptors))), *tables)
    input_receipts = list(owners[0][1].lineage)
    # Mapping and classifier use records remain pinned even when originals are
    # unavailable locally. They are historical evidence, not new acquisitions.
    if value.evidence is not None:
        input_receipts.extend(value.evidence.inputs)
    pinned = tuple(dict.fromkeys(replace(item, availability="reference_only") for item in input_receipts))
    coverage = owners[0][1].coverage
    version = version_id or ByteIdentity.of(canonical_manifest_bytes({
        "profile": _PROFILE, "kind": kind, "tables": [[name, table.identity.sha256, table.identity.size] for name, table in tables],
        "coverage": asdict(coverage), "inputs": [input_value(item) for item in pinned],
    })).sha256
    return DatasetSnapshot.build(dataset_id or f"cbr.sors.{kind}", version, _CONTRACTS[kind], tables, coverage=coverage, inputs=pinned)


def from_snapshot(value, *, expected_kind=None, checkpoint=None):
    if not isinstance(value, DatasetSnapshot) or not value.complete:
        raise ValueError("sors.snapshot_incomplete")
    try:
        context_table, frame_table = value.table("context"), value.table("frames")
    except KeyError:
        raise ValueError("sors.snapshot_structure_invalid") from None
    if context_table.schema != CONTEXT or len(context_table.rows) != 1 or frame_table.schema != DESCRIPTORS:
        raise ValueError("sors.snapshot_structure_invalid")
    context = _parse_json(context_table.rows[0][0])
    if (not isinstance(context, dict) or set(context) != {"profile", "kind", "dependencies", "owners"}
            or context["profile"] != _PROFILE or context["kind"] not in _CONTRACTS
            or context["dependencies"] != _dependency_values()):
        raise ValueError("sors.snapshot_profile_unsupported")
    kind = context["kind"]
    if expected_kind is not None and kind != expected_kind or value.manifest.contract != _CONTRACTS[kind]:
        raise ValueError("sors.snapshot_kind_invalid")
    owner_names = {"bundle": ("bundle",), "restoration": ("bundle", "restoration"), "crosswalk": ("bundle", "restoration", "crosswalk")}[kind]
    if not isinstance(context["owners"], dict) or set(context["owners"]) != set(owner_names):
        raise ValueError("sors.snapshot_context_required")
    expected_frames = tuple(f"{name}.{grid}" for name in owner_names for grid in _grid_names(_TYPES[name]))
    if (tuple(name for name, _ in frame_table.rows) != expected_frames
            or tuple(name for name, _ in value.tables) != ("context", "frames", *expected_frames)):
        raise ValueError("sors.snapshot_structure_invalid")
    frames = {}
    for name, descriptor in frame_table.rows:
        grid = name.split(".", 1)[1]
        table = value.table(name)
        if table.schema.contract != DataContract(f"cbr.sors.frame.{grid}", 1, DataRole.INTEGRATED):
            raise ValueError("sors.snapshot_frame_contract_invalid")
        frames[name] = frame_from_table(table, _parse_json(descriptor), max_cells=_MAX_CELLS, checkpoint=checkpoint)
    restored = {}
    for name in owner_names:
        metadata = context["owners"][name]
        cls = _TYPES[name]
        grids = {grid: frames[f"{name}.{grid}"] for grid in _grid_names(cls)}
        expected = {"kind", "evidence"} | ({"as_of_date", "publication_step", "lineage", "coverage", "method_version", "source_uses"} if name == "bundle"
                    else {"summary", "run_config"} if name == "restoration" else {"crosswalk_run_id", "status", "crosswalk_config"})
        if not isinstance(metadata, dict) or set(metadata) != expected or metadata["kind"] != name:
            raise ValueError("sors.snapshot_context_invalid")
        evidence = computation_from(metadata["evidence"])
        if name == "bundle":
            restored[name] = SorsSourceBundle(**grids, evidence=evidence, as_of_date=metadata["as_of_date"], publication_step=metadata["publication_step"],
                lineage=tuple(input_from(item) for item in metadata["lineage"]), coverage=coverage_from(metadata["coverage"]), method_version=metadata["method_version"],
                source_uses=tuple(source_use_from(item) for item in metadata["source_uses"]))
        elif name == "restoration":
            restored[name] = SorsRestorationResult(**grids, evidence=evidence, summary=_summary(metadata["summary"]),
                                                   source_bundle=restored["bundle"], run_config=run_config_from(metadata["run_config"]))
        else:
            restored[name] = SorsCrosswalkResult(**grids, evidence=evidence, strict_result=restored["restoration"],
                crosswalk_config=crosswalk_config_from(metadata["crosswalk_config"]), status=metadata["status"], crosswalk_run_id=metadata["crosswalk_run_id"])
    result = restored[kind]
    validate_context(result)
    if value.manifest.coverage != restored["bundle"].coverage:
        raise ValueError("sors.snapshot_coverage_mismatch")
    input_receipts = [*restored["bundle"].lineage, *result.evidence.inputs]
    pinned = tuple(dict.fromkeys(replace(item, availability="reference_only") for item in input_receipts))
    if value.manifest.inputs != pinned or value.manifest.parents:
        raise ValueError("sors.snapshot_lineage_mismatch")
    return result
