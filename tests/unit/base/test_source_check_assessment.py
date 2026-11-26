"""Incomplete publisher evidence cannot certify that the original is unchanged."""
from stratbox.sdk import StrategyBox
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.shared.data.values import Material

SOURCE="cbr.reporting_forms.f101"


def test_missing_offline_index_returns_unknown_without_network_fallback():
    class Forbidden:
        def fetch(self,request):raise AssertionError("An explicitly supplied index must not fetch")
    with StrategyBox(providers={"http":Forbidden()}) as box:
        result=box.invoke("operation.source.check",inputs={"index":Material(b"<html>empty</html>","text/html",SOURCE+".index")},target=SeriesTarget(SOURCE))
        assert result.outcome=="succeeded",result.diagnostics
        assessment=result.output("assessment")
        assert assessment.status=="unknown" and assessment.basis=="publication_listing_incomplete"
        assert result.output("selection").assessment.status=="partial"


def test_unchanged_listing_never_certifies_unchanged_file_bytes():
    html=Material(b'<a href="/vfs/credit/forms/101-20261101.zip">01.11.2026</a>',"text/html",SOURCE+".index")
    with StrategyBox() as box:
        listing=box.invoke("command.publication.scan",inputs={"index":html},target=SeriesTarget(SOURCE)).output("listing")
        result=box.invoke("command.source.assess",inputs={"evidence":listing,"baseline":listing},target=SeriesTarget(SOURCE))
        assert result.outcome=="succeeded" and result.output("assessment").status=="unknown"
        assert "does_not_certify_asset_bytes" in result.output("assessment").findings[0]
