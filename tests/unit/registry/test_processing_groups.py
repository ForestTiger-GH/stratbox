"""Reusable processing facts expand additively without route inheritance."""
from copy import deepcopy
import json

import pytest

from stratbox.core.registry import sources


@pytest.mark.parametrize("owner,route_id,group_id", [
    ("frank_rg", "frg.regional.issuance.route", "frg.report_processing"),
    ("minfin", "minfin.fedbud.annex3.monthly.route", "minfin.fiscal_processing"),
    ("minfin", "minfin.nwf.volume.route", "minfin.document_extract"),
])
def test_grouped_route_matches_the_same_explicit_processing_facts(owner, route_id, group_id):
    grouped = sources.profile_document(owner, route_id)
    assert grouped["groups"] == [group_id]
    group = sources.group_document(owner, group_id)
    explicit = deepcopy(grouped)
    explicit.pop("groups")
    for name in ("operations", "stages", "transitions"):
        explicit[name] = deepcopy(group[name]) + explicit.get(name, [])
    assert sources.decode_route(grouped, owner=owner) == sources.decode_route(explicit, owner=owner)


def test_shared_transformations_preserve_independent_source_profiles():
    regional = sources.source_route("frg.regional.issuance")
    special = sources.source_route("frg.special.mortgage_refinancing")
    assert regional.operations == special.operations
    assert regional.profile_id != special.profile_id
    assert regional.profiles != special.profiles


def test_local_route_facts_add_without_overriding_shared_bindings():
    value = sources.profile_document("frank_rg", "frg.regional.issuance.route")
    value["operations"] = [{"operation_id": "example.local_extension"}]
    value["stages"] = ["publish"]
    value["transitions"] = [{"from": "render", "to": "publish"}]
    route = sources.decode_route(value, owner="frank_rg")
    assert route.operations[-1].operation_id == "example.local_extension"
    assert route.allows("render", "publish")
    assert route.binding("frg.capture").identity_parameter == "source_id"


@pytest.mark.parametrize("change", [
    lambda value: value.update(groups=["missing.group"]),
    lambda value: value.update(groups=["frg.report_processing", "frg.report_processing"]),
    lambda value: value.update(operations=[{"operation_id": "frg.capture"}]),
])
def test_unknown_duplicate_and_overridden_group_bindings_are_rejected(change):
    value = sources.profile_document("frank_rg", "frg.regional.issuance.route")
    change(value)
    with pytest.raises(ValueError):
        sources.decode_route(value, owner="frank_rg")


def test_processing_groups_are_scoped_to_their_explicit_owner():
    with pytest.raises(ValueError, match="registry.group_unknown"):
        sources.group_document("minfin", "frg.report_processing")


@pytest.mark.parametrize("change", [
    lambda value: value.update(groups=["another.group"]),
    lambda value: value.update(owner_id="frank_rg"),
    lambda value: value["operations"].append(deepcopy(value["operations"][0])),
    lambda value: value["transitions"].append(deepcopy(value["transitions"][0])),
])
def test_group_records_reject_nested_includes_wrong_owner_and_duplicate_facts(monkeypatch, tmp_path, change):
    value = sources.group_document("minfin", "minfin.fiscal_processing")
    change(value)
    resource = tmp_path / "GROUP_minfin.fiscal_processing.yaml"
    resource.write_text(json.dumps(value), encoding="utf-8")
    original = sources.iter_resources
    monkeypatch.setattr(sources, "iter_resources", lambda owner, kind:
                        (resource,) if owner == "minfin" and kind == "groups" else original(owner, kind))
    sources._group_documents.cache_clear()
    try:
        with pytest.raises(ValueError):
            sources.group_document("minfin", "minfin.fiscal_processing")
    finally:
        sources._group_documents.cache_clear()
