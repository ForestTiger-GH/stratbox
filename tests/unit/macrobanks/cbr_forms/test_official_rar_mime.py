"""CBR reports use application/rar for official form archives."""
from datetime import date, datetime, timezone

import pytest

from stratbox.base.net import HttpResponse
from stratbox.macrobanks import cbr_forms


@pytest.mark.parametrize("code", ["101", "102", "123", "135", "802", "805"])
def test_forms_accept_official_application_rar_content_type(code):
    key = cbr_forms.FormKey(code, date(2024, 1, 1))
    source = cbr_forms.select_sources(cbr_forms.SelectFormSourcesRequest((key,)))
    assert source.outcome == "succeeded"
    expected_url = source.value[0].url
    stub_rar = b"Rar!\x1a\x07\x00" + b"small test archive"

    class Stub:
        def exchange(self, request, *, cancelled=None):
            assert request.url == expected_url
            assert request.permits(request.url)
            return HttpResponse(
                200, stub_rar, {"content-type": "application/rar"},
                datetime.now(timezone.utc), "https://www.cbr.ru",
            )

    received = cbr_forms.acquire(key, transport=Stub())
    assert received.outcome == "succeeded", received.diagnostics
    assert received.value.payload.data == stub_rar
    assert received.value.payload.media_type == "application/rar"
    assert received.value.receipt.media_type == "application/rar"


@pytest.mark.parametrize("media,body,expected", [
    ("text/html", b"Rar!\x1a\x07\x00arbitrary", "source.media_type_unexpected"),
    ("application/rar", b"<html>not an archive</html>", "source.archive_signature_invalid"),
])
def test_forms_keep_media_and_signature_validation(media, body, expected):
    key = cbr_forms.FormKey("101", date(2024, 1, 1))

    class Stub:
        def exchange(self, request, *, cancelled=None):
            return HttpResponse(
                200, body, {"content-type": media},
                datetime.now(timezone.utc), "https://www.cbr.ru",
            )

    result = cbr_forms.acquire(key, transport=Stub())
    assert result.outcome == "failed"
    assert any(d.code == expected for d in result.diagnostics)
