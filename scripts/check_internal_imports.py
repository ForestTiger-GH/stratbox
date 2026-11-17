"""Check canonical package owners, import directions and public importability.

No historical package-path exceptions are accepted. This check analyzes source
syntax without importing optional integrations, then imports selected public
surfaces to expose missing exports and circular initialization.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE = SRC / "stratbox"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DOMAINS = frozenset(
    path.name for path in (PACKAGE / "domains").iterdir()
    if path.is_dir() and not path.name.startswith("_")
    and (path / "__init__.py").is_file()
)
CRITICAL_MODULES = [
    "stratbox",
    "stratbox.core",
    "stratbox.core.runtime",
    "stratbox.core.runtime.providers",
    "stratbox.core.storage",
    "stratbox.core.storage.filestore",
    "stratbox.core.network",
    "stratbox.core.formats",
    "stratbox.core.formats.spreadsheets.dispatch",
    "stratbox.core.formats.spreadsheets.workbook_input",
    "stratbox.core.formats.archives",
    "stratbox.core.rendering.excel",
    "stratbox.core.execution",
    "stratbox.core.execution.catalog",
    "stratbox.core.execution.machine",
    "stratbox.core.operations.source.originals",
    "stratbox.core.observability",
    "stratbox.core.observability.journal.file_reader",
    "stratbox.core.observability.journal.file_writer",
    "stratbox.core.observability.journal.gate",
    "stratbox.core.observability.capture.sinks",
    "stratbox.core.observability.capture.file_sink",
    "stratbox.core.notifications",
    "stratbox.core.notifications.state.memory",
    "stratbox.core.notifications.dispatch.delivery",
    "stratbox.core.notifications.dispatch.reconciliation",
    "stratbox.core.registry",
    "stratbox.shared.data",
    "stratbox.shared.registries",
    "stratbox.shared.time",
    "stratbox.shared.text.banks",
    "stratbox.domains.registry",
    "stratbox.domains.cbr_file_collector",
    "stratbox.domains.cbr_industries",
    "stratbox.domains.cbr_industries.issuance_0104",
    "stratbox.domains.cbr_forms",
    "stratbox.domains.cbr_offices",
    "stratbox.domains.cbr_offices_reg",
    "stratbox.domains.cbr_sors_restoration",
    "stratbox.domains.escrow",
    "stratbox.domains.frg",
    "stratbox.domains.fns_sme",
    "stratbox.domains.fns_1yur",
]


def _imports(path: Path, tree: ast.AST):
    relative = path.relative_to(SRC).with_suffix("")
    package = ".".join(relative.parts if path.name == "__init__.py" else relative.parts[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            if node.level:
                try:
                    target = importlib.util.resolve_name(name, package)
                except (ImportError, ValueError):
                    yield node.lineno, "INVALID_RELATIVE_IMPORT"
                    continue
            else:
                target = node.module or ""
            yield node.lineno, target
            if target.startswith(("stratbox.core", "stratbox.shared", "stratbox.domains")):
                for alias in node.names:
                    yield node.lineno, f"{target}.{alias.name}"


def _owner(path: Path) -> str:
    parts = path.relative_to(PACKAGE).parts
    if len(parts) >= 2 and parts[0] == "domains":
        if parts[1] == "registry.py":
            return "domains.registry"
        if parts[1] in DOMAINS:
            return f"domain:{parts[1]}"
        return "domains.utility"
    if len(parts) >= 2 and parts[0] == "core":
        return f"core:{parts[1]}"
    if len(parts) >= 2 and parts[0] == "shared":
        return f"shared:{parts[1]}"
    return "package"


def _domain(target: str) -> str | None:
    parts = target.split(".")
    if len(parts) >= 3 and parts[:2] == ["stratbox", "domains"] and parts[2] in DOMAINS:
        return parts[2]
    return None


def check_dependency_direction() -> list[str]:
    failures: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        owner = _owner(path)
        source = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for line, target in _imports(path, source):
            prefix = f"{relative}:{line}"
            if target == "INVALID_RELATIVE_IMPORT":
                failures.append(f"{prefix}: invalid relative import")
                continue
            if target.startswith(("stratbox.system", "stratbox.core.base", "stratbox.core.ioapi")):
                failures.append(f"{prefix}: obsolete package import {target}")
            if target.startswith("stratbox_"):
                failures.append(f"{prefix}: concrete integration import {target}")
            if owner.startswith(("core:", "shared:")) and target.startswith("stratbox.domains"):
                failures.append(f"{prefix}: foundational package imports domain {target}")
            if owner.startswith("shared:") and target.startswith("stratbox.core"):
                failures.append(f"{prefix}: shared contracts depend on executable core {target}")
            if owner == "domains.registry" and _domain(target):
                failures.append(f"{prefix}: domain catalog depends on concrete domain {target}")
            target_domain = _domain(target)
            if owner.startswith("domain:") and target_domain is not None:
                source_domain = owner.split(":", 1)[1]
                if source_domain != target_domain and not (
                    source_domain == "cbr_sors_restoration" and target_domain == "cbr_industries"
                ):
                    failures.append(f"{prefix}: cross-domain import {target}")
            if owner == "core:execution" and target.startswith((
                "stratbox.core.operations", "stratbox.core.observability", "stratbox.core.notifications"
            )):
                failures.append(f"{prefix}: execution imports higher-level operation {target}")
            if owner == "core:observability" and target.startswith("stratbox.core.notifications"):
                failures.append(f"{prefix}: observability imports notifications {target}")
            if relative.startswith("core/observability/journal/") and target.startswith((
                "stratbox.core.observability.capture", "stratbox.core.observability.analysis",
                "stratbox.core.notifications",
            )):
                failures.append(f"{prefix}: journal imports consumer layer {target}")
            if (target.split(".")[0] in {"requests", "urllib3", "httpx", "aiohttp"}
                    or target.startswith("urllib.request")) and relative != "core/network/transport.py":
                failures.append(f"{prefix}: HTTP transport implementation outside core.network")
    return failures


def main() -> int:
    failures = check_dependency_direction()
    for name in CRITICAL_MODULES:
        try:
            importlib.import_module(name)
            print(f"OK   {name}")
        except Exception as error:
            failures.append(f"{name}: {type(error).__name__}: {error}")
    if (PACKAGE / "system").exists():
        failures.append("obsolete stratbox.system package remains")
    if failures:
        print("\nCore import and direction checks failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK   canonical core owners and dependency direction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
