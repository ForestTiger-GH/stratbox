"""Publication recognition and exact material effects retain separate evidence."""
from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import representation_identity
from stratbox.shared.data.values import FetchEvidence, Material, SourceClaim, request_identity


SERIES = "cbr.funding.funds_all"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def workbook():
    book = Workbook()
    book.active.append(["Published data", 1])
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def required(result, output):
    assert result.outcome == "succeeded", result.diagnostics
    return result.output(output)


class HTTP:
    def __init__(self, data):
        self.data, self.calls = data, []

    def fetch(self, request):
        self.calls.append(request)
        return Material(self.data, XLSX, request.source_id, metadata=request.metadata)


def test_selected_fixed_asset_acquisition_retains_exact_request_and_content_evidence():
    provider = HTTP(workbook())
    with StrategyBox(providers={"http": provider}) as box:
        target = SeriesTarget(SERIES)
        listing = required(box.invoke("command.publication.scan",
            inputs={"index": Material(b"<html>index</html>", "text/html", SERIES + ".index")}, target=target), "listing")
        selection = required(box.invoke("command.issue.select", inputs={"listing": listing}, target=target), "selection")
        asset, = selection.entries
        acquired = box.invoke("operation.material.acquire", inputs={"locator": asset,
            "claim": SourceClaim(SERIES)}, target=target)
        identified = required(acquired, "material")
        assert len(provider.calls) == 1
        assert identified.material.data == provider.data
        assert identified.claim.issue_id == ""
        assert identified.identity == identified.material.identity
        assert provider.calls[0].url == asset.locator
        evidence, = (item for item in identified.material.lineage if isinstance(item, FetchEvidence))
        assert evidence.material_identity == identified.identity and evidence.status_code == 200
        assert evidence.request_identity == request_identity(provider.calls[0])
        assert evidence.representation_identity == representation_identity(provider.calls[0])
        assert evidence.observed_at.tzinfo is not None
        assert evidence.observation_id == ""
        marked_request = replace(provider.calls[0], observation_id="caller-check-001")
        marked = required(box.invoke("command.material.fetch", inputs={"request": marked_request}), "evidence")
        assert marked.observation_id == "caller-check-001"


def test_undated_fixed_asset_cannot_gain_an_arbitrary_publisher_issue():
    provider = HTTP(workbook())
    with StrategyBox(providers={"http": provider}) as box:
        target = SeriesTarget(SERIES)
        listing = required(box.invoke("command.publication.scan",
            inputs={"index": Material(b"index", "text/html", SERIES + ".index")}, target=target), "listing")
        acquired = box.invoke("operation.material.acquire", inputs={"locator": listing.entries[0],
            "claim": SourceClaim(SERIES, "2026-11-01")}, target=target)
        assert acquired.outcome == "failed"
        assert "cbr.material_asset_mismatch" in acquired.diagnostics


def test_selected_asset_context_cannot_be_replaced_by_another_series():
    from stratbox.shared.data.values import PublicationAsset
    source = DOMAIN.series[SERIES].publication
    asset = PublicationAsset("cbr.funding.funds_clients", "2026-11-01", "main", source.locator, "xlsx")
    spec = DOMAIN.series[SERIES].commands["command.request.prepare"]
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="source|context|asset"):
        spec.method.resolve()({"locator": asset}, spec.settings,
            SimpleNamespace(parameters={}, checkpoint=lambda: None))


def test_same_bytes_and_different_processing_parameters_remain_distinct_evidence():
    original = Material(workbook(), XLSX, SERIES)
    with StrategyBox() as box:
        same = required(box.invoke("command.source.assess",
            inputs={"evidence": original, "baseline": original}, target=SeriesTarget(SERIES)), "assessment")
        assert same.status == "unchanged" and same.basis == "exact_material_bytes"
        first = box.prepare("command.workbook.decode", inputs={"material": original},
            target=SeriesTarget(SERIES), parameters={"issue_id": "2026-11-01"})
        changed = box.prepare("command.workbook.decode", inputs={"material": original},
            target=SeriesTarget(SERIES), parameters={"issue_id": "2026-11-02"})
        assert first.fingerprint != changed.fingerprint
        assert required(box.invoke("command.source.assess",
            inputs={"evidence": replace(original, data=original.data + b"revision"), "baseline": original},
            target=SeriesTarget(SERIES)), "assessment").status == "changed"


def test_same_material_bytes_keep_distinct_dated_issue_claims():
    source = "cbr.project_finance.escrow"
    original = Material(workbook(), XLSX, source)
    with StrategyBox() as box:
        claims = []
        for issue in ("2026-10-01", "2026-11-01"):
            claims.append(required(box.invoke("command.material.identify",
                inputs={"material": original, "claim": SourceClaim(source, issue)},
                target=SeriesTarget(source)), "material"))
        assert claims[0].identity == claims[1].identity
        assert claims[0].claim.issue_id != claims[1].claim.issue_id
        first = box.prepare("operation.series.extract_workbook", inputs={"material": claims[0]},
            parameters={"issue_id": claims[0].claim.issue_id}, target=SeriesTarget(source))
        second = box.prepare("operation.series.extract_workbook", inputs={"material": claims[1]},
            parameters={"issue_id": claims[1].claim.issue_id}, target=SeriesTarget(source))
        assert first.fingerprint != second.fingerprint


def test_index_comparison_never_certifies_unchanged_asset_material():
    from types import SimpleNamespace
    spec = DOMAIN.series[SERIES].commands["command.publication.scan"]
    context = SimpleNamespace(parameters={}, checkpoint=lambda: None)
    listing = spec.method.resolve()({"index": Material(b"index", "text/html", SERIES)}, spec.settings, context)["listing"]
    assess = DOMAIN.series[SERIES].commands["command.source.assess"]
    result = assess.method.resolve()({"evidence": listing, "baseline": listing}, assess.settings, context)["assessment"]
    assert result.status in {"unknown", "indeterminate"}
    assert result.basis != "exact_material_bytes"


def test_selected_original_archive_uses_generic_pack_and_immutable_commit(tmp_path):
    first = Material(workbook(), XLSX, SERIES, metadata={"member": "funds.xlsx"})
    from stratbox.shared.data.values import canonical_tree
    import json
    dispositions = {"good": "completed", "bad": "failed", "later": "not_attempted"}
    manifest = Material(json.dumps(canonical_tree(dispositions)).encode(), "application/json",
        metadata={"member": "selection_manifest.json"})
    with StrategyBox(providers={"filestore": LocalFileStore(str(tmp_path))}) as box:
        archive = required(box.invoke("command.archive.pack", inputs={"members": (first, manifest)}), "material")
        saved = required(box.invoke("command.artifact.commit",
            inputs={"material": archive, "destination": "archives"}), "reference")
        loaded = required(box.invoke("command.material.read", inputs={"location": saved}), "material")
        assert loaded.identity == archive.identity
        with ZipFile(BytesIO(loaded.data)) as value:
            assert value.read("funds.xlsx") == first.data
            assert value.read("selection_manifest.json") == manifest.data
            assert len(value.namelist()) == 2
