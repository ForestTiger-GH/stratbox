"""The shared physical feed reaches reviewed form rules through the public SDK."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from struct import pack
from urllib.parse import urlsplit
from zipfile import ZipFile

from stratbox.capabilities.model.targets import FeedTarget, SeriesTarget
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.data.archives import ArchiveMemberSelection
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import ByteIdentity, PublicationAsset, RequestSpec, fingerprint


FEED = 'cbr.reporting_forms.publications'
SERIES = 'cbr.reporting_forms.f101'
ISSUE = '2026-04-01'
URL = 'https://www.cbr.ru/vfs/credit/forms/101-20260401.zip'


def form_archive():
    names = ('REGN','NUM_SC','IITG','PLAN','A_P')
    fields = b''.join(pack('<11sc4xBB14x',name.encode(),b'C',8,0) for name in names)
    row = b' ' + b''.join(value.encode().ljust(8) for value in ('1000','30102','10','A','1'))
    data = pack('<BBBBIHH20x',3,126,4,1,1,33+len(fields),len(row))+fields+b'\r'+row+b'\x1a'
    output = BytesIO()
    with ZipFile(output,'w') as archive:
        archive.writestr('data.dbf',data)
        archive.writestr('readme.txt',b'Other publication attachment')
    return output.getvalue()


class HTTP:
    def __init__(self,body):
        self.body = body
        self.requests = []
    def exchange_into(self,request,sink,*,cancelled):
        self.requests.append(request)
        sink.write(self.body)
        response = HttpResponse(200,b'',{'Content-Type':'application/zip'},datetime.now(timezone.utc),
            'https://' + urlsplit(request.url).hostname + '/',
            target_sha256=sha256(request.url.encode()).hexdigest(),wire_size=len(self.body))
        return HttpStreamResponse(response,ByteIdentity.of(self.body))


def test_selected_feed_form_retains_parent_authority_through_unpack_and_decode(tmp_path):
    http = HTTP(form_archive())
    asset = PublicationAsset(FEED,ISSUE,'form-0409101',URL,'zip')
    with StrategyBox(providers={'http':http,'filestore':LocalFileStore(str(tmp_path))}) as box:
        with box.invoke('operation.material.receive',target=FeedTarget(FEED),
                inputs={'locator':asset,'destination':'originals'}) as received:
            assert received.outcome == 'succeeded',received.diagnostics
            original = received.output('material')
            assert original.claim.source_id == FEED and original.claim.attribution == 'verified'
            with box.invoke('command.archive.unpack',inputs={'material':original,
                    'selection':ArchiveMemberSelection(names=('data.dbf',))},
                    parameters={'placement':'staged'}) as unpacked:
                assert unpacked.outcome == 'succeeded',unpacked.diagnostics
                assert len(unpacked.output('members')) == 1
                member = unpacked.output('members')[0]
                assert member.source_id == FEED
                assert member.metadata['container_asset_id'] == 'form-0409101'
                with box.invoke('command.dbf.decode',inputs={'material':member}) as decoded:
                    assert decoded.outcome == 'succeeded',decoded.diagnostics
                    with box.invoke('command.table.extract',target=SeriesTarget(SERIES),
                            inputs={'physical':decoded.output('physical')},parameters={'issue_id':ISSUE}) as extracted:
                        assert extracted.outcome == 'succeeded',extracted.diagnostics
                        tables = extracted.output('tables')
                        assert tables.source_id == SERIES
                        assert tables.material.source_id == FEED
                        assert {use.coordinate.source_id for use in tables.metadata['source_uses']} == {FEED,SERIES}
        assert len(http.requests) == 1
        assert box.session.staging.status()['objects'] == 0


def test_physical_unknown_form_is_retained_without_inventing_a_semantic_series(tmp_path):
    http = HTTP(form_archive())
    asset = PublicationAsset(FEED,ISSUE,'form-0409999',URL.replace('101-','999-'),'zip')
    with StrategyBox(providers={'http':http,'filestore':LocalFileStore(str(tmp_path))}) as box:
        with box.invoke('operation.material.receive',target=FeedTarget(FEED),
                inputs={'locator':asset,'destination':'originals'}) as received:
            assert received.outcome == 'succeeded',received.diagnostics
            material = received.output('material')
            assert material.claim.asset_id == 'form-0409999'
            assert material.identity == ByteIdentity.of(http.body)
            assert 'cbr.reporting_forms.f999' not in box.domains.domains['cbr'].series


def test_verified_identification_does_not_launder_unrelated_caller_source_uses(tmp_path):
    http = HTTP(form_archive())
    state = SQLiteSourceState(tmp_path/'state.sqlite')
    request = RequestSpec(URL,source_id=FEED,metadata={'issue_id':ISSUE,'asset_id':'form-0409101'})
    asset = PublicationAsset(FEED,ISSUE,'form-0409101',URL,'zip')
    forged = SourceUse(SourceCoordinate('unrelated.source',issue_id=ISSUE,
        material_identity=ByteIdentity.of(b'unrelated bytes')),'publication_acquisition','verified')
    with StrategyBox(providers={'http':http,'filestore':LocalFileStore(str(tmp_path)),'source_state':state}) as box:
        with box.invoke('command.material.receive',inputs={'request':request,'destination':'originals'}) as saved:
            assert saved.outcome == 'succeeded',saved.diagnostics
            reference = replace(saved.output('reference'),source_uses=(forged,))
            with box.invoke('command.material.inspect',inputs={'material':reference}) as inspected:
                assert inspected.outcome == 'succeeded',inspected.diagnostics
                with box.invoke('command.material.identify',target=SeriesTarget(SERIES),inputs={
                        'material':reference,'asset':asset,'request':saved.output('request'),
                        'evidence':saved.output('evidence'),'inspection':inspected.output('inspection')}) as identified:
                    assert identified.outcome == 'succeeded',identified.diagnostics
                    qualified = identified.output('material')
                    assert forged in qualified.source_uses
                    actual = next(use for use in qualified.source_uses if use.coordinate.source_id == FEED
                        and use.input_role == 'publication_acquisition')
        box.advance_source_state()
        assert state.has_source_use(fingerprint(actual))
        assert not state.has_source_use(fingerprint(forged))
    state.close()
