"""Closed, JSON-compatible workflow codec without executable type imports.

Scalar prepared values are portable. Rich domain data should travel through
its retained artifact contract rather than an arbitrary Python pickle.
"""
from __future__ import annotations

import base64
import math
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from pathlib import PurePath, Path
from typing import Mapping

from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput, ResultReference
from stratbox.shared.data.operations import OperationKey
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.identity import ByteIdentity
from . import models
from .models import CompositionError


@lru_cache(maxsize=1)
def _value_types():
    """Closed portable shared-value registry; documents never select imports."""
    from stratbox.shared.evidence import SourcePayload, AcquisitionReceipt, AcquiredSource, UsedInputReceipt, StoredBytesReceipt
    from stratbox.shared.data.observations import SubjectRef, MetricRef, PeriodRef, Observation, ObservationBatch
    from stratbox.shared.data.views import ObservationView
    from stratbox.shared.data.assessment import CoverageCoordinate,CoverageAssessment,ProcessingFinding,CalculationEvidence,ValueEvidence
    from stratbox.shared.data.representation import Representation
    from stratbox.shared.data.workbook_cells import WorkbookCells, SheetCells, WorkbookCell
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext
    from stratbox.shared.data.datasets import DatasetVersion, ComputationReceipt
    from stratbox.shared.data.snapshots import (
        ColumnSchema, TableSchema, TypedTable, TableComponent, CoverageDimension,
        SnapshotCoverage, DatasetManifest, DatasetSnapshot,
    )
    from stratbox.core.execution.contracts import EffectReceipt
    return {kind.__name__:kind for kind in (
        object,str,bool,int,float,bytes,dict,list,tuple,
        SourcePayload,AcquisitionReceipt,AcquiredSource,UsedInputReceipt,StoredBytesReceipt,
        SubjectRef,MetricRef,PeriodRef,Observation,ObservationBatch,ObservationView,
        Representation,WorkbookCells,SheetCells,WorkbookCell,SourceCoordinate,SourceUse,ValueContext,
        DatasetVersion,ComputationReceipt,ColumnSchema,TableSchema,TypedTable,TableComponent,
        CoverageDimension,SnapshotCoverage,DatasetManifest,DatasetSnapshot,EffectReceipt,
        CoverageCoordinate,CoverageAssessment,ProcessingFinding,CalculationEvidence,ValueEvidence,
    )}


@lru_cache(maxsize=1)
def _types():
    names = (
        "PlanOutputRef", "InputRef", "SourceSelection", "Condition", "RetryPolicy",
        "OperationStep", "ScenarioDefinition", "ScenarioStep", "CascadeDefinition",
        "MapStep", "CollectSpec", "CollectStep", "CompiledMap", "PlanScope",
        "CompiledTask", "ExecutionPlan",
    )
    kinds = [getattr(models, name) for name in names]
    from .plan import CanonicalMapTemplate, ScopeOutputRef
    kinds.extend((CanonicalMapTemplate,ScopeOutputRef))
    kinds.extend((DataContract, ByteIdentity, PreparedInput, ProjectedOutput, ResultReference, OperationKey))
    kinds.extend(kind for kind in _value_types().values() if is_dataclass(kind))
    from stratbox.capabilities.model import PortContract, AcceptanceContract, SemanticPredicate, CollectionMembership
    kinds.extend((PortContract, AcceptanceContract, SemanticPredicate, CollectionMembership))
    from stratbox.capabilities.model.reuse import ReuseContract,WorkIdentity
    kinds.extend((ReuseContract,WorkIdentity))
    try:
        from .templates import TemplateDefinition, TemplateSlot
        kinds.extend((TemplateDefinition, TemplateSlot))
    except ImportError:
        pass
    return {kind.__name__: kind for kind in kinds}


