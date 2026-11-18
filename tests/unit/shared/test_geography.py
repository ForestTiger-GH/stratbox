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
        RegionNameRule("a", "Alpha", "Alpha", "example", "1", "subject", review_basis="fixture"),
        RegionNameRule("b", "Alpha", "Alpha", "example", "2", "subject", review_basis="fixture"),
    )
    decision = RegionNameResolver(rules=rules).resolve("Alpha")
    assert decision.status == "ambiguous"
    assert decision.subject is None
    assert len(decision.candidates) == 2
    only_2020 = RegionNameRule("historical", "Earlier", "Earlier", "example", "7",
                               "subject", effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31), review_basis="fixture")
    history = RegionNameResolver(rules=(only_2020,))
    assert history.resolve("Earlier").status == "out_of_scope"  # Date is required for dated rules.
    assert history.resolve("Earlier", context=RegionNameContext(as_of=date(2020, 6, 1))).status == "exact"
    assert history.resolve("Earlier", context=RegionNameContext(as_of=date(2026, 6, 1))).status == "out_of_scope"


def test_batch_matches_are_deterministic_and_preserve_raw_names():
    resolver = RegionNameResolver()
    decisions = resolver.resolve_many(["Россия", "Москва", "Московская область"])
    assert [decision.raw_name for decision in decisions] == ["Россия", "Москва", "Московская область"]
    assert [decision.status for decision in decisions] == ["alias", "alias", "exact"]
    assert decisions == resolver.resolve_many(["Россия", "Москва", "Московская область"])
    assert len({decision.reference_edition_id for decision in decisions}) == 1


def test_supplied_rules_have_distinct_digest_and_no_packaged_provenance():
    from stratbox.shared.reference.assets import ReferenceError
    a = RegionNameRule("alpha", "Alpha", "Alpha", "example", "a", "subject",
                       review_basis="fixture")
    b = RegionNameRule("alpha", "Alpha", "Alpha", "example", "b", "subject",
                       review_basis="fixture")
    left, right = RegionNameResolver(rules=(a,)), RegionNameResolver(rules=(b,))
    assert left.ruleset_identity != right.ruleset_identity
    assert left.resolve("Alpha").provenance == "supplied"
    assert left.resolve("Alpha").reference_id is None
    assert left.resolve("Alpha").reference_snapshot_identity is None
    assert left.resolve("Alpha").reference_edition_id != right.resolve("Alpha").reference_edition_id
    with pytest.raises(ReferenceError):
        RegionNameResolver(edition_id="reviewed-2026-11", rules=(a,))
    with pytest.raises(ReferenceError):
        RegionNameResolver(rules=(a, a))


def test_source_and_perimeter_rules_need_explicit_matching_context():
    source = RegionNameRule("source", "Delta", "Delta", "x", "d", "subject",
                            source_family="cbr", review_basis="fixture")
    perimeter = RegionNameRule("perimeter", "Echo", "Echo", "x", "e", "subject",
                               perimeter_id="p1", review_basis="fixture")
    resolver = RegionNameResolver(rules=(source, perimeter))
    assert resolver.resolve("Delta").status == "out_of_scope"
    assert resolver.resolve("Echo").status == "out_of_scope"
    assert resolver.resolve("Delta", context=RegionNameContext(source_family="fns")).status == "out_of_scope"
    assert resolver.resolve("Delta", context=RegionNameContext(source_family="cbr")).status == "exact"
    assert resolver.resolve("Echo", context=RegionNameContext(perimeter_hint="p1")).status == "exact"
    assert resolver.resolve("Echo", context=RegionNameContext(perimeter_hint="p2")).status == "out_of_scope"


def test_invalid_supplied_rule_cannot_bypass_packaged_validation():
    from stratbox.shared.reference.assets import ReferenceError
    invalid = RegionNameRule("r", "A", "A", "x", "1", "subject")
    with pytest.raises(ReferenceError, match="review basis"):
        RegionNameResolver(rules=(invalid,))
    unknown = RegionNameRule("r", "A", "A", "x", "1", "invented", review_basis="fixture")
    with pytest.raises(ReferenceError, match="kind"):
        RegionNameResolver(rules=(unknown,))
