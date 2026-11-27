"""Retained carriers fulfill the present destination; repairs have new occurrences."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import RetainedRepresentation
from stratbox.shared.data.values import Material, RequestSpec, SnapshotRef, SourceClaim, SourceDataset, fingerprint
from stratbox.shared.identity import ByteIdentity


class ConditionalHTTP:
    def __init__(self):
        self.requests = []
        self.body = b'key,value\na,1\n'
    def exchange_into(self, request, sink, *, cancelled):
        self.requests.append(request)
        conditional = 'if-none-match' in {name.lower() for name in request.headers}
        body = b'' if conditional else self.body
        sink.write(body)
        response = HttpResponse(304 if conditional else 200, b'',
            {'ETag': 'revision-one', 'Content-Type': 'text/csv'}, datetime.now(timezone.utc),
            'https://fixture.example/', target_sha256=sha256(request.url.encode()).hexdigest(), wire_size=len(body))
        return HttpStreamResponse(response, ByteIdentity.of(body))


@pytest.mark.parametrize('operation', (False, True))
def test_304_reuse_fulfills_a_new_destination_through_the_same_commit_path(tmp_path, operation):
    http = ConditionalHTTP()
    request = RequestSpec('https://fixture.example/table.csv', source_id='fixture.table')
    providers = {'http': http, 'filestore': LocalFileStore(tmp_path), 'effect_state': FileEffectState(tmp_path / 'effects')}
    with StrategyBox(providers=providers) as box:
        if operation:
            command = 'operation.material.receive'
            inputs = {'locator': request.url, 'claim': SourceClaim('fixture.table', '2026-11', 'table', 'recognized')}
        else:
            command, inputs = 'command.material.receive', {'request': request}
        first = box.invoke(command, inputs={**inputs, 'destination': 'first'})
        assert first.outcome == 'succeeded', first.diagnostics
        reference, evidence = first.output('reference'), first.output('evidence')
        retained = RetainedRepresentation(reference, evidence.representation_identity,
            {'etag': 'revision-one'}, evidence.observed_at, (), evidence.request_identity, evidence=evidence)
        second = box.invoke(command, inputs={**inputs, 'destination': 'second', 'retained': retained})
        assert second.outcome == 'succeeded', second.diagnostics
        current = second.output('reference')
        assert second.output('evidence').status_code == 304
        assert current.location == str(Path('second') / reference.identity.sha256)
        assert current.effect_id != reference.effect_id
        assert (tmp_path / current.location).read_bytes() == http.body
        assert box.session.lookup_effect(current.effect_id).value == current
        assert box.session.staging.status()['objects'] == 0
    assert len(http.requests) == 2


def test_missing_confirmed_retention_requires_explicit_new_repair_occurrence(tmp_path):
    state = FileEffectState(tmp_path / 'effects')
    with StrategyBox(providers={'filestore': LocalFileStore(tmp_path), 'effect_state': state}) as box:
        inputs = {'material': Material(b'exact bytes'), 'destination': 'objects'}
        original = box.invoke('command.artifact.commit', inputs=inputs)
        assert original.outcome == 'succeeded', original.diagnostics
        historical = original.output('receipt')
        path = tmp_path / original.output('reference').location
        path.unlink()
        repeated = box.invoke('command.artifact.commit', inputs=inputs)
        assert repeated.outcome == 'failed' and not path.exists()
        assert state.get(historical.effect_id) == historical
        repaired = box.invoke('command.artifact.commit', inputs=inputs, parameters={'repair_id': 'recovery-one'})
        assert repaired.outcome == 'succeeded', repaired.diagnostics
        assert repaired.output('receipt').effect_id != historical.effect_id
        assert state.get(historical.effect_id) == historical and path.read_bytes() == b'exact bytes'
        repeated_repair = box.invoke('command.artifact.commit', inputs=inputs, parameters={'repair_id': 'recovery-one'})
        assert repeated_repair.outcome == 'succeeded'
        assert repeated_repair.output('receipt') == repaired.output('receipt')


@pytest.mark.parametrize('field', ('provider_id', 'provider_scope', 'identity'))
def test_dataset_writer_cannot_confirm_a_foreign_snapshot_payload(field):
    class Writer:
        provider_id, scope_id = 'fixture.writer', 'fixture.scope'
        calls = 0
        def ingest(self, dataset, *, destination, identity):
            self.calls += 1
            correct = SnapshotRef('snapshot', self.provider_id, identity, self.scope_id)
            return replace(correct, **{field: 'foreign'})
    writer = Writer()
    with StrategyBox(providers={'dataset_writer': writer}) as box:
        inputs = {'dataset': SourceDataset('fixture', ({'period': '2026', 'value': 1},)), 'destination': 'series'}
        first = box.invoke('command.dataset.ingest', inputs=inputs)
        assert first.outcome == 'unknown'
        assert box.invoke('command.dataset.ingest', inputs=inputs).outcome == 'unknown'
        assert writer.calls == 1


def test_lost_conditional_replacement_needs_causal_evidence_even_when_bytes_match(tmp_path):
    class Lost(LocalFileStore):
        @contextmanager
        def stage_write(self, path):
            with super().stage_write(path) as stage:
                class Wrapped:
                    stream = stage.stream
                    def commit(self, mode, revision):
                        result = stage.commit(mode, revision)
                        if mode == 'replace_expected_revision':
                            raise OSError('Killed acknowledgement before transition record')
                        return result
                yield Wrapped()
    target = tmp_path / 'named'
    target.write_bytes(b'old')
    state = FileEffectState(tmp_path / 'effects')
    with StrategyBox(providers={'filestore': Lost(tmp_path), 'effect_state': state}) as box:
        result = box.invoke('command.artifact.materialize', inputs={'material': Material(b'new'),
            'destination': 'named', 'expected_destination': ByteIdentity.of(b'old')},
            parameters={'policy': 'replace_if_matches', 'delivery_id': 'replace-one'})
        assert result.outcome == 'unknown' and target.read_bytes() == b'new'
        receipt, = result.effects.values()
        assessed = box.invoke('command.artifact.reconcile', inputs={'effect': receipt})
        assert assessed.outcome == 'succeeded' and not assessed.output('assessment').complete
        assert state.get(receipt.effect_id).status == 'unknown'


def test_explicit_publication_occurrence_can_repeat_a_conditional_transition(tmp_path):
    store, state = LocalFileStore(tmp_path), FileEffectState(tmp_path / 'effects')
    with StrategyBox(providers={'filestore': store, 'effect_state': state}) as box:
        encoded = box.invoke('command.value.encode', inputs={'value': {'series': (1, 2)}})
        retained = box.invoke('command.artifact.commit', inputs={'material': encoded.output('representation'),
            'destination': 'objects'})
        assembled = box.invoke('command.release.assemble', inputs={'members': (retained.output('reference'),)})
        inputs = {'manifest': assembled.output('manifest'), 'expected_token': ByteIdentity.of(b'A').sha256}
        store.write_bytes('release.json', b'A')
        first = box.invoke('command.release.publish', inputs=inputs, parameters={'destination': 'release.json'})
        assert first.outcome == 'succeeded', first.diagnostics
        old = first.output('receipt')
        store.write_bytes('release.json', b'A')
        repeated = box.invoke('command.release.publish', inputs=inputs, parameters={'destination': 'release.json'})
        assert repeated.outcome == 'failed' and store.read_bytes('release.json') == b'A'
        current = box.invoke('command.release.publish', inputs=inputs,
            parameters={'destination': 'release.json', 'publication_id': 'repeat-transition-2'})
        assert current.outcome == 'succeeded', current.diagnostics
        assert current.output('receipt').effect_id != old.effect_id
        assert state.get(old.effect_id) == old
