"""Observable archive and lexical DBF contracts over bounded physical readers."""
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from struct import pack, unpack_from
from types import SimpleNamespace
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
import zlib

import pytest

from stratbox.core.commands.archives import archive_inspect, archive_pack, archive_unpack
from stratbox.core.commands.decoding import dbf_decode
from stratbox.core.commands.tabular_export import dbf_export_csv
from stratbox.core.formats.archives.members import ArchiveError, ArchiveLimits, RarArchiveReader
from stratbox.core.formats.archives.store import ArchiveEntry, encode_zip
from stratbox.core.formats.dbf_lossless import DBFDecodeError, DBFReader, decode_dbf
from stratbox.core.limits import BudgetExceeded, BudgetMeter, ExecutionBudget
from stratbox.core.storage.readable import open_material
from stratbox.core.storage.staged_values import StagedValueStore
from stratbox.shared.data.archives import ArchiveMemberSelection
from stratbox.shared.data.dbf import DBFEncodingOverride, DBFPreservationPolicy
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import IdentifiedMaterial, Material, SourceClaim
from stratbox.shared.identity import ByteIdentity


class Context:
    def __init__(self, directory, **parameters):
        self.parameters, self.budget = parameters, None
        self.service = SimpleNamespace(staging=StagedValueStore(directory=directory))
        self.checkpoints = 0

    def checkpoint(self):
        self.checkpoints += 1

    def stage(self, **properties):
        return self.service.staging.builder("test", budget=self.budget,
            checkpoint=self.checkpoint, **properties)

    def open_material(self, value):
        return open_material(value, self)

    def provider(self, role):
        assert role == "archive_reader"
        return RarArchiveReader()

    def read(self, value):
        with self.open_material(value) as stream:
            return stream.read()

    def close(self):
        self.service.staging.release("test")
        self.service.staging.close()


@pytest.fixture
def context(tmp_path):
    value = Context(tmp_path)
    try:
        yield value
    finally:
        value.close()


def dbf_bytes(fields, rows, *, version=3, driver=0, eof=True):
    header = bytearray(pack("<BBBBIHH20x", version, 126, 11, 26,
        len(rows), 33 + 32 * len(fields), 1 + sum(field[2] for field in fields)))
    header[29] = driver
    for name, kind, width, decimals in fields:
        header.extend(pack("<11sc4xBB14x", name.encode("ascii"), kind.encode("ascii"), width, decimals))
    header.extend(b"\r")
    for deleted, values in rows:
        header.extend(b"*" if deleted else b" ")
        for definition, value in zip(fields, values):
            assert len(value) <= definition[2]
            header.extend(value.ljust(definition[2], b" "))
    return bytes(header) + (b"\x1a" if eof else b"")


def zip_bytes(files, *, method=ZIP_STORED):
    result = BytesIO()
    with ZipFile(result, "w", compression=method) as archive:
        for name, data in files:
            archive.writestr(name, data)
    return result.getvalue()


def stored_rar_bytes(files):
    """Valid single-volume RAR4 framing with actual header/file CRC checks."""
    def header(body):
        return pack("<H", zlib.crc32(body) & 0xFFFF) + body
    result = bytearray(b"Rar!\x1a\x07\x00")
    result.extend(header(pack("<BHHHI", 0x73, 0, 13, 0, 0)))
    for name, data in files:
        name = name.encode("ascii")
        body = pack("<BHH", 0x74, 0x8000, 32 + len(name)) + pack("<LLBLLBBHL",
            len(data), len(data), 3, zlib.crc32(data), 0, 20, 0x30, len(name), 0o100644) + name
        result.extend(header(body))
        result.extend(data)
    result.extend(header(pack("<BHH", 0x7B, 0, 7)))
    return bytes(result)


