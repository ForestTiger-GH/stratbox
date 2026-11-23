"""DBF source semantics and continuation through an independently opened store."""

from dataclasses import replace
from datetime import date
from io import BytesIO
from struct import pack

import pandas as pd
import pytest
from openpyxl import load_workbook

from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.formats.archives.members import zip_bytes
from stratbox.core.formats.dbf_lossless import DBFDecodeError, decode_dbf
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.shared.material_collections import decode_collection, encode_collection
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.operations import reporting_forms as forms
from stratbox.domains.cbr.operations.reporting_forms import source_definitions as D
from stratbox.domains.cbr.operations.reporting_forms.definitions import BUILD, VIEWS, RENDER


def dbf(fields, records, *, version=3):
    width = 1 + sum(field[2] for field in fields)
    header = pack("<BBBBIHH20x", version, 126, 4, 1, len(records), 33 + 32 * len(fields), width)
    columns = b"".join(pack("<11sc4xBB14x", name.encode("ascii"), kind.encode("ascii"), size, decimals)
                       for name, kind, size, decimals in fields)
    rows = b"".join(flag + b"".join(value.ljust(field[2]) for field, value in zip(fields, values))
                    for flag, values in records)
    return header + columns + b"\r" + rows + b"\x1a"


def accepted(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result


def test_source_lexemes_deleted_records_and_schema_remain_explicit():
    source = dbf((("CODE", "C", 7, 0), ("VALUE", "N", 16, 4), ("DATE", "D", 8, 0), ("FLAG", "L", 1, 0)), (
        (b" ", (b"0012", b"000001.2300", b"20260231", b"?")),
        (b"*", (b" 0013", b"", b"00000000", b"F")),
        (b" ", (b"0014", b"0", b"", b"")),
    ))
    table = decode_dbf(source)
    assert table.records[0].values == ("0012", "000001.2300", "20260231", "?")
    assert table.records[1].values == (" 0013", "", "00000000", "F")
    assert table.records[2].values[1] == "0"
    assert [row.ordinal for row in table.records] == [1, 2, 3]
    assert [row.deleted for row in table.records] == [False, True, False]
    assert table.header_date == bytes((126, 4, 1))
    assert table.fields[1].decimals == 4
    assert table.encoding == "cp866"


@pytest.mark.parametrize("mutate,code", (
    (lambda b: b[:4], "dbf.header_truncated"),
    (lambda b: bytes((0x04,)) + b[1:], "dbf.dialect_unsupported"),
    (lambda b: b[:64] + b"x" + b[65:], "dbf.header_geometry_invalid"),
    (lambda b: b[:65] + b"?" + b[66:], "dbf.deletion_flag_invalid"),
    (lambda b: b[:-3], "dbf.records_truncated"),
    (lambda b: b + b"extra", "dbf.trailing_data"),
    (lambda b: b[:43] + b"M" + b[44:], "dbf.companion_or_binary_profile_required"),
    (lambda b: b[:10] + pack("<H", 8) + b[12:], "dbf.records_truncated"),
))
def test_strict_decoder_rejects_unverified_geometry_and_dialects(mutate, code):
    data = dbf((("CODE", "C", 4, 0),), ((b" ", (b"0012",)),))
    with pytest.raises(DBFDecodeError, match=code):
        decode_dbf(mutate(data))


def test_source_only_forms_and_unknown_models_are_separate():
    payload = SourcePayload(dbf((("CODE", "C", 4, 0),), ((b" ", (b"0012",)),)))
    for code in ("134", "803"):
        key = forms.FormKey(code, date(2026, 4, 1))
        assert accepted(forms.select_sources(forms.SelectFormSourcesRequest((key,)))).value[0].key == key
        flakes = accepted(forms.extract_forms(forms.ExtractFormRequest(key, payload)))
        assert flakes.value.members[0].table.records[0].values == ("0012",)
        refused = forms.normalize_form(forms.NormalizeFormRequest(flakes.value))
        assert refused.diagnostics[0].code == "source.form_layout_unsupported"


def test_index_selects_actual_published_dates_and_accepts_offline_html():
    payload = SourcePayload(b'<a href="/vfs/credit/forms/803-20260401.rar">form</a>'
        b'<a href="/vfs/credit/forms/134-20160101.rar">old</a>'
        b'<a href="/vfs/credit/forms/803-20260401.rar">duplicate</a>', "text/html")
    result = accepted(forms.discover_sources(forms.DiscoverFormsRequest(payload, date(2023, 1, 1), date(2028, 1, 1))))
    assert [(x.key.code, x.key.as_of) for x in result.value.sources] == [("803", date(2026, 4, 1))]
    assert result.value.index_identity == payload.identity


def _roundtrip(tmp_path, snapshot):
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    written = accepted(datasets.write_snapshot(datasets.WriteSnapshotRequest(snapshot), store=store))
    reopened = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    return accepted(datasets.read_snapshot(datasets.ReadSnapshotRequest(written.value.reference), store=reopened))


def test_full_flakes_history_calculation_and_views_replay_after_file_read(tmp_path):
    data = dbf((("REGN_GKO", "C", 12, 0), ("STR", "C", 12, 0), ("VSEGO", "N", 20, 4)), (
        (b" ", (b"1000", b"14", b"000001.2300")),
        (b"*", (b"1000", b"14", b"999.9")),
    ))
    dictionary = dbf((("FIELD", "C", 8, 0),), ((b" ", (b"0012",)),))
    original = SourcePayload(zip_bytes({"PK802.dbf": data, "metadata.dbf": dictionary, "readme.txt": b"companion"}))
    extracted = accepted(forms.extract_forms(forms.ExtractFormRequest(forms.FormKey("802", date(2026, 4, 1)), original)))
    assert len(extracted.value.members) == 3
    encoded = accepted(forms.flake_snapshot(forms.FormFlakeSnapshotRequest(extracted.value, "cbr.form.802", "raw-1")))
    read = _roundtrip(tmp_path, encoded.value)
    restored = accepted(bind_request(D.RESTORE_FLAKES, {"snapshot": project_output(read, "snapshot")}).invoke(forms.restore_flakes))
    assert restored.value == extracted.value
    assert restored.value.members[2].data == b"companion"
    normalized = accepted(bind_request(D.NORMALIZE, {"flakes": project_output(restored, "flakes")}).invoke(forms.normalize_form))
    assert len(normalized.value.rows) == 1
    assert normalized.value.rows.iloc[0]["total"] == "000001.2300"
    history = accepted(forms.build_source_history(forms.FormHistoryRequest((normalized.value,), "cbr.form.802", "history-1")))
    read_history = _roundtrip(tmp_path, history.value)
    released = accepted(bind_request(D.RESTORE_HISTORY, {"snapshot": project_output(read_history, "snapshot")}).invoke(forms.restore_history))
    data_result = accepted(bind_request(BUILD, {"snapshots": project_output(released, "snapshots")},
        parameters={"banks": (forms.BankSelection("1000", "Bank"),)}).invoke(forms.build_form_data))
    saved_data = accepted(forms.snapshot_result(forms.FormResultSnapshotRequest(data_result.value, "cbr.form.802", "data-1")))
    reopened_data = _roundtrip(tmp_path, saved_data.value)
    replayed_data = accepted(bind_request(D.RESTORE_DATA, {"snapshot": project_output(reopened_data, "snapshot")}).invoke(forms.restore_data))
    pd.testing.assert_frame_equal(replayed_data.value.long, data_result.value.long)
    assert replayed_data.value.evidence == data_result.value.evidence
    views = accepted(bind_request(VIEWS, {"data": project_output(replayed_data, "result")}).invoke(forms.build_form_views))
    saved_views = accepted(forms.snapshot_result(forms.FormResultSnapshotRequest(views.value, "cbr.form.802", "views-1")))
    reopened_views = _roundtrip(tmp_path, saved_views.value)
    replayed_views = accepted(bind_request(D.RESTORE_VIEWS, {"snapshot": project_output(reopened_views, "snapshot")}).invoke(forms.restore_views))
    rendered = accepted(bind_request(RENDER, {"views": project_output(replayed_views, "result")}).invoke(forms.render_workbook))
    workbook = load_workbook(BytesIO(rendered.value.data), data_only=True)
    assert set(workbook.sheetnames) == {"Обзор", "Полная форма", "Данные"}
    rows = list(workbook["Данные"].values)
    header = list(rows[0])
    values = {row[header.index("Код")]: row[header.index("Значение")] for row in rows[1:]}
    assert values["14"] == 1.23
    workbook.close()


def test_unsupported_member_is_preserved_but_prevents_complete_normalization(tmp_path):
    valid = dbf((("CODE", "C", 4, 0),), ((b" ", (b"0012",)),))
    unsupported = bytes((0x30,)) + valid[1:]
    result = forms.extract_forms(forms.ExtractFormRequest(forms.FormKey("803", date(2026, 4, 1)),
        SourcePayload(zip_bytes({"valid.dbf": valid, "unsupported.dbf": unsupported})), strict=False))
    assert result.outcome == "partial"
    assert result.value.members[1].status == "unsupported"
    encoded = accepted(forms.flake_snapshot(forms.FormFlakeSnapshotRequest(result.value, "cbr.form.803", "partial-1")))
    read = _roundtrip(tmp_path, encoded.value)
    replayed = forms.restore_flakes(read.value)
    assert replayed.outcome == "partial"
    assert replayed.value == result.value
    assert replayed.value.members[1].data == unsupported


def test_incomplete_dataset_cannot_be_relabelled_as_restored_flakes(tmp_path):
    valid = dbf((("CODE", "C", 4, 0),), ((b" ", (b"0012",)),))
    flakes = accepted(forms.extract_forms(forms.ExtractFormRequest(forms.FormKey("134", date(2012, 1, 1)), SourcePayload(valid))))
    snapshot = accepted(forms.flake_snapshot(forms.FormFlakeSnapshotRequest(flakes.value, "form.134", "one"))).value
    partial = replace(snapshot, tables=snapshot.tables[:1])
    result = forms.restore_flakes(partial)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "cbr.forms.flake_snapshot_invalid"


def test_csv_package_uses_common_manifest_and_restores_without_dbf_parsing(tmp_path, monkeypatch):
    import json
    from zipfile import ZipFile
    from stratbox.domains.cbr.tables.reporting_forms import flakes as flake_module
    original = dbf((("CODE", "C", 8, 0), ("VALUE", "N", 16, 4)), (
        (b" ", (b"0012", b"000001.2300")), (b"*", (b"0013", b"")),
    ))
    extracted = accepted(forms.extract_forms(forms.ExtractFormRequest(forms.FormKey("803", date(2026, 4, 1)),
        SourcePayload(zip_bytes({"nested/A.dbf": original, "readme.txt": b"notes"})))))
    rendered = accepted(forms.render_flakes(forms.RenderFormFlakesRequest(extracted.value,
        "regulatory-reporting/2026/2026-04-01/form-0409803")))
    exports = rendered.value
    fields = tuple((name, SourcePayload(rep.data, rep.media_type)) for name, rep in exports.files)
    manifest = decode_collection(encode_collection(exports.manifest))
    monkeypatch.setattr(flake_module, "decode_dbf", lambda *args, **kwargs: pytest.fail("DBF was parsed during CSV replay"))
    restored = accepted(forms.read_flake_export(forms.ReadFormFlakeExportRequest(fields, manifest)))
    assert restored.value == extracted.value
    stored = accepted(archive_materials(ArchiveRequest(
        tuple(ArchiveMember(name, payload) for name, payload in fields),
        OriginalDestination("forms.zip"), manifest=manifest), output_store=LocalFileStore(str(tmp_path))))
    with ZipFile(tmp_path / "forms.zip") as archive:
        csv_name = next(name for name in archive.namelist() if name.endswith("A.csv"))
        assert archive.read(csv_name).decode("utf-8") == "CODE,VALUE\n0012,000001.2300\n0013,\n"
        assert json.loads(archive.read("manifest.json"))["schema"] == "stratbox.material-collection.v1"
    assert stored.value.manifest == manifest
