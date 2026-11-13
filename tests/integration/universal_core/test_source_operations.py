from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.archive_bytes import zip_bytes
from stratbox.base.ioapi.bytes import read_bounded_bytes, write_verified_bytes
from stratbox.base.net import HttpResponse
from stratbox.data import ByteIdentity, SourcePayload
from stratbox.data.releases import CompareReleaseRequest, ReadReleaseRequest
from stratbox.macrobanks import cbr_offices as daily, cbr_offices_reg as monthly
from stratbox.organizations import fns_1yur, fns_sme

from source_fixtures import (
    FORM_EPOCHS,
    encoded,
    fixture,
    form_workbook,
    sample_page,
    sample_xlsx,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/universal_core"
OBSERVED = datetime(2026, 11, 11, 22, 30, tzinfo=timezone.utc)
RELEASE = date(2026, 11, 12)
SME_DAY = date(2026, 11, 10)


class FakeHTTP:
    def __init__(self, body, content_type, host):
        self.response = HttpResponse(
            200, body, {"Content-Type": content_type}, OBSERVED, "https://" + host
        )
        self.requests = []

    def exchange(self, request, *, cancelled=None):
        self.requests.append(request)
        return self.response


@pytest.mark.parametrize("layout", ["basic", "grouped-header"])
def test_offices_from_exact_html_bytes_and_capture(layout, tmp_path):
    data = (FIXTURES / f"offices-{layout}.html").read_bytes()
    provider = FakeHTTP(data, "text/html; charset=utf-8", "www.cbr.ru")
    request = daily.AcquireOfficesRequest(timezone(timedelta(hours=3)))
    acquired = daily.acquire(request, transport=provider)
    assert acquired.outcome == "succeeded", acquired.diagnostics
    assert acquired.value.capture_date == RELEASE
    source = acquired.value.payload
    store = LocalFileStore(root=str(tmp_path))
    receipt = write_verified_bytes(
        "original.html",
        source.data,
        store=store,
        expected_sha256=source.identity.sha256,
    )
    assert receipt.status == "stored"
    offline = daily.parse(
        daily.ParseOfficesRequest(
            SourcePayload(
                read_bounded_bytes("original.html", store=store, limit=10000)
            ),
            RELEASE,
        )
    )
    online = daily.capture(request, transport=provider)
    assert offline.outcome == online.outcome == "succeeded"
    assert offline.invocation_id != online.invocation_id
    assert (
        offline.used_inputs[0].identity
        == online.used_inputs[0].identity
        == receipt.identity
    )
    assert offline.value.dataset_version == online.value.dataset_version
    assert (
        offline.value.representation.data
        == (FIXTURES / f"offices-{layout}.csv").read_bytes()
    )
    assert not online.effects
    csv_result = daily.read_representation(
        ReadReleaseRequest(SourcePayload(offline.value.representation.data), RELEASE)
    )
    assert csv_result.outcome == "succeeded"
    assert csv_result.used_inputs[0].role == "csv_representation"
    assert csv_result.used_inputs[0].identity != receipt.identity
    assert (
        daily.compare(
            CompareReleaseRequest(offline.value, csv_result.value)
        ).value.state
        == "unchanged"
    )


def test_offices_reports_content_and_provider_failures():
    payload = SourcePayload(b"<html>Access denied</html>")
    assert daily.parse(daily.ParseOfficesRequest(payload, RELEASE)).outcome == "failed"
    assert (
        daily.acquire(daily.AcquireOfficesRequest(timezone.utc)).diagnostics[0].code
        == "provider.capability_missing"
    )
    original = (FIXTURES / "offices-basic.html").read_bytes()
    result = daily.parse(
        daily.ParseOfficesRequest(SourcePayload(original + original), RELEASE)
    )
    assert result.diagnostics[0].code == "source.source_table_ambiguous"


def test_monthly_discovery_cached_formula_and_workbook_bytes():
    result = monthly.discover(
        monthly.DiscoverOfficesRegRequest(SourcePayload(sample_page().encode("utf-8")))
    )
    assert result.outcome == "succeeded"
    link = result.value[-1]
    original = sample_xlsx(formula=True)
    provider = FakeHTTP(original, "application/octet-stream", "www.cbr.ru")
    received = monthly.acquire(link, transport=provider)
    assert received.outcome == "succeeded"
    assert received.value.payload.data == original
    parsed = monthly.capture(link, transport=provider)
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert (
        parsed.value.representation.data == (FIXTURES / "offices-reg.csv").read_bytes()
    )
    assert parsed.value.source_details["formula_lineage"]["3"]["4"]["formula"] == "2+3"
    assert parsed.used_inputs[0].identity == received.value.payload.identity
    files = {}
    with ZipFile(BytesIO(original)) as archive:
        files.update({name: archive.read(name) for name in archive.namelist()})
    sheet = "xl/worksheets/sheet1.xml"
    files[sheet] = files[sheet].replace(b"<f>2+3</f><v>5</v>", b"<f>2+3</f>")
    invalid = monthly.parse(
        monthly.ParseOfficesRegRequest(SourcePayload(zip_bytes(files)), link.as_of)
    )
    assert invalid.outcome == "succeeded"
    assert invalid.value.qualification.analysis == "qualified_subset"
    assert invalid.value.source_details["formula_lineage"]["3"]["4"]["cache_missing"]


def test_sme_post_and_offline_representations_match():
    expected = (FIXTURES / "sme-reg.csv").read_bytes()
    first = fns_sme.parse(
        fns_sme.ParseSmeRequest(SourcePayload(encoded(fixture())), SME_DAY)
    )
    provider = FakeHTTP(
        encoded(fixture(as_strings=True)), "application/json", "rmsp.nalog.ru"
    )
    second = fns_sme.capture(fns_sme.AcquireSmeRequest(SME_DAY), transport=provider)
    assert first.outcome == second.outcome == "succeeded"
    assert (
        first.value.representation.data == second.value.representation.data == expected
    )
    assert first.value.dataset_version.identity != second.value.dataset_version.identity
    assert provider.requests[0].method == "POST"
    assert provider.requests[0].form_fields == {"statDate": "10.11.2026"}
    assert (
        fns_sme.compare(CompareReleaseRequest(second.value, first.value)).value.state
        == "unchanged"
    )
    assert (
        fns_sme.compare(CompareReleaseRequest(second.value)).value.state
        == "indeterminate"
    )
    assert (
        fns_sme.compare(
            CompareReleaseRequest(second.value, baseline_state="confirmed_absent")
        ).value.state
        == "first_seen"
    )
    assert all(row.subject.id != "" for row in first.value.batch.observations)


def test_sme_region_drop_date_mismatch_and_duplicate_json_keys():
    def parse(data):
        return fns_sme.parse(fns_sme.ParseSmeRequest(SourcePayload(data), SME_DAY))

    older = parse(encoded(fixture(count=95))).value
    newer = parse(encoded(fixture(count=80))).value
    assert (
        fns_sme.compare(CompareReleaseRequest(newer, older)).value.reason
        == "source.coverage_drop"
    )
    assert (
        parse(encoded(fixture(date(2026, 11, 9)))).diagnostics[0].code
        == "source.source_date_mismatch"
    )
    raw = encoded(fixture()).replace(
        b'"cnt_level": 2', b'"cnt_level": 2, "cnt_level": 2', 1
    )
    assert parse(raw).diagnostics[0].code == "source.json_duplicate_key"


@pytest.mark.parametrize(
    "day,epoch,indicators,kinds", FORM_EPOCHS, ids=[item[1] for item in FORM_EPOCHS]
)
def test_1yur_epoch_parity_and_independent_archive_member_evidence(
    day, epoch, indicators, kinds
):
    source = form_workbook(indicators, kinds, legacy=epoch == "A")
    member = "edition_I.xls"  # OOXML can be published with a legacy suffix.
    container = SourcePayload(zip_bytes({member: source, "edition_II.xls": b"ignored"}))
    parsed = fns_1yur.parse(fns_1yur.Parse1YurRequest(container, day))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert parsed.value.source_details["mapping"]["epoch"] == epoch
    assert (
        parsed.value.representation.data
        == (FIXTURES / f"1yur-{epoch}.csv").read_bytes()
    )
    assert parsed.used_inputs[0].identity == container.identity
    assert parsed.used_inputs[1].identity == ByteIdentity.of(source)
    assert parsed.used_inputs[1].container == container.identity
    assert parsed.used_inputs[1].member == member
    if epoch == "B":
        assert parsed.value.source_details["mapping"]["omitted_fields"]
    baseline = fns_1yur.read_representation(
        ReadReleaseRequest(
            SourcePayload(parsed.value.representation.data),
            day,
        )
    )
    assert baseline.outcome == "succeeded", baseline.diagnostics
    assert (
        fns_1yur.compare(
            CompareReleaseRequest(parsed.value, baseline.value)
        ).value.state
        == "unchanged"
    )


def test_1yur_unsafe_archive_part_ii_and_unavailable_rar_reader():
    day = date(2026, 11, 1)
    with BytesIO() as stream:
        with ZipFile(stream, "w") as archive:
            archive.writestr("../edition_I.xls", b"data")
        unsafe = stream.getvalue()
    result = fns_1yur.parse(fns_1yur.Parse1YurRequest(SourcePayload(unsafe), day))
    assert result.diagnostics[0].code == "archive.unsafe_member"
    part_ii = SourcePayload(zip_bytes({"edition_II.xls": b"data"}))
    assert fns_1yur.parse(fns_1yur.Parse1YurRequest(part_ii, day)).outcome == "failed"
    rar = fns_1yur.parse(fns_1yur.Parse1YurRequest(SourcePayload(b"Rar!"), day))
    assert rar.diagnostics[0].code == "provider.capability_missing"


def test_monthly_dynamic_roles_exact_block_and_ambiguity():
    import openpyxl

    from stratbox.base.ioapi.workbook_input import preview_workbook

    period = date(2026, 10, 1)
    baseline = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(sample_xlsx()), period))
    assert baseline.value.qualification.analysis == "qualified"

    def workbook(*, group="Количество, ед.", printed="1.10.2026", duplicate=False,
                 revision=0, extra=False, adjacent=False):
        book = openpyxl.Workbook()
        book.active.title = "Notes"
        book.active["A1"] = "=1+1"
        sheet = book.create_sheet("Published observations")
        names = ["Российская Федерация"] + [
            "Белгородская область", "Брянская область", "Республика Алтай",
        ] * 15

        def add_block(title):
            sheet.append(["Данные по состоянию на " + title])
            sheet.append([None, group])
            sheet.merge_cells(start_row=sheet.max_row, end_row=sheet.max_row,
                              start_column=2, end_column=5)
            captions = ["Территория", "Всего", "Мобильные офисы", "Филиалы", "Кредитные организации"]
            sheet.append(captions + (["Дополнительная отметка"] if extra else []))
            for index, name in enumerate(names):
                values = [name, 10 + (revision if index == 0 else 0), 5, 3, 2]
                sheet.append(values + (["новая категория"] if extra else []))

        add_block(printed)
        if adjacent:
            add_block("1.11.2026")
        if duplicate:
            book.copy_worksheet(sheet).title = "Competing block"
        stream = BytesIO()
        book.save(stream)
        return stream.getvalue()

    raw = workbook()
    parsed = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(raw), period))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert parsed.value.facts_identity == baseline.value.facts_identity
    assert parsed.value.representation.identity != baseline.value.representation.identity
    assert parsed.value.dataset_version != baseline.value.dataset_version
    chosen = parsed.value.source_details["selection"]
    assert chosen["sheet"] == "Published observations" and chosen["first_row"] == 4
    assert chosen["header_rows"] == (2, 3) and chosen["date_basis"] == "printed"
    assert parsed.value.source_details["formula_lineage"] == {}
    assert monthly.compare(CompareReleaseRequest(parsed.value, baseline.value)).value.state == "unchanged"
    revised = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook(revision=1)), period))
    assert monthly.compare(CompareReleaseRequest(revised.value, parsed.value)).value.state == "revised"
    scaled = monthly.parse(monthly.ParseOfficesRegRequest(
        SourcePayload(workbook(group="Остатки, млн рублей")), period,
    ))
    assert scaled.value.qualification.analysis == "literal_only" and scaled.value.batch is None
    assert monthly.compare(CompareReleaseRequest(scaled.value, parsed.value)).value.state == "indeterminate"
    conflict = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook(printed="1.9.2026")), period))
    assert conflict.diagnostics[0].code == "source.xlsx_report_date_mismatch"
    raw = workbook(duplicate=True)
    ambiguous = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(raw), period))
    assert ambiguous.outcome == "partial"
    assert ambiguous.value.source_identity == ByteIdentity.of(raw)
    assert ambiguous.value.blocks == (("Published observations", 4, 1), ("Competing block", 4, 1))
    assert preview_workbook(raw, sheet="Competing block", max_rows=1).rows[0][0].startswith("Данные")
    explicit = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(raw), period, sheet="Competing block"))
    assert explicit.outcome == "succeeded" and explicit.value.facts_identity == parsed.value.facts_identity
    assert explicit.value.source_details["selection"]["sheet"] == "Competing block"
    extended = monthly.parse(monthly.ParseOfficesRegRequest(SourcePayload(workbook(extra=True)), period))
    assert extended.outcome == "succeeded"
    assert extended.value.qualification.analysis == "qualified_subset"
    assert extended.value.qualification.excluded_fields == ("Дополнительная отметка",)
    assert extended.value.facts_identity == parsed.value.facts_identity
    assert "новая категория".encode() in extended.value.representation.data
    assert monthly.compare(CompareReleaseRequest(extended.value, parsed.value)).value.state == "unchanged"
    comparison = monthly.compare(CompareReleaseRequest(extended.value, parsed.value)).value
    assert comparison.layers.original == comparison.layers.structure == comparison.layers.representation == "changed"
    assert comparison.layers.facts == comparison.layers.method == "same"
    assert comparison.coverage.common_observations == len(parsed.value.batch.observations)
    fragment = monthly.parse(monthly.ParseOfficesRegRequest(
        SourcePayload(workbook()), period, national_row=4, last_row=6,
    ))
    assert fragment.outcome == "succeeded", fragment.diagnostics
    assert fragment.value.row_count == 3 and fragment.value.qualification.scope == "selected_fragment"
    assert monthly.compare(CompareReleaseRequest(fragment.value, parsed.value)).value.state == "indeterminate"
    one_sheet = SourcePayload(workbook(adjacent=True))
    ambiguous = monthly.parse(monthly.ParseOfficesRegRequest(one_sheet, period))
    assert ambiguous.outcome == "partial"
    assert tuple(row for _, row, _ in ambiguous.value.blocks) == (4, 53)
    chosen = monthly.parse(monthly.ParseOfficesRegRequest(
        one_sheet, date(2026, 11, 1), sheet="Published observations", national_row=53,
    ))
    assert chosen.outcome == "succeeded", chosen.diagnostics
    assert chosen.value.source_details["selection"]["first_row"] == 53
    assert chosen.value.source_details["selection"]["date_basis"] == "printed"
    assert chosen.value.row_count == parsed.value.row_count
    wrong_period = monthly.parse(monthly.ParseOfficesRegRequest(one_sheet, period, national_row=53))
    assert wrong_period.diagnostics[0].code == "source.xlsx_report_date_mismatch"
