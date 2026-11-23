"""Minfin's canonical sources, static profiles and runtime operation bindings."""
from dataclasses import replace
from datetime import date
import json
from importlib import resources
from pathlib import Path
from io import BytesIO

import pytest
from openpyxl import Workbook

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.minfin import (
    DiscoverRequest, ExtractRequest, BuildFlakeRequest, SummaryRequest,
    SourceCheckpoint, UpdateRequest, discover, extract, plan_updates,
    build_source_flake, calculate_headlines, family, families,
    bind_family, bind_series, validate_all_profiles,
)
from stratbox.domains.minfin.publications.catalog import _decode
from stratbox.domains.registry.declarations import publication_families, source_documents
from stratbox.domains.minfin.publications.profiles import identification_profile
from stratbox.domains.minfin.publications.discovery import check_asset


def _publisher_card(document_id="80042", name="Prilozhenie_3_dannye_109-111_—_mes.xlsx", modified="12.11.2026"):
    return (f'<html><div class="document_card" data-href="/ru/statistics/fedbud/execute?id_57={document_id}-report">'
            f'<span class="date">Опубликовано: 10.11.2026</span>'
            f'<span class="date">Изменено: {modified}</span>'
            f'<a class="file_item" title="Месячное исполнение федерального бюджета" '
            f'href="/common/upload/library/2026/11/main/{name}">Скачать</a>'
            '</div></html>')


def _discover(page):
    result = discover(DiscoverRequest("minfin.fedbud", SourcePayload(
        page.encode("utf-8"), "text/html", "minfin.fedbud.index", charset="utf-8")))
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def test_all_root_registry_series_resolve_to_registered_typed_profiles():
    bindings = validate_all_profiles()
    assert len(families()) == 4 and len(bindings) == 13
    assert len({(b.parent.source.family_id, b.series.slot) for b in bindings}) == 13
    assert sum(b.table is not None for b in bindings) == 10
    assert sum(b.metrics is not None for b in bindings) == 10
    assert sum(b.table is None and b.metrics is None for b in bindings) == 3
    for b in bindings:
        assert b.parent.identification.rule(b.series.slot).format
        if b.table is not None:
            assert b.table.method_version.startswith("minfin.flake.")
            assert b.metrics.calculator is not None


def test_registry_declares_only_source_identifiers_and_profile_refs():
    for content in publication_families("minfin", series_fields=(("source_id", "series_id"), ("title", "title"))):
        assert content["schema"] == "stratbox.minfin.registry"
        assert set(content) == {"schema", "family_id", "publisher_id", "title", "profiles", "series"}
        assert all(set(item) == {"source_id", "slot", "title", "periodicity", "basis", "kind"}
                   for item in content["series"])
        assert "operations" not in content and "parser" not in content
        assert content["profiles"]["acquisition"].startswith("minfin.")
        assert content["profiles"]["identification"].startswith("minfin.")
    assert all("filename" not in item and "operations" not in item for item in source_documents("minfin"))


def test_unknown_profile_and_extra_executable_field_fail():
    obj = next(value for value in publication_families("minfin", series_fields=(("source_id", "series_id"), ("title", "title"))) if value["family_id"] == "minfin.fedbud")
    obj["parser"] = "evil.module:run"
    with pytest.raises(ValueError, match="minfin.registry.invalid_shape"):
        _decode(json.dumps(obj).encode())
    with pytest.raises(ValueError, match="minfin.profile.identification_unknown"):
        identification_profile("minfin.not_registered")


def test_document_id_survives_renaming_without_identity_change():
    observed = _discover(_publisher_card(name="revised_finances_2027.xlsx"))
    item, = observed.assets
    assert item.recognition == "registered_variant"
    assert item.source_id == "minfin.fedbud.annex3.monthly"
    assert item.asset_id == "annex3_monthly"
    assert item.document_id == "id_57:80042"
    assert item.modified_on == date(2026, 11, 12)
    binding = bind_family("minfin.fedbud")
    check_asset(item, binding.source, binding.identification)


def test_conflicting_document_id_and_filename_never_choose_a_series():
    observed = _discover(_publisher_card(name="Prilozhenie_3_dannye_109-111_—_kvartal.xlsx"))
    item, = observed.assets
    assert item.recognition == "conflicted"
    assert item.source_id == "minfin.fedbud.attachments"
    assert "annex3_monthly" in observed.ambiguous_asset_ids
    assert "annex3_quarterly" in observed.ambiguous_asset_ids
    with pytest.raises(ValueError, match="minfin.asset_ambiguous"):
        check_asset(item, bind_family("minfin.fedbud").source, bind_family("minfin.fedbud").identification)
    plan = plan_updates(UpdateRequest(observed, selected_sources=("minfin.fedbud.annex3.monthly",)))
    assert plan.outcome == "succeeded", plan.diagnostics
    assert plan.value.decisions[0].state == "ambiguous"
    assert plan.value.decisions[0].download_required is False


def test_processing_method_upgrade_does_not_trigger_original_reacquisition():
    item, = _discover(_publisher_card()).assets
    bound = bind_series("minfin.fedbud", item.source_id)
    previous = SourceCheckpoint(item.source_id, item.asset_id, item.document_id,
                                item.modified_on, item.url, SourcePayload(b"prior").identity,
                                "minfin.flake.legacy.v1")
    request = UpdateRequest(_discover(_publisher_card()), (previous,), (item.source_id,),
                            frozenset((item.source_id,)), "flake")
    result = plan_updates(request)
    assert result.outcome == "succeeded", result.diagnostics
    decision, = result.value.decisions
    assert bound.method_version != previous.processing.method_version
    assert decision.state == "unchanged" and not decision.download_required
    assert decision.processing_required
    assert previous.publication.modified_on == item.modified_on
    assert previous.material.identity == previous.original_identity


