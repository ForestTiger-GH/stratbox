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

from stratbox.domains._structure import DomainLayoutError, discover_operation_owners  # noqa: E402

def _registered_domains() -> frozenset[str]:
    """Resolve manifest owners by full relative package path, regardless of depth."""
    root = PACKAGE / "domains"
    if not root.is_dir():
        return frozenset()
    return frozenset(discover_operation_owners(root))


# These names are invalid even when a stale import would not be resolved at runtime.
LEGACY_DOMAIN_PACKAGES = frozenset({
    "cbr_file_collector", "cbr_forms", "cbr_industries", "cbr_offices",
    "cbr_offices_reg", "cbr_sors_restoration", "escrow",
    "fns_1yur", "fns_sme", "frg", "_cbr",
})


def _is_legacy_domain_path(module: str) -> bool:
    prefix = "stratbox.domains."
    if not module.startswith(prefix):
        return False
    part = module[len(prefix):].split(".", 1)[0]
    return part in LEGACY_DOMAIN_PACKAGES


def _literal_module_refs(tree: ast.AST):
    """Find importlib imports and explicit declaration links without guessing strings."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        operation = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else ""
        )
        if operation in {"import_module", "__import__"} and node.args:
            literal = node.args[0]
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                yield node.lineno, literal.value
        if operation == "OperationRef":
            values = (*node.args[2:6], *(
                keyword.value for keyword in node.keywords
                if keyword.arg in {"definition_ref", "handler_ref", "wire_codec_ref", "wire_contract_ref"}
            ))
            for value in values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    yield node.lineno, value.value.split(":", 1)[0]


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
    "stratbox.core.execution.handoff",
    "stratbox.core.operations.materials.operations",
    "stratbox.core.operations.materials.archive",
    "stratbox.core.storage.datasets",
    "stratbox.core.storage.datasets.operations",
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
    "stratbox.shared.data.snapshots",
    "stratbox.shared.materials",
    "stratbox.shared.reference",
    "stratbox.shared.reference.assets",
    "stratbox.shared.reference.banks.names",
    "stratbox.shared.reference.banks.registry",
    "stratbox.shared.reference.okved2.registry",
    "stratbox.shared.reference.geography",
    "stratbox.shared.time",
    "stratbox.domains.registry",
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
            if target.startswith(("stratbox.core", "stratbox.shared", "stratbox.domains")) and all(
                alias.name != "*" for alias in node.names
            ):
                for alias in node.names:
                    yield node.lineno, f"{target}.{alias.name}"
            else:
                yield node.lineno, target


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
    """Publisher follows the physical Python package even without a manifest."""
    parts = target.split(".")
    if len(parts) < 3 or parts[:2] != ["stratbox", "domains"]:
        return None
    publisher = parts[2]
    package = PACKAGE / "domains" / publisher
    return publisher if (package / "__init__.py").is_file() else None


def _source_publisher(path: Path) -> str | None:
    parts = path.relative_to(PACKAGE).parts
    if len(parts) < 3 or parts[0] != "domains":
        return None
    parent = PACKAGE / "domains" / parts[1]
    return parts[1] if (parent / "__init__.py").is_file() else None


def _approved_inter_owner_reference(source: str, target: str, module: str) -> bool:
    """Directional published-source reuse, constrained to named semantic modules."""
    prefix = "stratbox.domains.cbr.corporate_lending.industries.debt_0105a."
    if source == "cbr.corporate_lending.sors_restoration" and (
        target == "cbr.corporate_lending.industries.debt_0105a"
    ):
        allowed = {
            "parser": {"", "parse_cbr_0105a_debt_corp_excel_bytes"},
            "schema": {"", "CBR_0105A_DEBT_CORP_INDUSTRY_SPECS"},
            "contracts": {"", "ParsedCbr0105ADebtCorpFile"},
        }
        return any(
            module == prefix + name or module in {
                prefix + name + "." + symbol for symbol in symbols if symbol
            }
            for name, symbols in allowed.items()
        )
    if source == "cbr.corporate_lending.industries.issuance_0104" and (
        target == "cbr.corporate_lending.industries.debt_0105a"
    ):
        # Publication 01_04_A uses the same official industry, region,
        # stream, APK and workbook rules as published in the 01_05_A profile.
        # Direct use of the debt operation implementation is prohibited.
        modules = {
            "schema", "regions", "derived", "pivots",
        }
        return any(
            module == prefix + name or module.startswith(prefix + name + ".")
            for name in modules
        )
    return False



def check_dependency_direction() -> list[str]:
    failures: list[str] = []
    try:
        owners = _registered_domains()
    except (DomainLayoutError, OSError) as error:
        return [f"invalid domain hierarchy: {error}"]
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        owner = _owner(path, owners)
        source_publisher = _source_publisher(path)
        source = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for line, target in (*_imports(path, source), *_literal_module_refs(source)):
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
            if _is_legacy_domain_path(target):
                failures.append(f"{prefix}: obsolete domain import {target}")
            target_publisher = _publisher(target, owners)
            if source_publisher is not None and target_publisher is not None:
                if source_publisher != target_publisher:
                    failures.append(f"{prefix}: cross-source import {target}")
                elif target_domain is not None:
                    source_domain = owner.split(":", 1)[1] if owner.startswith("domain:") else None
                    if source_domain is None:
                        # Grouping packages are not allowed to depend on child
                        # implementations. They may expose names lazily.
                        failures.append(f"{prefix}: grouping imports domain implementation {target}")
                    elif source_domain != target_domain:
                        parent_dependency = source_domain.startswith(target_domain + ".")
                        if not (parent_dependency or _approved_inter_owner_reference(
                            source_domain, target_domain, target
                        )):
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
    """Scan active non-library code for obsolete static and dynamic imports."""
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
                if isinstance(node, ast.ImportFrom) and node.module == "stratbox.shared.data":
                    if any(alias.name in migrated_symbols for alias in node.names):
                        failures.append(f"{file_label}:{node.lineno}: moved symbol from shared.data")
            # The helper above requires a source path; supporting files use
            # the same import syntax without relative name resolution.
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    values = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    values = [node.module or ""] + [
                        f"{node.module}.{alias.name}" for alias in node.names
                    ]
                else:
                    continue
                for value in values:
                    if _is_legacy_domain_path(value) or value.startswith(forbidden):
                        failures.append(f"{file_label}:{node.lineno}: obsolete import {value}")
            for lineno, value in _literal_module_refs(tree):
                if _is_legacy_domain_path(value) or value.startswith(forbidden):
                    failures.append(f"{file_label}:{lineno}: obsolete dynamic import {value}")
    return failures


def main() -> int:
    failures = check_dependency_direction()
    failures.extend(check_supporting_source_imports())
    try:
        domain_names = tuple(
            "stratbox.domains." + owner for owner in sorted(_registered_domains())
        )
    except (DomainLayoutError, OSError) as error:
        failures.append(f"invalid domain hierarchy: {error}")
        domain_names = ()
    for name in (*CRITICAL_MODULES, *domain_names):
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
