"""Real FNS interpretation exercises the common lifecycle with controlled providers."""
from collections import Counter
from dataclasses import replace
from datetime import date
import pytest

from stratbox.capabilities.preparation import InvocationRequest
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, ByteIdentity
from tests.domains_target.fns.fixtures import encoded, fixture


def material(day=date(2026, 11, 10)):
    return Material(encoded(fixture(day)), 'application/json', 'fns.sme',
                    metadata={'issue_id': day.isoformat()})


class Http:
    def __init__(self): self.calls = Counter()
    def fetch(self, request):
        self.calls[(request.method, request.url)] += 1
        if request.method == 'POST':
            assert request.read_only and request.form['statDate'] == '10.11.2026'
            return material()
        return Material(b'<select><option value="10.11.2026">10.11.2026</option></select>',
                        'text/html', 'fns.sme.index')


def test_source_refresh_has_visible_check_acquire_decode_interpret_validate():
    http = Http()
    with StrategyBox(providers={'http': http}) as box:
        plan = box.prepare('scenario.series.refresh', target='fns.sme',
            inputs={'issue': '2026-11-10'}, parameters={'as_of': '2026-11-10'})
        result = box.run(plan, timeout=10)
        assert result.outcome == 'succeeded', result.diagnostics
        dataset = result.output('dataset')
        assert dataset.rows and dataset.issue_id == '2026-11-10'
        assert dataset.source_id == 'fns.sme'
        assert sum(http.calls.values()) == 2  # HTML observation, then dated read-only JSON POST.
        assert dataset.source_uses and all(use.coordinate.material_identity for use in dataset.source_uses)


def test_supplied_physical_evidence_prunes_network_and_decode():
    with StrategyBox() as box:
        physical = box.invoke('command.json.decode', inputs={'material': material()}).output('physical')
        plan = box.prepare('scenario.series.refresh', target='fns.sme',
            inputs={'physical': physical, 'issue': '2026-11-10'})
        assert not any(getattr(task, 'command', None) and task.command.id in
            {'command.material.fetch', 'command.json.decode'} for task in plan.tasks)
        result = box.run(plan, timeout=10)
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('dataset').rows


def test_cascade_keeps_independent_targets_issues_and_logical_scopes():
    members = tuple(InvocationRequest('scenario.series.refresh',
        {'material': material(day), 'issue': day.isoformat()}, target='fns.sme')
        for day in (date(2026, 10, 10), date(2026, 11, 10)))
    with StrategyBox() as box:
        result = box.invoke('cascade.sources.refresh', inputs={'members': members}, timeout=10)
        assert result.outcome == 'succeeded', result.diagnostics
        datasets = result.output('results')
        assert [item.issue_id for item in datasets] == ['2026-10-10', '2026-11-10']
        assert len({item.identity for item in datasets}) == 2
        assert any('member0' in key for key in result.scopes)
        assert any('member1' in key for key in result.scopes)


def test_retained_semantic_data_replays_without_original_or_transport(tmp_path):
    with StrategyBox(providers={'filestore': LocalFileStore(str(tmp_path))}) as box:
        dataset = box.invoke('scenario.series.refresh', target='fns.sme',
            inputs={'material': material(), 'issue': '2026-11-10'}, timeout=10).output('dataset')
        retained = box.invoke('operation.dataset.retain', target='fns.sme',
            inputs={'dataset': dataset, 'destination': 'semantic'}, timeout=10)
        assert retained.outcome == 'succeeded', retained.diagnostics
        reference = retained.output('reference')
        read = box.invoke('command.material.read', inputs={'location': reference}, timeout=10)
        assert read.outcome == 'succeeded', read.diagnostics
        replay = box.invoke('command.value.decode', target='fns.sme',
            inputs={'representation': read.output('material')}, timeout=10)
        assert replay.outcome == 'succeeded', replay.diagnostics
        restored = replay.output('value')
        assert restored == dataset and restored.identity == dataset.identity
        assert restored.source_uses == dataset.source_uses
        assert reference.identity == ByteIdentity.of((tmp_path / reference.location).read_bytes())


def test_wrong_source_and_wrong_issue_cannot_be_relabelled():
    with StrategyBox() as box:
        for supplied, issue in ((replace(material(), source_id='fns.1yur'), '2026-11-10'),
                                (material(), '2026-10-10')):
            try:
                result = box.invoke('scenario.series.refresh', target='fns.sme',
                    inputs={'material': supplied, 'issue': issue}, timeout=10)
            except (ValueError, TypeError):
                continue
            assert result.outcome != 'succeeded'


def test_refresh_never_promotes_a_partial_scientific_assessment_to_complete():
    rows=fixture(date(2026,11,10))
    rows[0]['unreviewed_publisher_field']={'code':'new'}
    original=Material(encoded(rows),'application/json','fns.sme')
    with StrategyBox() as box:
        result=box.invoke('scenario.series.refresh',target='fns.sme',
            inputs={'material':original,'issue':'2026-11-10'},timeout=10)
        assert result.outcome in {'succeeded','partial'},result.diagnostics
        assessment=result.output('dataset').assessment
        assert assessment.status=='partial'
        assert any('unreviewed_publisher_field' in finding for finding in assessment.findings)
