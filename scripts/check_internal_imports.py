"""Validate component import direction and exposed package roots."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DOMAINS = frozenset(
    path.name
    for path in (SRC / "stratbox" / "domains").iterdir()
    if path.is_dir() and not path.name.startswith("_")
    and (path / "__init__.py").is_file()
)
CRITICAL_MODULES = [
    "stratbox", "stratbox.shared.data", "stratbox.shared.registries",
    "stratbox.shared.time", "stratbox.shared.text.banks",
    "stratbox.system.base.runtime", "stratbox.system.base.ioapi",
    "stratbox.system.base.filestore", "stratbox.system.base.net",
    "stratbox.system.base.secrets", "stratbox.system.execution",
    "stratbox.system.execution.registry", "stratbox.system.execution.machine",
    "stratbox.system.observability", "stratbox.system.notifications",
    "stratbox.domains.registry",
    "stratbox.domains.cbr_file_collector",
    "stratbox.domains.cbr_industries",
    "stratbox.domains.cbr_industries.issuance_0104",
    "stratbox.domains.cbr_forms", "stratbox.domains.cbr_offices",
    "stratbox.domains.cbr_offices_reg",
    "stratbox.domains.cbr_sors_restoration",
    "stratbox.domains.escrow", "stratbox.domains.frg",
    "stratbox.domains.fns_sme", "stratbox.domains.fns_1yur",
]


def _imports(path: Path, tree: ast.AST):
    rel = path.relative_to(SRC).with_suffix("")
    package = list(rel.parts if path.name == "__init__.py" else rel.parts[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                length = len(package) - node.level + 1
                prefix = ".".join(package[:length] + (node.module or "").split("."))
                prefix = prefix.rstrip(".")
            else:
                prefix = node.module or ""
            yield node.lineno, prefix
            if prefix in {"stratbox.domains", "stratbox.system", "stratbox.shared"}:
                for alias in node.names:
                    yield node.lineno, f"{prefix}.{alias.name}"


def _owner(path: Path) -> str:
    parts = path.relative_to(SRC / "stratbox").parts
    if parts[:2] == ("domains", "registry.py"):
        return "domains.registry"
    if parts[:1] == ("domains",) and len(parts) >= 2 and parts[1] in DOMAINS:
        return f"domain:{parts[1]}"
    if parts[:1] == ("system",) and len(parts) >= 2:
        return f"system:{parts[1]}"
    if parts[:1] == ("shared",) and len(parts) >= 2:
        return f"shared:{parts[1]}"
    return ".".join(parts[:2])


def _target_domain(name: str) -> str | None:
    parts = name.split(".")
    if len(parts) >= 3 and parts[:2] == ["stratbox", "domains"] and parts[2] in DOMAINS:
        return parts[2]
    return None


def check_dependency_direction() -> list[str]:
    failures = []
    for path in sorted((SRC / "stratbox").rglob("*.py")):
        rel = path.relative_to(SRC / "stratbox")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        owner = _owner(path)
        for line, target in _imports(path, tree):
            prefix = f"{rel}:{line}"
            domain = _target_domain(target)
            if target.startswith("stratbox_"):
                failures.append(f"{prefix}: external integration import {target}")
            if owner.startswith(("system:", "shared:")) and target.startswith("stratbox.domains"):
                failures.append(f"{prefix}: {owner} imports domain namespace {target}")
            if domain:
                if owner.startswith(("system:", "shared:")):
                    continue
                    failures.append(f"{prefix}: {owner} imports concrete domain {target}")
                elif owner.startswith("domain:"):
                    source = owner.split(":", 1)[1]
                    if source != domain and not (
                        source == "cbr_sors_restoration" and domain == "cbr_industries"
                    ):
                        failures.append(f"{prefix}: prohibited cross-domain import {target}")
                elif owner == "domains.registry":
                    failures.append(f"{prefix}: registry imports concrete domain {target}")
            if owner == "system:observability" and target.startswith("stratbox.system.notifications"):
                failures.append(f"{prefix}: observability imports notifications")
            if (target.split(".")[0] in {"requests", "urllib3", "httpx", "aiohttp"}
                    or target.startswith("urllib.request")) and (
                rel.as_posix() != "system/base/net/transport.py"
            ):
                failures.append(f"{prefix}: transport outside system.base.net")
    return failures


def main() -> int:
    failures = check_dependency_direction()
    for module in CRITICAL_MODULES:
        try:
            importlib.import_module(module)
            print(f"OK   {module}")
        except Exception as error:
            failures.append(f"{module}: {type(error).__name__}: {error}")
    if failures:
        print("\nImport checks failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK   core dependency direction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
