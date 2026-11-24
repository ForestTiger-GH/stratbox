# Stratbox

Stratbox provides reusable Python operations for acquiring, interpreting and
presenting banking and economic data. Applications pass dates and
destinations and can choose their own infrastructure providers.

The package organizes neutral execution and infrastructure under `stratbox.core`,
shared data contracts and reference resources under `stratbox.shared`,
business packages and source declarations under `stratbox.domains`, and
typed command, operation, scenario and cascade definitions under
`stratbox.capabilities`. Existing domain declarations remain an explicit
contribution from `stratbox.operations` during their domain migration.
The public `stratbox.sdk.StrategyBox` facade prepares all four kinds through
`stratbox.composition` and executes them in one bounded session.

- [Capability definitions, preparation and execution ownership](docs/architecture/capability-execution.md)
- [Direct capability calls, temporary graphs and retained results](docs/current-how/capability-session.md)
- [Independent domain routes, source cards and portable replay](docs/current-how/independent-domain-data-routes.md)
- [Shared semantic owners and reference editions](docs/architecture/shared-ownership.md)
- [Geography name matching](docs/current-how/geography-name-resolution.md)
- [Operation discovery and source templates](docs/current-how/domain-operation-registry.md)
- [Executable scenarios, shared resources and the SDK](docs/current-how/executable-composition.md)
- [Processing roles, bounded catalog discovery and domain coverage](docs/current-how/processing-operation-catalog.md)
- [Core API and domain operations](docs/current-how/universal-business-core.md)
- [Universal material flow, named adapters and typed operation handoff](docs/current-how/universal-data-flow.md)
- [Logical dataset snapshots in memory, files and distributed stores](docs/current-how/logical-dataset-snapshots.md)
- [CBR publication registry, collection and independent processing routes](docs/current-how/cbr-data-pipeline.md)
- [CBR statistical workbooks, semantic mappings and retained products](docs/current-how/cbr-statistical-workbooks.md)
- [Execution, admission and recovery](docs/current-how/core-execution-and-admission.md)
- [Execution finalization and effect integrity](docs/architecture/execution-finalization.md)
- [Installation and offline quickstart](docs/how/install-and-run-core.md)
- [Execution and storage boundaries](docs/architecture/core-operation-boundaries.md)
- [Observability: qualified events, journals and recovery](docs/architecture/observability.md)
- [Notification subscriptions and recovery](docs/current-how/notifications.md)
- [Rosstat publisher original acquisition and revision evidence](docs/current-how/rosstat-publications.md)
- [Strategy Box Knowledge Product](docs/README.md)

```sh
python -m pip install .
python -m pip install -e ".[test]"
python -B scripts/check_release_integrity.py
python -B scripts/check_internal_imports.py
python -B scripts/admit_registry.py --level executable
python -B scripts/reference_editions.py verify --reference all
python -B -m pytest -q
# Offline regression and distribution admission (requires build, pytest, wheel):
# python -B scripts/local_release_check.py
# After local wheel build, verify the exact distribution bytes:
# python -B scripts/inspect_reference_wheel.py dist/stratbox-0.24.0-py3-none-any.whl
```
