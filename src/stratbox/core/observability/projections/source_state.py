"""Replay accepted evidence into source-state storage without owning effects."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from stratbox.shared.data.journal import JournalPage
from stratbox.shared.data.processing import SourceStateKey, SourceObservation, RetainedOutput
from stratbox.shared.data.source_context import SourceUse
from stratbox.shared.data.values import ImmutableMaterialRef, SnapshotRef, Assessment, fingerprint


def output_stage(capability_id, output_name=None):
    direct = {
        'command.material.fetch': {'material': 'raw'},
        'command.material.read': {'material': 'raw'},
        'command.material.receive': {'reference': 'raw'},
        'command.material.inspect': {'inspection': 'inspection'},
        'command.material.identify': {'material': 'original'},
        'command.archive.unpack': {'members': 'raw'},
        'command.table.extract': {'tables': 'tables'},
        'command.table.interpret': {'dataset': 'observations'},
        'command.observations.validate': {'dataset': 'observations'},
        'command.observations.merge': {'dataset': 'observations'},
        'command.observations.select': {'dataset': 'observations'},
        'command.observations.resolve_revisions': {'dataset': 'observations'},
        'command.observations.assemble': {'dataset': 'observations'},
        'command.view.prepare': {'view': 'view'},
        'command.product.render': {'product': 'representation'},
        'command.value.encode': {'representation': 'representation'},
        'command.dbf.export_csv': {'csv': 'representation', 'evidence': 'representation'},
        'command.archive.pack': {'material': 'archive'},
        'command.artifact.commit': {'reference': 'retained'},
        'command.dataset.ingest': {'reference': 'retained'},
        'command.artifact.materialize': {'receipt': 'delivery'},
        'command.timeseries.partition': {'items': 'calculation'},
        'command.timeseries.prepare': {'series': 'calculation'},
        'command.timeseries.adjust': {'adjustment': 'calculation'},
    }
    if capability_id in direct:
        return direct[capability_id].get(output_name)
    if capability_id in {'command.workbook.decode', 'command.dbf.decode', 'command.csv.decode',
                         'command.json.decode', 'command.document.decode'}:
        return 'physical' if output_name == 'physical' else None
    if capability_id.startswith(('command.calculate.', 'command.calculation.')):
        return 'calculation' if output_name == 'dataset' else None
    return None


def _observation(data, fact):
    if isinstance(data, SourceObservation):
        return replace(data, sequence=fact.sequence)
    if not isinstance(data, Mapping) or not data.get('source_id') or not data.get('evidence_identity'):
        return None
    return SourceObservation(SourceStateKey(data['source_id'], data.get('issue_id') or '', data.get('asset_id')),
        data.get('observation_id') or fact.run_id, data.get('observed_at') or fact.occurred_at,
        data.get('comparison_scope', 'unspecified'), data['evidence_identity'], data.get('material_identity'),
        data.get('representation_identity'), data.get('retained_reference'), fact.sequence, data.get('acquisition_evidence'))


def project_page(page):
    if not isinstance(page, JournalPage) or page.filters:
        raise ValueError('source_state.unfiltered_page_required')
    records, authority, links = [], [], []
    for fact in page.facts:
        data = fact.data
        observation = _observation(data if fact.kind == 'source.observed' else data.get('observation'), fact)
        if observation is not None:
            records.append(observation)
        if (fact.kind != 'output.accepted' or data.get('output_disposition', 'accepted') != 'accepted'
                or data.get('output_role') == 'diagnostic'
                or not data.get('accepted_value_id') or not data.get('value_identity')):
            continue
        capability_id = data.get('capability_id') or fact.command_id or ''
        acquisition_id = data.get('acquisition_evidence_id')
        if (capability_id in {'command.material.fetch', 'command.material.receive', 'command.material.read'}
                and (fact.output_name or data.get('output_name')) == 'evidence'
                and isinstance(acquisition_id, str) and acquisition_id):
            authority.append(('acquisition', acquisition_id, fact.sequence))
        if (capability_id in {'command.material.fetch', 'command.material.receive', 'command.material.read'}
                and observation is not None and observation.acquisition_evidence is not None):
            authority.append(('acquisition', observation.evidence_identity, fact.sequence))
        if capability_id == 'command.observations.validate':
            authority.extend(('certificate', key, fact.sequence) for key in data.get('certificate_ids', ()) if isinstance(key, str) and key)
        authority.extend(('source_use', fingerprint(use), fact.sequence) for use in data.get('trusted_source_uses', ()) if isinstance(use, SourceUse))
        reference = data.get('retained_reference')
        persistent = data.get('persistent') is True and isinstance(reference, (ImmutableMaterialRef, SnapshotRef))
        if persistent and getattr(reference, 'accepted_value_id', None):
            links.append((reference.accepted_value_id, reference, fact.sequence))
        stage = output_stage(capability_id, fact.output_name or data.get('output_name'))
        if stage is None:
            continue
        uses = tuple(use for use in data.get('source_uses', ()) if isinstance(use, SourceUse))
        keys = tuple(dict.fromkeys(SourceStateKey(use.coordinate.source_id, use.coordinate.issue_id or '', use.coordinate.asset_id)
                                   for use in uses if use.coordinate.source_id is not None))
        if not keys and data.get('source_id'):
            keys = (SourceStateKey(data['source_id'], data.get('issue_id') or '', data.get('asset_id')),)
        basis = tuple(data.get('processing_basis', ()))
        if any(not isinstance(value, str) or not value for value in basis):
            continue
        dependencies = tuple(dict.fromkeys((*data.get('certificate_dependencies', ()),
            *(data.get('certificate_ids', ()) if capability_id == 'command.observations.validate' else ()))))
        for key in keys:
            records.append(RetainedOutput(key, data['accepted_value_id'], data['value_identity'], stage,
                capability_id, basis, fact.occurred_at, fact.sequence, reference if persistent else None, persistent,
                data.get('assessment') if isinstance(data.get('assessment'), Assessment) else None,
                data.get('selection_identity'), data.get('observation_ref'), uses, tuple(data.get('effect_ids', ())),
                data.get('destination_identity'), dependencies,
                reference.identity if isinstance(reference, SnapshotRef) else data.get('represents_value_identity'),
                output_name=fact.output_name or data.get('output_name')))
    return tuple(records), tuple(authority), tuple(links)


class SourceStateIndex:
    """Advance a derivative index through exact global journal pages."""
    def __init__(self, store, *, consumer_id='source-state'):
        self.store, self.consumer_id = store, consumer_id

    def advance(self, journal, *, max_pages=10, page_limit=1000):
        if (type(max_pages) is not int or not 1 <= max_pages <= 1000
                or type(page_limit) is not int or not 1 <= page_limit <= 10000):
            raise ValueError('source_state.advance_limit_invalid')
        journal_checkpoint = journal.checkpoint()
        checkpoint = self.store.checkpoint(journal_checkpoint.stream_id)
        applied = checkpoint.applied_through if checkpoint else 0
        if checkpoint is None and journal_checkpoint.retained_after:
            raise ValueError('source_state.history_missing')
        if applied < journal_checkpoint.retained_after:
            raise ValueError('source_state.checkpoint_expired')
        registered = journal_checkpoint.consumers.get(self.consumer_id)
        if registered is None:
            cursor = journal.register_consumer(self.consumer_id, after=applied)
        else:
            cursor = journal.register_consumer(self.consumer_id, after=registered)
        if cursor > applied:
            raise ValueError('source_state.acknowledgement_ahead')
        for _ in range(max_pages):
            page = journal.read_page(after=cursor, limit=page_limit, scan_limit=page_limit)
            records, authority, links = project_page(page)
            checkpoint = self.store.apply_page(page, records, authority, links)
            # Database rows and cursor are durable before acknowledgement allows
            # pruning. A lost acknowledgement safely replays an already applied page.
            cursor = journal.acknowledge(self.consumer_id, page)
            if not page.has_more:
                break
        return checkpoint
