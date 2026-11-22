"""Minfin publisher marker, clean flake, headline and notification contracts.

Works offline with synthetic fixtures; real publisher XLSX files are checked
separately in the optional Minfin fixture-validation program.
"""
from datetime import date
from decimal import Decimal

import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.minfin.tables.contracts import Cell, Sheet, TableExtract
from stratbox.domains.minfin.publications.contracts import Asset, PublicationIndex
import stratbox.domains.minfin as M
from stratbox.domains.minfin import (
    plan_updates, build_source_flake, render_source_flake,
    calculate_headlines, prepare_notice_facts,
)
from stratbox.domains.minfin import discover
from stratbox.domains.minfin import DiscoverRequest
from stratbox.domains.minfin.tables.periods import normalize_period
from stratbox.domains.minfin.publications.updates import checkpoint_for
from stratbox.domains.registry import operation_catalog


def _publisher_page(source_file="Prilozhenie_3_dannye_109-111_—_mes.xlsx", modified="12.11.2026"):
    return f'''<html><div data-href="/ru/statistics/fedbud/execute?id_57=80042-document"
      class="document_card inner_link">
      <div><span class="date">Опубликовано: 10.11.2026</span>
      <span class="date">Изменено: {modified}</span></div>
      <a class="document_title" title="Исполнение федерального бюджета">Документ</a>
      <div><a class="file_item" title="Ежемесячные данные" href="/common/upload/library/2026/11/main/{source_file}">xlsx</a></div>
    </div></html>'''


def _index(modified="12.11.2026"):
    html = _publisher_page(modified=modified)
    result = discover(DiscoverRequest(
        "minfin.fedbud", SourcePayload(html.encode(), "text/html", "minfin.fedbud.index"),
    ))
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def _extract(source_id, family, headers, rows, name="месяц"):
    cells = [Cell(name, 3, 1, "text", "№ п/п"), Cell(name, 3, 2, "text", "Показатель")]
    for c, label in enumerate(headers, 3):
        cells.append(Cell(name, 3, c, "text", label))
    for idx, (code, label, values) in enumerate(rows, 5):
        cells.extend((Cell(name, idx, 1, "text", code), Cell(name, idx, 2, "text", label)))
        for c, value in enumerate(values, 3):
            if value is not None:
                cells.append(Cell(name, idx, c, "number", str(value)))
    cells.extend((Cell(name, 1, 1, "text", "Приложение 3"),
                  Cell(name, 4, 2, "text", "РАЗДЕЛ I"),
                  Cell(name, 12, 1, "text", "* Примечание: лишняя строка")))
    return TableExtract(family, source_id, ByteIdentity.of(b"same official XLSX"),
                        "xlsx", (Sheet(name, 12, len(headers) + 2, tuple(cells)),))


def test_document_card_dates_are_associated_with_the_correct_variant():
    index = _index()
    asset, = index.assets
    assert asset.document_id == "id_57:80042"
    assert asset.published_on == date(2026, 11, 10)
    assert asset.modified_on == date(2026, 11, 12)
    assert asset.source_id == "minfin.fedbud.annex3.monthly"
    assert index.coverage == "unknown"


def test_cheap_update_probe_skips_redundant_file_download():
    index = _index()
    asset = index.assets[0]
    cp = M.SourceCheckpoint(asset.source_id, asset.asset_id, asset.document_id,
                            asset.modified_on, asset.url, ByteIdentity.of(b"previous"),
                            "minfin.flake.v1")
    unchanged = plan_updates(M.UpdateRequest(index, (cp,), (asset.source_id,)))
    assert unchanged.outcome == "succeeded"
    item, = unchanged.value.decisions
    assert item.state == "unchanged"
    assert item.download_required is False
    assert item.processing_required is False
    reparsing = plan_updates(M.UpdateRequest(index, (cp,), (asset.source_id,),
                                             frozenset({asset.source_id}), "flake"))
    assert reparsing.value.decisions[0].download_required is False
    assert reparsing.value.decisions[0].processing_required is True
    no_retained = plan_updates(M.UpdateRequest(index, (cp,), (asset.source_id,),
                                               frozenset(), "flake"))
    assert no_retained.value.decisions[0].download_required is True
    revised = plan_updates(M.UpdateRequest(_index("13.11.2026"), (cp,), (asset.source_id,)))
    assert revised.value.decisions[0].state == "revised"
    assert revised.value.decisions[0].download_required is True


def test_missing_candidate_never_proves_source_was_removed():
    i = _index()
    plan = plan_updates(M.UpdateRequest(i, selected_sources=("minfin.fedbud.annex3.annual",)))
    assert plan.value.decisions[0].state == "missing"
    assert plan.value.inventory_coverage == "unknown"


