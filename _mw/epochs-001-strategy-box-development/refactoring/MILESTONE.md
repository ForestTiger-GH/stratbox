# Capability execution foundation: P00-P11

Date: 2026-11-25. Scope: local library foundation and controlled vertical pilots. Status: verified local foundation. Source checkpoint: 76d8e58b444283709becc1e486d1e8f22a0a64d7. Audit resolution: [P11-R](reviews/2026-11-25-foundation/REPORT.md).

The foundation provides one catalog-to-plan-to-session route for four capability kinds. The initial domain corpus remains a migration contribution. This checkpoint completes M0/M1 within the authorized P00-P11 slice; it does not claim the later full-domain or public-machine migration.

## 1. Implemented package boundaries

| Package | Implemented outcome | Evidence owners |
| --- | --- | --- |
| P00 | Complete immutable starting scope and acceptance trace | `scripts/refactoring_inventory.py; refactoring/p00/baseline.json; refactoring/p00/acceptance.json` |
| P01 | Pure owners, lazy metadata and dependency rules | `scripts/check_internal_imports.py; docs/architecture/capability-execution.md` |
| P02 | Four typed kinds, semantic ports, authoring graph and physical IR | `src/stratbox/capabilities/model; src/stratbox/composition/plan.py` |
| P03 | Canonical resolution, methods, profiles, processing groups, overlays and metadata projection | `src/stratbox/capabilities/catalog; src/stratbox/sdk/bootstrap.py` |
| P04 | Inspectable useful command graphs and exact standard operations | `src/stratbox/capabilities/commands; src/stratbox/capabilities/operations; src/stratbox/core/capabilities` |
| P05 | Closure, supplied values, exact and goal preparation, maps and portable plans | `src/stratbox/composition/prepare.py; tests/unit/composition; tests/integration/capability_pilots/test_plan_codec.py` |
| P06 | One session, initial/dynamic admission and independent acceptance scopes | `src/stratbox/core/execution/session.py; tests/unit/execution/test_scope_early_outputs.py` |
| P07 | Coherent acceptance, owned retained values, mutation isolation, leases and codecs | `src/stratbox/core/execution/values; src/stratbox/core/execution/retention.py; tests/unit/execution/test_values_session.py` |
| P08 | Coordinator sharing, bounded acquisition, resource claims, fairness and backpressure | `src/stratbox/core/execution/session.py; src/stratbox/core/network/shared.py; tests/integration/capability_pilots/test_bounded_acquisition.py` |
| P09 | Effect authority, revision fencing, unknown outcomes, reconciliation and host ports | `src/stratbox/core/execution/effects.py; src/stratbox/core/execution/recovery.py; tests/integration/capability_pilots/test_effect_recovery.py` |
| P10 | Authoritative progress, retained accepted facts, destination receipts and notification topics | `src/stratbox/core/observability; src/stratbox/core/notifications; tests/unit/notifications/test_accepted_values.py` |
| P11 | Three local vertical pilots and combined failure/recovery cases | `tests/integration/capability_pilots` |

## 2. Quantitative scope

- Starting inventory: 785 library Python files, 356 operation declarations, 90 sources and source groups, 144 profiles, 19 route templates, 181 test files, 3,336 callables and 1,350 source/group-stage cells.
- All starting objects retain disposition candidates; reference assets and fixture identities are pinned.
- Canonical catalog: 22 commands, 12 exact operations, 2 scenarios, 1 cascade, 2 interpretation methods, 1 processing group and 3 goal recipes.
- Test files: 219, an increase of 38 from the initial inventory. Library Python files: 821.
- Full regression: 1,874 passed, 7 skipped; baseline 1,675 passed, 7 skipped. Added passing tests: 199; 95 were added during P11-R.
- All 120 original acceptance cases retain verification routes. Local fixture evidence is mapped separately; later domain/host outcomes remain explicit obligations. A mapped mechanism test alone does not discharge an entire publisher or historical-edition claim.

## 3. Pilot evidence and limits

Pilot A uses actual CBR acquisition profiles for debt_0105a, issuance_0104a, fd_okved2 and sme_fd_okved2. A controlled shared index yields four distinct synthetic originals. One index acquisition serves all logical source uses.

Pilot B uses a synthetic workbook with two tables. Two extraction profiles and convert.readable share one decoder. Two-input ratios, independently useful scenarios, a cascade, a required conditional save and concurrent preview run through the same session.

Pilot C specializes extract.observations for the actual Minfin budget_table period-column contract. Controlled data preserve cumulative YTD periods and RUB-billion scale. This is deterministic layout evidence, not certification of every published workbook.

Fault evidence includes missing members, unsupported format, source status distinctions, shared-consumer cancellation, observer failure, unknown save reconciliation from retained outputs, late stale completion, acquisition limits and portable-plan tamper rejection.

## 4. Continuing scope

P12-P18 own complete general-stage and domain migration. The existing 356 declarations, 90 sources, 144 profiles and 19 templates remain preserved at their existing owners until those stages assign final dispositions. Old composition/builtins publisher dispatch and integral/expanded contributions remain identified transition paths for that migration. Canonical preparation has no publisher dispatch.

P19-P21 own the complete public/machine surface and removal of transition owners. The minimal direct SDK route is implemented for the pilots; existing machine endpoints are not represented as migrated. H01 supplies the actual durable application host, and H02 supplies the actual external protocol adapter. Core supplies recovery ports and a conformance harness. Process-private spill remains temporary.

## 5. Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 python scripts/check_release_integrity.py
PYTHONDONTWRITEBYTECODE=1 python scripts/check_internal_imports.py
PYTHONDONTWRITEBYTECODE=1 python scripts/admit_registry.py --level executable
PYTHONDONTWRITEBYTECODE=1 python scripts/reference_editions.py verify --reference all
PYTHONDONTWRITEBYTECODE=1 python -m build --no-isolation
```

The exact built wheel and sdist are inspected with scripts/inspect_reference_wheel.py. A separate minimal environment verifies metadata without numerical/workbook extras, a direct command, retained output lifetime and packaged reference manifests outside the checkout.

## 6. Final validation

The final P11-R local suite passed in 315.29 seconds: 1,874 passed and 7 skipped. Import direction, release integrity, executable catalog admission, reference editions and maintained README checks passed. Exact wheel and sdist implementation/resource inventories were verified. The installed wheel ran the public offline example in a separate minimal environment outside the checkout; metadata discovery imported no numerical/workbook backend. No GitHub Actions were used.

Validation identity, distribution digests and external scope limits are retained in validation.json. The implementation commit identifies the tested code; the subsequent report-only commit adds the updated validation records. The P11-R report maps each confirmed audit item to its implementation and regression evidence. The original 120 acceptance cases retain their scoped status: 49 implemented local slices, 67 planned and 4 external-pending.
