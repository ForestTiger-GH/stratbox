from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stratbox.domains._structure import DomainLayoutError, discover_operation_owners  # noqa: E402

REQUIRED_FILES = [
    # Knowledge consolidation bootstrap and content-preserved legacy sources.
    'docs/README.md',
    'docs/science/README.md',
    'docs/what/README.md',
    'docs/current-how/README.md',
    'docs/how/README.md',
    'docs/architecture/README.md',
    'docs/ldd/README.md',
    'docs_old/README.md',
    '_mw/epochs-001-strategy-box-development/consolidation/README.md',
    '_mw/epochs-001-strategy-box-development/consolidation/CYCLE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/STATE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/BASELINE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/ARCHITECTURE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/sources/SEED.md',
    'docs_old/cbr_sors_restoration/crosswalk.md',
    'docs_old/cbr_sors_restoration/diagnostics.md',
    'docs_old/cbr_sors_restoration/execution_modes.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-07.md',
    'docs_old/cbr_sors_restoration/methodology.md',
    'docs_old/cbr_sors_restoration/pivot_and_export.md',
    'docs_old/cbr_sors_restoration/result_grids.md',
    'docs_old/cbr_sors_restoration/source_contracts.md',
    'docs_old/files_catalog_methods.md',
    'docs_old/frg_stage1.md',
    'docs/current-how/universal-business-core.md',
    'docs/current-how/core-execution-and-admission.md',
    'docs/architecture/core-operation-boundaries.md',
    'docs/how/install-and-run-core.md',
    'src/stratbox/shared/README.md',
    'src/stratbox/shared/reference/README.md',
    'docs/architecture/shared-ownership.md',
    'docs/current-how/shared-semantic-contracts.md',
    'docs/current-how/reference-snapshots-and-update.md',
    'docs/current-how/geography-name-resolution.md',
    'tests/unit/shared/test_identity_evidence.py',
    'tests/unit/shared/test_reference_assets.py',
    'tests/unit/shared/test_bank_names.py',
    'tests/unit/shared/test_geography.py',
    'tests/unit/shared/test_periods.py',
    'scripts/reference_editions.py',
    'scripts/inspect_reference_wheel.py',
    'scripts/local_release_check.py',
    'scripts/check_readme_links.py',
    'tests/cbr_sors_restoration/test_identity_provenance.py',
    'src/stratbox/shared/identity.py',
    'src/stratbox/shared/evidence.py',
    'src/stratbox/shared/data/datasets.py',
    'src/stratbox/shared/reference/assets.py',
    'src/stratbox/shared/reference/banks/_resources/manifest.json',
    'src/stratbox/shared/reference/okved2/_resources/manifest.json',
    'src/stratbox/shared/reference/geography/_resources/manifest.json',
    'src/stratbox/shared/reference/geography/_resources/aliases.csv',
    'src/stratbox/py.typed',
    'src/stratbox/domains/cbr/__init__.py',
    'src/stratbox/domains/cbr/_source.py',
    'src/stratbox/domains/cbr/file_collection/_registration.py',
    'src/stratbox/domains/cbr/reporting_forms/_registration.py',
    'src/stratbox/domains/cbr/corporate_lending/__init__.py',
    'src/stratbox/domains/cbr/corporate_lending/industries/debt_0105a/_registration.py',
    'src/stratbox/domains/cbr/corporate_lending/industries/issuance_0104/_registration.py',
    'src/stratbox/domains/cbr/corporate_lending/sors_restoration/_registration.py',
    'src/stratbox/domains/cbr/service_network/__init__.py',
    'src/stratbox/domains/cbr/service_network/bank_offices/_registration.py',
    'src/stratbox/domains/cbr/service_network/territorial_offices/_registration.py',
    'src/stratbox/domains/cbr/escrow/_registration.py',
    'src/stratbox/domains/fns/__init__.py',
    'src/stratbox/domains/fns/legal_entities_1yur/_registration.py',
    'src/stratbox/domains/fns/sme_register/_registration.py',
    'src/stratbox/domains/frank_rg/__init__.py',
    'src/stratbox/domains/frank_rg/_registration.py',
    'src/stratbox/domains/registry.py',
    'src/stratbox/core/execution/catalog.py',
    'src/stratbox/core/execution/runner.py',
    'src/stratbox/core/execution/contracts.py',
    'src/stratbox/core/execution/effects.py',
    'src/stratbox/core/execution/resolution.py',
    'src/stratbox/core/observability/records/effect_refs.py',
    'tests/unit/observability/test_effect_identity.py',
    'tests/unit/execution/test_output_accounting.py',
    'tests/unit/execution/test_capability_declarations.py',
    'tests/unit/execution/test_terminal_resilience.py',
    'tests/unit/observability/test_result_summary_bounds.py',
    'docs/architecture/execution-finalization.md',
    'tests/unit/execution/test_finalization.py',
    'tests/integration/universal_core/test_execution_effect_pipeline.py',
    'src/stratbox/core/__init__.py',
    'src/stratbox/core/registry.py',
    'src/stratbox/core/runtime/providers.py',
    'src/stratbox/core/storage/filestore/ports.py',
    'src/stratbox/core/observability/journal/file_reader.py',
    'src/stratbox/core/notifications/state/transactions.py',
    'tests/fixtures/universal_core/README.md',
    'examples/parse_offices_from_bytes.py',
    'README.md',
    'pyproject.toml',
    'src/stratbox/__init__.py',
    'src/stratbox/README.md',
    'docs_old/architecture.md',
    'docs_old/development.md',
    'docs_old/plugin-integration.md',
    'docs_old/examples.md',
    'examples/cbr_file_collector_example.py',
    'tests/smoke/test_core_imports.py',
    'tests/unit/test_runtime_providers.py',
    'src/stratbox/domains/cbr/corporate_lending/sors_restoration/README.md',
    'docs_old/cbr_sors_restoration/architecture.md',
    'docs_old/cbr_sors_restoration/acceptance.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-05.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-06.md',
    'examples/cbr_sors_restoration_colab.py',
    'tests/cbr_sors_restoration/test_publication.py',
]

