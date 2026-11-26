"""The external finite collector restores conditional evidence and archive work."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.observability.journal import FileJournal
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.identity import ByteIdentity


def test_explicit_rolling_originals_restart_uses_304_and_retained_archive(tmp_path):
    specification = spec_from_file_location('selective_originals', Path(__file__).parents[3] / 'examples' / 'selective_originals.py')
    example = module_from_spec(specification)
    specification.loader.exec_module(example)
    workbook = Workbook()
    workbook.active['A1'] = 'Physical fixture; no semantic interpretation is claimed.'
    buffer = BytesIO()
    workbook.save(buffer)
    body = buffer.getvalue()

    class HTTP:
        def __init__(self, status):
            self.status, self.requests = status, []
        def exchange_into(self, request, sink, *, cancelled):
            self.requests.append(request)
            payload = body if self.status == 200 else b''
            sink.write(payload)
            response = HttpResponse(self.status, b'', {'ETag': 'fixture-v1',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
                datetime.now(timezone.utc), 'https://www.cbr.ru/',
                target_sha256=sha256(request.url.encode()).hexdigest(), wire_size=len(payload))
            return HttpStreamResponse(response, ByteIdentity.of(payload))

    reports = []
    for status in (200, 304):
        http = HTTP(status)
        store = LocalFileStore(str(tmp_path / 'materials'))
        with FileJournal(tmp_path / 'journal') as journal, SQLiteSourceState(tmp_path / 'state.sqlite') as state:
            with StrategyBox(journal=journal, build_identity='selective-collector-fixture', providers={'http': http, 'filestore': store,
                    'effect_state': FileEffectState(tmp_path / 'effects'), 'source_state': state}) as box:
                reports.append(example.collect_once(box, ('cbr.corporate_lending.corp_debt_a',),
                    store=store, output='exports/selected.zip'))
                assert box.session.staging.status()['objects'] == 0
        assert len(http.requests) == 1
        if status == 304:
            assert http.requests[0].headers['if-none-match'] == 'fixture-v1'
    assert not reports[0]['archive_reused'] and reports[1]['archive_reused']
    assert reports[0]['archive_identity'] == reports[1]['archive_identity']
    assert reports[1]['delivery_status'] == 'confirmed'
