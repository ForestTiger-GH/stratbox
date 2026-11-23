"""Semantic ownership invariants independent of the number of future owners."""

from collections import defaultdict

from stratbox.domains.registry import domain_registration_inventory


def test_semantic_namespaces_have_one_publisher_owner():
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
    assert "cbr" in operation_namespaces
    assert len(operation_namespaces["cbr"]) > 1
    assert all(owner == "cbr" for namespace, owner in namespace_owner.items() if namespace.startswith("cbr."))


def test_industry_stock_and_flow_remain_distinct_publication_semantics():
    import stratbox.domains.cbr.operations.corporate_lending.debt.operations as stock
    import stratbox.domains.cbr.tables.corporate_lending.debt.schema as stock_schema
    import stratbox.domains.cbr.operations.corporate_lending.issuance.operations as flow
    import stratbox.domains.cbr.tables.corporate_lending.issuance.parser as flow_parser
    import stratbox.domains.cbr.publications.corporate_lending.issuance_editions as flow_editions

    assert stock.PARSE.operation_id != flow.PARSE.operation_id
    assert stock.PARSE.value_type is not flow.PARSE.value_type
    assert {spec.measure for spec in stock_schema.CBR_0105A_DEBT_CORP_SHEET_SPECS} == {
        "debt", "overdue_debt",
    }
    assert len(stock_schema.CBR_0105A_DEBT_CORP_SHEET_SPECS) == 6
    assert {spec.measure for spec in flow_parser._SHEETS} == {"new_loans"}
    assert len(flow_parser._SHEETS) == 3
    assert flow_editions.reference_period("2027-01-01") == "2026-12"
    assert flow_editions.reference_period("2026-08-01") == "2026-07"


def test_registry_matches_its_physical_semantic_owners():
    from stratbox.domains._structure import discover_operation_owners
    from importlib import resources

    registered = {owner for owner, _, _ in domain_registration_inventory()}
    physical = set(discover_operation_owners(resources.files("stratbox.domains")))
    assert registered == physical
