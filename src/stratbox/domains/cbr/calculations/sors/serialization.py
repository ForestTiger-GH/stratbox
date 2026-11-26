"""Bounded data-only snapshots of SORS values and resumable numerical states.

The type vocabulary is local and explicit. Encoded data never selects an import
or creates a solver session. The current Stratbox build owns this contract.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import json

import numpy as np
import pandas as pd

from stratbox.shared.data.frame_codec import _atom, _unatom, _axis_value, _axis_from, _dtype_value, _dtype_from
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.coverage import SnapshotCoverage, CoverageDimension
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext
from stratbox.shared.data.values import Assessment, DerivedDataset, SourceDataset, IntegratedDataset, EncodedProduct, View

from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsWorkbookRequest, SorsPivotRequest
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsViewPack, SorsPivotResult
from stratbox.domains.cbr.calculations.sors.identity import SorsContentEvidence
from stratbox.domains.cbr.calculations.sors.crosswalk.problem import CrosswalkCompilation
from stratbox.domains.cbr.calculations.sors.crosswalk.analysis import _ScenarioExecution
from stratbox.domains.cbr.calculations.sors.crosswalk.stages import (CrosswalkModel, CrosswalkState, CrosswalkCandidates,
                               CrosswalkProblem, CrosswalkFeasibility, CrosswalkOptimization)
from stratbox.domains.cbr.calculations.sors.contracts import (SorsRunConfig, SorsCrosswalkConfig, SorsDeterministicConfig,
                        SorsOptimizationConfig, SorsSelectionPolicy, SorsTargetScope)
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.calculations.sors.results import SorsRestorationResult, SorsCrosswalkResult, SorsRunSummary
from stratbox.domains.cbr.calculations.sors.strict.quantities import SorsQuantityGraph
from stratbox.domains.cbr.calculations.sors.strict.compiler import StrictCompilation
from stratbox.domains.cbr.calculations.sors.strict.solver import StrictFeasibilityExecution
from stratbox.domains.cbr.calculations.sors.strict.interval_closure import SorsIntervalClosureState
from stratbox.domains.cbr.calculations.sors.publication.partitions import SorsPublicationGraph
from stratbox.domains.cbr.calculations.sors.publication.ledger import SorsPublicationLedger
from stratbox.domains.cbr.calculations.sors.linear.contracts import CsrMatrixData, SorsLinearProblem, LinearTarget
from stratbox.domains.cbr.calculations.sors.linear.highs import SolveResult
from stratbox.domains.cbr.calculations.sors.stages import (SorsModelInputs, SorsConstraintModel, SorsInferenceState,
                     SorsCandidateFacts, SorsCompiledProblem, SorsFeasibilityAssessment,
                     SorsOptimizationProposal, SorsOptimizationRecord, SorsCertifiedValues)


_CLASSES = (
    SorsRunConfig, SorsCrosswalkConfig, SorsDeterministicConfig, SorsOptimizationConfig,
    SorsSelectionPolicy, SorsTargetScope, SorsSourceBundle, SorsRestorationResult,
    SorsCrosswalkResult, SorsRunSummary, SorsQuantityGraph, StrictCompilation,
    StrictFeasibilityExecution, SorsPublicationGraph, SorsPublicationLedger,
    CsrMatrixData, SorsLinearProblem, LinearTarget, SolveResult,
    SorsModelInputs, SorsConstraintModel, SorsInferenceState, SorsCandidateFacts,
    SorsCompiledProblem, SorsFeasibilityAssessment, SorsOptimizationProposal, SorsOptimizationRecord,
    SorsCertifiedValues, ByteIdentity, UsedInputReceipt, SorsContentEvidence,
    SnapshotCoverage, CoverageDimension, SourceCoordinate, SourceUse, ValueContext,
    Assessment, DerivedDataset, SourceDataset, IntegratedDataset, View,
    SorsWorkbookRequest, SorsPivotRequest, SorsViewPack, SorsPivotResult,
    CrosswalkCompilation, _ScenarioExecution, CrosswalkModel, CrosswalkState,
    CrosswalkCandidates, CrosswalkProblem, CrosswalkFeasibility, CrosswalkOptimization,
)
_TYPES = {cls.__name__: cls for cls in _CLASSES}
assert len(_TYPES) == len(_CLASSES)


def _option(settings, context, name, default):
    params = getattr(context, "parameters", {}) if context is not None else {}
    return params.get(name, settings.get(name, default) if isinstance(settings, Mapping) else default)


def _checkpoint(context):
    if context is not None and hasattr(context, "checkpoint"):
        context.checkpoint()


def encode(value, *, max_bytes=256 * 1024 * 1024, max_cells=80_000_000, context=None):
    cells = 0

    def pack(item, depth=0):
        nonlocal cells
        if depth > 128:
            raise ValueError("sors.snapshot_depth_limit")
        if isinstance(item, pd.DataFrame):
            cells += item.size
            if cells > max_cells:
                raise ValueError("sors.snapshot_cell_limit")
            _checkpoint(context)
            return {"frame": {
                "columns": _axis_value(item.columns), "index": _axis_value(item.index),
                "dtypes": [_dtype_value(dtype) for dtype in item.dtypes],
                "rows": [[pack(v, depth + 1) for v in row] for row in item.itertuples(index=False, name=None)],
            }}
        if isinstance(item, np.ndarray):
            if item.dtype.kind not in "biuf":
                raise TypeError("sors.snapshot_array_dtype")
            cells += item.size
            if cells > max_cells:
                raise ValueError("sors.snapshot_cell_limit")
            return {"array": {"dtype": str(item.dtype), "shape": list(item.shape),
                              "values": pack(item.ravel().tolist(), depth + 1)}}
        if isinstance(item, SorsIntervalClosureState):
            return {"closure": pack({
                "quantities": item.quantities_grid, "relations": item._relations_grid,
                "bindings": item._bindings_grid, "derivations": item.derivations_grid,
                "conflicts": item.conflicts_grid, "tolerance": item.tolerance,
                "max_passes": item.max_passes, "total_passes": item.total_passes,
                "total_bound_updates": item.total_bound_updates,
            }, depth + 1)}
        if type(item) in _CLASSES:
            return {"record": type(item).__name__, "fields": {
                field.name: pack(getattr(item, field.name), depth + 1) for field in fields(item) if field.init}}
        if is_dataclass(item):
            raise TypeError("sors.snapshot_unadmitted_type")
        if isinstance(item, Mapping):
            if any(type(key) is not str for key in item):
                raise TypeError("sors.snapshot_string_keys_required")
            # Row dictionaries also determine table column order when a ledger
            # is materialized. Retain their order explicitly in the data format.
            return {"mapping": [[key, pack(value, depth + 1)] for key, value in item.items()]}
        if isinstance(item, (tuple, list)):
            return {"tuple" if isinstance(item, tuple) else "list": [pack(v, depth + 1) for v in item]}
        if isinstance(item, (set, frozenset)):
            values = [pack(v, depth + 1) for v in item]
            return {"set": sorted(values, key=lambda x: json.dumps(x, sort_keys=True))}
        return {"scalar": _atom(item)}

    data = json.dumps({"kind": "sors.value", "value": pack(value)}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(data) > max_bytes:
        raise ValueError("sors.snapshot_byte_limit")
    return data


def decode(data, *, max_bytes=256 * 1024 * 1024, max_cells=80_000_000, context=None):
    if type(data) is not bytes or len(data) > max_bytes:
        raise ValueError("sors.snapshot_byte_limit")
    cells = 0

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("sors.snapshot_duplicate_key")
            result[key] = value
        return result

    def unpack(item, depth=0):
        nonlocal cells
        if depth > 128 or not isinstance(item, dict):
            raise ValueError("sors.snapshot_structure_invalid")
        if set(item) == {"scalar"}:
            return _unatom(item["scalar"])
        if set(item) == {"mapping"} and isinstance(item["mapping"], list):
            result = {}
            for pair in item["mapping"]:
                if not isinstance(pair, list) or len(pair) != 2 or type(pair[0]) is not str or pair[0] in result:
                    raise ValueError("sors.snapshot_mapping_invalid")
                result[pair[0]] = unpack(pair[1], depth + 1)
            return result
        for tag, constructor in (("tuple", tuple), ("list", list), ("set", frozenset)):
            if set(item) == {tag} and isinstance(item[tag], list):
                return constructor(unpack(value, depth + 1) for value in item[tag])
        if set(item) == {"record", "fields"}:
            cls = _TYPES.get(item["record"])
            if cls is None or not isinstance(item["fields"], dict):
                raise ValueError("sors.snapshot_unadmitted_type")
            if set(item["fields"]) != {field.name for field in fields(cls) if field.init}:
                raise ValueError("sors.snapshot_record_fields_invalid")
            return cls(**{key: unpack(value, depth + 1) for key, value in item["fields"].items()})
        if set(item) == {"frame"}:
            value = item["frame"]
            if not isinstance(value, dict) or set(value) != {"columns", "index", "dtypes", "rows"}:
                raise ValueError("sors.snapshot_frame_invalid")
            columns, index = _axis_from(value["columns"]), _axis_from(value["index"])
            if not isinstance(value["rows"], list) or len(value["rows"]) != len(index):
                raise ValueError("sors.snapshot_frame_invalid")
            cells += len(columns) * len(index)
            if cells > max_cells:
                raise ValueError("sors.snapshot_cell_limit")
            if len(value["dtypes"]) != len(columns) or any(len(row) != len(columns) for row in value["rows"]):
                raise ValueError("sors.snapshot_frame_invalid")
            _checkpoint(context)
            # Construct each column in its declared dtype. Building an inferred
            # frame first would turn object-column None into NaN irreversibly.
            restored = [[unpack(v, depth + 1) for v in row] for row in value["rows"]]
            series = [pd.Series([row[position] for row in restored], index=index,
                                dtype=_dtype_from(dtype))
                      for position, dtype in enumerate(value["dtypes"])]
            result = pd.concat(series, axis=1) if series else pd.DataFrame(index=index)
            result.columns = columns
            return result
        if set(item) == {"array"}:
            value = item["array"]
            if not isinstance(value, dict) or set(value) != {"dtype", "shape", "values"}:
                raise ValueError("sors.snapshot_array_invalid")
            dtype = np.dtype(value["dtype"])
            if dtype.kind not in "biuf" or not isinstance(value["shape"], list):
                raise ValueError("sors.snapshot_array_invalid")
            shape = tuple(value["shape"])
            if any(type(n) is not int or n < 0 for n in shape):
                raise ValueError("sors.snapshot_array_invalid")
            size = 1
            for n in shape:
                size *= n
            cells += size
            if cells > max_cells:
                raise ValueError("sors.snapshot_cell_limit")
            values = unpack(value["values"], depth + 1)
            if not isinstance(values, list) or len(values) != size:
                raise ValueError("sors.snapshot_array_invalid")
            return np.asarray(values, dtype=dtype).reshape(shape)
        if set(item) == {"closure"}:
            value = unpack(item["closure"], depth + 1)
            if set(value) != {"quantities", "relations", "bindings", "derivations", "conflicts", "tolerance",
                             "max_passes", "total_passes", "total_bound_updates"}:
                raise ValueError("sors.snapshot_closure_invalid")
            result = SorsIntervalClosureState(SorsQuantityGraph(value["quantities"], value["relations"], value["bindings"]),
                                              tolerance=value["tolerance"], max_passes=value["max_passes"])
            result.derivations_grid, result.conflicts_grid = value["derivations"], value["conflicts"]
            result.total_passes, result.total_bound_updates = value["total_passes"], value["total_bound_updates"]
            return result
        raise ValueError("sors.snapshot_structure_invalid")

    try:
        payload = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError("sors.snapshot_nonfinite")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("sors.snapshot_structure_invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {"kind", "value"} or payload["kind"] != "sors.value":
        raise ValueError("sors.snapshot_structure_invalid")
    return unpack(payload["value"])


def value_encode(inputs, settings, context):
    data = encode(inputs["value"], max_bytes=_option(settings, context, "max_bytes", 256 * 1024 * 1024),
                  max_cells=_option(settings, context, "max_cells", 80_000_000), context=context)
    value = inputs["value"]
    lineage = tuple(getattr(value, "lineage", ()))
    if not lineage and isinstance(value, (SorsRestorationResult, SorsCrosswalkResult)):
        strict = value.strict_result if isinstance(value, SorsCrosswalkResult) else value
        lineage = tuple(strict.source_bundle.lineage) if strict.source_bundle else ()
    uses = tuple(getattr(value, "source_uses", ()))
    if not uses and isinstance(value, (SorsRestorationResult, SorsCrosswalkResult)):
        from stratbox.domains.cbr.calculations.sors.identity import source_uses
        uses = source_uses(value)
    return {"representation": EncodedProduct(data, "application/vnd.stratbox.sors+json", lineage, source_uses=uses,
        assessment=getattr(value, "assessment", None))}


def value_decode(inputs, settings, context):
    from stratbox.core.commands._physical import bounded_material_bytes
    data = bounded_material_bytes(inputs["representation"], context,
        max_bytes=_option(settings, context, "max_materialized_bytes", 32 * 1024 * 1024))
    return {"value": decode(data, max_bytes=_option(settings, context, "max_bytes", 256 * 1024 * 1024),
                             max_cells=_option(settings, context, "max_cells", 80_000_000), context=context)}