@pytest.mark.parametrize("build", [zip_bytes, stored_rar_bytes])
@pytest.mark.parametrize("placement", ["buffered", "staged"])
def test_zip_and_real_rar_share_selection_lineage_and_dispositions(context, build, placement):
    source = Material(build((("form.dbf", b"physical table"), ("nested/support.DBF", b"codes"),
                             ("readme.txt", b"excluded"))), metadata={"issue_id": "2026-11-01"})
    use = SourceUse(SourceCoordinate(source_id="fixture.forms", issue_id="2026-11-01",
        material_identity=source.identity), qualification="related")
    identified = IdentifiedMaterial(source, SourceClaim("fixture.forms", "2026-11-01", "form"),
        source_uses=(use,))
    context.parameters = {"placement": placement}
    output = archive_unpack({"material": identified, "selection": ArchiveMemberSelection(suffixes=(".dbf",))}, None, context)
    assert output["assessment"].complete
    assert [context.read(member) for member in output["members"]] == [b"physical table", b"codes"]
    assert [entry.disposition for entry in output["inventory"].members] == ["verified", "verified", "excluded"]
    assert output["inventory"].coverage == "selected_members_verified"
    for member in output["members"]:
        assert member.lineage[-1] == source.identity and member.source_uses == (use,)
        assert member.source_id == "fixture.forms" and member.metadata["container_asset_id"] == "form"
        assert isinstance(member, StagedMaterialRef) == (placement == "staged")


def test_only_selected_member_inflates_and_explicit_empty_is_complete(context):
    data = bytearray(zip_bytes((("wanted", b"good"), ("excluded", b"bad checksum"))))
    with ZipFile(BytesIO(data)) as archive:
        entry = archive.getinfo("excluded")
        position = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
    data[position] ^= 1
    material = Material(bytes(data))
    inventory = archive_inspect({"material": material}, None, context)["inventory"]
    assert all(member.identity is None for member in inventory.members)
    context.parameters = {"names": ("wanted",), "max_unpacked_bytes": 4}
    selected = archive_unpack({"material": material}, None, context)
    assert selected["members"][0].data == b"good"
    context.parameters = {"names": ()}
    empty = archive_unpack({"material": material}, None, context)
    assert empty["members"] == () and empty["assessment"].complete
    context.parameters = {"names": ("excluded",)}
    with pytest.raises(ArchiveError, match="archive.invalid_zip"):
        archive_unpack({"material": material}, None, context)


def test_unselected_unsafe_names_are_rejected_and_missing_names_are_explicit(context):
    with pytest.raises(ArchiveError, match="archive.unsafe_member"):
        archive_unpack({"material": Material(zip_bytes((("wanted", b"a"), ("../bad", b"b")))),
                        "selection": ArchiveMemberSelection(names=("wanted",))}, None, context)
    with pytest.raises(ArchiveError, match="archive.selected_member_missing"):
        archive_unpack({"material": Material(zip_bytes((("wanted", b"a"),))),
                        "selection": ArchiveMemberSelection(names=("absent",))}, None, context)


def test_inventory_limits_precede_zipfile_central_directory_allocation(context, monkeypatch):
    material = Material(zip_bytes((("a", b"a"), ("b", b"b"))))
    context.parameters = {"max_members": 1}
    import stratbox.core.formats.archives.members as archive_members
    monkeypatch.setattr(archive_members, "ZipFile", lambda *a, **kw: pytest.fail("Unadmitted directory allocated"))
    with pytest.raises(ArchiveError, match="archive.inventory_limit"):
        archive_inspect({"material": material}, None, context)


@pytest.mark.parametrize("compression", ["stored", "deflated"])
def test_pack_uses_one_kernel_for_both_placements_and_zip64(context, monkeypatch, compression):
    import zipfile
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 128)
    members = tuple(Material(bytes([index]) * 1024, metadata={"member": f"dir/{index}.dat"}) for index in range(3))
    context.parameters = {"placement": "buffered", "compression": compression}
    buffered = archive_pack({"members": members}, None, context)["material"]
    context.parameters = {"placement": "staged", "compression": compression}
    staged = archive_pack({"members": members}, None, context)["material"]
    assert context.read(staged) == buffered.data and staged.identity == buffered.identity
    with ZipFile(BytesIO(buffered.data)) as archive:
        assert all(archive.read(f"dir/{index}.dat") == member.data for index, member in enumerate(members))
        assert all(item.compress_type == (ZIP_STORED if compression == "stored" else ZIP_DEFLATED) for item in archive.infolist())
    assert b"PK\x06\x06" in buffered.data


