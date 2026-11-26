"""Source evidence survives independent physical decoding and retained-value replay."""
from dataclasses import replace
from io import BytesIO
from struct import pack

import pytest
from openpyxl import load_workbook

from stratbox.core.commands import standard
from stratbox.core.formats.archives.members import zip_bytes
from stratbox.core.formats.dbf_lossless import DBFDecodeError, decode_dbf
from stratbox.shared.data.values import Material
from .support import DAY, calculate, command, context, dbf, physical, render, reopen, series, tables, view


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



@pytest.mark.parametrize("code,fields,values,parameters", (
    ("134", (("REGN","N",4,0),("C1","C",15,0),("C3","N",16,0)),
        (b"1000",b"0012",b"1.2300"), {"period": DAY,"unit":"RUB","scale":1000}),
    ("803", (("REGN_GKO","N",4,0),("RAZDEL","C",3,0),("STR","C",5,0),
        ("KORR_P","N",16,0),("KORR_M","N",16,0),("VSEGO","N",16,0)),
        (b"1000",b"1",b"0012",b"",b"",b"1.2300"),
        {"period": ("2026-01-01","2026-03-31"),"unit":"RUB","scale":1000}),
))
def test_published_fields_are_available_separately_from_unreviewed_financial_models(code, fields, values, parameters):
    source = tables(code, dbf(fields, ((b" ",values),)))
    normalized = command(code,"table.interpret",{"tables":source},issue_id=DAY,**parameters)["dataset"]
    assert normalized.rows[-1]["value"] == __import__("decimal").Decimal("1.2300")
    assert normalized.assessment.qualifications == frozenset({"published_fields_only"})
    with pytest.raises(ValueError, match="requires_publisher_evidence"):
        calculate(code, normalized)


def test_index_selects_actual_published_dates_and_accepts_offline_html():
    material = Material(b'<a href="/vfs/credit/forms/803-20260401.rar">form</a>'
        b'<a href="/vfs/credit/forms/134-20160101.rar">old</a>'
        b'<a href="/vfs/credit/forms/803-20260401.rar">duplicate</a>', "text/html")
    listing = command("803", "publication.scan", {"index":material})["listing"]
    assert [(x.source_id,x.issue_id) for x in listing.entries] == [(series("803").id,DAY)]
    assert listing.lineage == (material.identity,)
    assert "observed_index_only" in listing.assessment.qualifications


def test_full_members_history_calculation_and_views_replay_after_file_read(tmp_path):
    data = dbf((("REGN_GKO","C",12,0),("STR","C",12,0),("VSEGO","N",20,4)), (
        (b" ",(b"1000",b"14",b"000001.2300")),(b"*",(b"1000",b"14",b"999.9"))))
    dictionary = dbf((("FIELD","C",8,0),),((b" ",(b"0012",)),))
    original = Material(zip_bytes({"PK802.dbf":data,"metadata.dbf":dictionary,"readme.txt":b"companion"}),
        source_id=series("802").id)
    members = standard.archive_unpack({"material":original},None,context())["members"]
    retained = reopen(tmp_path,members)
    assert retained == members and retained[2].data == b"companion"
    decoded = tuple(physical("802",member.data,**member.metadata) for member in retained[:2])
    extracted = command("802","table.extract",{"physical":decoded},issue_id=DAY)["tables"]
    assert len(extracted.metadata["all_members"]) == 2
    restored = reopen(tmp_path,extracted)
    assert restored == extracted and restored.tables[0].records[1].deleted
    normalized = command("802","table.interpret",{"tables":restored},issue_id=DAY)["dataset"]
    assert len(normalized.rows)==1 and normalized.rows[0]["raw_token"]=="000001.2300"
    restored_data = reopen(tmp_path,calculate("802",reopen(tmp_path,normalized)))
    prepared = reopen(tmp_path,view(restored_data))
    product = render(prepared)
    workbook = load_workbook(BytesIO(product.data),data_only=True)
    assert workbook.sheetnames == ["Обзор","Полная форма","Данные"]
    rows=list(workbook["Данные"].values);header=list(rows[0])
    values={row[header.index("Код")]:row[header.index("Значение")] for row in rows[1:]}
    assert values["14"]==1.23
    workbook.close()


def test_unsupported_member_remains_retained_and_cannot_be_decoded_as_supported(tmp_path):
    valid=dbf((("CODE","C",4,0),),((b" ",(b"0012",)),))
    unsupported=bytes((0x30,))+valid[1:]
    original=Material(zip_bytes({"valid.dbf":valid,"unsupported.dbf":unsupported}))
    members=standard.archive_unpack({"material":original},None,context())["members"]
    replayed=reopen(tmp_path,members)
    assert replayed[1].data==unsupported
    with pytest.raises(DBFDecodeError,match="dialect_unsupported"):
        standard.dbf_decode({"material":replayed[1]},None,context())


def test_lossless_dbf_replay_keeps_schema_lexemes_deleted_flag_without_reparse(tmp_path,monkeypatch):
    original=dbf((("CODE","C",8,0),("VALUE","N",16,4)), (
        (b" ",(b"0012",b"000001.2300")),(b"*",(b"0013",b""))))
    evidence=physical("803",original)
    import stratbox.core.formats.dbf_lossless as parser
    monkeypatch.setattr(parser,"decode_dbf",lambda *a,**kw:pytest.fail("DBF parsed during value replay"))
    restored=reopen(tmp_path,evidence)
    assert restored==evidence
    assert restored.records[0].values==("0012","000001.2300")
    assert restored.records[1].deleted and restored.records[1].values==("0013","")
    assert restored.fields[1].decimals==4


def test_unknown_or_truncated_value_envelope_is_rejected(tmp_path):
    from stratbox.shared.data.values import canonical_tree
    import json
    evidence=physical("803",dbf((("CODE","C",4,0),),((b" ",(b"0012",)),)))
    encoded=standard.value_encode({"value":evidence},None,context())["representation"]
    with pytest.raises((ValueError,TypeError)):
        standard.value_decode({"representation":encoded.data[:-1]},None,context())
    forged=canonical_tree(evidence);forged["type"]="caller.supplied:Arbitrary"
    with pytest.raises(ValueError,match="type_not_admitted"):
        standard.value_decode({"representation":json.dumps(forged).encode()},None,context())
