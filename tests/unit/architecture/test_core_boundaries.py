"""Regression tests for canonical semantic ownership of the core package."""

from __future__ import annotations

import importlib
import importlib.util
import ast
import runpy
from pathlib import Path

import pytest


def test_historical_system_package_is_absent():
    import stratbox.core
    assert importlib.util.find_spec("stratbox.system") is None
    assert importlib.util.find_spec("stratbox.core.base") is None
    assert importlib.util.find_spec("stratbox.core.ioapi") is None


def test_semantic_owners_export_concrete_implementations():
    from stratbox.core.observability import (
        FileJournalReader, FileJournalWriter, BufferedFileJournal,
        RequiredJournalGate, FileEventSink, ObserverGenerationSnapshot,
        JournalWriteReceipt, PersistencePolicy, PresentationPolicy,
        export_projection_csv,
    )
    from stratbox.core.notifications import (
        MemoryNotificationState, DeliveryResult, RetryPolicy, flush_audit,
    )
    expected = {
        FileJournalReader: "stratbox.core.observability.journal.file_reader",
        FileJournalWriter: "stratbox.core.observability.journal.file_writer",
        BufferedFileJournal: "stratbox.core.observability.journal.buffered",
        RequiredJournalGate: "stratbox.core.observability.journal.gate",
        FileEventSink: "stratbox.core.observability.capture.file_sink",
        ObserverGenerationSnapshot: "stratbox.core.observability.assessment.generation",
        JournalWriteReceipt: "stratbox.core.observability.journal.contracts",
        PersistencePolicy: "stratbox.core.observability.journal.policies",
        PresentationPolicy: "stratbox.core.observability.analysis.policies",
        MemoryNotificationState: "stratbox.core.notifications.state.memory",
        DeliveryResult: "stratbox.core.notifications.dispatch.contracts",
        RetryPolicy: "stratbox.core.notifications.dispatch.contracts",
    }
    for definition, module in expected.items():
        assert definition.__module__ == module
        assert getattr(importlib.import_module(module), definition.__name__) is definition
    assert export_projection_csv.__module__ == "stratbox.core.observability.analysis.exports"
    assert flush_audit.__module__ == "stratbox.core.notifications.state.audit"


def test_static_checker_rejects_forbidden_core_imports(tmp_path):
    root = Path(__file__).resolve().parents[3]
    checker = runpy.run_path(str(root / "scripts" / "check_internal_imports.py"))
    check = checker["check_dependency_direction"]
    src = tmp_path / "src"
    journal = src / "stratbox" / "core" / "observability" / "journal"
    operation = src / "stratbox" / "core" / "operations"
    journal.mkdir(parents=True)
    operation.mkdir(parents=True)
    (journal / "bad.py").write_text(
        "from stratbox.core.notifications.state import StateMutation\n", encoding="utf-8"
    )
    (operation / "bad.py").write_text(
        "from stratbox.domains.cbr.escrow import operations\n", encoding="utf-8"
    )
    check.__globals__["SRC"] = src
    check.__globals__["PACKAGE"] = src / "stratbox"
    failures = check()
    assert any("journal imports consumer layer" in error for error in failures)
    assert any("foundational package imports domain" in error for error in failures)


def test_core_catalog_preserves_logical_operations():
    from stratbox.core.registry import core_catalog
    from stratbox.domains.registry import operation_catalog

    core = core_catalog()
    all_ops = operation_catalog()
    assert set(core.references).issubset(set(all_ops.references))
    assert {(ref.operation_id, ref.contract_version) for ref in core.references} >= {
        ("source.receive_original", 1),
        ("source.save_original", 1),
        ("source.receive_to_store", 1),
        ("source.read_original", 1),
        ("source.reconcile_original", 1),
        ("notifications.prepare", 3),
        ("notifications.deliver", 3),
        ("notifications.qualify", 3),
        ("notifications.reconcile", 2),
    }


@pytest.mark.parametrize("module", [
    "stratbox.core.runtime.providers",
    "stratbox.core.storage.bytes",
    "stratbox.core.formats.spreadsheets.workbook_input",
    "stratbox.core.formats.archives.members",
    "stratbox.core.rendering.excel",
    "stratbox.core.execution.catalog",
    "stratbox.core.observability.journal.file_reader",
    "stratbox.core.observability.analysis.exports",
    "stratbox.core.notifications.dispatch.intents",
    "stratbox.core.notifications.dispatch.reconciliation",
])
def test_new_semantic_module_imports(module):
    assert importlib.import_module(module) is not None


