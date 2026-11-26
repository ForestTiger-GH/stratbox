"""Check final ownership boundaries and internal imports without legacy fallbacks."""
from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
PACKAGE = SRC / 'stratbox'
FORBIDDEN = (
    'stratbox.operations', 'stratbox.composition', 'stratbox.domains.registry',
    'stratbox.core.operations', 'stratbox.core.capabilities',
)
PURE_CAPABILITIES = ('model', 'route', 'commands', 'operations', 'scenarios', 'cascades', 'plan')
METADATA_MODULES = (
    'stratbox.capabilities.model.domains', 'stratbox.capabilities.catalog',
    'stratbox.capabilities.catalog.domains', 'stratbox.capabilities.preparation',
    'stratbox.core.execution.service', 'stratbox.sdk',
)


def imports(path: Path, tree: ast.AST):
    relative = path.relative_to(SRC).with_suffix('')
    package = '.'.join(relative.parts[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            name = '.' * node.level + (node.module or '')
            try:
                resolved = importlib.util.resolve_name(name, package) if node.level else name
            except (ImportError, ValueError):
                yield node.lineno, '<invalid-relative-import>'
            else:
                yield node.lineno, resolved


def check_source(root: Path = PACKAGE) -> list[str]:
    errors = []
    for path in sorted(root.rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except SyntaxError as error:
            errors.append(f'{path.relative_to(ROOT)}:{error.lineno}: {error.msg}')
            continue
        relative = path.relative_to(PACKAGE)
        for line, module in imports(path, tree):
            reason = None
            if any(module == old or module.startswith(old + '.') for old in FORBIDDEN):
                reason = 'retired owner'
            elif module.startswith('stratbox.'):
                local = SRC.joinpath(*module.split('.'))
                if not local.with_suffix('.py').is_file() and not local.joinpath('__init__.py').is_file():
                    reason = 'missing internal module'
            if relative.parts[0] == 'capabilities' and len(relative.parts) > 1 and relative.parts[1] in PURE_CAPABILITIES:
                if module.startswith(('stratbox.core', 'stratbox.domains', 'stratbox.sdk')):
                    reason = 'standard definitions must be independent of implementations'
            if relative.parts[0] == 'shared' and module.startswith(('stratbox.core', 'stratbox.domains', 'stratbox.capabilities', 'stratbox.sdk')):
                reason = 'shared values must be independent of implementation'
            if relative.parts[0] == 'domains' and module.startswith('stratbox.sdk'):
                reason = 'domain cannot depend on application facade'
            if reason:
                errors.append(f'{path.relative_to(ROOT)}:{line}: {reason}: {module}')
    return errors


def main() -> int:
    sys.path.insert(0, str(SRC))
    errors = check_source()
    if not errors:
        for module in METADATA_MODULES:
            try:
                importlib.import_module(module)
            except Exception as error:
                errors.append(f'{module}: {type(error).__name__}: {error}')
    for error in errors:
        print(error)
    print(f'Internal ownership/import check: {len(errors)} failure(s)')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
