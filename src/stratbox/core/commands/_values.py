"""Checked material and observation carriers shared by technical actions."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, ConvertedMaterial, DerivedDataset, IdentifiedMaterial, Material, SourceDataset, fingerprint


# Observation identity excludes the value, its reporting status and evidence.
# Shared defaults prevent each numerical action from forgetting an axis.
OBSERVATION_GRAIN = (
    'metric', 'subject_namespace', 'subject', 'unit', 'scale', 'perimeter',
    'measure_kind', 'frequency', 'period_kind', 'basis', 'value_basis',
    'dimensions', 'legal_kind', 'currency', 'portfolio', 'activity', 'bank',
    'sex', 'age',
)


def _material(value):
    if isinstance(value, IdentifiedMaterial):
        original, claim = value.material, value.claim
        for key, expected in (("issue_id", claim.issue_id), ("asset_id", claim.asset_id)):
            if expected and original.metadata.get(key) not in {None, "", expected}:
                raise ExecutionFailure("source.context_conflict")
        if original.source_id not in {None, claim.source_id}:
            raise ExecutionFailure("source.context_conflict")
        from dataclasses import replace
        return replace(original, source_id=claim.source_id,
            metadata={**dict(original.metadata), "issue_id": claim.issue_id, "asset_id": claim.asset_id})
    if isinstance(value, ConvertedMaterial):
        return value.material
    if isinstance(value, bytes):
        return Material(value)
    if not isinstance(value, Material):
        raise ExecutionFailure("material.required")
    return value


def _rows(dataset):
    if not isinstance(dataset, SourceDataset):
        raise ExecutionFailure("dataset.required")
    return dataset.rows


def _grain_key(row,names):
    values = []
    for name in names:
        value = row.get(name)
        try: hash(value)
        except TypeError: value = fingerprint(value)
        values.append(value)
    return tuple(values)


def _derivation_assessment(*datasets):
    assessments = tuple(dataset.assessment for dataset in datasets)
    common = frozenset.intersection(*(item.qualifications for item in assessments))
    return Assessment('complete' if all(item.complete for item in assessments) else 'partial',
        tuple(dict.fromkeys(finding for item in assessments for finding in item.findings)),
        qualifications=common | frozenset({'derived_coordinates'}))


def _derived(dataset, rows, *, sources=(), semantics=None):
    assessment = _derivation_assessment(dataset)
    return DerivedDataset(dataset.source_id, tuple(rows), semantics or dataset.semantics,
        dataset.issue_id, (*dataset.lineage, dataset.identity, *sources), assessment, source_uses=dataset.source_uses)