def test_encoder_hashes_sources_and_enforces_sink_size_during_writes():
    @contextmanager
    def changed(_):
        yield BytesIO(b"changed")
    with pytest.raises(ArchiveError, match="archive.source_changed"):
        encode_zip((ArchiveEntry("source", "source", ByteIdentity.of(b"original")),), BytesIO(), open_member=changed)
    @contextmanager
    def large(_):
        yield BytesIO(b"x" * 1000)
    with pytest.raises(ArchiveError, match="archive.output_limit"):
        encode_zip((ArchiveEntry("source", "source", ByteIdentity.of(b"x" * 1000)),), BytesIO(),
                   open_member=large, compression="stored", max_output_bytes=100)


@pytest.mark.parametrize("placement", ["buffered", "staged"])
def test_dbf_csv_preserves_exact_lexemes_deleted_rows_header_and_source(context, placement):
    fields = (("CODE", "C", 8, 0), ("AMOUNT", "N", 18, 4), ("RATE", "F", 10, 3),
              ("DAY", "D", 8, 0), ("FLAG", "L", 1, 0))
    source = Material(dbf_bytes(fields, ((False, (b' 0,"\n', b"00123.4500", b"+000.500", b"20261126", b"?")),
        (True, ("Ж".encode("cp866"), b"", b"-0.000", b"00000000", b"F"))), driver=0x65),
        source_id="fixture.form", metadata={"issue_id": "2026-11-01", "member": "FORM.DBF"})
    context.parameters = {"placement": placement}
    output = dbf_export_csv({"material": source, "policy": DBFPreservationPolicy()}, None, context)
    expected = 'CODE,AMOUNT,RATE,DAY,FLAG\n" 0,""\n",00123.4500,+000.500,20261126,?\nЖ,,-0.000,00000000,F\n'.encode()
    assert context.read(output["csv"]) == expected
    evidence = json.loads(context.read(output["evidence"]))
    assert evidence["deleted_record_ordinals"] == [2]
    assert evidence["header"] == {"version": 3, "raw_date_hex": "7e0b1a", "header_length": 193,
        "record_length": 46, "record_count": 2, "language_driver": 0x65,
        "eof_marker": True, "integrity": "complete_original_verified"}
    assert evidence["csv"]["sha256"] == ByteIdentity.of(expected).sha256
    assert evidence["source"]["sha256"] == source.identity.sha256
    assert evidence["encoding"]["effective"] == "cp866"
    decoded = dbf_decode({"material": source}, None, context)["physical"]
    assert decoded.header.record_count == 2 and decoded.header.language_driver == 0x65
    assert decoded.records[1].deleted and decoded.records[1].ordinal == 2
    assert decoded.records[0].values[1] == "00123.4500"


def test_encoding_override_requires_exact_source_issue_and_member(context):
    source = Material(dbf_bytes((("NAME", "C", 8, 0),), ((False, ("Ж".encode("utf-8"),)),)),
        source_id="fixture.form", metadata={"issue_id": "2026-11-01", "member": "exact.DBF"})
    policy = DBFPreservationPolicy(encoding="ascii", overrides=(DBFEncodingOverride(
        "fixture.form", "2026-11-01", "exact.DBF", "utf-8", "reviewed_exact_member"),))
    result = dbf_export_csv({"material": source, "policy": policy}, None, context)
    assert context.read(result["csv"]) == "NAME\nЖ\n".encode()
    assert result["summary"]["encoding_basis"] == "reviewed_exact_member"
    other = replace(source, metadata={**source.metadata, "member": "other.DBF"})
    with pytest.raises(DBFDecodeError, match="dbf.value_encoding_invalid"):
        dbf_export_csv({"material": other, "policy": policy}, None, context)
    with pytest.raises(ValueError, match="dbf.explicit_preservation_policy_required"):
        dbf_export_csv({"material": source}, None, context)