def test_profile_based_budget_flake_and_economic_calculation():
    book = Workbook()
    sh = book.active
    sh.title = "Федеральный бюджет"
    sh.append(["Приложение 3"])
    sh.append(["Код", "Показатель", "окт.25 **", "окт.26 **"])
    sh.append(["1", "Доходы, всего", 100, 110])
    sh.append(["2", "Расходы, всего", 120, 135])
    sh.append(["3", "Дефицит (-)/Профицит (+)", -20, -25])
    sh.append(["*", "Примечание", "—", "—"])
    out = BytesIO()
    book.save(out)
    original = SourcePayload(out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             "minfin.fedbud.annex3.monthly")
    extracted = extract(ExtractRequest("minfin.fedbud", original, "xlsx"))
    assert extracted.outcome == "succeeded", extracted.diagnostics
    flake = build_source_flake(BuildFlakeRequest(extracted.value, original.source_id))
    assert flake.outcome == "succeeded", flake.diagnostics
    assert flake.value.method_version == bind_series("minfin.fedbud", original.source_id).method_version
    assert [col.period_id for col in flake.value.columns] == ["2025-10", "2026-10"]
    assert len(flake.value.rows) == 3
    result = calculate_headlines(SummaryRequest(flake.value))
    assert result.outcome == "succeeded", result.diagnostics
    assert [float(metric.value) for metric in result.value.metrics] == [110, 135, -25]


def test_new_root_registry_is_discovered_without_adding_a_python_name(monkeypatch, tmp_path):
    from shutil import copytree
    from stratbox.domains.minfin.publications import catalog
    from stratbox.core import resources as registry_resources, sources
    root = Path(str(registry_resources.registry_root()))
    copytree(root, tmp_path / "registry")
    declaration_root = tmp_path / "registry" / "domains" / "minfin"
    profile = declaration_root / "families" / "fedbud" / "FAMILY_minfin.fedbud.publication.yaml"
    added = json.loads(profile.read_text())
    added["profile_id"] = "minfin.future.publication"
    added["declaration"]["family_id"] = "minfin.future"
    added["declaration"]["title"] = "Another logical family using a registered typed profile"
    (profile.parent / "FAMILY_minfin.future.publication.yaml").write_text(json.dumps(added))
    for source in (declaration_root / "sources").rglob("SOURCE_minfin.fedbud.*.yaml"):
        value = json.loads(source.read_text())
        value["family_id"] = "minfin.future"
        value["series_id"] = value["series_id"].replace("minfin.fedbud", "minfin.future")
        value["family_profile"] = added["profile_id"]
        (source.parent / ("SOURCE_" + value["series_id"] + ".yaml")).write_text(json.dumps(value))
    monkeypatch.setattr(registry_resources, "registry_root", lambda: tmp_path / "registry")
    catalog.families.cache_clear()
    sources._sources.cache_clear()
    sources._profile_documents.cache_clear()
    try:
        discovered = catalog.families()
        assert len(discovered) == 5
        assert {item.family_id for item in discovered} >= {"minfin.fedbud", "minfin.future"}
    finally:
        catalog.families.cache_clear()
        sources._sources.cache_clear()
        sources._profile_documents.cache_clear()


def test_force_refresh_and_reprocess_are_distinct_decisions():
    index = _discover(_publisher_card())
    asset, = index.assets
    method_id = bind_series("minfin.fedbud", asset.source_id).method_version
    checkpoint = SourceCheckpoint(asset.source_id, asset.asset_id, asset.document_id,
                                  asset.modified_on, asset.url, SourcePayload(b"original").identity,
                                  method_id)
    common = dict(index=index, checkpoints=(checkpoint,), selected_sources=(asset.source_id,),
                  retained_sources=frozenset({asset.source_id}))
    same = plan_updates(UpdateRequest(**common, target="flake"))
    assert same.value.decisions[0].state == "unchanged"
    assert not same.value.decisions[0].processing_required
    assert not same.value.decisions[0].download_required
    reprocess = plan_updates(UpdateRequest(**common, target="flake", force_reprocess=True))
    assert reprocess.value.decisions[0].processing_required
    assert not reprocess.value.decisions[0].download_required
    refresh = plan_updates(UpdateRequest(**common, target="probe", force_refresh=True))
    assert refresh.value.decisions[0].state == "unchanged"
    assert refresh.value.decisions[0].download_required
    assert not refresh.value.decisions[0].processing_required
    assert refresh.value.decisions[0].reason == "minfin.update.forced_material_verification"


def test_force_controls_qualify_computation_identity_with_unchanged_publication_markers():
    index = _discover(_publisher_card())
    asset, = index.assets
    method = bind_series("minfin.fedbud", asset.source_id).method_version
    checkpoint = SourceCheckpoint(asset.source_id, asset.asset_id, asset.document_id,
        asset.modified_on, asset.url, SourcePayload(b"same original").identity, method)
    request = UpdateRequest(index, (checkpoint,), (asset.source_id,), frozenset({asset.source_id}), "flake")
    baseline = plan_updates(request)
    reprocessed = plan_updates(replace(request, force_reprocess=True))
    refreshed = plan_updates(replace(request, force_refresh=True))
    assert baseline.outcome == reprocessed.outcome == refreshed.outcome == "succeeded"
    assert baseline.value.decisions[0].processing_required is False
    assert reprocessed.value.decisions[0].processing_required is True
    assert refreshed.value.decisions[0].download_required is True
    assert len({result.computation.computation_id for result in (baseline, reprocessed, refreshed)}) == 3
