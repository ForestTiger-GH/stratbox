"""Physical DBF variants and archive lineage through the public API."""

from datetime import date
from struct import pack

import pandas as pd

from stratbox.base.ioapi.archive_bytes import zip_bytes
from stratbox.data import ByteIdentity, SourcePayload
from stratbox.macrobanks import cbr_forms as forms


def dbf_bytes(fields, records):
    header = pack("<BBBBIHH20x", 3, 126, 4, 1, len(records), 33 + 32 * len(fields), 1 + 12 * len(fields))
    columns = b"".join(pack("<11sc4xBB14x", name.encode("ascii"), b"C", 12, 0) for name in fields)
    rows = b"".join(b" " + b"".join(str(item).encode("ascii").ljust(12) for item in row) for row in records)
    return header + columns + b"\r" + rows + b"\x1a"


def test_historical_form802_keeps_optional_adjustment_empty_and_proves_archive_member():
    dbf = dbf_bytes(
        ["REGN_GKO", "STR", "KORR_P", "KORR_M", "VSEGO"], [("1000", "14", "", "", "0")],
    )
    unrelated = dbf_bytes(["FSORT", "FRAZD"], [("1", "2")])
    source = SourcePayload(zip_bytes({"PK8022512.dbf": dbf, "F802META.dbf": unrelated}))
    key = forms.FormKey("802", date(2026, 4, 1))
    parsed = forms.parse_form(forms.ParseFormRequest(key, source))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert parsed.value.rows.loc[0, "total"] == "0"
    assert pd.isna(parsed.value.rows.loc[0, "intragroup_adjustment"])
    member = parsed.used_inputs[1]
    assert member.member == "PK8022512.dbf"
    assert member.identity == ByteIdentity.of(dbf)
    assert member.container == source.identity


def test_current_form802_can_read_present_adjustment_from_standalone_dbf():
    dbf = dbf_bytes(
        ["REGN_GKO", "STR", "VSEGO", "KORR_GR"], [("1000", "14", "10", "1")],
    )
    parsed = forms.parse_form(forms.ParseFormRequest(forms.FormKey("802", date(2026, 4, 1)), SourcePayload(dbf)))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert parsed.value.physical_fields["intragroup_adjustment"] == "KORR_GR"
    assert parsed.value.rows.loc[0, "intragroup_adjustment"] == "1"
    built = forms.build_form_data(forms.BuildFormDataRequest(
        (parsed.value,), (forms.BankSelection("1000", "Bank"),),
    ))
    assert built.outcome == "succeeded", built.diagnostics
    by_code = built.value.long.set_index("Код")["Значение"]
    assert by_code["14"] == 10
    assert by_code["15.4"] == ""


def test_formula_source_absence_is_not_coerced_to_zero():
    dbf = dbf_bytes(["REGN", "C1", "C3"], [("1000", "000", "0"), ("1000", "102", "10")])
    parsed = forms.parse_form(forms.ParseFormRequest(forms.FormKey("123", date(2026, 4, 1)), SourcePayload(dbf)))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    built = forms.build_form_data(forms.BuildFormDataRequest(
        (parsed.value,), (forms.BankSelection("1000", "Bank"),),
    ))
    assert built.outcome == "succeeded", built.diagnostics
    values = built.value.long.set_index("IndicatorId")["Значение"]
    assert values["capital_total"] == 0
    assert values["base_capital"] == 10
    assert values["main_capital"] == ""