@pytest.mark.parametrize("label,freq,expected", [
    ("окт.26 **", "monthly", "2026-10"),
    ("Январь 2008¹", "monthly", "2008-01"),
    ("2025-08-31T00:00:00", "monthly", "2025-08"),
    ("45869", "monthly", "2025-07"),
    ("2 кв.2026 ***", "quarterly", "2026-Q2"),
    ("2025", "annual", "2025"),
])
def test_publisher_period_spelling(label, freq, expected):
    assert normalize_period(label, freq) == expected


def test_budget_flake_strips_notes_and_computes_cumulative_yoy():
    src = "minfin.fedbud.annex3.monthly"
    original = _extract(src, "minfin.fedbud", ("окт.25 **", "окт.26 **"), (
        ("1", "Доходы, всего", ("100", "110")),
        ("2", "Расходы, всего", ("120", "135")),
        ("3", "Дефицит (-)/Профицит (+)", ("-20", "-25")),
        ("2.1.", "Образование ***", ("5", "6")),
    ))
    flake_result = build_source_flake(M.BuildFlakeRequest(original, src))
    assert flake_result.outcome == "succeeded", flake_result.diagnostics
    flake = flake_result.value
    assert [x.period_id for x in flake.columns] == ["2025-10", "2026-10"]
    assert flake.value_basis == "ytd"
    assert [x.indicator for x in flake.rows][-1] == "Образование"
    assert len(flake.rows) == 4
    cleaned = render_source_flake(M.RenderFlakeRequest(flake))
    assert cleaned.outcome == "succeeded"
    assert cleaned.value.data.startswith(b"\xef\xbb\xbfcode,indicator,2025-10,2026-10")
    assert "Примечание" not in cleaned.value.data.decode("utf-8-sig")
    summary = calculate_headlines(M.SummaryRequest(flake))
    assert summary.outcome == "succeeded", summary.diagnostics
    values = summary.value.metrics
    assert [Decimal(m.yoy_pct).quantize(Decimal("0.1")) for m in values] == [
        Decimal("10.0"), Decimal("12.5"), Decimal("25.0"),
    ]


def test_nwf_liquid_is_total_minus_other_assets_and_has_its_own_yoy():
    src = "minfin.nwf.flows"
    original = _extract(src, "minfin.nwf", ("окт.25", "окт.26"), (
        ("2", "Объем на конец периода", ("13201.46", "13055.34")),
        ("5", "Размещено в иные разрешенные активы на конец периода", ("9043.91", "9476.86")),
    ), name="Таблица по ФНБ")
    result = build_source_flake(M.BuildFlakeRequest(original, src))
    assert result.outcome == "succeeded"
    headlines = calculate_headlines(M.SummaryRequest(result.value))
    assert headlines.outcome == "succeeded", headlines.diagnostics
    total, liquid = headlines.value.metrics
    assert Decimal(total.value) == Decimal("13055.34")
    assert Decimal(liquid.value) == Decimal("3578.48")
    assert Decimal(liquid.previous_year_value) == Decimal("4157.55")


def test_notification_is_channel_neutral_deterministic_and_quiet_on_initial():
    i = _index()
    a, = i.assets
    original = _extract(a.source_id, i.family_id, ("окт.25", "окт.26"), (
        ("1", "Доходы, всего", (100, 110)),
        ("2", "Расходы, всего", (120, 135)),
        ("3", "Дефицит (-)/Профицит (+)", (-20, -25)),
    ))
    flake = build_source_flake(M.BuildFlakeRequest(original, a.source_id)).value
    cp = checkpoint_for(a, flake)
    assert cp.modified_on == a.modified_on
    summary = calculate_headlines(M.SummaryRequest(flake)).value
    initial = plan_updates(M.UpdateRequest(i, selected_sources=(a.source_id,))).value.decisions[0]
    suppressed = prepare_notice_facts(M.NoticeRequest(summary, a, initial))
    assert suppressed.value.state == "skipped" and suppressed.value.facts is None
    previous_cp = M.SourceCheckpoint(a.source_id, a.asset_id, a.document_id,
                                     date(2026, 11, 11), a.url,
                                     ByteIdentity.of(b"old source"), "minfin.flake.v1")
    revised = plan_updates(M.UpdateRequest(i, (previous_cp,), (a.source_id,))).value.decisions[0]
    notice = prepare_notice_facts(M.NoticeRequest(summary, a, revised))
    assert notice.outcome == "succeeded" and notice.value.state == "ready"
    fact = notice.value.facts
    assert fact.topic == "minfin.budget_headline"
    assert len(fact.values) == 3 and fact.event_key == prepare_notice_facts(M.NoticeRequest(summary, a, revised)).value.facts.event_key
    assert "telegram" not in str(fact).casefold()


