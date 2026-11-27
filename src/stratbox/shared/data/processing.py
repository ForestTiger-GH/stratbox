"""Explicit retained-state evidence and pure finite processing requirements."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections.abc import Mapping

from .values import Assessment, fingerprint, immutable


def processing_input_identity(value, *, max_nodes=5000000, max_depth=64):
    """Content and semantic context, independent of a polling attempt.

    Only known carriers and scientific values receive this normalization.
    Unknown objects retain their complete canonical identity. This is a work
    comparison key, never a substitute for accepted provenance or availability.
    """
    from dataclasses import fields, replace
    from .source_context import SourceUse
    from .history import ValidationCertificate
    from .materials import StagedMaterialRef, MaterialInspection, RetainedRepresentation, representation_identity
    from .values import (Material, ImmutableMaterialRef, IdentifiedMaterial,
        RequestSpec, FetchEvidence, ReadEvidence, SourceDataset, WorkbookEvidence, JsonEvidence,
        DbfEvidence, DocumentEvidence, TableEvidenceSet, View, EncodedProduct)
    if (type(max_nodes) is not int or max_nodes < 1 or type(max_depth) is not int or max_depth < 1):
        raise ValueError('processing.identity_limits_invalid')
    visited = 0
    physical_types = (WorkbookEvidence, JsonEvidence, DbfEvidence, DocumentEvidence, TableEvidenceSet)

    def normalized(item, depth=0):
        nonlocal visited
        visited += 1
        if visited > max_nodes or depth > max_depth:
            raise ValueError('processing.identity_limit')
        def child(part):
            return normalized(part, depth + 1)
        if isinstance(item, SourceUse):
            return ('source_use', item.coordinate, item.input_role, item.qualification)
        def uses(values):
            normalized_uses = {fingerprint(child(use)): child(use) for use in values}
            return tuple(normalized_uses[key] for key in sorted(normalized_uses))
        if isinstance(item, IdentifiedMaterial):
            carrier = item.material
            all_uses = (*getattr(carrier, 'source_uses', ()), *item.source_uses)
            if isinstance(carrier, (Material, ImmutableMaterialRef, StagedMaterialRef)):
                carrier = replace(carrier, source_uses=())
            return ('identified_material', child(carrier), item.claim,
                    child(item.assessment), uses(all_uses))
        if isinstance(item, (Material, ImmutableMaterialRef, StagedMaterialRef)):
            metadata = {key: part for key, part in item.metadata.items()
                        if key not in {'url', 'role', 'discovery', 'media_type', 'charset', 'source_id'}}
            return ('material_content', item.identity, item.media_type, item.source_id,
                    item.charset, child(metadata), uses(item.source_uses), child(getattr(item, 'assessment', None)))
        if isinstance(item, FetchEvidence):
            headers = {str(key).lower(): part for key, part in item.headers.items()
                       if str(key).lower() in {'content-type', 'content-encoding'}}
            return ('fetch_qualification', item.material_identity, item.representation_identity,
                item.effective_locator, item.observed_origin_assurance, item.transport_assurance,
                item.actual_target_identity, item.logical_target_identity, child(headers))
        if isinstance(item, RequestSpec):
            return ('request_representation', representation_identity(item), item.source_id,
                    item.max_bytes, child(item.metadata))
        if isinstance(item, ReadEvidence):
            return ('read_qualification', item.material_identity, item.location,
                    item.provider_scope, item.assurance)
        if isinstance(item, RetainedRepresentation):
            return ('retained_representation', child(item.reference), item.representation_identity,
                    item.assurance, child(item.evidence))
        if isinstance(item, MaterialInspection):
            return ('material_inspection', item.material_identity, item.format, item.media_type,
                    item.qualifications, item.findings, child(item.metadata))
        if isinstance(item, ValidationCertificate):
            # Rows and semantic binding live in the normalized dataset itself;
            # the certificate additionally names the exact competent rules.
            return ('validation_certificate', item.rule_id, item.method_identity,
                item.build_identity, item.source_id, item.issue_id, item.material_identities,
                item.coordinates, child(item.assessment), item.row_identities, item.semantics_identity)
        if isinstance(item, SourceDataset):
            return ('source_dataset', type(item).__qualname__, item.source_id, item.issue_id,
                child(item.rows), child(item.semantics), child(item.assessment),
                uses(item.source_uses), child(item.validation_certificates), child(item.history_membership))
        if isinstance(item, physical_types):
            return (type(item).__qualname__, tuple((field.name, child(getattr(item, field.name)))
                for field in fields(item)))
        if isinstance(item, View):
            return ('view', child(item.value), child(item.settings), uses(item.source_uses), child(item.assessment))
        if isinstance(item, EncodedProduct):
            return ('encoded_product', item.identity, item.media_type,
                    child(item.descriptor), uses(item.source_uses), child(item.assessment))
        if (type(item).__module__.startswith('pandas')
                and hasattr(item, 'columns') and hasattr(item, 'itertuples')):
            # A work key is not a portable-frame codec. Admitted object cells
            # may contain owned lists/mappings; include their exact contents
            # recursively instead of requiring scalar-only serialization.
            from .frame_codec import _axis_value, _dtype_value
            rows = tuple(tuple(child(cell) for cell in row)
                         for row in item.itertuples(index=False, name=None)) if len(item.columns) else tuple(() for _ in item.index)
            return ('dataframe', _axis_value(item.columns), _axis_value(item.index),
                    tuple(_dtype_value(dtype) for dtype in item.dtypes), rows)
        if isinstance(item, Mapping):
            return {key: child(part) for key, part in item.items()}
        if isinstance(item, (tuple, list)):
            return tuple(child(part) for part in item)
        if isinstance(item, (set, frozenset)):
            return ('unordered', tuple(sorted(fingerprint(child(part)) for part in item)))
        # Canonical fingerprinting includes all fields of other typed values,
        # including explicit clocks for a pure time-dependent assessment.
        return item
    return fingerprint(normalized(value))


def processing_basis(inputs, *, capability_id, method, settings, parameters, build_identity,
                     _input_identity=processing_input_identity):
    """Return the same three-part basis emitted for a bound command result."""
    locator = getattr(method, 'locator', method)
    if not all(isinstance(value, str) and value for value in (capability_id, locator, build_identity)):
        raise ValueError('processing.bound_command_required')
    if not isinstance(inputs, Mapping) or not isinstance(parameters, Mapping):
        raise ValueError('processing.named_inputs_required')
    return (fingerprint(('named_processing_inputs', tuple(sorted(
                (name, _input_identity(value)) for name, value in inputs.items())))),
            fingerprint((capability_id, locator, settings, parameters)), build_identity)


STAGES = frozenset({'raw', 'inspection', 'original', 'physical', 'tables', 'observations', 'calculation',
                    'view', 'representation', 'archive', 'retained', 'delivery'})


def retained_reference_identity(reference):
    """Physical reference matching excludes incidental lineage/metadata fields."""
    return fingerprint((type(reference).__name__, getattr(reference, 'provider_id', None),
        getattr(reference, 'provider_scope', None), getattr(reference, 'location', getattr(reference, 'snapshot_id', None)),
        getattr(reference, 'identity', None), getattr(reference, 'effect_id', None)))


def _strings(values, *, limit=10000):
    result = tuple(values)
    if len(result) > limit or any(not isinstance(value, str) or not value for value in result):
        raise ValueError('processing.invalid_members')
    return result


def utc_instant(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('processing.aware_time_required')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class SourceStateKey:
    source_id: str
    issue_id: str | None = None
    asset_id: str | None = None

    def __post_init__(self):
        if (not isinstance(self.source_id, str) or not self.source_id
                or self.issue_id is not None and not isinstance(self.issue_id, str)
                or self.asset_id is not None and not isinstance(self.asset_id, str)):
            raise ValueError('source_state.key_invalid')

    @property
    def identity(self):
        return fingerprint(self)


@dataclass(frozen=True, slots=True)
class SourceObservation:
    key: SourceStateKey
    observation_id: str
    observed_at: datetime
    comparison_scope: str
    evidence_identity: str
    material_identity: object | None = None
    representation_identity: str | None = None
    retained_reference: object | None = None
    sequence: int = 0
    acquisition_evidence: object | None = None

    def __post_init__(self):
        if not isinstance(self.key, SourceStateKey) or not self.observation_id or not self.comparison_scope or not self.evidence_identity:
            raise ValueError('source_state.observation_invalid')
        object.__setattr__(self, 'observed_at', utc_instant(self.observed_at))
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError('source_state.sequence_invalid')
        if self.acquisition_evidence is not None:
            from .values import FetchEvidence, ReadEvidence
            if (not isinstance(self.acquisition_evidence, (FetchEvidence, ReadEvidence))
                    or self.acquisition_evidence.material_identity != self.material_identity
                    or fingerprint(self.acquisition_evidence) != self.evidence_identity):
                raise ValueError('source_state.acquisition_binding_invalid')


@dataclass(frozen=True, slots=True)
class RetainedOutput:
    key: SourceStateKey
    accepted_value_id: str
    value_identity: str
    stage: str
    capability_id: str
    processing_basis: tuple[str, ...]
    accepted_at: datetime
    sequence: int
    retained_reference: object | None = None
    persistent: bool = False
    assessment: Assessment | None = None
    selection_identity: str | None = None
    observation_ref: str | None = None
    source_uses: tuple[object, ...] = ()
    effect_ids: tuple[str, ...] = ()
    destination_identity: str | None = None
    certificate_ids: tuple[str, ...] = ()
    represents_value_identity: str | None = None
    restore_via: str | None = None
    output_name: str | None = None

    def __post_init__(self):
        if not isinstance(self.key, SourceStateKey) or self.stage not in STAGES or not self.accepted_value_id or not self.value_identity:
            raise ValueError('source_state.output_invalid')
        if type(self.sequence) is not int or self.sequence < 1 or type(self.persistent) is not bool:
            raise ValueError('source_state.output_position_invalid')
        object.__setattr__(self, 'accepted_at', utc_instant(self.accepted_at))
        for name in ('processing_basis', 'effect_ids', 'certificate_ids'):
            object.__setattr__(self, name, _strings(getattr(self, name)))
        object.__setattr__(self, 'source_uses', tuple(self.source_uses))

    @property
    def basis_identity(self):
        return fingerprint(self.processing_basis)


@dataclass(frozen=True, slots=True)
class StateProjectionCheckpoint:
    stream_id: str
    applied_through: int
    retained_after: int = 0
    observed_tail: int = 0
    coverage_complete: bool = True

    def __post_init__(self):
        if (not self.stream_id or any(type(value) is not int or value < 0 for value in
                (self.applied_through, self.retained_after, self.observed_tail))
                or self.retained_after > self.applied_through or self.applied_through > self.observed_tail):
            raise ValueError('source_state.checkpoint_invalid')


@dataclass(frozen=True, slots=True)
class SourceStateSnapshot:
    keys: tuple[SourceStateKey, ...]
    checkpoint: StateProjectionCheckpoint
    outputs: tuple[RetainedOutput, ...] = ()
    observations: tuple[SourceObservation, ...] = ()
    minimum_applied_through: int = 0
    truncated: bool = False
    next_after: tuple[int, str] | None = None
    starts_after: tuple[int, str] | None = None
    view: str = 'current'
    history_retained_after: int = 0

    def __post_init__(self):
        object.__setattr__(self, 'keys', tuple(self.keys))
        object.__setattr__(self, 'outputs', tuple(self.outputs))
        object.__setattr__(self, 'observations', tuple(self.observations))
        if len(self.keys) > 10000 or len(self.outputs) + len(self.observations) > 10000:
            raise ValueError('source_state.snapshot_limit')
        if type(self.minimum_applied_through) is not int or self.minimum_applied_through < 0:
            raise ValueError('source_state.horizon_invalid')
        if (self.view not in {'current', 'history'} or type(self.history_retained_after) is not int
                or not 0 <= self.history_retained_after <= self.checkpoint.applied_through):
            raise ValueError('source_state.history_horizon_invalid')

    @property
    def complete(self):
        return (self.checkpoint.coverage_complete and not self.truncated and self.starts_after is None
                and self.checkpoint.applied_through >= self.minimum_applied_through
                and (self.view == 'current' or self.history_retained_after == 0))

    def for_source(self, source_id):
        from dataclasses import replace
        return replace(self, keys=tuple(k for k in self.keys if k.source_id == source_id),
            outputs=tuple(value for value in self.outputs if value.key.source_id == source_id),
            observations=tuple(value for value in self.observations if value.key.source_id == source_id))


@dataclass(frozen=True, slots=True)
class ProcessingRequirement:
    stage: str
    basis_identity: str | None = None
    destination_identity: str | None = None
    persistent: bool = True
    allow_partial: bool = False
    output_name: str | None = None

    def __post_init__(self):
        if self.stage not in STAGES or type(self.persistent) is not bool or type(self.allow_partial) is not bool:
            raise ValueError('processing.requirement_invalid')
        if self.output_name is not None and (not isinstance(self.output_name, str) or not self.output_name):
            raise ValueError('processing.output_name_invalid')


@dataclass(frozen=True, slots=True)
class ProcessingGoal:
    key: SourceStateKey
    requirements: tuple[ProcessingRequirement, ...]
    selection_identity: str | None = None

    def __post_init__(self):
        values = tuple(self.requirements)
        if not isinstance(self.key, SourceStateKey) or not values or len(values) > 100 or any(not isinstance(v, ProcessingRequirement) for v in values):
            raise ValueError('processing.goal_invalid')
        if len({(v.stage, v.destination_identity, v.output_name) for v in values}) != len(values):
            raise ValueError('processing.duplicate_requirement')
        object.__setattr__(self, 'requirements', values)

    @property
    def identity(self):
        return fingerprint(self)


@dataclass(frozen=True, slots=True)
class ProcessingBasis:
    stages: Mapping[str, str] = field(default_factory=dict)
    input_identity: str | None = None

    def __post_init__(self):
        if not isinstance(self.stages, Mapping) or set(self.stages) - STAGES or any(not isinstance(v, str) or not v for v in self.stages.values()):
            raise ValueError('processing.basis_invalid')
        object.__setattr__(self, 'stages', immutable(self.stages))


@dataclass(frozen=True, slots=True)
class ReferenceAvailability:
    reference_identity: str
    checked_at: datetime
    status: str

    def __post_init__(self):
        if not self.reference_identity or self.status not in {'available', 'missing', 'unknown'}:
            raise ValueError('processing.availability_invalid')
        object.__setattr__(self, 'checked_at', utc_instant(self.checked_at))


@dataclass(frozen=True, slots=True)
class ProcessingPolicy:
    max_observation_age_seconds: float | None = None
    max_availability_age_seconds: float | None = None
    availability: tuple[ReferenceAvailability, ...] = ()
    unknown_effect_ids: tuple[str, ...] = ()
    confirmed_effect_ids: tuple[str, ...] = ()
    force_stages: tuple[str, ...] = ()

    def __post_init__(self):
        from math import isfinite
        for name in ('max_observation_age_seconds', 'max_availability_age_seconds'):
            value = getattr(self, name)
            if value is not None and (type(value) not in {int, float} or value < 0 or not isfinite(value)):
                raise ValueError('processing.freshness_invalid')
        object.__setattr__(self, 'availability', tuple(self.availability))
        if any(not isinstance(v, ReferenceAvailability) for v in self.availability) or len(self.availability) > 10000:
            raise ValueError('processing.availability_required')
        for name in ('unknown_effect_ids', 'confirmed_effect_ids', 'force_stages'):
            object.__setattr__(self, name, _strings(getattr(self, name)))
        if set(self.force_stages) - STAGES or set(self.unknown_effect_ids) & set(self.confirmed_effect_ids):
            raise ValueError('processing.policy_conflict')


@dataclass(frozen=True, slots=True)
class ProcessingDecision:
    key: SourceStateKey
    stage: str
    action: str
    reasons: tuple[str, ...]
    basis_identity: str | None = None
    entrance: object | None = None
    effect_ids: tuple[str, ...] = ()
    restore_via: str | None = None
    output_name: str | None = None

    def __post_init__(self):
        if self.action not in {'reuse', 'observe', 'index_catch_up', 'verify', 'acquire', 'inspect', 'identify', 'extract', 'interpret',
                'calculate', 'prepare', 'render', 'pack', 'retain', 'materialize', 'reconcile'}:
            raise ValueError('processing.action_invalid')
        object.__setattr__(self, 'reasons', _strings(self.reasons))
        object.__setattr__(self, 'effect_ids', _strings(self.effect_ids))


@dataclass(frozen=True, slots=True)
class ProcessingAssessment:
    goal_identity: str
    evaluation_time: datetime
    decisions: tuple[ProcessingDecision, ...]
    checkpoint: StateProjectionCheckpoint

    def __post_init__(self):
        object.__setattr__(self, 'evaluation_time', utc_instant(self.evaluation_time))
        object.__setattr__(self, 'decisions', tuple(self.decisions))

    @property
    def no_work(self):
        return bool(self.decisions) and all(v.action == 'reuse' for v in self.decisions)

    @property
    def identity(self):
        return fingerprint(self)
