"""One external SDK pass selects an observed form and publishes required pairs."""
import csv
from datetime import datetime, timezone
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO, StringIO
import json
from pathlib import Path
from struct import pack
from zipfile import ZipFile

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.observability.journal import FileJournal
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.dbf import DBFPreservationPolicy
from stratbox.shared.identity import ByteIdentity


def dbf_bytes(value):
    fields = (pack('<11sc4xBB14x', b'CODE', b'C', 4, 0)
              + pack('<11sc4xBB14x', b'VALUE', b'N', 10, 2))
    rows = b' ' + b'001 ' + value.rjust(10) + b'*' + b'002 ' + b'0002.30'.rjust(10)
    return pack('<BBBBIHH20x', 3, 126, 4, 1, 2, 33 + len(fields), 15) + fields + b'\r' + rows + b'\x1a'


def test_selected_form_export_publishes_each_csv_with_full_evidence(tmp_path):
    specification = spec_from_file_location('selective_form_exports',
        Path(__file__).parents[3] / 'examples' / 'selective_form_exports.py')
    example = module_from_spec(specification)
    specification.loader.exec_module(example)
    original_members = {'tables/BANKS.DBF': dbf_bytes(b'0001.20'),
                        'tables/DETAIL.DBF': dbf_bytes(b'-0004.00')}
    source = BytesIO()
    with ZipFile(source, 'w') as archive:
        for name, data in original_members.items():
            archive.writestr(name, data)
        archive.writestr('readme.txt', b'Excluded by the explicit DBF suffix selection.')
    body = source.getvalue()
    selected_url = 'https://www.cbr.ru/vfs/credit/forms/999-20260401.zip'
    index_url = 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/'
    index = (f'<a href="{selected_url}">Selected physical form</a>'
             '<a href="/vfs/credit/forms/999-20260401.rar">Alternative format</a>'
             '<a href="/vfs/credit/forms/101-20260401.zip">Unselected form</a>').encode()

    class HTTP:
        def __init__(self):
            self.requests = []

        def exchange(self, request):
            self.requests.append(request.url)
            assert request.url == index_url
            return HttpResponse(200, index, {'Content-Type': 'text/html'}, datetime.now(timezone.utc), 'https://www.cbr.ru/',
                target_sha256=sha256(request.url.encode()).hexdigest(), wire_size=len(index))

        def exchange_into(self, request, sink, *, cancelled):
            self.requests.append(request.url)
            assert request.url == selected_url and not cancelled()
            sink.write(body)
            response = HttpResponse(200, b'', {'Content-Type': 'application/zip'}, datetime.now(timezone.utc), 'https://www.cbr.ru/',
                target_sha256=sha256(request.url.encode()).hexdigest(), wire_size=len(body))
            return HttpStreamResponse(response, ByteIdentity.of(body))

    http, store = HTTP(), LocalFileStore(tmp_path / 'materials')
    with FileJournal(tmp_path / 'journal') as journal:
        with StrategyBox(journal=journal, providers={'http': http, 'filestore': store,
                'effect_state': FileEffectState(tmp_path / 'effects')}) as box:
            report = example.export_forms_once(box, ('999',), ('2026-04-01',), formats=('zip', 'rar'),
                policy=DBFPreservationPolicy(encoding='cp866', encoding_basis='caller', include_deleted=True),
                store=store, output='exports/selected.zip')
            assert box.session.staging.status()['objects'] == 0
            assert len(report['exports']) == 2
            for exported in report['exports']:
                assert len(exported['receipt_ids']) == 2
                assert all(box.session.lookup_effect(identity).status == 'confirmed'
                           for identity in exported['receipt_ids'])
    assert http.requests == [index_url, selected_url]
    assert report['selected_forms'] == ['form-0409999']
    assert report['delivery_status'] == 'confirmed'
    output = tmp_path / 'materials' / 'exports' / 'selected.zip'
    assert ByteIdentity.of(output.read_bytes()).sha256 == report['archive_sha256']
    with ZipFile(output) as archive:
        assert archive.namelist() == report['archive_members']
        assert len(archive.namelist()) == 4
        for name, data in original_members.items():
            prefix = 'form-0409999/2026-04-01/' + name
            csv_data = archive.read(prefix + '.csv')
            evidence = json.loads(archive.read(prefix + '.preservation.json'))
            rows = list(csv.reader(StringIO(csv_data.decode('utf-8'))))
            assert rows[0] == ['CODE', 'VALUE'] and rows[1][0] == '001'
            assert rows[2] == ['002', '0002.30']
            assert evidence['deleted_record_ordinals'] == [2]
            assert evidence['source'] == {'sha256': sha256(data).hexdigest(), 'size': len(data)}
            assert evidence['csv']['sha256'] == sha256(csv_data).hexdigest()
            assert evidence['header']['integrity'] == 'complete_original_verified'
            assert evidence['encoding']['effective'] == 'cp866'
            assert evidence['encoding']['scope']['asset_id'] == 'form-0409999'
