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
    decision = resolve_bank_name("СБЕРБАНК", aliases={"СБЕРБАНК": "СБЕР"}, policy_edition_id="fixture")
    assert decision.match_kind == "alias"
    assert decision.display_name == "СБЕР"
    assert decision.raw_name == "СБЕРБАНК"
    assert decision.policy_edition_id == "fixture"


def test_default_bundled_bank_names_use_verified_aliases():
    assert registry.normalize_registered_bank("СБЕРБАНК") == "СБЕР"
    assert registry.normalize_registered_bank("ТИНЬКОФФ БАНК") == "ТБАНК"


def test_bank_registry_preserves_expected_columns_and_four_inputs():
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    inputs = []
    frame = registry.read(inputs=inputs)
    assert len(frame) > 100
    assert {"regn", "bank_name", "bank_name_norm", "is_canonical",
            "replacements_list", "replacements_json", "is_legacy"}.issubset(frame.columns)
    assert {r.role for r in inputs} == {"official_xlsx", "aliases", "default_selection", "legacy_selection"}
    assert len({r.version for r in inputs}) == 1
    first = frame.iloc[0]
    assert registry.lookup(first["regn"]) is not None


def test_conflicting_bank_alias_is_rejected():
    class ConflictingBundle:
        def read(self, role, *, inputs=None):
            assert role == "aliases"
            return b"canon,alias\nFIRST,ALIAS\nSECOND,ALIAS\n"
    with pytest.raises(ReferenceError, match="Conflicting"):
        registry._aliases(ConflictingBundle())