def test_all_live_python_imports_use_canonical_core_paths():
    root = Path(__file__).resolve().parents[3]
    obsolete = ("stratbox.system", "stratbox.core.base", "stratbox.core.ioapi")
    bad = []
    for section in ("src", "tests", "examples", "scripts", "benchmarks"):
        folder = root / section
        if not folder.exists():
            continue
        for source in folder.rglob("*.py"):
            syntax = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(syntax):
                if isinstance(node, ast.Import):
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported = [node.module] if node.module and node.level == 0 else []
                else:
                    continue
                bad.extend(
                    f"{source.relative_to(root)}:{node.lineno} {name}"
                    for name in imported
                    if any(name == old or name.startswith(old + ".") for old in obsolete)
                )
    assert not bad, "\\n".join(bad)


def test_builtin_transport_evidence_identifiers_are_stable():
    from stratbox.core.network import RequestsTransport, RoutedTransport, PeerBoundTransport
    from stratbox.core.operations.source.acquisition import _transport_identity

    assert _transport_identity(RequestsTransport()) == "http.requests.v1"
    assert _transport_identity(object.__new__(RoutedTransport)) == "http.routed.v1"
    assert _transport_identity(object.__new__(PeerBoundTransport)) == "http.peer_bound.v1"


def test_shared_owner_boundaries_reject_wrong_direction_and_old_paths(tmp_path):
    root = Path(__file__).resolve().parents[3]
    checker = runpy.run_path(str(root / "scripts" / "check_internal_imports.py"))
    src = tmp_path / "src"
    shared = src / "stratbox" / "shared"
    data = shared / "data"
    shared.mkdir(parents=True)
    data.mkdir()
    (shared / "identity.py").write_text(
        "from stratbox.shared.reference import assets\n", encoding="utf-8"
    )
    (data / "bad.py").write_text(
        "from stratbox.shared.reference.banks import registry\n", encoding="utf-8"
    )
    check = checker["check_dependency_direction"]
    check.__globals__["SRC"] = src
    check.__globals__["PACKAGE"] = src / "stratbox"
    failures = check()
    assert any("identity imports higher-level" in failure for failure in failures)
    assert any("shared data imports" in failure for failure in failures)


def test_external_source_scanner_rejects_moved_imports(tmp_path):
    root = Path(__file__).resolve().parents[3]
    checker = runpy.run_path(str(root / "scripts" / "check_internal_imports.py"))
    test_file = tmp_path / "tests" / "test_old.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("from stratbox.shared.data import ByteIdentity\n", encoding="utf-8")
    check = checker["check_supporting_source_imports"]
    check.__globals__["ROOT"] = tmp_path
    assert any("moved symbol" in failure for failure in check())


def test_nested_domain_analyzer_preserves_owner_and_publisher_isolation(tmp_path):
    """Nested business owners are not collapsed into a single CBR namespace."""
    root = Path(__file__).resolve().parents[3]
    checker = runpy.run_path(str(root / "scripts" / "check_internal_imports.py"))
    check = checker["check_dependency_direction"]
    source = tmp_path / "src"
    package = source / "stratbox"

    def owner(path: str):
        directory = package / "domains" / path
        directory.mkdir(parents=True)
        current = directory
        while current != package / "domains":
            (current / "__init__.py").write_text("", encoding="utf-8")
            current = current.parent
        (directory / "_registration.py").write_text("", encoding="utf-8")
        return directory

    (package / "domains" / "__init__.py").write_text("", encoding="utf-8")
    escrow = owner("cbr/escrow")
    owner("cbr/reporting_forms")
    owner("fns/sme_register")
    sors = owner("cbr/corporate_lending/sors_restoration")
    owner("cbr/corporate_lending/industries")

    (escrow / "bad.py").write_text(
        "from stratbox.domains.cbr.reporting_forms import contracts\n"
        "from stratbox.domains.fns.sme_register import operations\n",
        encoding="utf-8",
    )
    (sors / "allowed.py").write_text(
        "from stratbox.domains.cbr.corporate_lending.industries import schema\n",
        encoding="utf-8",
    )
    check.__globals__["SRC"] = source
    check.__globals__["PACKAGE"] = package
    failures = check()
    assert sum("cross-domain import" in message for message in failures) >= 1
    assert sum("cross-source import" in message for message in failures) >= 1
    assert not any("allowed.py" in message for message in failures)
