from dataclasses import replace
from io import BytesIO
from struct import pack
from zipfile import ZipFile

import openpyxl
import pytest
import xlwt

from stratbox.base.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.base.ioapi.archive_bytes import zip_bytes
from stratbox.base.ioapi.spreadsheet_view import spreadsheet_view
from stratbox.base.ioapi.workbook_input import WorkbookError, preview_workbook, workbook_profile
from stratbox.base.limits import BudgetExceeded, BudgetMeter, ExecutionBudget
from stratbox.data import ByteIdentity, Representation


def _book():
    workbook = openpyxl.Workbook()
    workbook.active.title = "Notes"
    workbook.active.append(("Any text", 12))
    table = workbook.create_sheet("Observations")
    table.append(("First field", "Second field", "Third field"))
    table.append(("literal", 4, 5))
    table.append(("another", 7, 8))
    raw = BytesIO()
    workbook.save(raw)
    return raw.getvalue()


def _parts(data):
    with ZipFile(BytesIO(data)) as workbook:
        return {name: workbook.read(name) for name in workbook.namelist()}


def _binary_fixture():
    def record(identifier, body=b""):
        assert len(body) < 128
        return identifier.to_bytes(1 if identifier < 128 else 2, "little") + bytes([len(body)]) + body

    def string(text):
        return pack("<I", len(text)) + text.encode("utf-16-le")

    return zip_bytes({
        "[Content_Types].xml": (
            b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            b'<Override PartName="/xl/workbook.bin" '
            b'ContentType="application/vnd.ms-excel.sheet.binary.macroEnabled.main"/></Types>'
        ),
        "xl/workbook.bin": b"".join((
            record(0x183), record(0x18f),
            record(0x19c, pack("<II", 0, 1) + string("rId1") + string("Sheet")),
            record(0x190), record(0x184),
        )),
        "xl/_rels/workbook.bin.rels": (
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.bin"/></Relationships>'
        ),
        "xl/worksheets/sheet1.bin": b"".join((
            record(0x194, pack("<IIII", 0, 0, 0, 0)), record(0x191),
            record(0, pack("<I", 0)), record(5, pack("<IId", 0, 0, 12.5)), record(0x192),
        )),
    })


def test_ordinary_book_uses_actual_sheet_and_range_without_mapping():
    raw = _book()
    value = preview_workbook(raw, sheet="Observations", start_row=2, start_column=2,
                             max_rows=1, max_columns=1)
    assert value.rows == ((4,),)
    assert (value.start_row, value.start_column) == (2, 2)
    assert value.sheets == ("Notes", "Observations")
    assert value.truncated and value.identity == ByteIdentity.of(raw)
    assert value.value_basis == "cached_values"
    with pytest.raises(WorkbookError, match="workbook.sheet_missing"):
        preview_workbook(raw, sheet="Other")
    with pytest.raises(WorkbookError, match="workbook.preview_range_invalid"):
        preview_workbook(raw, start_row=True)


def test_content_selects_legacy_binary_and_macro_decoders():
    legacy = xlwt.Workbook()
    legacy.add_sheet("Notes").write(0, 0, "legacy")
    data = BytesIO()
    legacy.save(data)
    assert preview_workbook(data.getvalue()).rows == (("legacy",),)
    binary = preview_workbook(_binary_fixture())
    assert binary.kind == "xlsb" and binary.rows == ((12.5,),)
    assert binary.value_basis == "decoder_values"

    parts = _parts(_book())
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
        b"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        b"application/vnd.ms-excel.sheet.macroEnabled.main+xml",
    )
    parts["xl/vbaProject.bin"] = b"uninterpreted part"
    rel = "xl/_rels/workbook.xml.rels"
    parts[rel] = parts[rel].replace(b"</Relationships>", (
        b'<Relationship Type="https://example.org/relation" Target="https://example.org/data" '
        b'TargetMode="External" Id="external"/></Relationships>'
    ))
    raw = zip_bytes(parts)
    assert workbook_profile(raw).active_parts and workbook_profile(raw).external_relations
    assert preview_workbook(raw).kind == "xlsm"
    with pytest.raises(WorkbookError, match="workbook.not_spreadsheet"):
        preview_workbook(zip_bytes({"word/document.xml": b"<document/>"}))


def test_physical_extent_cells_and_parser_budgets_are_independent():
    parts = _parts(_book())
    name = "xl/worksheets/sheet1.xml"
    parts[name] = parts[name].replace(b'<dimension ref="A1:B1"', b'<dimension ref="A1:XFD1048576"')
    raw = zip_bytes(parts)
    assert workbook_profile(raw).largest_sheet_extent == 9
    assert preview_workbook(raw, max_rows=1, max_columns=2).rows == (("Any text", 12),)
    with pytest.raises(BudgetExceeded, match="budget.cells"):
        preview_workbook(raw, budget=BudgetMeter(ExecutionBudget(cells=1)))
    with pytest.raises(BudgetExceeded, match="budget.decoded_bytes"):
        workbook_profile(raw, budget=BudgetMeter(ExecutionBudget(decoded_bytes=1024)))
    with pytest.raises(BudgetExceeded, match="budget.archive_depth"):
        workbook_profile(raw, depth=2, budget=BudgetMeter(ExecutionBudget(archive_depth=1)))
    parts[name] = parts[name].replace(b'r="B1"', b'r="XFE1"')
    with pytest.raises(WorkbookError, match="workbook.cell_reference_invalid"):
        workbook_profile(zip_bytes(parts))


