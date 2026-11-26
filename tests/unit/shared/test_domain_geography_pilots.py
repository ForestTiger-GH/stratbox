"""Domain-specific source keys remain intact in read-only geography projections."""

from __future__ import annotations

import pytest

from stratbox.shared.reference.geography import RegionNameResolver


def inspect_region_names(rows):
    resolver = RegionNameResolver()
    return tuple((code, resolver.resolve(row[1])) for code, row in sorted(rows.items()))
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.geography import normalize_cbr_0105a_region_name


def test_fns_names_annotate_without_rekeying_source_data():
    source = {"77": ("77", "Москва", "100"), "50": ("50", "Московская область", "200")}
    before = dict(source)
    decisions = inspect_region_names(source)
    assert source == before
    assert [code for code, _ in decisions] == ["50", "77"]
    assert {decision.subject.id for _, decision in decisions} == {"RU-MOW", "RU-MOS"}
    assert source["77"][0] == "77"  # An FNS publisher code is not ISO.


def test_cbr_series_name_key_uses_common_lexical_normalizer():
    assert normalize_cbr_0105a_region_name("  Кемеровская область  ") == "кемеровская область"
    assert normalize_cbr_0105a_region_name("Тюменская область без данных по ХМАО") != (
        normalize_cbr_0105a_region_name("Тюменская область"))


def test_escrow_diagnostics_preserve_original_parsed_row_objects():
    pytest.importorskip("pandas")
    from stratbox.shared.reference.geography import RegionNameResolver
    from types import SimpleNamespace
    rows = [SimpleNamespace(entity_name="г. Москва", row_kind="region"),
            SimpleNamespace(entity_name="Итого по РФ", row_kind="country_total")]
    resolver = RegionNameResolver()
    diagnostics = tuple((row, resolver.resolve(row.entity_name)) for row in rows if row.row_kind == "region")
    assert len(diagnostics) == 1
    assert diagnostics[0][0] is rows[0]
    assert diagnostics[0][1].subject.id == "RU-MOW"