def test_encoding_override_can_distinguish_identical_members_in_one_feed(context):
    source = Material(dbf_bytes((("NAME", "C", 8, 0),), ((False, ("Ж".encode("utf-8"),)),)),
        source_id="fixture.raw_feed", metadata={"issue_id": "2026-11-01", "member": "BANKS.DBF",
                                               "container_asset_id": "form-a"})
    override = DBFEncodingOverride("fixture.raw_feed", "2026-11-01", "BANKS.DBF", "utf-8",
                                   "reviewed_form_a", asset_id="form-a")
    policy = DBFPreservationPolicy(encoding="ascii", overrides=(override,))
    result = dbf_export_csv({"material": source, "policy": policy}, None, context)
    assert context.read(result["csv"]) == "NAME\nЖ\n".encode()
    other = replace(source, metadata={**source.metadata, "container_asset_id": "form-b"})
    with pytest.raises(DBFDecodeError, match="dbf.value_encoding_invalid"):
        dbf_export_csv({"material": other, "policy": policy}, None, context)
    with pytest.raises(ValueError, match="dbf.encoding_override_ambiguous"):
        DBFPreservationPolicy(overrides=(override, replace(override, asset_id=None)))


def test_archive_names_are_explicit_or_come_from_physical_member_then_filename(context):
    values = ({"name": "chosen.csv", "material": Material(b"a", metadata={"member": "ignored"})},
              Material(b"b", metadata={"member": "physical.csv", "filename": "ignored.csv"}),
              Material(b"c", metadata={"filename": "download.csv"}), Material(b"d"))
    packed = archive_pack({"members": values}, None, context)
    with ZipFile(BytesIO(packed["material"].data)) as archive:
        assert archive.namelist() == ["chosen.csv", "physical.csv", "download.csv", "3"]


def test_dbf_admission_rejects_counts_before_record_or_descriptor_allocation():
    original = dbf_bytes((("CODE", "C", 4, 0),), ((False, (b"0001",)),))
    class Tracked(BytesIO):
        def __init__(self, data):
            super().__init__(data)
            self.requested = []
        def read(self, size=-1):
            assert 0 <= size <= 65536
            self.requested.append(size)
            return super().read(size)
    stream = Tracked(original)
    with pytest.raises(DBFDecodeError, match="dbf.cell_limit"):
        DBFReader(stream, ByteIdentity.of(original), max_records=0)
    assert stream.requested == [32]
    meter = BudgetMeter(ExecutionBudget(cells=0))
    stream = Tracked(original)
    with pytest.raises(BudgetExceeded, match="budget.cells"):
        DBFReader(stream, ByteIdentity.of(original), budget=meter)
    assert stream.requested == [32]


@pytest.mark.parametrize("kind,width,diagnostic", [
    ("M", 10, "dbf.memo_companion_required"), ("B", 8, "dbf.binary_dialect_unsupported"),
    ("I", 4, "dbf.binary_dialect_unsupported"), ("Y", 8, "dbf.binary_dialect_unsupported"),
    ("D", 7, "dbf.field_width_invalid"), ("L", 2, "dbf.field_width_invalid")])
def test_unproved_binary_memo_and_invalid_width_never_produce_text(kind, width, diagnostic):
    data = dbf_bytes((("FIELD", kind, width, 0),), ((False, (b"0" * width,)),))
    with pytest.raises(DBFDecodeError, match=diagnostic):
        decode_dbf(data)


def test_one_million_deleted_ordinals_stream_to_evidence_without_row_collection(context):
    count = 1_000_001
    with context.stage() as original:
        header = dbf_bytes((("CODE", "C", 1, 0),), (), eof=False)
        original.write(header[:4] + pack("<I", count) + header[8:])
        remaining = count
        while remaining:
            amount = min(4096, remaining)
            original.write(b"*0" * amount)
            remaining -= amount
        original.write(b"\x1a")
        source = original.seal()
    output = dbf_export_csv({"material": source, "policy": DBFPreservationPolicy()}, None, context)
    assert output["summary"]["deleted_records"] == count
    assert output["summary"]["records"] == count
    actual = sha256()
    with context.open_material(output["evidence"]) as stream:
        prefix = b'{"deleted_record_ordinals":['
        assert stream.read(len(prefix)) == prefix
        while True:
            chunk = stream.read(65536)
            end = chunk.find(b"]")
            if end >= 0:
                actual.update(chunk[:end])
                break
            assert chunk
            actual.update(chunk)
    expected = sha256()
    for ordinal in range(1, count + 1):
        expected.update((b"," if ordinal > 1 else b"") + str(ordinal).encode())
    assert actual.digest() == expected.digest()
    assert context.service.staging.status()["objects"] == 3
    assert context.service.staging.status()["readers"] == 0


