"""Semantic ownership invariants independent of the number of future owners."""

from collections import defaultdict

from stratbox.domains.registry import domain_registration_inventory


def test_each_operation_owner_publishes_one_semantic_namespace():
    operation_namespaces: dict[str, set[str]] = defaultdict(set)
    namespace_owner: dict[str, str] = {}
    for owner, operation_id, version in domain_registration_inventory():
        assert version >= 1
        namespace, separator, verb = operation_id.rpartition(".")
        assert separator and namespace and verb
        operation_namespaces[owner].add(namespace)
        previous = namespace_owner.setdefault(namespace, owner)
        assert previous == owner, (namespace, previous, owner)
    assert operation_namespaces
    assert all(len(prefixes) == 1 for prefixes in operation_namespaces.values())


def test_industry_stock_and_flow_remain_distinct_publication_semantics():
    from stratbox.domains.cbr.corporate_lending.industries.debt_0105a import (
        operations as stock, schema as stock_schema,
    )
    from stratbox.domains.cbr.corporate_lending.industries.issuance_0104 import (
        operations as flow, parser as flow_parser, sources as flow_sources,
    )

    assert stock.PARSE.operation_id != flow.PARSE.operation_id
    assert stock.PARSE.value_type is not flow.PARSE.value_type
    assert {spec.measure for spec in stock_schema.CBR_0105A_DEBT_CORP_SHEET_SPECS} == {
        "debt", "overdue_debt",
    }
    assert len(stock_schema.CBR_0105A_DEBT_CORP_SHEET_SPECS) == 6
    assert {spec.measure for spec in flow_parser._SHEETS} == {"new_loans"}
    assert len(flow_parser._SHEETS) == 3
    assert flow_sources.reference_period("2027-01-01") == "2026-12"
    assert flow_sources.reference_period("2026-08-01") == "2026-07"


def test_registry_matches_its_physical_semantic_owners():
    from stratbox.domains._structure import discover_operation_owners
    from importlib import resources

    registered = {owner for owner, _, _ in domain_registration_inventory()}
    physical = set(discover_operation_owners(resources.files("stratbox.domains")))
    assert registered == physical