def encode(value):
    if isinstance(value, type):
        if value not in _value_types().values():
            raise CompositionError("composition.value_not_portable")
        return {"$type": "python_type", "value": value.__name__}
    if isinstance(value, Enum):
        from stratbox.shared.data.snapshots import ScalarType
        if isinstance(value,(DataRole,ScalarType)):
            return {"$type":type(value).__name__,"value":value.value}
        raise CompositionError("composition.value_not_portable")
    if value is None or type(value) in {str, bool, int}:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CompositionError("composition.value_not_portable")
        return value
    if isinstance(value, bytes):
        return {"$type": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (datetime, date, time)):
        return {"$type": type(value).__name__, "value": value.isoformat()}
    if isinstance(value, timedelta):
        return {"$type": "timedelta", "days": value.days, "seconds": value.seconds, "microseconds": value.microseconds}
    if isinstance(value, Decimal):
        return {"$type": "Decimal", "value": str(value)}
    if isinstance(value, PurePath):
        return {"$type": "Path", "value": str(value)}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CompositionError("composition.value_not_portable")
        return {"$type": "mapping", "items": {key: encode(item) for key, item in value.items()}}
    if isinstance(value, (list, tuple, frozenset)):
        items = list(value)
        if isinstance(value, frozenset):
            items = sorted(items)
        return {"$type": type(value).__name__, "items": [encode(item) for item in items]}
    if is_dataclass(value) and type(value) in _types().values():
        return {"$type": type(value).__name__, "fields": {item.name: encode(getattr(value, item.name)) for item in fields(value)}}
    raise CompositionError("composition.value_not_portable")


def decode(value):
    if value is None or type(value) in {str, bool, int}:
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if not isinstance(value, dict) or not isinstance(value.get("$type"), str):
        raise CompositionError("composition.invalid_document")
    tag = value["$type"]
    try:
        if tag in _types():
            kind = _types()[tag]
            if set(value) != {"$type", "fields"} or not isinstance(value["fields"], dict) or set(value["fields"]) != {field.name for field in fields(kind)}:
                raise CompositionError("composition.invalid_document")
            decoded = {key:decode(item) for key,item in value["fields"].items()}
            result = kind(**{item.name:decoded[item.name] for item in fields(kind) if item.init})
            if any(getattr(result,item.name) != decoded[item.name] for item in fields(kind) if not item.init):
                raise CompositionError("composition.value_identity_mismatch")
            if kind.__name__ == "WorkbookCells":
                from stratbox.shared.data.workbook_cells import validate_sheet_cells
                for sheet in result.sheets:
                    validate_sheet_cells(sheet)
            return result
        if tag in {"tuple", "list", "frozenset", "mapping"}:
            if set(value) != {"$type", "items"}:
                raise CompositionError("composition.invalid_document")
            if tag == "mapping":
                if not isinstance(value["items"], dict) or any(not isinstance(key, str) for key in value["items"]):
                    raise CompositionError("composition.invalid_document")
                return {key: decode(item) for key, item in value["items"].items()}
            if not isinstance(value["items"], list):
                raise CompositionError("composition.invalid_document")
            return {"tuple": tuple, "list": list, "frozenset": frozenset}[tag](decode(item) for item in value["items"])
        if tag == "timedelta":
            if set(value) != {"$type", "days", "seconds", "microseconds"}:
                raise CompositionError("composition.invalid_document")
            return timedelta(**{key: item for key, item in value.items() if key != "$type"})
        if set(value) != {"$type", "value"} or not isinstance(value["value"], str):
            raise CompositionError("composition.invalid_document")
        literal = value["value"]
        if tag == "python_type":
            kinds = _value_types()
            if literal not in kinds:
                raise CompositionError("composition.unknown_type")
            return kinds[literal]
        from stratbox.shared.data.snapshots import ScalarType
        factories = {"DataRole":DataRole,"ScalarType":ScalarType,"date":date.fromisoformat,
                     "datetime":datetime.fromisoformat,"time":time.fromisoformat,
                     "Decimal": Decimal, "Path": Path,
                     "bytes": lambda text: base64.b64decode(text, validate=True)}
        if tag not in factories:
            raise CompositionError("composition.unknown_type")
        return factories[tag](literal)
    except (TypeError, KeyError, ValueError, OverflowError) as error:
        if isinstance(error, CompositionError):
            raise
        raise CompositionError("composition.invalid_document") from None


def definition_to_dict(value):
    if not isinstance(value, (models.ScenarioDefinition, models.CascadeDefinition)):
        raise CompositionError("composition.definition_required")
    return encode(value)


def definition_from_dict(value):
    result = decode(value)
    if not isinstance(result, (models.ScenarioDefinition, models.CascadeDefinition)):
        raise CompositionError("composition.definition_required")
    return result
