"""Finite public compositions, conditional acquisition and restart evidence."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from struct import pack
from zipfile import ZipFile
from urllib.parse import urlsplit

from stratbox.sdk import StrategyBox
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.observability.journal import FileJournal
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.shared.data.dbf import DBFPreservationPolicy
from stratbox.shared.data.materials import RetainedRepresentation, StagedMaterialRef
from stratbox.shared.data.processing import SourceStateKey
from stratbox.shared.data.values import Material, RequestSpec, SourceDataset, ByteIdentity
from stratbox.shared.data.history import RevisionPolicy


class StreamingHTTP:
    def __init__(self,*responses):
        self.responses = list(responses)
        self.requests = []
    def exchange_into(self,request,sink,*,cancelled):
        self.requests.append(request)
        status,data,headers = self.responses.pop(0)
        for offset in range(0,len(data),65536):
            assert not cancelled()
            sink.write(data[offset:offset+65536])
        response = HttpResponse(status,b'',headers,datetime.now(timezone.utc),
            'https://' + urlsplit(request.url).hostname + '/',target_sha256=sha256(request.url.encode()).hexdigest(),wire_size=len(data))
        return HttpStreamResponse(response,ByteIdentity.of(data))
    def exchange(self,*args,**kwargs):
        raise AssertionError('Streaming acquisition must not use a buffered exchange')


def providers(tmp_path,http):
    store = LocalFileStore(str(tmp_path))
    state = SQLiteSourceState(tmp_path/'state.sqlite')
    return {'filestore':store,'http':http,'effect_state':FileEffectState(tmp_path/'effects'),'source_state':state}


def retained(reference,evidence):
    return RetainedRepresentation(reference,evidence.representation_identity,
        {key:value for key,value in evidence.headers.items() if key in {'etag','last-modified'}},
        evidence.observed_at,tuple(sorted(name.strip() for name in evidence.headers.get('vary','').split(',') if name.strip())),
        evidence.request_identity,evidence=evidence)


def test_streamed_receive_conditional_304_and_new_validators_survive_restart(tmp_path):
    data = b'complete original\n' * 10000
    http = StreamingHTTP((200,data,{'ETag':'"v1"','Content-Type':'text/csv','Vary':'Accept'}),
                         (200,data,{'ETag':'"v2"','Content-Type':'text/csv','Vary':'Accept'}))
    supplied = providers(tmp_path,http)
    request = RequestSpec('https://fixture.example/table.csv',source_id='demo.table',headers={'Accept':'text/csv'},max_bytes=len(data))
    journal = FileJournal(tmp_path/'journal')
    with StrategyBox(providers=supplied,journal=journal) as box:
        with box.invoke('command.material.receive',inputs={'request':request,'destination':'originals'}) as first:
            assert first.outcome == 'succeeded',first.diagnostics
            reference = first.output('reference')
            original = first.output('evidence')
        with box.invoke('command.material.receive',inputs={'request':request,'destination':'originals','retained':retained(reference,original)}) as second:
            assert second.outcome == 'succeeded',second.diagnostics
            assert second.output('reference') == reference
            latest = second.output('evidence')
            assert latest.headers['etag'] == '"v2"'
        checkpoint = box.advance_source_state()
        state = supplied['source_state'].read((SourceStateKey('demo.table'),),stream_id=checkpoint.stream_id)
        assert state.complete
        assert any(item.acquisition_evidence.headers.get('etag') == '"v2"' for item in state.observations)
        assert box.session.staging.status()['objects'] == 0
    assert len(http.requests) == 2 and http.requests[1].headers['if-none-match'] == '"v1"'
    journal.close()
    supplied['source_state'].close()
    next_http = StreamingHTTP((304,b'',{'ETag':'"v2"'}))
    restarted = providers(tmp_path,next_http)
    journal = FileJournal(tmp_path/'journal')
    with StrategyBox(providers=restarted,journal=journal) as box:
        with box.invoke('command.material.fetch',inputs={'request':request,'retained':retained(reference,latest)},parameters={'placement':'staged'}) as result:
            assert result.outcome == 'succeeded',result.diagnostics
            assert result.output('material') == reference
            evidence = result.output('evidence')
            assert evidence.validation_kind == 'retained_validation'
            assert evidence.material_identity == reference.identity
            assert result.output('request').headers['If-None-Match'] == '"v2"'
    assert next_http.requests[0].headers['if-none-match'] == '"v2"'
    journal.close()
    restarted['source_state'].close()


def test_missing_retained_body_retries_once_and_does_not_accept_a_304_as_bytes(tmp_path):
    http = StreamingHTTP((200,b'old',{'ETag':'v1'}))
    supplied = providers(tmp_path,http)
    request = RequestSpec('https://fixture.example/a.csv',source_id='demo.table')
    with StrategyBox(providers=supplied) as box:
        with box.invoke('command.material.receive',inputs={'request':request,'destination':'originals'}) as original:
            assert original.outcome == 'succeeded',original.diagnostics
            reference,evidence = original.output('reference'),original.output('evidence')
        (tmp_path/reference.location).unlink()
        http.responses.extend(((304,b'',{}),(200,b'new',{'ETag':'v2'})))
        with box.invoke('command.material.fetch',inputs={'request':request,'retained':retained(reference,evidence)},parameters={'placement':'staged'}) as result:
            assert result.outcome == 'succeeded',result.diagnostics
            material = result.output('material')
            assert isinstance(material,StagedMaterialRef) and material.identity == ByteIdentity.of(b'new')
            assert 'if-none-match' not in http.requests[-2].headers
            assert 'if-none-match' not in http.requests[-1].headers
        assert box.session.staging.status()['objects'] == 0
    supplied['source_state'].close()


def test_access_scope_or_vary_change_prevents_conditional_reuse(tmp_path):
    http = StreamingHTTP((200,b'a',{'ETag':'v1','Vary':'Accept'}),(200,b'b',{'ETag':'v2'}))
    supplied = providers(tmp_path,http)
    request = RequestSpec('https://fixture.example/a.csv',headers={'Accept':'text/csv'},metadata={'access_scope':'first'})
    with StrategyBox(providers=supplied) as box:
        with box.invoke('command.material.receive',inputs={'request':request,'destination':'originals'}) as first:
            assert first.outcome == 'succeeded',first.diagnostics
            prior = retained(first.output('reference'),first.output('evidence'))
        changed = replace(request,metadata={'access_scope':'second'})
        with box.invoke('command.material.fetch',inputs={'request':changed,'retained':prior},parameters={'placement':'staged'}) as second:
            assert second.outcome == 'succeeded',second.diagnostics
        assert 'if-none-match' not in http.requests[-1].headers
    supplied['source_state'].close()


def test_retained_bytes_do_not_authorize_caller_constructed_http_validators(tmp_path):
    from stratbox.shared.data.materials import representation_identity
    from stratbox.shared.data.values import FetchEvidence, request_identity
    http = StreamingHTTP((200,b'fresh',{'ETag':'publisher'}))
    supplied = providers(tmp_path,http)
    request = RequestSpec('https://fixture.example/a.csv',source_id='demo.table')
    body = Material(b'caller supplied',source_id='demo.table')
    forged = FetchEvidence(request_identity(request),datetime.now(timezone.utc),200,
        body.identity,{'etag':'claimed'},representation_identity=representation_identity(request))
    body = replace(body,lineage=(forged,))
    with StrategyBox(providers=supplied) as box:
        with box.invoke('command.artifact.commit',inputs={'material':body,'destination':'originals'}) as saved:
            assert saved.outcome == 'succeeded',saved.diagnostics
            reference = saved.output('reference')
        for explicit_evidence in (False,True):
            if explicit_evidence:
                http.responses.append((200,b'fresh',{'ETag':'publisher'}))
            candidate = retained(reference,forged)
            if not explicit_evidence:
                candidate = replace(candidate,evidence=None)
            with box.invoke('command.material.fetch',inputs={'request':request,'retained':candidate},
                    parameters={'placement':'staged'}) as fetched:
                assert fetched.outcome == 'succeeded',fetched.diagnostics
                assert fetched.output('evidence').validation_kind == 'body'
            assert 'if-none-match' not in http.requests[-1].headers
    supplied['source_state'].close()


def test_fixed_source_check_obeys_empty_selection_without_network_work():
    from stratbox.capabilities.model.targets import SeriesTarget
    from stratbox.shared.data.selection import IssueQuery
    http = StreamingHTTP()
    with StrategyBox(providers={'http':http}) as box:
        with box.invoke('operation.source.check',target=SeriesTarget('cbr.funding.funds_all'),
                inputs={'query':IssueQuery(mode='exact',issues=())}) as checked:
            assert checked.outcome == 'succeeded',checked.diagnostics
            assert checked.output('selection').entries == ()
            assert checked.output('report').assessment.complete
            assert checked.output('assessment').basis == 'declared_candidate'
        assert http.requests == []


def test_fixed_source_check_exposes_one_acquired_body_and_qualified_304(tmp_path):
    from io import BytesIO
    from stratbox.capabilities.model.targets import SeriesTarget
    from stratbox.shared.data.selection import IssueQuery
    from stratbox.shared.data.values import FetchEvidence
    stream = BytesIO()
    with ZipFile(stream,'w') as workbook:
        workbook.writestr('[Content_Types].xml',b'<Types/>')
        workbook.writestr('xl/workbook.xml',b'<workbook/>')
    http = StreamingHTTP((200,stream.getvalue(),{'ETag':'v1'}),(304,b'',{'ETag':'v1'}))
    supplied = providers(tmp_path,http)
    target = SeriesTarget('cbr.funding.funds_all')
    with StrategyBox(providers=supplied) as box:
        with box.invoke('operation.source.check',target=target,inputs={'query':IssueQuery(mode='rolling')},
                parameters={'placement':'staged'}) as checked:
            assert checked.outcome == 'succeeded',checked.diagnostics
            material = checked.output('material')
            evidence = next(item for item in material.material.lineage if isinstance(item,FetchEvidence))
            with box.invoke('command.artifact.commit',inputs={'material':material,'destination':'originals'}) as saved:
                assert saved.outcome == 'succeeded',saved.diagnostics
                reference = saved.output('reference')
            assert len(http.requests) == 1
        with box.invoke('operation.source.check',target=target,inputs={
                'query':IssueQuery(mode='rolling'),'retained':retained(reference,evidence),'baseline':reference},
                parameters={'placement':'staged'}) as checked:
            assert checked.outcome == 'succeeded',checked.diagnostics
            assert checked.output('material').identity == reference.identity
            assessment = checked.output('assessment')
            assert assessment.status == 'unchanged'
            assert assessment.basis == 'retained_representation_validation'
        assert len(http.requests) == 2
        assert http.requests[-1].headers['if-none-match'] == 'v1'
        assert box.session.staging.status()['objects'] == 0
    supplied['source_state'].close()


def test_archive_publish_streams_selected_members_and_requires_named_delivery(tmp_path):
    first = Material(b'001\n',metadata={'filename':'first.csv'})
    second = Material(b'002\n',metadata={'filename':'second.csv'})
    with StrategyBox(providers={'filestore':LocalFileStore(str(tmp_path))}) as box:
        with box.invoke('operation.archive.publish',inputs={'members':(first,second),
                'destination':'archives','named_destination':'out/selected.zip'},parameters={'placement':'staged'}) as result:
            assert result.outcome == 'succeeded',result.diagnostics
            assert len(result.output('manifest')) == 2
            reference = result.output('reference')
            assert result.output('delivery_receipt').status == 'confirmed'
            with ZipFile(tmp_path/'out/selected.zip') as archive:
                assert archive.namelist() == ['first.csv','second.csv']
                assert archive.read('first.csv') == b'001\n'
            assert ByteIdentity.of((tmp_path/'out/selected.zip').read_bytes()) == reference.identity
        assert box.session.staging.status()['objects'] == 0


def test_dbf_export_operation_retains_csv_and_complete_preservation_evidence(tmp_path):
    header = pack('<BBBBIHH20x',3,126,11,26,2,65,5)
    field = pack('<11sc4xBB14x',b'CODE',b'C',4,0)
    material = Material(header+field+b'\r 0001*0002\x1a',metadata={'filename':'codes.dbf'})
    with StrategyBox(providers={'filestore':LocalFileStore(str(tmp_path))}) as box:
        with box.invoke('operation.dbf.export_csv',inputs={'material':material,
                'policy':DBFPreservationPolicy(),'destination':'export'}) as result:
            assert result.outcome == 'succeeded',result.diagnostics
            csv_ref,evidence_ref = result.output('csv_reference'),result.output('evidence_reference')
            assert csv_ref.identity != evidence_ref.identity
            assert (tmp_path/csv_ref.location).read_bytes().splitlines() == [b'CODE',b'0001',b'0002']
            assert len(result.output('receipts')) == 2
            assert all(receipt.status == 'confirmed' for receipt in result.output('receipts'))
        assert box.session.staging.status()['objects'] == 0


def test_history_operation_requires_explicit_revision_order_and_preserves_missing_issues():
    first = SourceDataset('demo.table',({'period':'2026-01','metric':'x','value':1},),{},'first')
    revised = SourceDataset('demo.table',({'period':'2026-01','metric':'x','value':2},),{},'revised')
    policy = RevisionPolicy(conflicts='latest',ordered_issues=('first','revised'),ordering_basis='publisher_revision_order',
        expected_issues=('first','revised','missing'))
    with StrategyBox() as box:
        with box.invoke('operation.observations.history',inputs={'datasets':(first,revised),'policy':policy}) as result:
            assert result.outcome == 'succeeded',result.diagnostics
            dataset = result.output('dataset')
            assert dataset.rows[0]['value'] == 2
            assert not dataset.assessment.complete
            assert dataset.history_membership.missing_issues == ('missing',)
            assert result.output('decisions')