def test_encoded_dtd_unsafe_member_and_crc_are_rejected():
    parts = _parts(_book())
    name = "xl/worksheets/sheet1.xml"
    parts[name] = ('<!DOCTYPE worksheet [<!ENTITY leak SYSTEM "file:///private">]>'
                   + parts[name].decode()).encode("utf-16")
    with pytest.raises(WorkbookError, match="xml.dtd_forbidden"):
        workbook_profile(zip_bytes(parts))
    parts["XL/WORKBOOK.XML"] = b"<alias/>"
    with pytest.raises(WorkbookError, match="archive.unsafe_member"):
        workbook_profile(_unchecked_zip(parts))
    raw = _unchecked_zip(_parts(_book()))
    assert b"<worksheet " in raw
    damaged = raw.replace(b"<worksheet ", b"<workshEet ", 1)
    with pytest.raises(WorkbookError, match="archive.invalid_zip"):
        workbook_profile(damaged)


def _unchecked_zip(parts):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_worker_protocol_rechecks_material_and_result_shape():
    raw = _book()
    preview = preview_workbook(raw, max_rows=1, max_columns=2)

    class Worker:
        def __init__(self, result):
            self.result = result

        def preview(self, data, **options):
            assert data == raw
            assert (options["start_row"], options["start_column"]) == (1, 1)
            return self.result

    with pytest.raises(WorkbookError, match="workbook.isolation_missing"):
        preview_workbook(raw, require_isolation=True)
    worker = Worker(preview)
    capability = CapabilityRequirement("workbook_decoder", guarantees=frozenset({"isolation_enforced"}))
    binding = ProviderBinding("fixture", capability, "ready", worker)
    assert preview_workbook(raw, max_rows=1, max_columns=2, worker=worker,
                            require_isolation=True, binding=binding) == preview
    with pytest.raises(WorkbookError, match="provider.binding_mismatch"):
        preview_workbook(raw, worker=Worker(preview), require_isolation=True, binding=binding)
    worker.result = replace(preview, identity=ByteIdentity.of(b"substitution"))
    with pytest.raises(WorkbookError, match="workbook.worker_result_invalid"):
        preview_workbook(raw, worker=worker)
    worker.result = replace(preview, rows=(("x" * 32_768,),))
    with pytest.raises(WorkbookError, match="workbook.text_limit"):
        preview_workbook(raw, worker=worker)


def test_safe_spreadsheet_keeps_exact_untrusted_text_as_cells():
    raw = b'=SUM(1,2),unused\n"https://example.org",+1\n'.replace(
        b'=SUM(1,2)', b'"=SUM(1,2)"'
    )
    source = Representation("fixture.csv", 1, "text/csv", raw, encoding="utf-8")
    view = spreadsheet_view(source)
    assert source.data == raw and source.identity != view.identity
    workbook = openpyxl.load_workbook(BytesIO(view.data))
    sheet = workbook.active
    assert [[cell.value for cell in row] for row in sheet] == [
        ["=SUM(1,2)", "unused"], ["https://example.org", "+1"],
    ]
    assert all(cell.data_type == "s" and cell.hyperlink is None for row in sheet for cell in row)


def test_legacy_record_and_xlsx_text_limits_reject_before_decoder():
    def record(kind, data=b""):
        return pack("<HH", kind, len(data)) + data

    bof = record(0x0809, b"\x00\x06\x05\x00")
    with pytest.raises(WorkbookError, match="workbook.encrypted"):
        workbook_profile(bof + record(0x002f, b"\x01\x00") + record(0x000a))
    with pytest.raises(WorkbookError, match="workbook.legacy_stream_invalid"):
        workbook_profile(bof + b"\x0a\x00\x01\x00")
    parts = _parts(_book())
    name = "xl/worksheets/sheet1.xml"
    parts[name] = parts[name].replace(b"Any text", b"x" * 131_073)
    with pytest.raises(WorkbookError, match="xml.text_limit"):
        workbook_profile(zip_bytes(parts))


def test_dbf_header_geometry_and_temporary_quota():
    from stratbox.base.ioapi.dbf_bytes import open_dbf_bytes

    header = bytearray(33)
    header[0] = 3
    header[4:12] = pack("<IHH", 1, 33, 1)
    header[32] = 0x0d
    with pytest.raises(ValueError, match="DBF record geometry"):
        with open_dbf_bytes(bytes(header)):
            pytest.fail("invalid DBF reached the decoder")
    with pytest.raises(BudgetExceeded, match="budget.temporary_bytes"):
        with open_dbf_bytes(bytes(header) + b" ", budget=BudgetMeter(ExecutionBudget(temporary_bytes=1))):
            pytest.fail("DBF reached staging beyond quota")
