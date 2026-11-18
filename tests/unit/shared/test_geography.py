"""Territory-name matching never implies an unverified statistical perimeter."""

from __future__ import annotations

from datetime import date

import pytest

from stratbox.shared.reference.geography import (
    RegionNameContext, RegionNameResolver, RegionNameRule, normalize_region_label,
)


def test_lexical_normalizer_is_idempotent_and_retains_qualifiers():
    raw = "  Ханты-Мансийский  автономный округ — Югра  "
    result = normalize_region_label(raw)
    assert result == normalize_region_label(result)
    assert "югра" in result
    assert normalize_region_label("Тюменская область без данных по ХМАО") != (
        normalize_region_label("Тюменская область"))
    assert normalize_region_label(None) is None
    with pytest.raises(TypeError):
        normalize_region_label(42)


def test_city_and_oblast_or_republic_and_krai_never_collapse():
    resolver = RegionNameResolver()
    city = resolver.resolve("город Москва")
    oblast = resolver.resolve("Московская область")
    assert city.status == "alias"
    assert oblast.status == "exact"
    assert city.subject.id == "RU-MOW"
    assert oblast.subject.id == "RU-MOS"
    assert city.subject != oblast.subject
    assert resolver.resolve("Республика Алтай").subject != resolver.resolve("Алтайский край").subject
    assert resolver.resolve("Алтай").status == "unmatched"


def test_unverified_aggregations_and_legacy_compositions_are_not_guessed():
    resolver = RegionNameResolver()
    assert resolver.resolve("Тюменская область без данных по автономным округам").status == "unmatched"
    assert resolver.resolve("Ханты-Мансийский автономный округ — Югра").subject.id == "RU-KHM"
    assert resolver.resolve("Ханты-Мансийский автономный округ — Югра").perimeter_id is None
    assert resolver.resolve("Ненецкий автономный округ").subject.id != (
        resolver.resolve("Архангельская область").subject.id)


def test_namespace_qualified_code_and_name_must_agree():
    resolver = RegionNameResolver()
    agreed = RegionNameContext(source_code="RU-MOW", code_namespace="iso3166-2", observed_kind="subject")
    wrong = RegionNameContext(source_code="RU-MOS", code_namespace="iso3166-2", observed_kind="subject")
    assert resolver.resolve("Москва", context=agreed).subject.id == "RU-MOW"
    mismatch = resolver.resolve("Москва", context=wrong)
    assert mismatch.status == "out_of_scope"
    assert mismatch.subject is None
    assert resolver.resolve("Москва", context=RegionNameContext(
        source_code="77", code_namespace="fns.ssrf")).subject is None
    with pytest.raises(ValueError, match="namespace"):
        RegionNameContext(source_code="RU-MOW")


def test_ambiguous_alias_and_time_scope_are_explicit():
    rules = (
        RegionNameRule("a", "Alpha", "Alpha", "example", "1", "subject"),
        RegionNameRule("b", "Alpha", "Alpha", "example", "2", "subject"),
    )
    decision = RegionNameResolver(rules=rules).resolve("Alpha")
    assert decision.status == "ambiguous"
    assert decision.subject is None
    assert len(decision.candidates) == 2
    only_2020 = RegionNameRule("historical", "Earlier", "Earlier", "example", "7",
                               "subject", effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31))
    history = RegionNameResolver(rules=(only_2020,))
    assert history.resolve("Earlier", context=RegionNameContext(as_of=date(2020, 6, 1))).status == "exact"
    assert history.resolve("Earlier", context=RegionNameContext(as_of=date(2026, 6, 1))).status == "out_of_scope"


def test_batch_matches_are_deterministic_and_preserve_raw_names():
    resolver = RegionNameResolver()
    decisions = resolver.resolve_many(["Россия", "Москва", "Московская область"])
    assert [decision.raw_name for decision in decisions] == ["Россия", "Москва", "Московская область"]
    assert [decision.status for decision in decisions] == ["alias", "alias", "exact"]
    assert decisions == resolver.resolve_many(["Россия", "Москва", "Московская область"])
    assert len({decision.reference_edition_id for decision in decisions}) == 1
