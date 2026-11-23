"""Offline tests derived from the four Minfin HTML pages saved 2026-11-22.

Publisher links may change. These fixtures test the observed page structure and
source identity rules without asserting global/current index completeness.
"""
from datetime import datetime, timezone

import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.core.network import HttpResponse
from stratbox.domains.minfin import (
    DiscoverRequest, AcquireRequest, InspectRequest, discover, acquire, inspect,
    family, families, all_sources, bind_family,
)
from stratbox.domains.minfin.publications.access import allowed_file


@pytest.fixture
def official_pages():
    # Titles, filenames, capitalization and em dashes follow supplied HTML.
    return {
        'minfin.fedbud': [
            ('Краткая ежемесячная информация об исполнении федерального бюджета (млрд руб., накоплено с начала года)',
             '2026/11/main/Prilozhenie_3_dannye_109-111_—_mes.xlsx'),
            ('Краткая ежеквартальная информация об исполнении федерального бюджета (млрд руб., накоплено с начала года)',
             '2026/11/main/Prilozhenie_3_dannye_109-111_—_kvartal.xlsx'),
            ('Краткая ежегодная информация об исполнении федерального бюджета (млрд руб.)',
             '2026/05/main/Prilozhenie_3_dannye_109-111_—_god.xlsx'),
        ],
        'minfin.conbud': [
            ('Краткая ежемесячная информация об исполнении консолидированного бюджета РФ и государственных внебюджетных фондов',
             '2026/11/main/Prilozhenie_8_dannye_115-117_—_mesyats.xlsx'),
            ('Краткая ежеквартальная информация об исполнении консолидированного бюджета РФ и государственных внебюджетных фондов',
             '2026/11/main/Prilozhenie_8_dannye_115-117_—_kvartal.xlsx'),
            ('Краткая ежегодная информация об исполнении консолидированного бюджета РФ и государственных внебюджетных фондов',
             '2026/05/main/Prilozhenie_8_dannye_115-117_—_god.xlsx'),
        ],
        'minfin.subbud': [
            ('Краткая ежемесячная информация об исполнении консолидированных бюджетов субъектов РФ',
             '2026/11/main/Prilozhenie_6_dannye_112-114_—_mes.xlsx'),
            ('Краткая ежеквартальная информация об исполнении консолидированных бюджетов субъектов РФ',
             '2026/11/main/Prilozhenie_6_dannye_112-114_—_Kvartal.xlsx'),
            ('Краткая ежегодная информация об исполнении консолидированных бюджетов субъектов РФ',
             '2026/05/main/Prilozhenie_6_dannye_112-114_—_god.xlsx'),
        ],
        'minfin.nwf': [
            ('Данные о движении средств и результатах управления средствами Фонда национального благосостояния',
             '2026/11/main/Dannye_20261101.xlsx'),
            ('Сведения о размещении средств ФНБ на депозитах в ВЭБ.РФ',
             '2024/12/main/Svedeniya_o_razmeshchenii_sredstv_FNB_na_depozitakh_v_VEB.doc'),
            ('Объем Фонда национального благосостояния',
             '2024/11/main/Obem_na_01.11.2024.docx'),
            ('Сведения о размещении средств ФНБ в привилегированные акции российских кредитных организаций',
             '2023/11/main/Svedeniya_na_01.11.2023.docx'),
        ],
    }


def _page(source, links):
    anchors = ''.join(f'<a title="{title}" href="/common/upload/library/{path}">Документ</a>'
                      for title, path in links)
    return SourcePayload(('<html><body>'+anchors+'</body></html>').encode(),
                         'text/html', source+'.index', charset='utf-8')


