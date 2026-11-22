"""Continue office analysis after portable storage, keeping qualification intact."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from openpyxl import Workbook

from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.execution.machine import invoke_read_only
from stratbox.core.network import HttpResponse
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.domains.cbr.service_network import bank_offices as daily
from stratbox.domains.cbr.service_network import territorial_offices as monthly
from stratbox.domains.registry import operation_catalog
from stratbox.shared.data.releases import CompareReleaseRequest
from stratbox.shared.evidence import SourcePayload


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/universal_core/offices-basic.html"
CAPTURED = date(2026, 11, 22)
OFFICIAL = date(2026, 11, 1)


def accepted(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result


def store_at(path):
    return FileDatasetStore(LocalFileStore(str(path)), "datasets", provider_id="files", scope_id="test")


def roundtrip(path, snapshot):
    written = accepted(datasets.write_snapshot(datasets.WriteSnapshotRequest(snapshot), store=store_at(path)))
    loaded = accepted(datasets.read_snapshot(datasets.ReadSnapshotRequest(written.value.reference), store=store_at(path)))
    assert loaded.value == snapshot
    return loaded, written.value.reference


def workbook(*, extra=True, formula=True, copies=1):
    book = Workbook()
    sheet = book.active
    sheet.title = "Published observations"
    sheet.append(["Данные по состоянию на 01.11.2026"])
    labels = ["Территория", "Кредитные организации", "Филиалы", "Мобильные офисы", "Всего"]
    sheet.append(labels + (["Дополнительная отметка"] if extra else []))
    names = ["Российская Федерация"] + [f"Новая территория {index:03d}" for index in range(35)]
    for index, name in enumerate(names):
        values = [name, 2, 3, "=2+3" if formula and index == 0 else 5, 10]
        sheet.append(values + (["новая категория"] if extra else []))
    for index in range(1, copies):
        book.copy_worksheet(sheet).title = f"Competing block {index:02d}"
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


@pytest.mark.parametrize("official", (None, OFFICIAL))
def test_daily_complete_replay_preserves_dates_and_comparison(tmp_path, monkeypatch, official):
    parsed = accepted(daily.parse(daily.ParseOfficesRequest(SourcePayload(FIXTURE.read_bytes()), CAPTURED, official)))
    encoded = accepted(bind_request(daily.SNAPSHOT, {"release": project_output(parsed, "release")},
        parameters={"dataset_id": "office.observations", "version_id": "release-1"}).invoke(daily.snapshot_release))
    loaded, reference = roundtrip(tmp_path, encoded.value)
    from stratbox.domains.cbr.service_network.bank_offices import operations
    monkeypatch.setattr(operations, "extract_records", lambda *_: pytest.fail("replay parsed the original HTML"))
    restored = accepted(bind_request(daily.RESTORE, {"snapshot": project_output(loaded, "snapshot")}).invoke(daily.restore_release))
    assert restored.value == parsed.value
    assert restored.value.source_details == {"captured_on": CAPTURED, "official_as_of": official}
    expected = daily.compare(CompareReleaseRequest(parsed.value, parsed.value)).value
    actual = daily.compare(CompareReleaseRequest(restored.value, parsed.value)).value
    assert actual == expected and actual.state == "unchanged"
    assert all(item.period.as_of == (official or CAPTURED) for item in restored.value.batch.observations)
    assert all(item.period.kind == ("as_of" if official else "capture") for item in restored.value.batch.observations)
    if official is not None:
        # Only the store and its pinned reference cross this process boundary.
        script = """
