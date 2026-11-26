"""Source identification validates official archive media and actual signatures."""
import pytest

from stratbox.shared.data.values import Material
from .support import DAY, command


@pytest.mark.parametrize("code", ["101","102","123","135","802","805"])
def test_forms_accept_official_application_rar_content_type(code):
    request=command(code,"request.prepare",{"query":{"issue_id":DAY}})["request"]
    assert request.url.endswith(f"/{code}-20260401.rar")
    original=Material(b"Rar!\x1a\x07\x00small test archive","application/rar")
    identified=command(code,"material.identify",{"material":original},issue_id=DAY)["material"]
    assert identified.material==original and identified.material.media_type=="application/rar"


@pytest.mark.parametrize("media,body", [
    ("text/html",b"Rar!\x1a\x07\x00arbitrary"),
    ("application/rar",b"<html>not an archive</html>"),
])
def test_forms_keep_media_and_signature_validation(media,body):
    with pytest.raises(ValueError):
        command("101","material.identify",{"material":Material(body,media)},issue_id=DAY)
