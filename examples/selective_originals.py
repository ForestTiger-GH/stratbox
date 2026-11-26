"""One finite pass over caller-selected rolling workbooks, with durable restart state.

Usage:
    python examples/selective_originals.py --workspace ./collector-state \
        --source SOURCE_ID --source ANOTHER_SOURCE_ID --output exports/selected.zip

Use --replace only when this invocation may replace the observed output file.
The host owns cadence, retry policy, source membership and retention maintenance.
"""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.observability.journal import FileJournal
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import RetainedRepresentation
from stratbox.shared.data.processing import (ProcessingGoal, ProcessingRequirement,
    ProcessingPolicy, ReferenceAvailability, SourceStateKey, retained_reference_identity)
from stratbox.shared.data.selection import IssueQuery, SourceQuery
from stratbox.shared.data.values import ImmutableMaterialRef, fingerprint


def _outputs(box, capability, *, ports, **arguments):
    with box.invoke(capability, **arguments) as result:
        if result.outcome != 'succeeded':
            raise RuntimeError(f'{capability}: {result.outcome}: {result.diagnostics}')
        return tuple(result.output(port) for port in ports)


def _state(box, source_ids, *, index_pages):
    horizon = box.session.journal.checkpoint().tail
    checkpoint = box.advance_source_state(max_pages=index_pages, page_limit=1000)
    if checkpoint.applied_through < horizon:
        raise RuntimeError('The bounded index advance has more history to process; advance it before collecting.')
    (snapshot,) = _outputs(box, 'command.source.state.read', ports=('state',), inputs={
        'keys': tuple(SourceStateKey(source) for source in source_ids),
        'stream_id': checkpoint.stream_id, 'minimum_applied_through': horizon},
        parameters={'limit': 10000})
    if not snapshot.complete:
        raise RuntimeError('The selected state exceeds one complete bounded page; narrow this external pass.')
    return snapshot


def _retained(snapshot, source_id):
    observations = [item for item in snapshot.observations if item.key.source_id == source_id
                    and item.acquisition_evidence is not None and item.representation_identity]
    if not observations:
        return None
    latest = max(observations, key=lambda item: (item.observed_at, item.sequence))
    evidence = latest.acquisition_evidence
    reference = latest.retained_reference
    if not isinstance(reference, ImmutableMaterialRef):
        candidates = [item for item in snapshot.outputs if item.key == latest.key and item.persistent
            and item.stage in {'raw', 'original', 'retained'}
            and isinstance(item.retained_reference, ImmutableMaterialRef)
            and item.retained_reference.identity == latest.material_identity]
        reference = max(candidates, key=lambda item: item.sequence).retained_reference if candidates else None
    if reference is None:
        return None
    vary = tuple(part.strip().lower() for part in evidence.headers.get('vary', '').split(',') if part.strip())
    if '*' in vary:
        return None
    return RetainedRepresentation(reference, latest.representation_identity,
        {key: value for key, value in evidence.headers.items() if key in {'etag', 'last-modified'}},
        latest.observed_at, vary, evidence.request_identity, evidence=evidence)


def _availability(store, reference, instant):
    try:
        actual = store.inspect_file(reference.location).identity
        expected_scope = fingerprint((store.provider_id, store.storage_scope(reference.location)))
        status = 'available' if actual == reference.identity and expected_scope == reference.provider_scope else 'missing'
    except FileNotFoundError:
        status = 'missing'
    return ReferenceAvailability(retained_reference_identity(reference), instant, status)


