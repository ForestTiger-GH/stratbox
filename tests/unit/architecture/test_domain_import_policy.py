"""Boundary-checker regression tests for nested domains and removed API paths."""

from pathlib import Path
import runpy


def _checker(tmp_path):
    root = Path(__file__).resolve().parents[3]
    code = runpy.run_path(str(root / "scripts/check_internal_imports.py"))
    globals_ = code["check_dependency_direction"].__globals__
    local_src = tmp_path / "src"
    local_domain = local_src / "stratbox" / "domains"
    local_domain.mkdir(parents=True)
    (local_domain / "__init__.py").write_text("", encoding="utf-8")
    globals_["ROOT"] = tmp_path
    globals_["SRC"] = local_src
    globals_["PACKAGE"] = local_src / "stratbox"
    return code, local_domain


def _package(domain, name, *, manifest=False):
    current = domain
    for part in name.split("/"):
        current = current / part
        current.mkdir(exist_ok=True)
        (current / "__init__.py").write_text("", encoding="utf-8")
    if manifest:
        (current / "_registration.py").write_text("", encoding="utf-8")
    return current


def test_source_grouping_helpers_obey_publisher_boundaries(tmp_path):
    checker, domains = _checker(tmp_path)
    cbr = _package(domains, "cbr")
    _package(domains, "fns/sme_register", manifest=True)
    (cbr / "_source.py").write_text(
        "from stratbox.domains.fns.sme_register import operations\n",
        encoding="utf-8",
    )
    problems = checker["check_dependency_direction"]()
    assert any("cross-source import" in problem for problem in problems)


def test_distinct_owners_cannot_import_implementations(tmp_path):
    checker, domains = _checker(tmp_path)
    source = _package(domains, "cbr/escrow", manifest=True)
    _package(domains, "cbr/reporting_forms", manifest=True)
    (source / "bad.py").write_text(
        "from stratbox.domains.cbr.reporting_forms import operations\n",
        encoding="utf-8",
    )
    assert any("cross-domain import" in x for x in checker["check_dependency_direction"]())


def test_legacy_domain_imports_and_dynamic_targets_are_rejected(tmp_path):
    checker, domains = _checker(tmp_path)
    source = _package(domains, "cbr/escrow", manifest=True)
    (source / "bad.py").write_text(
        "import importlib\n"
        "from stratbox.domains import cbr_offices\n"
        "importlib.import_module('stratbox.domains.cbr_industries.operations')\n"
        "from stratbox.core.execution.catalog import OperationRef\n"
        "ref = OperationRef('test.x', 1, "
        "'stratbox.domains.frg.api:SCAN', 'stratbox.domains.frg.api:scan')\n",
        encoding="utf-8",
    )
    errors = checker["check_dependency_direction"]()
    assert sum("obsolete domain import" in issue for issue in errors) >= 3


def test_legacy_domain_imports_in_examples_are_rejected(tmp_path):
    checker, domains = _checker(tmp_path)
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "bad.py").write_text(
        "from stratbox.domains import fns_sme\n"
        "from importlib import import_module\n"
        "import_module('stratbox.domains.cbr_offices.operations')\n",
        encoding="utf-8",
    )
    errors = checker["check_supporting_source_imports"]()
    assert sum("obsolete" in issue for issue in errors) >= 2


def test_new_source_group_and_child_are_discovered_without_changes(tmp_path):
    checker, domains = _checker(tmp_path)
    owner = _package(domains, "new_publisher/family/series", manifest=True)
    (owner / "logic.py").write_text(
        "from stratbox.domains.new_publisher.family import common\n",
        encoding="utf-8",
    )
    assert checker["check_dependency_direction"]() == []


def test_invalid_intermediate_folder_fails_import_checker(tmp_path):
    checker, domains = _checker(tmp_path)
    series = domains / "cbr/family/series"
    series.mkdir(parents=True)
    (domains / "cbr" / "__init__.py").write_text("", encoding="utf-8")
    (series / "__init__.py").write_text("", encoding="utf-8")
    (series / "_registration.py").write_text("", encoding="utf-8")
    assert any("unreachable_manifest" in x for x in checker["check_dependency_direction"]())


def test_sors_only_imports_published_debt_parser_schema(tmp_path):
    checker, domains = _checker(tmp_path)
    sors = _package(domains, "cbr/corporate_lending/sors_restoration", manifest=True)
    _package(domains, "cbr/corporate_lending/industries/debt_0105a", manifest=True)
    (sors / "allowed.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.parser "
        "import parse_cbr_0105a_debt_corp_excel_bytes\n",
        encoding="utf-8",
    )
    assert checker["check_dependency_direction"]() == []
    (sors / "forbidden.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries.debt_0105a "
        "import operations\n",
        encoding="utf-8",
    )
    assert any("cross-domain import" in x for x in checker["check_dependency_direction"]())


def test_issuance_cannot_import_debt_operation_implementation(tmp_path):
    checker, domains = _checker(tmp_path)
    debt = _package(domains, "cbr/corporate_lending/industries/debt_0105a", manifest=True)
    flow = _package(domains, "cbr/corporate_lending/industries/issuance_0104", manifest=True)
    (flow / "allowed.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries.debt_0105a "
        "import schema\n",
        encoding="utf-8",
    )
    assert checker["check_dependency_direction"]() == []
    (flow / "forbidden.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries.debt_0105a "
        "import operations\n",
        encoding="utf-8",
    )
    assert any("cross-domain import" in x for x in checker["check_dependency_direction"]())

def test_issuance_cannot_import_stock_private_export_or_selection(tmp_path):
    checker, domains = _checker(tmp_path)
    flow = _package(domains, "cbr/corporate_lending/industries/issuance_0104", manifest=True)
    _package(domains, "cbr/corporate_lending/industries/debt_0105a", manifest=True)
    (flow / "bad.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries.debt_0105a "
        "import export, selection\n",
        encoding="utf-8",
    )
    problems = checker["check_dependency_direction"]()
    assert any("cross-domain import" in message and "export" in message for message in problems)
    assert any("cross-domain import" in message and "selection" in message for message in problems)
