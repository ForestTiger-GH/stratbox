"""Bank spelling and explicit alias policy are separate responsibilities."""

from __future__ import annotations

from io import StringIO

import pytest

from stratbox.shared.reference.assets import ReferenceError
from stratbox.shared.reference.banks.names import (
    normalize_bank_spelling, normalize_bank_name, resolve_bank_name,
)
from stratbox.shared.reference.banks import registry


def test_lexical_normalization_requires_no_packaged_dictionary():
    assert normalize_bank_spelling("Публичное акционерное общество Сбербанк") == "СБЕРБАНК"
    assert normalize_bank_spelling("СБЕРБАНК") == "СБЕРБАНК"
    assert normalize_bank_spelling(None) is None
    assert normalize_bank_name("СБЕРБАНК") == "СБЕРБАНК"
    assert normalize_bank_name("СБЕРБАНК", aliases={"СБЕРБАНК": "СБЕР"}) == "СБЕР"
    assert normalize_bank_name(["СБЕРБАНК", "ВТБ"], aliases={"СБЕРБАНК": "СБЕР"}) == ["СБЕР", "ВТБ"]


def test_bank_resolution_reports_explicit_alias():
    decision = resolve_bank_name("СБЕРБАНК", aliases={"СБЕРБАНК": "СБЕР"}, policy_content_id="fixture")
    assert decision.match_kind == "alias"
    assert decision.display_name == "СБЕР"
    assert decision.raw_name == "СБЕРБАНК"
    assert decision.policy_content_id == "fixture"
    assert resolve_bank_name("UNKNOWN", aliases={"СБЕРБАНК": "СБЕР"}).match_kind == "unmatched"
    assert resolve_bank_name("СБЕР", aliases={"СБЕРБАНК": "СБЕР"}).match_kind == "exact"


def test_default_bundled_bank_names_use_verified_aliases():
    assert registry.normalize_registered_bank("СБЕРБАНК") == "СБЕР"
    assert registry.normalize_registered_bank("ТИНЬКОФФ БАНК") == "ТБАНК"
    assert registry.normalize_registered_bank("БАНК 131") == "БАНК 131"
    assert registry.normalize_registered_bank("САНКТ-ПЕТЕРБУРГ") == "БАНК САНКТ-ПЕТЕРБУРГ"


def test_bank_registry_preserves_expected_columns_and_four_inputs():
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    inputs = []
    frame = registry.read(inputs=inputs)
    assert len(frame) > 100
    assert {"regn", "bank_name", "bank_name_norm", "is_canonical",
            "replacements_list", "replacements_json", "is_legacy"}.issubset(frame.columns)
    assert {r.role for r in inputs} == {"official_xlsx", "aliases", "default_selection", "legacy_selection"}
    assert len({r.content_basis for r in inputs}) == 1
    first = frame.iloc[0]
    assert registry.lookup(first["regn"]) is not None


def test_conflicting_bank_alias_is_rejected():
    class ConflictingBundle:
        def read(self, role, *, inputs=None):
            assert role == "aliases"
            return b"canon,alias\nFIRST,ALIAS\nSECOND,ALIAS\n"
    with pytest.raises(ReferenceError, match="Conflicting"):
        registry._aliases(ConflictingBundle())


def test_bank_reference_asset_provenance_and_traceable_name_policy():
    from stratbox.shared.reference.assets import load_reference
    bundle = load_reference("stratbox.shared.reference.banks")
    assert bundle.reference.publisher is None
    assert bundle.reference.curator == "Strategy Box"
    assert bundle.asset("official_xlsx").publisher == "Bank of Russia"
    assert bundle.asset("official_xlsx").origin_kind == "published_source"
    assert bundle.asset("aliases").origin_kind == "curated_policy"
    assert bundle.asset("default_selection").publisher is None
    receipts = []
    assert registry.normalize_registered_bank("СБЕРБАНК", inputs=receipts) == "СБЕР"
    assert [r.role for r in receipts] == ["aliases"]
    assert receipts[0].content_basis == bundle.snapshot_identity
    decision = registry.resolve_registered_bank("СБЕРБАНК", inputs=[])
    assert decision.reference_id == "reference.banks"
    assert decision.policy_snapshot_identity == bundle.snapshot_identity
    assert decision.match_kind == "alias"


def test_registered_bank_entity_is_distinct_from_display_name_policy():
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    receipts = []
    official = registry.read_official_registry(inputs=receipts)
    assert {x.role for x in receipts} == {"official_xlsx"}
    unique = official.loc[~official["regn"].duplicated(keep=False)]
    assert not unique.empty
    chosen = str(unique.iloc[0]["regn"])
    lookup_inputs = []
    result = registry.resolve_bank_entity(chosen, inputs=lookup_inputs)
    assert result.status == "matched"
    assert result.subject.namespace == "cbr.bank.registration"
    assert result.subject.id == chosen
    assert [r.role for r in lookup_inputs] == ["official_xlsx"]
    assert registry.resolve_bank_entity("unknown-registration").status == "unmatched"
