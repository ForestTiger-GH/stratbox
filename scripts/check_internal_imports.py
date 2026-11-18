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

def _registered_domains() -> frozenset[str]:
    """Resolve manifest owners by full relative package path, regardless of depth."""
    root = PACKAGE / "domains"
    if not root.is_dir():
        return frozenset()
    return frozenset(
        ".".join(manifest.parent.relative_to(root).parts)
        for manifest in root.rglob("_registration.py")
        if (manifest.parent / "__init__.py").is_file()
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
    "stratbox.shared.identity",
    "stratbox.shared.evidence",
    "stratbox.shared.data.datasets",
    "stratbox.shared.reference",
    "stratbox.shared.reference.assets",
    "stratbox.shared.reference.banks.names",
    "stratbox.shared.reference.banks.registry",
    "stratbox.shared.reference.okved2.registry",
    "stratbox.shared.reference.geography",
    "stratbox.shared.time",
    "stratbox.domains.registry",
    "stratbox.domains.cbr.file_collection",
    "stratbox.domains.cbr.corporate_lending.industries",
    "stratbox.domains.cbr.corporate_lending.industries.issuance_0104",
    "stratbox.domains.cbr.reporting_forms",
    "stratbox.domains.cbr.service_network.bank_offices",
    "stratbox.domains.cbr.service_network.territorial_offices",
    "stratbox.domains.cbr.corporate_lending.sors_restoration",
    "stratbox.domains.cbr.escrow",
    "stratbox.domains.frank_rg.retail_banking",
    "stratbox.domains.fns.sme_register",
    "stratbox.domains.fns.legal_entities_1yur",
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


def _owner(path: Path, owners: frozenset[str]) -> str:
    parts = path.relative_to(PACKAGE).parts
    if len(parts) >= 2 and parts[0] == "domains":
        if parts[1] == "registry.py":
            return "domains.registry"
        package = ".".join(parts[1:-1])
        candidates = (name for name in owners if package == name or package.startswith(name + "."))
        nearest = max(candidates, key=lambda item: len(item.split(".")), default=None)
        return f"domain:{nearest}" if nearest else "domains.utility"
    if len(parts) >= 2 and parts[0] == "core":
        return f"core:{parts[1]}"
    if len(parts) >= 2 and parts[0] == "shared":
        return f"shared:{Path(parts[1]).stem if parts[1].endswith('.py') else parts[1]}"
    return "package"


def _domain(target: str, owners: frozenset[str]) -> str | None:
    prefix = "stratbox.domains."
    if not target.startswith(prefix):
        return None
    subpath = target[len(prefix):]
    candidates = (item for item in owners if subpath == item or subpath.startswith(item + "."))
    return max(candidates, key=lambda item: len(item.split(".")), default=None)


def _publisher(target: str, owners: frozenset[str]) -> str | None:
    parts = target.split(".")
    if len(parts) < 3 or parts[:2] != ["stratbox", "domains"]:
        return None
    publishers = {owner.split(".", 1)[0] for owner in owners}
    return parts[2] if parts[2] in publishers else None


def check_dependency_direction() -> list[str]:
    failures: list[str] = []
    owners = _registered_domains()
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        owner = _owner(path, owners)
        source = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for line, target in _imports(path, source):
            prefix = f"{relative}:{line}"
            if target == "INVALID_RELATIVE_IMPORT":
                failures.append(f"{prefix}: invalid relative import")
                continue
            if target.startswith(("stratbox.system", "stratbox.core.base", "stratbox.core.ioapi")):
                failures.append(f"{prefix}: obsolete package import {target}")
            if target.startswith((
                "stratbox.shared.registries", "stratbox.shared.text",
                "stratbox.shared.data.evidence", "stratbox.shared.data.identity",
            )):
                failures.append(f"{prefix}: obsolete shared import {target}")
            if owner == "shared:identity" and target.startswith(("stratbox.shared.evidence", "stratbox.shared.data", "stratbox.shared.reference")):
                failures.append(f"{prefix}: identity imports higher-level shared semantic owner {target}")
            if owner == "shared:evidence" and target.startswith(("stratbox.shared.data", "stratbox.shared.reference")):
                failures.append(f"{prefix}: evidence imports higher-level shared semantic owner {target}")
            if owner == "shared:data" and target.startswith("stratbox.shared.reference"):
                failures.append(f"{prefix}: shared data imports a concrete reference owner {target}")
            if target.startswith("stratbox_"):
                failures.append(f"{prefix}: concrete integration import {target}")
            if target in {"stratbox.shared.data.ByteIdentity", "stratbox.shared.data.canonical_manifest_bytes", "stratbox.shared.data.SourcePayload", "stratbox.shared.data.AcquisitionReceipt", "stratbox.shared.data.AcquiredSource", "stratbox.shared.data.UsedInputReceipt", "stratbox.shared.data.StoredBytesReceipt", "stratbox.shared.data.MaterialReference", "stratbox.shared.data.PublicationReceipt"}:
                failures.append(f"{prefix}: shared data re-exports a moved foundational type {target}")
            if owner.startswith(("core:", "shared:")) and target.startswith("stratbox.domains"):
                failures.append(f"{prefix}: foundational package imports domain {target}")
            if owner.startswith("shared:") and target.startswith("stratbox.core"):
                failures.append(f"{prefix}: shared contracts depend on executable core {target}")
            if owner == "domains.registry" and _domain(target, owners):
                failures.append(f"{prefix}: domain catalog depends on concrete domain {target}")
            target_domain = _domain(target, owners)
            if owner.startswith("domain:"):
                source_domain = owner.split(":", 1)[1]
                source_publisher = source_domain.split(".", 1)[0]
                target_publisher = _publisher(target, owners)
                if target_publisher is not None and source_publisher != target_publisher:
                    failures.append(f"{prefix}: cross-source import {target}")
                elif target_domain is not None and source_domain != target_domain:
                    # A child series uses the owning parent's shared parsing/model rules.
                    parent_dependency = source_domain.startswith(target_domain + ".")
                    # SORS reuses the exact official 01_05_A parser and geography schema.
                    sors_dependency = (
                        source_domain == "cbr.corporate_lending.sors_restoration"
                        and target_domain == "cbr.corporate_lending.industries"
                    )
                    if not (parent_dependency or sors_dependency):
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


def check_supporting_source_imports() -> list[str]:
    """Check examples, tests, benchmarks and scripts for stale public imports."""
    failures: list[str] = []
    forbidden = (
        "stratbox.shared.registries", "stratbox.shared.text",
        "stratbox.shared.data.evidence", "stratbox.shared.data.identity",
        "stratbox.system", "stratbox.core.base", "stratbox.core.ioapi",
    )
    migrated_symbols = frozenset({
        "ByteIdentity", "canonical_manifest_bytes", "SourcePayload",
        "AcquisitionReceipt", "AcquiredSource", "UsedInputReceipt",
        "StoredBytesReceipt", "MaterialReference", "PublicationReceipt",
    })
    for folder in ("tests", "examples", "scripts", "benchmarks"):
        directory = ROOT / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            file_label = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=file_label)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    imported = (node.module or "",)
                    if node.module == "stratbox.shared.data" and any(
                        alias.name in migrated_symbols for alias in node.names
                    ):
                        failures.append(f"{file_label}:{node.lineno}: moved symbol imported from shared.data")
                else:
                    continue
                if any(value.startswith(forbidden) for value in imported):
                    failures.append(f"{file_label}:{node.lineno}: obsolete package import {imported}")
    return failures


def main() -> int:
    failures = check_dependency_direction()
    failures.extend(check_supporting_source_imports())
    for name in CRITICAL_MODULES:
        try:
            importlib.import_module(name)
            print(f"OK   {name}")
        except Exception as error:
            failures.append(f"{name}: {type(error).__name__}: {error}")
    for obsolete in ("registries", "text"):
        if (PACKAGE / "shared" / obsolete).exists():
            failures.append(f"obsolete shared package remains: {obsolete}")
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