def test_seekable_workbook_keeps_raw_numeric_text_and_formula_without_compressed_buffer(context, monkeypatch):
    from decimal import Decimal
    import openpyxl
    from stratbox.core.commands import decoding
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = 1.2
    workbook.active["A1"].number_format = "0.000"
    workbook.active["B1"] = "0001"
    data = BytesIO()
    workbook.save(data)
    with ZipFile(BytesIO(data.getvalue())) as archive:
        parts = [(name, archive.read(name)) for name in archive.namelist()]
    parts = [(name, value.replace(b"<v>1.2</v>", b"<f>SUM(B1:C1)</f><v>001.200</v>"))
             if name == "xl/worksheets/sheet1.xml" else (name, value) for name, value in parts]
    with context.stage() as stage:
        stage.write(zip_bytes(parts, method=ZIP_DEFLATED))
        source = stage.seal()
    context.parameters = {"max_materialized_bytes": 1}
    monkeypatch.setattr(decoding, "bounded_material_bytes", lambda *a, **kw: pytest.fail("Compressed workbook materialized"))
    physical = decoding.workbook_decode({"material": source}, None, context)["physical"]
    cell = physical.workbook.sheets[0].cells[0]
    assert physical.material is source and physical.workbook.identity == source.identity
    assert cell.raw_token == "001.200" and cell.value == Decimal("1.200")
    assert cell.formula == "SUM(B1:C1)" and cell.number_format == "0.000"
    assert context.service.staging.status()["readers"] == 0


def test_csv_and_docx_consume_seekable_stages_and_json_has_explicit_buffer_limit(context):
    from docx import Document
    from stratbox.core.commands.decoding import csv_decode, document_decode, json_decode
    with context.stage(charset="utf-8") as stage:
        stage.write(b'code,value\n"00\n01",1.200\n')
        csv_source = stage.seal()
    evidence = csv_decode({"material": csv_source}, None, context)["physical"]
    assert evidence.tables == ((("code", "value"), ("00\n01", "1.200")),)
    assert evidence.material is csv_source
    doc = Document()
    doc.add_paragraph("Preserved text")
    data = BytesIO()
    doc.save(data)
    with context.stage() as stage:
        stage.write(data.getvalue())
        doc_source = stage.seal()
    evidence = document_decode({"material": doc_source}, None, context)["physical"]
    assert evidence.material is doc_source
    assert evidence.document.blocks[0].text == "Preserved text"
    with context.stage() as stage:
        stage.write(b'{"number":1.200}')
        json_source = stage.seal()
    context.parameters = {"max_materialized_bytes": 1}
    with pytest.raises(ValueError, match="material.materialization_limit"):
        json_decode({"material": json_source}, None, context)
    context.parameters = {"max_materialized_bytes": 64}
    evidence = json_decode({"material": json_source}, None, context)["physical"]
    assert str(evidence.value["number"]) == "1.200" and evidence.material is json_source


def test_sdk_staged_dbf_export_is_composable_with_csv_and_archive_commands():
    from stratbox.sdk import StrategyBox
    source = Material(dbf_bytes((("CODE", "C", 4, 0),), ((True, (b"0012",)),)))
    with StrategyBox() as box:
        export = box.invoke("command.dbf.export_csv", inputs={"material": source,
                            "policy": DBFPreservationPolicy()})
        assert export.outcome == "succeeded", export.diagnostics
        assert not export.effects
        csv_value = export.output("csv")
        decoded = box.invoke("command.csv.decode", inputs={"material": csv_value})
        assert decoded.outcome == "succeeded", decoded.diagnostics
        assert decoded.output("physical").tables == ((("CODE",), ("0012",)),)
        packed = box.invoke("command.archive.pack", inputs={"members": (csv_value, export.output("evidence"))},
            parameters={"placement": "staged", "names": ("data.csv", "preservation.json")})
        assert packed.outcome == "succeeded", packed.diagnostics
        unpacked = box.invoke("command.archive.unpack", inputs={"material": packed.output("material")},
            parameters={"names": ("data.csv",), "placement": "buffered"})
        assert unpacked.outcome == "succeeded", unpacked.diagnostics
        assert unpacked.output("members")[0].data == b"CODE\n0012\n"
