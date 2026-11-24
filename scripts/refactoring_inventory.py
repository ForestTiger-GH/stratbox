"""Capture the complete migration scope without importing analytical backends."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import asdict, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def json_value(value):
    if is_dataclass(value):
        return {key: json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [json_value(item) for item in value]
    return value


def capture(root=ROOT, *, base_commit=None):
    """Keep declared coverage separate from verified execution evidence."""
    package = root / "src/stratbox"
    declarations = []
    sources, profiles, templates = [], [], []
    for path in sorted(package.rglob("*.yaml")):
        document = json.loads(path.read_text())
        record = {"path": path.relative_to(root).as_posix(),
                  "sha256": sha256(path.read_bytes()).hexdigest(), "document": document}
        if path.name.startswith("OPERATION_"):
            definition = document["definition"]
            kind = ("scenario" if definition.get("processing", {}).get("composition")
                    else "operation")
            record["disposition"] = {"candidate": kind, "stage": "P12" if document["owner_id"].startswith("core.") else {
                "cbr": "P13", "fns": "P14", "rosstat": "P15", "minfin": "P16", "frank_rg": "P17"
            }[document["owner_id"].split(".")[0]], "status": "pending_migration"}
            declarations.append(record)
        elif path.name.startswith("SOURCE_"):
            sources.append(record)
        elif path.name.startswith("PROFILE_"):
            profiles.append(record)
        elif path.name.startswith("TEMPLATE_"):
            templates.append(record)
    implementations = {reference.split(":", 1)[0] + ":" + reference.split(":", 1)[1]
        for record in declarations for reference in record["document"].get("implementation", {}).values()
        if isinstance(reference, str) and ":" in reference}
    callables = []
    python_files = sorted(package.rglob("*.py"))
    for path in python_files:
        module = ".".join(path.relative_to(root / "src").with_suffix("").parts)
        if module.endswith(".__init__"):
            module = module[:-9]
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                reference = module + ":" + node.name
                callables.append({"reference": reference, "line": node.lineno,
                    "disposition_candidate": "method_binding" if reference in implementations else "internal_helper"})
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        callables.append({"reference": module + ":" + node.name + "." + method.name,
                            "line": method.lineno, "disposition_candidate": "internal_helper"})
    from stratbox.operations import operation_catalog
    catalog = operation_catalog()
    source_catalog = catalog.source_catalog()
    matrix = []
    for card in source_catalog.sources:
        for group in card.source_groups:
            description = source_catalog.describe(card.series_id, operations=catalog, group_id=group.group_id)
            matrix.append({"source_id": card.series_id, "group_id": group.group_id,
                "formats": list(group.formats), "period_model": group.period_model,
                "editions": "bounded_by_declared_profiles", "period_scope": "declared_source_scope",
                "stages": [{"stage": item["stage"], "declared_state": item["state"],
                    "operations": list(item["operations"]), "reasons": list(item["reasons"]),
                    "verification": "not_inferred_from_declaration"} for item in description["stages"]]})
    assets = [{"path": path.relative_to(root).as_posix(), "sha256": sha256(path.read_bytes()).hexdigest(),
               "disposition_candidate": "preserve_semantics_and_bytes"}
              for path in sorted((package / "shared/reference").rglob("*")) if path.is_file() and "__pycache__" not in path.parts]
    fixtures = [{"path": path.relative_to(root).as_posix(), "sha256": sha256(path.read_bytes()).hexdigest()}
                for path in sorted((root / "tests/fixtures").rglob("*")) if path.is_file()]
    public_entries = [{"path": path.relative_to(root).as_posix(), "sha256": sha256(path.read_bytes()).hexdigest()}
                      for path in sorted((package / "sdk").rglob("*.py"))]
    return {"schema": "stratbox.refactoring.inventory.v1", "base_commit": base_commit or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "counts": {"python_files": len(python_files), "operations": len(declarations), "sources": len(sources),
            "groups": len(matrix), "profiles": len(profiles), "templates": len(templates),
            "test_files": len(list((root / "tests").rglob("test_*.py"))),
            "operations_by_owner": dict(Counter(item["document"]["owner_id"] for item in declarations))},
        "operations": declarations, "sources": sources, "profiles": profiles, "templates": templates,
        "callables": callables, "source_stage_matrix": matrix, "reference_assets": assets,
        "fixture_corpus": fixtures, "public_entries": public_entries,
        "constraints": {"python": ">=3.10", "backend_imports": "lazy", "compatibility": "not_required",
                        "external_durable_host": "H01", "external_machine_adapter": "H02"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit")
    options = parser.parse_args()
    data = capture(base_commit=options.base_commit)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n")
    print(json.dumps(data["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