def collect_once(box, source_ids, *, store, output, replace_existing=False,
                 index_pages=100, max_archive_bytes=8 * 1024**3):
    """Collect an exact external selection and return a small reviewable report.

    Network observations happen once per selected source per invocation. A
    qualified 304 keeps the old body. An unchanged archive basis reuses the
    retained ZIP, while named delivery verifies the requested current path.
    """
    if not source_ids or len(source_ids) > 200:
        raise ValueError('Choose between one and 200 explicit source IDs for this example.')
    selection = box.sources.select(SourceQuery(includes=tuple(source_ids), order=tuple(source_ids)))
    for source_id in selection.source_ids:
        descriptor = box.sources.descriptor(source_id)
        if (descriptor.target_kind != 'series' or descriptor.issue_model != 'rolling'
                or descriptor.delivery_mode != 'fixed_url' or descriptor.artifact_category != 'workbook'):
            raise ValueError(f'{source_id}: this external collector accepts declared rolling fixed-URL workbooks.')
    snapshot = _state(box, selection.source_ids, index_pages=index_pages)
    members, names, observations = [], [], []
    for ordinal, source_id in enumerate(selection.source_ids):
        inputs = {'query': IssueQuery(mode='rolling'),
                  'destination': 'originals/' + fingerprint(source_id)}
        retained = _retained(snapshot, source_id)
        if retained is not None:
            inputs['retained'] = retained
        material, assessment, inspection, evidence = _outputs(box, 'operation.material.receive',
            ports=('material', 'assessment', 'inspection', 'evidence'), inputs=inputs,
            target=SeriesTarget(source_id))
        if not assessment.complete:
            raise RuntimeError(f'{source_id}: source admission is incomplete: {assessment.findings}')
        if inspection.format not in {'xls', 'xlsx', 'xlsb'}:
            raise RuntimeError(f'{source_id}: the received envelope is not a workbook.')
        members.append(material)
        safe_id = re.sub(r'[^A-Za-z0-9_.-]', '_', source_id)
        names.append(f'{ordinal + 1:04d}-{safe_id}.{inspection.format}')
        observations.append({'source_id': source_id, 'status_code': evidence.status_code,
                             'sha256': material.identity.sha256, 'size': material.identity.size})
    members, names = tuple(members), tuple(names)
    parameters = {'placement': 'staged', 'names': names, 'max_bytes': max_archive_bytes}
    desired = fingerprint(box.processing_basis('command.archive.pack',
        inputs={'members': members}, parameters=parameters))
    snapshot = _state(box, selection.source_ids, index_pages=index_pages)
    instant = datetime.now(timezone.utc)
    candidates = [item for item in snapshot.outputs if item.stage == 'archive'
                  and item.basis_identity == desired and isinstance(item.retained_reference, ImmutableMaterialRef)]
    availability = tuple({retained_reference_identity(item.retained_reference):
        _availability(store, item.retained_reference, instant) for item in candidates}.values())
    goal = ProcessingGoal(SourceStateKey(selection.source_ids[0], '', 'main'),
        (ProcessingRequirement('archive', desired, output_name='material'),))
    (assessment,) = _outputs(box, 'command.processing.assess', ports=('assessment',), inputs={
        'goal': goal, 'state': snapshot, 'evaluation_time': instant,
        'policy': ProcessingPolicy(availability=availability)})
    reused = assessment.no_work
    if reused:
        reference = assessment.decisions[0].entrance
    else:
        (reference,) = _outputs(box, 'operation.archive.publish', ports=('reference',),
            inputs={'members': members, 'destination': 'archives'}, parameters=parameters)
    delivery_inputs = {'material': reference, 'retained_ancestor': reference, 'destination': output}
    delivery_parameters = {'policy': 'create_only'}
    if replace_existing:
        try:
            existing = store.inspect_file(output)
        except FileNotFoundError:
            existing = None
        if existing is not None and existing.identity != reference.identity:
            delivery_inputs['expected_destination'] = existing.identity
            delivery_parameters['policy'] = 'replace_if_matches'
    (receipt,) = _outputs(box, 'command.artifact.materialize', ports=('receipt',),
        inputs=delivery_inputs, parameters=delivery_parameters)
    _state(box, selection.source_ids, index_pages=index_pages)
    return {'selection_identity': selection.identity, 'sources': observations,
            'archive_reused': reused, 'archive_identity': reference.identity.sha256,
            'archive_location': reference.location, 'output': output,
            'delivery_status': receipt.status, 'delivery_effect_id': receipt.effect_id}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--source', action='append', required=True)
    parser.add_argument('--output', required=True, help='Named path relative to the workspace material store.')
    parser.add_argument('--replace', action='store_true', help='Replace only the exact destination observed by this pass.')
    parser.add_argument('--index-pages', type=int, default=100)
    parser.add_argument('--max-archive-bytes', type=int, default=8 * 1024**3)
    args = parser.parse_args()
    root = args.workspace.resolve()
    store = LocalFileStore(str(root / 'materials'))
    with FileJournal(root / 'journal') as journal, SQLiteSourceState(root / 'source-state.sqlite') as state:
        effects = FileEffectState(root / 'effects')
        with StrategyBox(journal=journal, providers={
            'filestore': store, 'effect_state': effects, 'source_state': state}) as box:
            result = collect_once(box, args.source, store=store, output=args.output,
                replace_existing=args.replace, index_pages=args.index_pages,
                max_archive_bytes=args.max_archive_bytes)
            print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
