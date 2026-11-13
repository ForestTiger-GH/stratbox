"""Check public import roots and core dependency direction."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CRITICAL_MODULES = [
    "stratbox",
    "stratbox.catalog",
    "stratbox.base.runtime",
    "stratbox.base.ioapi",
    "stratbox.base.filestore",
    "stratbox.base.net",
    "stratbox.base.secrets",
    "stratbox.data",
    "stratbox.execution",
    "stratbox.notifications",
    "stratbox.macrobanks.cbr_file_collector",
    "stratbox.macrobanks.cbr_industries",
    "stratbox.macrobanks.cbr_industries.issuance_0104",
    "stratbox.macrobanks.cbr_forms",
    "stratbox.macrobanks.cbr_offices",
    "stratbox.macrobanks.cbr_offices_reg",
    "stratbox.macrobanks.cbr_sors_restoration",
    "stratbox.macrobanks.escrow",
    "stratbox.macrobanks.frg",
    "stratbox.organizations.fns_sme",
    "stratbox.organizations.fns_1yur",
    "stratbox.registries",
    "stratbox.text.banks",
]


def check_dependency_direction() -> list[str]:
    failures = []
    for path in sorted((SRC / "stratbox").rglob("*.py")):
        rel = path.relative_to(SRC / "stratbox")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and not node.level:
                imports = (node.module or "",)
            elif isinstance(node, ast.Import):
                imports = tuple(alias.name for alias in node.names)
            else:
                continue
            for name in imports:
                if name.startswith("stratbox_"):
                    failures.append(f"{rel}:{node.lineno} depends on an external integration")
                if rel.parts[0] in {"base", "data", "execution"} and name.startswith(
                    ("stratbox.macrobanks", "stratbox.organizations", "stratbox.notifications")
                ):
                    failures.append(f"{rel}:{node.lineno} reverses the domain dependency")
                if (name.split(".")[0] in {"requests", "urllib3", "httpx", "aiohttp"} or name.startswith("urllib.request")) and (
                    rel.as_posix() != "base/net/transport.py"
                ):
                    failures.append(f"{rel}:{node.lineno} uses a transport outside base.net")
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