FORBIDDEN_PATHS = [
    'src/stratbox/domains/_cbr.py',
    'src/stratbox/domains/cbr_file_collector',
    'src/stratbox/domains/cbr_forms',
    'src/stratbox/domains/cbr_industries',
    'src/stratbox/domains/cbr_offices',
    'src/stratbox/domains/cbr_offices_reg',
    'src/stratbox/domains/cbr_sors_restoration',
    'src/stratbox/domains/escrow',
    'src/stratbox/domains/fns_1yur',
    'src/stratbox/domains/fns_sme',
    'src/stratbox/domains/frg',
    'src/stratbox/shared/registries',
    'src/stratbox/shared/text',
    'src/stratbox/shared/data/evidence.py',
    'src/stratbox/shared/data/identity.py',
    'src/stratbox/system',
    'src/stratbox/core/base',
    'src/stratbox/core/ioapi',
    'src/app',
    'appdock',
    '.tmp',
]

CHECK_IGNORE_PATHS = [
    '.tmp',
    '.venv',
    '.venv-build',
]


def main() -> int:
    failures: list[str] = []

    domains_root = SRC / "stratbox" / "domains"
    try:
        owners = discover_operation_owners(domains_root)
        if not owners:
            failures.append("no source-domain operation registrations discovered")
        for owner in owners:
            package = domains_root.joinpath(*owner.split("."))
            if not (package / "_registration.py").is_file():
                failures.append(f"discovered owner lacks a manifest: {owner}")
    except (DomainLayoutError, OSError) as error:
        failures.append(f"invalid source-domain hierarchy: {error}")

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            failures.append(f'missing required path: {rel}')
        else:
            print(f'OK required {rel}')

    for rel in FORBIDDEN_PATHS:
        if (ROOT / rel).exists():
            failures.append(f'forbidden path still exists: {rel}')
        else:
            print(f'OK absent {rel}')

    if (ROOT / '.git').exists():
        for rel in CHECK_IGNORE_PATHS:
            ignored_path = rel.rstrip('/') + '/'
            result = subprocess.run(
                ['git', 'check-ignore', '-v', '--no-index', ignored_path],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                failures.append(f'gitignore does not hide path: {rel}')
            else:
                print(f'OK ignored {rel}')

    generated = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob('*')
        if path.is_file()
        and (path.suffix == '.pyc' or '__pycache__' in path.parts)
        and not any(ignored in path.parts for ignored in CHECK_IGNORE_PATHS)
    ]
    if generated:
        failures.append(
            'generated Python bytecode is present: ' + ', '.join(generated[:20])
        )
    else:
        print('OK no generated Python bytecode')

    if failures:
        print('\nRelease integrity failed:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
