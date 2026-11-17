"""Regression tests for canonical semantic ownership of the core package."""

from __future__ import annotations

import importlib
import importlib.util
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
        "from stratbox.domains.escrow import operations\n", encoding="utf-8"
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
    assert len(core.references) == 9
    assert len(all_ops.references) == 77
    assert {(ref.operation_id, ref.contract_version) for ref in core.references} == {
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
