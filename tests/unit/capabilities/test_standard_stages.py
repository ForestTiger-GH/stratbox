"""Independent stages retain physical evidence and qualified semantic values."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.core.storage.datasets import MemoryDatasetStore, FileDatasetStore
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.assessment import ValueEvidence, ProcessingFinding
from stratbox.shared.data.observations import Observation, ObservationBatch, SubjectRef, MetricRef, PeriodRef
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.source_context import SourceUse, SourceCoordinate
from stratbox.shared.data.stages import MaterialMember
from stratbox.shared.data.updates import ProcessingTarget, RetainedProcessing
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity


def batch():
    source = SourcePayload(b"source bytes", "text/csv", "test.series")
    rows = tuple(Observation(SubjectRef("local", "A"), MetricRef("stock", "RUB", "stock", "v1", Decimal("1000")),
        PeriodRef("as_of", date(2026, 1, 1)), (("currency", "RUB"), ("slice", str(index))), "source_total",
        value, status, "cell:" + str(index), token) for index, (value, status, token) in enumerate((
            (Decimal("12.30"), "reported", "12,30"), (0, "reported", "0"), (None, "withheld", "..."),
            (None, "dash", "-"), (Decimal("4.25"), "reconstructed", None))))
    return ObservationBatch("test.observations", 1, "2026-01", rows, (UsedInputReceipt.for_payload(source, "source"),),
        (SourceUse(SourceCoordinate("test.series", material_identity=source.identity, layout_edition="layout-1"),
            qualification="source_reported"),), ValueEvidence(frozenset({"extraction.validated"}), findings=(
                ProcessingFinding("source.withheld", "information", 1, "Withheld source value"),),
            method_fingerprints=("method-1",), profile_fingerprints=("profile-1",), reference_fingerprints=("reference-1",)))


def invoke(box, capability, *, inputs=None, parameters=None, output="value"):
    result = box.invoke(capability, inputs=inputs, parameters=parameters, timeout=10)
    assert result.outcome == "succeeded", (capability, result.diagnostics,
        [(key, value.diagnostics) for key, value in result.results.items()])
    return result.output(output)


def portable_roundtrip(box, kind, value):
    retained = invoke(box, kind + ".snapshot", inputs={"value": value})
    encoded = invoke(box, "snapshot.encode", inputs={"snapshot": retained})
    restored = invoke(box, "snapshot.decode", inputs={"material": encoded})
    assert restored.identity == retained.identity
    return invoke(box, kind + ".replay", inputs={"snapshot": restored})


def test_observations_and_view_roundtrip_preserves_all_semantic_properties():
    value = batch()
    with StrategyBox() as box:
        assert portable_roundtrip(box, "observations", value) == value
        view = invoke(box, "view.table", inputs={"observations": value}, output="view")
        restored = portable_roundtrip(box, "view", view)
        assert restored == view
        rendered = invoke(box, "render.table", inputs={"view": restored}, output="representation")
        assert b"reconstructed" in rendered.data and b"withheld" in rendered.data
        assert not any(task.operation_id == "http.acquire" for task in box.prepare("render.table", inputs={"view": restored}).tasks)


def test_document_and_workbook_physical_replay_preserve_evidence():
    import openpyxl
    workbook = openpyxl.Workbook()
    workbook.active.append(["heading", "amount", "formula"])
    workbook.active.append(["unknown source field", 12.3, "=B2*2"])
    stream = BytesIO(); workbook.save(stream)
    with StrategyBox() as box:
        document = invoke(box, "document.decode", inputs={"material": SourcePayload(b"first\nsecond\n", "text/plain")},
            parameters={"series_id": "test.document", "issue_id": "2026-01"})
        assert portable_roundtrip(box, "document", document) == document
        readable = invoke(box, "document.readable", inputs={"value": document})
        assert b"first" in readable.data
        extracted = invoke(box, "workbook.extract", inputs={"material": SourcePayload(stream.getvalue())},
            parameters={"series_id": "test.workbook", "issue_id": "2026-01"})
        assert portable_roundtrip(box, "workbook", extracted) == extracted
        assert any(cell.formula for sheet in extracted.sheets for cell in sheet.cells)
        assert b"unknown source field" in invoke(box, "readable.workbook", inputs={"value": extracted}).data


def test_archive_members_bounded_selection_and_pack_keep_container_evidence():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("one.csv", "a,b\n1,2\n")
        archive.writestr("other.txt", "kept")
    payload = SourcePayload(stream.getvalue(), "application/zip", "test.archive")
    with StrategyBox() as box:
        members = invoke(box, "archive.members", inputs={"material": payload}, parameters={"names": ("one.csv",)})
        assert len(members) == 1 and members[0].lineage[0].container == payload.identity
        assert members[0].lineage[0].member == "one.csv"
        packed = invoke(box, "archive.pack", inputs={"members": members})
        unpacked = invoke(box, "archive.members", inputs={"material": packed})
        assert unpacked[0].material.identity == members[0].material.identity
        refused = box.invoke("archive.members", inputs={"material": payload}, parameters={"max_unpacked_bytes": 1}, timeout=5)
        assert refused.outcome == "failed"


def test_native_csv_roles_are_independent_and_portable_without_conversion():
    payload = SourcePayload(b"subject,value\nA,0\nB,...\n", "text/csv", "test.csv")
    with StrategyBox() as box:
        values = []
        for role in (DataRole.ORIGINALS, DataRole.READABLE, DataRole.EXTRACTS):
            value = invoke(box, "qualify.csv", inputs={"material": payload}, parameters={
                "contract": DataContract("test.csv", 2, role), "columns": ("subject", "value")})
            encoded = invoke(box, "qualified.snapshot", inputs={"value": value})
            restored = invoke(box, "qualified.replay", inputs={"material": encoded})
            assert restored == value and restored.contract.role == role
            values.append(restored)
        assert all(value.identity == payload.identity and value.material.data == payload.data for value in values)
        assert box.invoke("qualify.csv", inputs={"material": payload}, parameters={
            "contract": DataContract("test.csv", 1, DataRole.EXTRACTS), "columns": ("wrong",)}, timeout=5).outcome == "failed"


@pytest.mark.parametrize("storage", ["memory", "files"])
def test_alignment_retention_and_store_ingestion_are_independent(storage, tmp_path):
    store = (MemoryDatasetStore(provider_id="test", scope_id="local") if storage == "memory" else
        FileDatasetStore(LocalFileStore(tmp_path), "datasets", provider_id="test", scope_id="local"))
    references = (("geography", ByteIdentity.of(b"edition one")),)
    with StrategyBox(providers={"dataset_writer": store, "dataset_reader": store, "dataset_catalog": store}) as box:
        integrated = invoke(box, "align.observations", inputs={"observations": batch()}, parameters={
            "mappings": {"subjects": {"local:A": ("territory", "RU")}}, "references": references, "require_mapped": True})
        assert integrated.batch.observations[0].subject.id == "RU"
        assert integrated.reference_editions == references
        assert portable_roundtrip(box, "integrated", integrated) == integrated
        reference = invoke(box, "ingest.observations", inputs={"value": integrated})
        snapshot = invoke(box, "query.dataset", inputs={"reference": reference})
        restored = invoke(box, "integrated.replay", inputs={"snapshot": snapshot})
        assert restored == integrated
        assert invoke(box, "list.dataset_versions", parameters={"dataset_id": batch().dataset_id}) == (reference,)
        selected = invoke(box, "query.integrated", inputs={"observations": restored}, parameters={"subject_ids": ("missing",)})
        assert not selected.batch.observations and selected.reference_editions == references


def test_alignment_rejects_colliding_grains_and_reference_editions_change_identity():
    original = batch()
    another = replace(original.observations[0], subject=SubjectRef("local", "B"))
    colliding = replace(original, observations=(original.observations[0], another))
    with StrategyBox() as box:
        result = box.invoke("align.observations", inputs={"observations": colliding}, parameters={"mappings": {
            "subjects": {"local:A": ("territory", "RU"), "local:B": ("territory", "RU")}}}, timeout=5)
        assert result.outcome == "failed"
        one = invoke(box, "align.observations", inputs={"observations": original}, parameters={"references": (("geo", ByteIdentity.of(b"one")),)})
        two = invoke(box, "align.observations", inputs={"observations": original}, parameters={"references": (("geo", ByteIdentity.of(b"two")),)})
        assert one.identity != two.identity
        assert one.batch.observations == two.batch.observations


def test_alignment_requires_exact_conversion_and_maps_coverage_coordinates():
    from stratbox.shared.data.assessment import CoverageAssessment, observation_coordinate, observation_scope
    source = batch()
    row = source.observations[0]
    members, observed = observation_scope((row,))
    coverage = CoverageAssessment("source.scope", members, True, observed, observed,
        expected_coordinates=(observation_coordinate(row),))
    source = replace(source, observations=(row,), evidence=replace(source.evidence, coverage=coverage))
    mapping = {"subjects": {"local:A": ("territory", "RU")},
        "metrics": {"stock": {"id": "stock.rub", "scale": Decimal("1")}}}
    with StrategyBox() as box:
        assert box.invoke("align.observations", inputs={"observations": source}, parameters={"mappings": mapping}, timeout=5).outcome == "failed"
        mapping["metrics"]["stock"]["multiplier"] = Decimal("1000")
        aligned = invoke(box, "align.observations", inputs={"observations": source}, parameters={"mappings": mapping})
        result = aligned.batch.observations[0]
        assert result.value == Decimal("12300.00") and result.value_status == "derived"
        assert result.raw_token == "12,30" and source.observations[0].value == Decimal("12.30")
        assert aligned.batch.evidence.coverage.status == "complete"
        expected = aligned.batch.evidence.coverage.expected_coordinates[0]
        assert (expected.subject_namespace, expected.subject_id, expected.metric_id) == ("territory", "RU", "stock.rub")


def test_comparison_distinguishes_source_revision_from_period_change():
    before = batch()
    after = replace(before, observations=(replace(before.observations[0], value=Decimal("15")), *before.observations[1:]))
    with StrategyBox() as box:
        comparison = invoke(box, "observations.compare", inputs={"before": before, "after": after})
        assert comparison.kind == "revision" and len(comparison.differences) == 1
        row = before.observations[0]
        period_after = replace(before, observations=(replace(row, period=PeriodRef("as_of", date(2026, 2, 1))),))
        result = invoke(box, "observations.compare", inputs={"before": replace(before, observations=(row,)), "after": period_after},
            parameters={"kind": "period"})
        assert result.kind == "period" and len(result.differences) == 1


def test_update_plan_changes_references_and_retries_only_missing_destinations():
    target = ProcessingTarget(SourceAssetIdentity("test.series", "2026-01", "main"), DataContract("test.values"),
        ByteIdentity.of(b"source"), "method-1", (("geo", ByteIdentity.of(b"one")),), ("a", "b"))
    retained = RetainedProcessing(target, ByteIdentity.of(b"result"), ("a",))
    with StrategyBox() as box:
        plan = invoke(box, "processing.plan_update", parameters={"targets": (target,), "retained": (retained,)})
        assert not plan.decisions[0].recompute and plan.decisions[0].destinations_to_write == ("b",)
        changed = replace(target, references=(("geo", ByteIdentity.of(b"two")),))
        plan = invoke(box, "processing.plan_update", parameters={"targets": (changed,), "retained": (retained,)})
        assert plan.decisions[0].recompute and plan.decisions[0].source_state == "same"


def test_preserve_and_coherent_release_use_confirmed_bytes_and_effects(tmp_path):
    store = LocalFileStore(tmp_path)
    with StrategyBox(providers={"filestore": store, "output_filestore": store}) as box:
        original = SourcePayload(b"exact native bytes", "text/plain")
        receipt = invoke(box, "preserve.material", inputs={"material": original}, parameters={"destination": "original.txt"}, output="receipt")
        replay = invoke(box, "read.material_file", parameters={"path": "original.txt", "media_type": "text/plain"}, output="material")
        assert replay.data == original.data
        release = box.invoke("publish.release", inputs={"receipts": (receipt,)}, parameters={"release_id": "test.release",
            "members": ("original",), "destination": "release.json", "input_versions": {"source": original.identity.sha256},
            "member_versions": {"original": {"source": original.identity.sha256}},
            "expected_members": {"original": original.identity}}, timeout=5)
        assert release.outcome == "succeeded", release.diagnostics
        assert json.loads(release.output("manifest").data)["members"][0]["sha256"] == original.identity.sha256
        bad = replace(receipt, status="unknown")
        failed = box.invoke("publish.release", inputs={"receipts": (bad,)}, parameters={"release_id": "bad",
            "destination": "bad.json"}, timeout=5)
        assert failed.outcome == "failed" and not (tmp_path / "bad.json").exists()
        stale = box.invoke("publish.release", inputs={"receipts": (receipt,)}, parameters={"release_id": "stale",
            "destination": "stale.json", "members": ("original",), "input_versions": {"source": "new"},
            "member_versions": {"original": {"source": "old"}}}, timeout=5)
        assert stale.outcome == "failed" and not (tmp_path / "stale.json").exists()
        (tmp_path / "original.txt").write_bytes(b"changed")
        changed = box.invoke("publish.release", inputs={"receipts": (receipt,)}, parameters={"release_id": "changed",
            "destination": "changed.json"}, timeout=5)
        assert changed.outcome == "failed" and not (tmp_path / "changed.json").exists()


def test_reference_editions_are_verified_and_pinned_in_catalog_resolution():
    snapshot = catalog_snapshot()
    with StrategyBox() as box:
        editions = invoke(box, "resolve.reference_editions", parameters={"references": (("reference.geography.names", None),)})
        assert editions[0][0] == "reference.geography.names"
        resolved = snapshot.resolve("resolve.reference_editions")
        assert "reference:reference.geography.names" in resolved.identities


def test_original_transition_chain_preserves_return_to_previous_bytes():
    from stratbox.shared.source_versions import OriginalVersion
    with StrategyBox() as box:
        first = OriginalVersion("test.series:2026-01:main", ByteIdentity.of(b"A"))
        observed = invoke(box, "compare.source_versions", inputs={"candidate": first}, parameters={"baseline_state": "initial"})
        baseline = replace(first, transition_id=observed.transition_id)
        second = replace(first, identity=ByteIdentity.of(b"B"))
        changed = invoke(box, "compare.source_versions", inputs={"candidate": second, "baseline": baseline},
            parameters={"baseline_state": "available"})
        returned = invoke(box, "compare.source_versions", inputs={"candidate": first,
            "baseline": replace(second, transition_id=changed.transition_id)}, parameters={"baseline_state": "available"})
        assert returned.state == "revised" and returned.new_identity == first.identity
        assert len({observed.transition_id, changed.transition_id, returned.transition_id}) == 3
        assert returned.previous_transition_id == changed.transition_id


def test_artifact_save_read_transfer_preserve_descriptor_and_representation(tmp_path):
    from stratbox.shared.materials import MaterialArtifact
    from stratbox.shared.data.representation import Representation
    store = LocalFileStore(tmp_path)
    artifact = MaterialArtifact(DataContract("test.rows", 3, DataRole.EXTRACTS),
        Representation("native.csv", 1, "text/csv", b"a,b\n1,2\n", "utf-8",
            ValueEvidence(frozenset({"csv.structurally_valid"}), reference_fingerprints=("geo-edition-1",))), series_id="test.series")
    with StrategyBox(providers={"filestore": store, "output_filestore": store}) as box:
        reference = invoke(box, "save.artifact", inputs={"artifact": artifact}, parameters={"destination": "one.csv"}, output="artifact")
        restored = invoke(box, "read.artifact", inputs={"reference": reference})
        assert restored == artifact
        copied = invoke(box, "transfer.artifact", inputs={"reference": reference}, parameters={"destination": "two.csv"}, output="artifact")
        assert copied.identity == reference.identity
        assert invoke(box, "read.artifact", inputs={"reference": copied}) == artifact
        (tmp_path / "two.csv").write_bytes(b"tampered")
        assert box.invoke("read.artifact", inputs={"reference": copied}, timeout=5).outcome == "failed"


def test_all_neutral_declarations_have_resolving_dispositions():
    from pathlib import Path
    from stratbox.capabilities.operations.stages import dispositions
    root = Path(__file__).parents[3] / "src/stratbox/operations/specifications/core"
    baseline = {json.loads(path.read_text())["definition"]["operation_id"] for path in root.rglob("OPERATION_*.yaml")}
    assert baseline == set(dispositions()) and len(baseline) == 36
    for targets in dispositions().values():
        assert targets
        for target in targets:
            catalog_snapshot().definition(target)


def test_snapshot_query_is_typed_bounded_and_requires_the_pinned_identity():
    from stratbox.shared.data.query import TableQuery, TablePredicate
    with StrategyBox() as box:
        snapshot = invoke(box, "observations.snapshot", inputs={"value": batch()})
        query = TableQuery("observations", columns=("metric_id", "value_status"),
            predicates=(TablePredicate("value_status", "eq", "reported"),), limit=1, scan_limit=2)
        selected = invoke(box, "snapshot.query", inputs={"snapshot": snapshot}, parameters={"query": query,
            "expected_identity": snapshot.identity})
        assert selected.table.rows == (("stock", "reported"),) and selected.has_more
        assert selected.source_rows == (0,) and selected.source_identity == snapshot.identity
        assert box.invoke("snapshot.query", inputs={"snapshot": snapshot}, parameters={"query": query,
            "expected_identity": ByteIdentity.of(b"different")}, timeout=5).outcome == "failed"
        assert box.invoke("snapshot.encode", inputs={"snapshot": snapshot}, parameters={"max_bytes": 10}, timeout=5).outcome == "failed"