def test_four_root_registries_are_distinct_and_versioned():
    all_families = families()
    assert {item.family_id for item in all_families} == {
        'minfin.fedbud', 'minfin.conbud', 'minfin.subbud', 'minfin.nwf'}
    assert len(all_sources()) == 17  # four fallback families + 3+3+3+4 known statistical series
    assert len(set(all_sources())) == len(all_sources())
    for item in all_families:
        assert bind_family(item.family_id).acquisition.landing_url.startswith('https://minfin.gov.ru/ru/')
        assert not hasattr(item, 'landing_url')
        assert item.profiles.discovery == 'minfin.document_cards'
        assert item.profiles.identification.startswith('minfin.')
        assert item.series and all(series.source_id.startswith(item.family_id + '.')
                                   for series in item.series)
    assert [v.basis for v in family('minfin.fedbud').series] == ['ytd', 'ytd', 'annual']


@pytest.mark.parametrize('family_id, expected', [
    ('minfin.fedbud', ('annex3_monthly','annex3_quarterly','annex3_annual')),
    ('minfin.conbud', ('annex8_monthly','annex8_quarterly','annex8_annual')),
    ('minfin.subbud', ('annex6_monthly','annex6_quarterly','annex6_annual')),
    ('minfin.nwf', ('movement_workbook','veb_deposits','volume_report','preferred_shares')),
])
def test_discover_actual_page_families(official_pages, family_id, expected):
    result = discover(DiscoverRequest(family_id, _page(family_id, official_pages[family_id])))
    assert result.outcome == 'succeeded', result.diagnostics
    assets = result.value.assets
    assert result.value.coverage == 'unknown'  # HTML view alone is not complete history
    assert tuple(a.asset_id for a in assets) == tuple(sorted(expected)) or set(a.asset_id for a in assets) == set(expected)
    assert {a.source_id for a in assets} <= set(all_sources())
    assert all(a.recognition == 'registered_variant' and a.index_identity.size for a in assets)
    assert all(a.label != 'Документ' for a in assets)  # HTML title, not generic link text


def test_refusal_does_not_turn_missing_links_into_missing_publications():
    html = b'<a href="https://evil.example/download.xlsx">x</a><a href="/unknown.doc">no</a>'
    result = discover(DiscoverRequest('minfin.fedbud', SourcePayload(html, 'text/html', 'minfin.fedbud.index')))
    assert result.outcome == 'succeeded'
    assert result.value.assets == ()
    assert result.value.coverage == 'unknown'
    assert result.value.rejected_links == 2
    assert not allowed_file('https://minfin.gov.ru/ru/account/admin.xlsx')
    assert not allowed_file('https://minfin.gov.ru/common/upload/library/../admin.xlsx')
    assert not allowed_file('https://other.example/common/upload/library/data.xlsx')


def test_unsafe_html_base_fails_and_source_identity_must_match():
    page = SourcePayload(b'<base href="https://evil.example"><a href="/common/upload/library/a.xlsx">x</a>',
                         'text/html', 'minfin.fedbud.index')
    result = discover(DiscoverRequest('minfin.fedbud', page))
    assert result.outcome == 'failed'
    other = discover(DiscoverRequest('minfin.conbud', page))
    assert other.outcome == 'failed'


def test_inspection_is_not_authoritative_absence(official_pages):
    source = 'minfin.fedbud'
    previous = discover(DiscoverRequest(source, _page(source, official_pages[source][:2]))).value
    current = discover(DiscoverRequest(source, _page(source, official_pages[source]))).value
    result = inspect(InspectRequest(previous, current))
    assert result.outcome == 'succeeded'
    assert len(result.value.added_candidates) == 1
    assert result.value.coverage == 'unknown'


