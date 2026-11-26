"""Admit final declarations, domain records and package resources locally."""
from __future__ import annotations

import ast
from importlib import resources
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))
RETIRED = (
    'src/stratbox/operations', 'src/stratbox/composition',
    'src/stratbox/domains/registry', 'src/stratbox/core/operations',
    'src/stratbox/core/capabilities', 'src/stratbox/core/resources',
)
REQUIRED = (
    'README.md', 'pyproject.toml', 'src/stratbox/py.typed',
    'src/stratbox/capabilities/model/domains.py',
    'src/stratbox/capabilities/model/methods.py',
    'src/stratbox/capabilities/preparation/__init__.py',
    'src/stratbox/core/execution/service.py',
    'src/stratbox/shared/data/values.py', 'src/stratbox/sdk/client.py',
)
COMPONENT_COUNTERS = {'schema_version', 'profile_version', 'method_version', 'rules_version', 'definition_revision', 'contract_version'}


def main() -> int:
    errors = []
    errors.extend('Retired path remains: ' + name for name in RETIRED if (ROOT / name).exists())
    errors.extend('Required path missing: ' + name for name in REQUIRED if not (ROOT / name).is_file())
    for domain in (SRC / 'stratbox/domains').iterdir():
        if domain.is_dir():
            errors.extend('Retired domain layer remains: '+str((domain/name).relative_to(ROOT))
                for name in ('operations','capabilities','publications','tables','integration','analytics') if (domain/name).exists())
    for path in (SRC / 'stratbox').rglob('profiles.py'):
        errors.append('Retired profile owner remains: ' + str(path.relative_to(ROOT)))
    for path in (SRC / 'stratbox').rglob('*.py'):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError as error:
            errors.append(f'{path.relative_to(ROOT)}: {error}')
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in COMPONENT_COUNTERS:
                errors.append(f'{path.relative_to(ROOT)}:{node.lineno}: component counter {node.target.id}')
    if not errors:
        try:
            from stratbox.capabilities.catalog import standard_catalog
            from stratbox.capabilities.catalog.domains import load_domains
            catalog = standard_catalog()
            domains = load_domains()
            if not catalog.definitions or not domains.domains:
                errors.append('Empty canonical declarations')
            for domain_id, domain in domains.domains.items():
                if domain.id != domain_id or not domain.series:
                    errors.append(f'Domain identity/scope invalid: {domain_id}')
                for series_id, series in domain.series.items():
                    if series.id != series_id:
                        errors.append(f'Series identity mismatch: {series_id}')
                    for command_id in series.commands:
                        definition = catalog.definitions.get(command_id)
                        if definition is None or definition.kind != 'command':
                            errors.append(f'Unknown standard command: {series_id}: {command_id}')
            from stratbox.shared.reference.assets import load_reference
            for name in ('banks', 'geography', 'okved2'):
                load_reference('stratbox.shared.reference.' + name).validate_all()
        except Exception as error:
            errors.append(f'Declaration/resource admission: {type(error).__name__}: {error}')
    for error in errors:
        print(error)
    print(f'Release integrity: {len(errors)} failure(s)')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