def test_invalid_economic_rows_fail_instead_of_guessing():
    src = "minfin.fedbud.annex3.monthly"
    bad = _extract(src, "minfin.fedbud", ("окт.25", "окт.26"), (
        ("1", "Доходы, всего", (100, 110)),
        ("2", "Расходы, всего", (120, 135)),
        ("3", "Дефицит (-)/Профицит (+)", (-20, -24)),
    ))
    flake = build_source_flake(M.BuildFlakeRequest(bad, src)).value
    result = calculate_headlines(M.SummaryRequest(flake))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "minfin.summary.inconsistent_budget_totals"

def test_nwf_default_update_scope_excludes_archived_documents():
    page = """
    <div class="document_card" data-href="/ru/perfomance/nationalwealthfund/statistics?id_57=93488-report">
      <div><span class="date">Опубликовано: 13.11.2026</span><span class="date">Изменено: 13.11.2026</span></div>
      <a class="file_item" title="Движение средств ФНБ" href="/common/upload/library/2026/11/main/Dannye_20261101.xlsx">XLSX</a>
    </div>
    """
    index = discover(DiscoverRequest("minfin.nwf", SourcePayload(
        page.encode(), "text/html", "minfin.nwf.index",
    ))).value
    plan = plan_updates(M.UpdateRequest(index))
    assert plan.outcome == "succeeded", plan.diagnostics
    assert tuple(item.source_id for item in plan.value.decisions) == ("minfin.nwf.flows",)
    assert plan.value.decisions[0].state == "initial"


def test_marker_revision_without_byte_revision_does_not_notify():
    index = _index()
    asset, = index.assets
    original = _extract(asset.source_id, index.family_id, ("окт.25", "окт.26"), (
        ("1", "Доходы, всего", (100, 110)),
        ("2", "Расходы, всего", (120, 135)),
        ("3", "Дефицит (-)/Профицит (+)", (-20, -25)),
    ))
    flake = build_source_flake(M.BuildFlakeRequest(original, asset.source_id)).value
    summary = calculate_headlines(M.SummaryRequest(flake)).value
    prior = M.SourceCheckpoint(
        asset.source_id, asset.asset_id, asset.document_id,
        date(2026, 11, 11), asset.url, flake.original_identity, "minfin.flake.v1",
    )
    change = plan_updates(M.UpdateRequest(index, (prior,), (asset.source_id,))).value.decisions[0]
    assert change.state == "revised" and change.download_required
    notice = prepare_notice_facts(M.NoticeRequest(
        summary, asset, change, baseline_original_identity=prior.original_identity,
    ))
    assert notice.outcome == "succeeded"
    assert notice.value.state == "skipped"
    assert notice.value.reason == "minfin.notice.source_bytes_unchanged"
    assert notice.value.facts is None

def test_verified_same_date_byte_revision_can_produce_qualified_notice():
    index = _index()
    asset, = index.assets
    original = _extract(asset.source_id, index.family_id, ("окт.25", "окт.26"), (
        ("1", "Доходы, всего", (100, 110)),
        ("2", "Расходы, всего", (120, 135)),
        ("3", "Дефицит (-)/Профицит (+)", (-20, -25)),
    ))
    flake = build_source_flake(M.BuildFlakeRequest(original, asset.source_id)).value
    summary = calculate_headlines(M.SummaryRequest(flake)).value
    baseline = M.SourceCheckpoint(
        asset.source_id, asset.asset_id, asset.document_id,
        asset.modified_on, asset.url, ByteIdentity.of(b"previous official original"),
        flake.method_version,
    )
    plan = plan_updates(M.UpdateRequest(
        index, (baseline,), (asset.source_id,), frozenset({asset.source_id}),
        "probe", force_refresh=True,
    ))
    assert plan.outcome == "succeeded"
    decision, = plan.value.decisions
    assert decision.state == "unchanged" and decision.download_required
    assert not decision.processing_required
    prepared = prepare_notice_facts(M.NoticeRequest(
        summary, asset, decision, baseline_original_identity=baseline.original_identity,
    ))
    assert prepared.outcome == "succeeded"
    assert prepared.value.state == "ready"
    assert prepared.value.facts.publication_state == "material_revision"
    assert prepared.value.facts.original_sha256 == flake.original_identity.sha256