def test_download_uses_exact_minfin_host_and_preserves_bytes(official_pages):
    source = 'minfin.nwf'
    asset, = [a for a in discover(DiscoverRequest(source, _page(source, official_pages[source]))).value.assets
              if a.asset_id == 'movement_workbook']
    # Signature-only fixture is enough for raw acquisition. Workbook admission
    # belongs to extraction and needs a complete actual XLSX file.
    content = b'PK\x03\x04synthetic-original-material'

    class StubTransport:
        def exchange(self, request, *, cancelled=None):
            assert request.url == asset.url
            assert request.permits(request.url)
            assert not request.permits('https://evil.example/common/upload/library/a.xlsx')
            return HttpResponse(200, content, {'content-type': 'application/octet-stream'},
                                datetime(2026, 11, 22, tzinfo=timezone.utc), 'https://minfin.gov.ru')

    result = acquire(AcquireRequest(asset), transport=StubTransport())
    assert result.outcome == 'succeeded', result.diagnostics
    assert result.value.source.payload.data == content
    assert result.value.source.receipt.identity == result.value.source.payload.identity

def test_explicit_saved_page_is_authoritative_and_never_falls_back_to_http():
    class ForbiddenTransport:
        def exchange(self, request, *, cancelled=None):
            raise AssertionError("An explicit supplied page must never fetch another page")

    page = SourcePayload(b'<a href="/common/upload/library/new.xlsx">Attachment</a>', "text/html",
                         "minfin.fedbud.index")
    result = discover(DiscoverRequest("minfin.fedbud", page), transport=ForbiddenTransport())
    assert result.outcome == "succeeded", result.diagnostics
    invalid = SourcePayload(b"malformed saved page", "text/html", "minfin.fedbud.index")
    failed = discover(DiscoverRequest("minfin.fedbud", invalid), transport=ForbiddenTransport())
    assert failed.outcome == "failed"
    assert failed.diagnostics[0].code == "minfin.index_no_links"


def test_explicit_http_route_overrides_profile_default_and_refusal_has_no_fallback():
    selected = "https://minfin.gov.ru/ru/statistics/fedbud/execute/archive/"
    seen = []

    class PageTransport:
        def exchange(self, request, *, cancelled=None):
            seen.append(request.url)
            return HttpResponse(200, b'<a href="/common/upload/library/new.xlsx">Attachment</a>',
                                {"content-type": "text/html; charset=utf-8"},
                                datetime(2026, 11, 22, tzinfo=timezone.utc), "https://minfin.gov.ru")

    result = discover(DiscoverRequest("minfin.fedbud", page_url=selected), transport=PageTransport())
    assert result.outcome == "succeeded", result.diagnostics
    assert seen == [selected]
    refused = discover(DiscoverRequest("minfin.fedbud", page_url="https://example.invalid/other"),
                       transport=PageTransport())
    assert refused.outcome == "failed"
    assert refused.diagnostics[0].code == "minfin.page_forbidden"
    assert seen == [selected]


def test_named_http_adapter_is_used_without_ambiguous_default_selection(official_pages):
    from stratbox.core.execution import ExecutionContext
    from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection

    family_id = "minfin.nwf"
    asset, = [a for a in discover(DiscoverRequest(family_id, _page(family_id, official_pages[family_id]))).value.assets
              if a.asset_id == "movement_workbook"]
    calls = []
    class Chosen:
        def exchange(self, request, *, cancelled=None):
            calls.append("selected")
            return HttpResponse(200, b"PK\x03\x04original", {"content-type": "application/octet-stream"},
                                datetime(2026, 11, 23, tzinfo=timezone.utc), "https://minfin.gov.ru")
    class Unused:
        def exchange(self, request, *, cancelled=None):
            calls.append("other")
            raise AssertionError("The explicitly selected route must be respected")
    context = ExecutionContext(bindings=(
        ProviderBinding("chosen", CapabilityRequirement("http"), "ready", Chosen(), "primary"),
        ProviderBinding("other", CapabilityRequirement("http"), "ready", Unused(), "secondary"),
    ))
    result = acquire(AcquireRequest(asset), selection=ProviderSelection("chosen", "primary"), context=context)
    assert result.outcome == "succeeded", result.diagnostics
    refused = acquire(AcquireRequest(asset), selection=ProviderSelection("missing", "primary"), context=context)
    assert refused.outcome == "failed"
    assert refused.diagnostics[0].code == "provider.capability_missing"
    assert calls == ["selected"]
