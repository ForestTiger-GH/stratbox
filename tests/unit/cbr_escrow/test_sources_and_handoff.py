"""Historical source formats and neutral storage have explicit standard routes."""
from dataclasses import replace

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.domains.cbr.methods.actions import publications
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

from .test_replay import SERIES, context, decoded, encoded, publication, source


def test_historical_html_is_discoverable_without_false_semantic_layout_support():
    original = Material(b'''
<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">2019</a>
<a href="/analytics/finansirovanie-dolevogo-stroitelstva/2020-01-01/">2020</a>
<a href="/Collection/Collection/File/62244/01072026.xlsx">2026</a>
<a href="https://other.example/analytics/finansirovanie-dolevogo-stroitelstva/2019-08-26/">external</a>
''', "text/html")
    settings = DOMAIN.series[SERIES].commands["command.publication.scan"].settings
    listing = publications.scan({"index": original}, settings, context())["listing"]
    assert [entry.format for entry in listing.entries] == ["html", "html", "xlsx"]
    assert [entry.issue_id for entry in listing.entries] == ["2019-08-26", "2020-01-01", "2026-07-01"]
    content = b"<html><table><tr><td>Original historical material</td></tr></table></html>"
    class Publisher:
        def fetch(self, request):
            assert request.url == listing.entries[0].locator
            return Material(content, "text/html", SERIES)
    with StrategyBox(providers={"http": Publisher()}) as box:
        acquired = box.invoke("operation.material.acquire", inputs={"locator": listing.entries[0]}, target=SeriesTarget(SERIES))
        assert acquired.outcome == "succeeded", acquired.diagnostics
        material = acquired.output("material")
        assert material.material.data == content
        assert material.claim.issue_id == "2019-08-26"
        parsed = box.invoke("operation.series.extract_document", inputs={"material": material, "issue": "2019-08-26"}, target=SeriesTarget(SERIES))
        assert parsed.outcome == "failed"
        assert any("escrow_table_unresolved" in str(item) or "document.format_unsupported" in str(item)
            for item in parsed.diagnostics)


def test_retained_physical_table_and_dataset_handoff_do_not_repeat_decoding(tmp_path, monkeypatch):
    request = publication()
    path = tmp_path / "input.xlsx"
    path.write_bytes(request.payload.data)
    loaded = replace(request, payload=request.payload) if hasattr(request, "__dataclass_fields__") else request
    physical, tables, dataset = source(loaded)
    restored = decoded(encoded(tables))
    def unexpected(*args, **kwargs):
        raise AssertionError("Retained geometry is a legal route entrance")
    monkeypatch.setattr("stratbox.core.formats.spreadsheets.cells.read_workbook_cells", unexpected)
    with StrategyBox() as box:
        result = box.invoke("operation.series.extract_workbook", inputs={"tables": restored, "issue": "2026-06-01"}, target=SeriesTarget(SERIES))
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("dataset").rows == dataset.rows
        assert result.output("dataset").source_uses == dataset.source_uses


def test_every_escrow_action_binds_a_standard_command_and_declared_narrow_method():
    declaration = DOMAIN.series[SERIES]
    assert {"command.request.prepare", "command.publication.scan", "command.issue.select", "command.source.assess",
        "command.material.identify", "command.table.extract", "command.table.interpret", "command.observations.validate",
        "command.observations.align", "command.value.encode", "command.value.decode"} <= declaration.commands.keys()
    for command in declaration.commands.values():
        assert callable(command.method.resolve())
        assert not hasattr(command.settings, "commands")