import json, sys
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.domains.cbr.service_network import bank_offices as offices
from stratbox.shared.data.releases import CompareReleaseRequest
from stratbox.shared.data.snapshots import SnapshotReference
from stratbox.shared.identity import ByteIdentity
store = FileDatasetStore(LocalFileStore(sys.argv[1]), 'datasets', provider_id='files', scope_id='test')
reference = SnapshotReference('files', 'test', 'office.observations', 'release-1', ByteIdentity(sys.argv[2], int(sys.argv[3])))
loaded = datasets.read_snapshot(datasets.ReadSnapshotRequest(reference), store=store)
assert loaded.outcome == 'succeeded', loaded.diagnostics
release = offices.restore_release(loaded.value)
assert release.outcome == 'succeeded', release.diagnostics
comparison = offices.compare(CompareReleaseRequest(release.value, release.value))
assert comparison.value.state == 'unchanged'
print(json.dumps({'facts': release.value.facts_identity.sha256, 'captured': str(release.value.source_details['captured_on']), 'official': str(release.value.source_details['official_as_of'])}))
"""
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
        process = subprocess.run([sys.executable, "-B", "-c", script, str(tmp_path), reference.identity.sha256,
                                  str(reference.identity.size)], env=environment, check=True, text=True, capture_output=True)
        assert json.loads(process.stdout) == {"facts": parsed.value.facts_identity.sha256,
                                             "captured": str(CAPTURED), "official": str(OFFICIAL)}


def test_csv_period_is_explicit_and_unknown_remains_unknown(tmp_path):
    parsed = accepted(daily.parse(daily.ParseOfficesRequest(SourcePayload(FIXTURE.read_bytes()), CAPTURED, OFFICIAL))).value
    payload = SourcePayload(parsed.representation.data, "text/csv")
    unknown = accepted(daily.read_representation(daily.ReadOfficesRequest(payload, CAPTURED))).value
    assert unknown.batch is None and unknown.facts_identity is None
    assert unknown.source_details["period_basis"] == "unknown"
    assert unknown.source_details["official_as_of"] is None
    assert daily.compare(CompareReleaseRequest(unknown, parsed)).value.state == "indeterminate"
    encoded = accepted(daily.snapshot_release(daily.SnapshotOfficesRequest(unknown, "offices.csv", "unknown")))
    loaded, _ = roundtrip(tmp_path, encoded.value)
    assert accepted(daily.restore_release(loaded.value)).value == unknown
    replay = accepted(daily.read_representation(daily.ReadOfficesRequest(payload, CAPTURED, OFFICIAL))).value
    assert replay.facts_identity == parsed.facts_identity
    assert daily.compare(CompareReleaseRequest(replay, parsed)).value.state == "unchanged"
    conflict = daily.read_representation(daily.ReadOfficesRequest(payload, CAPTURED, OFFICIAL, "capture"))
    assert conflict.diagnostics[0].code == "request.observation_period_invalid"


def test_acquisition_evidence_survives_without_becoming_new_acquisition(tmp_path):
    observed = datetime(2026, 11, 21, 23, 30, tzinfo=timezone.utc)

    class HTTP:
        def exchange(self, request, **_):
            return HttpResponse(200, FIXTURE.read_bytes(), {"content-type": "text/html; charset=utf-8"},
                                observed, "https://www.cbr.ru")

    parsed = accepted(daily.capture(daily.AcquireOfficesRequest(timezone(timedelta(hours=3))), transport=HTTP())).value
    encoded = accepted(daily.snapshot_release(daily.SnapshotOfficesRequest(parsed, "offices.capture", "one")))
    loaded, _ = roundtrip(tmp_path, encoded.value)
    restored = accepted(daily.restore_release(loaded.value))
    assert restored.value == parsed
    assert restored.value.as_of == CAPTURED
    assert restored.value.acquisition.observed_at_utc == observed
    assert restored.value.qualification.provenance == "provider_reported"
    assert restored.used_inputs[0].role == "retained_snapshot"
    assert restored.value.inputs == parsed.inputs


@pytest.mark.parametrize("fragment", (False, True))
def test_territorial_selection_formula_unknown_fields_and_scope_survive(tmp_path, monkeypatch, fragment):
    parsed = accepted(monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook()), OFFICIAL,
        national_row=3 if fragment else None, last_row=5 if fragment else None)))
    value = parsed.value
    assert value.qualification.analysis == "qualified_subset"
    assert set(value.qualification.excluded_fields) == {"Мобильные офисы", "Дополнительная отметка"}
    assert value.source_details["formula_lineage"]["3"]["4"]["cache_missing"]
    assert "Новая территория 000" in {item.subject.id for item in value.batch.observations}
    encoded = accepted(monthly.snapshot_release(monthly.SnapshotOfficesRegRequest(value, "offices.territory", "one")))
    loaded, _ = roundtrip(tmp_path, encoded.value)
    from stratbox.domains.cbr.service_network.territorial_offices import operations
    monkeypatch.setattr(operations, "convert_xlsx", lambda *_args, **_kwargs: pytest.fail("replay parsed original XLSX"))
    restored = accepted(bind_request(monthly.RESTORE, {"snapshot": project_output(loaded, "snapshot")}).invoke(monthly.restore_release)).value
    assert restored == value
    assert restored.source_details["selection"]["column_order"] == (1, 2, 3, 4, 5, 6)
    assert restored.source_details["selection"]["header_rows"] == (2,)
    assert all(item.metric.unit == "count" for item in restored.batch.observations)
    assert monthly.compare(CompareReleaseRequest(restored, value)).value == monthly.compare(CompareReleaseRequest(value, value)).value
    assert restored.qualification.scope == ("selected_fragment" if fragment else "cbr.offices_reg")


def test_territorial_csv_cannot_silently_qualify_missing_formula_caches(tmp_path):
    parsed = accepted(monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook()), OFFICIAL,
                                                                   national_row=3, last_row=5))).value
    payload = SourcePayload(parsed.representation.data, "text/csv")
    literal = accepted(monthly.read_representation(monthly.ReadOfficesRegRequest(payload, OFFICIAL))).value
    assert literal.batch is None and literal.qualification.analysis == "literal_only"
    assert literal.qualification.scope == "unqualified_csv"
    encoded = accepted(monthly.snapshot_release(monthly.SnapshotOfficesRegRequest(literal, "offices.literal", "one")))
    loaded, _ = roundtrip(tmp_path, encoded.value)
    assert accepted(monthly.restore_release(loaded.value)).value == literal
    restored = accepted(monthly.read_representation(monthly.ReadOfficesRegRequest(payload, OFFICIAL, parsed.source_details))).value
    assert restored.facts_identity == parsed.facts_identity
    assert restored.qualification.excluded_fields == parsed.qualification.excluded_fields
    assert restored.qualification.scope == "selected_fragment"
    wrong = {**parsed.source_details, "selection": {**parsed.source_details["selection"], "unresolved_fields": ()}}
    failed = monthly.read_representation(monthly.ReadOfficesRegRequest(payload, OFFICIAL, wrong))
    assert failed.outcome == "failed"
    assert failed.diagnostics[0].code == "source.csv_formula_evidence_invalid"


def test_ambiguous_candidates_keep_all_blocks_and_replay_partial(tmp_path):
    parsed = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook(copies=35)), OFFICIAL))
    assert parsed.outcome == "partial" and len(parsed.value.blocks) == 35
    encoded = accepted(bind_request(monthly.SNAPSHOT, {"release": project_output(parsed, "candidates")},
        parameters={"dataset_id": "offices.candidates", "version_id": "one"}).invoke(monthly.snapshot_release))
    assert encoded.value.manifest.coverage.status == "partial"
    loaded, _ = roundtrip(tmp_path, encoded.value)
    restored = bind_request(monthly.RESTORE, {"snapshot": project_output(loaded, "snapshot")}).invoke(monthly.restore_release)
    assert restored.outcome == "partial"
    assert restored.value == parsed.value
    assert restored.value.as_of == OFFICIAL
    assert project_output(restored, "candidates").value == parsed.value


def test_incomplete_or_contradictory_release_cannot_be_restored():
    value = accepted(daily.parse(daily.ParseOfficesRequest(SourcePayload(FIXTURE.read_bytes()), CAPTURED, OFFICIAL))).value
    encoded = accepted(daily.snapshot_release(daily.SnapshotOfficesRequest(value, "offices.invalid", "one"))).value
    assert daily.restore_release(replace(encoded, tables=encoded.tables[:1])).outcome == "failed"
    altered = replace(value, source_details={"captured_on": CAPTURED, "official_as_of": date(2026, 10, 1)})
    failed = daily.snapshot_release(daily.SnapshotOfficesRequest(altered, "offices.invalid", "two"))
    assert failed.diagnostics[0].code == "cbr.offices.snapshot_invalid"


def test_machine_parse_keeps_both_dates():
    class Materials:
        def source(self, reference):
            assert reference == "fixture"
            return SourcePayload(FIXTURE.read_bytes())

    data = json.dumps({"operation_id": "cbr.offices.parse", "contract_version": 1,
        "input": {"source_ref": "fixture", "capture_date": str(CAPTURED), "official_as_of": str(OFFICIAL)}}).encode()
    result = json.loads(invoke_read_only(data, materials=Materials(), catalog=operation_catalog()))
    assert result["outcome"] == "succeeded"
    assert result["value"]["captured_on"] == str(CAPTURED)
    assert result["value"]["official_as_of"] == str(OFFICIAL)
