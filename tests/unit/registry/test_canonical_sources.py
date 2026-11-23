"""Source route admission, isolated metadata and strict canonical declarations."""
from copy import deepcopy
import json
import subprocess
import sys
import os
from pathlib import Path

import pytest

from stratbox.core.resources import decode_document
from stratbox.domains.registry.declarations import (
    decode_route, profile_document, source_cards, source_documents, source_route,
    validate_source_bindings, template_document,
)
from stratbox.operations import operation_catalog


def _route_document(owner, route_id):
    source_id = route_id.removesuffix(".route")
    source = next(item for item in source_documents(owner) if item["series_id"] == source_id)
    processing = source["processing"]
    template = template_document(owner, processing["template"])
    slots = {**template["slots"], **processing["bindings"]}
    return {"schema": "stratbox.route", "owner_id": owner, "profile_id": route_id,
            "stages": template["stages"], "operations": list(slots.values()),
            "profiles": processing["profiles"], "qualifications": processing["qualifications"]}


def test_complete_source_routes_validate_operation_identities_and_parameter_names():
    catalog = operation_catalog()
    assert validate_source_bindings(catalog) == 90
    for card in catalog.source_catalog().sources:
        route = source_route(card.series_id)
        assert route.operations == card.operations
        for binding in route.operations:
            definition = catalog.get(binding.operation_id)
            names = definition.processing.parameters if definition.processing else ()
            assert set(dict(binding.parameters)) <= set(names)


def test_format_qualifications_keep_historical_originals_outside_reviewed_parsers():
    route = source_route("cbr.project_finance.escrow")
    parse = next(binding for binding in route.operations if binding.operation_id == "cbr.escrow.parse")
    assert route.binding(parse.operation_id, format="xlsx") == parse
    with pytest.raises(ValueError, match="registry.source_operation_format_unavailable"):
        route.binding(parse.operation_id, format="html")
    acquire = next(binding for binding in route.operations if binding.operation_id == "cbr.publications.acquire")
    assert route.binding(acquire.operation_id, format="html") == acquire
    legacy = next(card for card in source_cards("minfin") if card.formats == ("doc",))
    assert not any(binding.operation_id == "minfin.extract_document" for binding in legacy.operations)


def test_source_route_declares_applicability_without_a_second_stage_graph():
    route = source_route("fns.sme")
    assert route.binding("fns.sme.extract")
    assert not hasattr(route, "transitions")
    assert "transitions" not in _route_document("fns", "fns.sme.route")
    with pytest.raises(ValueError, match="registry.source_operation_unbound"):
        route.binding("cbr.escrow.parse")


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(unknown="ignored metadata"),
    lambda d: d.update(transitions=[{"from": "publish", "to": "extract"}]),
    lambda d: d["stages"].append(d["stages"][0]),
    lambda d: d["operations"].append(deepcopy(d["operations"][0])),
    lambda d: d["operations"][0].update(formats="json"),
    lambda d: d.update(owner_id="other"),
    lambda d: d.update(schema="stratbox.route.v999"),
])
def test_malformed_routes_are_rejected_before_handler_resolution(mutate):
    document = _route_document("fns", "fns.sme.route")
    mutate(document)
    with pytest.raises(ValueError):
        decode_route(document, owner="fns")


@pytest.mark.parametrize("data", [
    b'{"owner_id":"fns","owner_id":"cbr"}', b'{"number":NaN}',
    b'{"number":Infinity}', b'[]', b'not a declaration',
])
def test_registry_reader_rejects_duplicate_and_non_finite_json_yaml(data):
    with pytest.raises(ValueError, match="registry.invalid_document"):
        decode_document(data)


def test_returned_declaration_copies_cannot_mutate_future_catalog_reads():
    document = source_documents("fns")[0]
    document["publication"].clear()
    assert source_documents("fns")[0]["publication"]
    profile = _route_document("fns", "fns.sme.route")
    profile["operations"].clear()
    assert source_route("fns.sme").operations


def test_route_profile_references_require_metadata_schema_and_exact_identity():
    route = _route_document("fns", "fns.sme.route")
    for reference, code in (("fns.missing.metadata", "registry.profile_unknown"),
                            ("fns.sme.publication", "registry.route_profile_schema_invalid")):
        mutated = deepcopy(route)
        mutated["profiles"] = [reference]
        with pytest.raises(ValueError, match=code):
            decode_route(mutated, owner="fns")


def test_profile_metadata_has_one_canonical_record_per_exact_context():
    from stratbox.core.resources import iter_documents, resource_owners
    identities = []
    for owner in resource_owners():
        for declaration in iter_documents(owner, "profiles"):
            if declaration["schema"] == "stratbox.source-profile":
                identities.append((owner, json.dumps(declaration["declaration"], sort_keys=True)))
    assert len(identities) == len(set(identities))


def test_source_resource_filename_must_match_its_declared_identity(monkeypatch, tmp_path):
    from stratbox.domains.registry import declarations as sources
    document = source_documents("fns")[0]
    renamed = tmp_path / "SOURCE_other.yaml"
    renamed.write_text(json.dumps(document))
    monkeypatch.setattr(sources, "iter_resources", lambda owner, kind: (renamed,) if kind == "sources" else ())
    sources._sources.cache_clear()
    try:
        with pytest.raises(ValueError, match="registry.source_filename_mismatch"):
            source_documents("fns")
    finally:
        sources._sources.cache_clear()


def test_source_metadata_discovery_imports_no_domain_implementation():
    code = '''
import importlib.abc, sys
class RejectDomain(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith("stratbox.domains.") and not fullname.startswith("stratbox.domains.registry"):
            raise AssertionError("Source metadata imported a domain implementation: " + fullname)
sys.meta_path.insert(0, RejectDomain())
from stratbox.domains.registry.declarations import source_cards, source_route
assert sum(len(source_cards(owner)) for owner in ("cbr","fns","frank_rg","minfin","rosstat")) == 90
assert source_route("rosstat.short_term_indicators").profile_id
'''
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
        env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[3] / "src")))
    assert result.returncode == 0, result.stderr
