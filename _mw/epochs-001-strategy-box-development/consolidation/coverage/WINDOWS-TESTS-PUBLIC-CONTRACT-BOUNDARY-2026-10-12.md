# Pinned Windows tests and selected AppDock public-contract boundary: source-first static evidence

**Work date:** 2026-10-12. **Role:** bounded Current HOW / conformance evidence, **PRODUCER STATIC REVIEW**; not an independent verifier, executed product suite or globally terminal source disposition. **Work program:** existing continuous Strategy Box consolidation, not a new stage.

## Exact evidence baseline and accounting

- Windows direct implementation, manifest and ten test witnesses: [`stratbox-windows@959e9c4`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b).
- Public platform contracts, *not the installed host runtime*: [`AppDock@a4d87c6`](https://github.com/ForestTiger-GH/AppDock/tree/a4d87c643e620e54e04083d4d0b8d867513e7065).
- Existing frozen census identities `SB-SRC-0527..0536` cover **all ten** Windows test files, whose `full_read` state was committed before this continuation. This review checked the complete text of those files and the manifest again.
- `SB-SRC-0543` (`activation_context.yaml`), `0544` (`connector_manifest.yaml`), `0547` (`surface_activation.yaml`) and `0548` (`specs/conformance/world/connector_manifest.md`) are **newly full-read and blob-SHA compared** to the census: all four matched exactly. Other platform contracts, notably the large Observability implementation-status history and portions of the JSON schema/runtime Python implementation, were inspected selectively, **not** marked full-read.
- CSV source total remains **566**; after the four precisely bounded promotions: **91 full_read, 10 governing_read, 465 not_full_read**; every file-level `material_unit_state` remains **unaccounted**. Source-reading evidence is a distinct axis from complete semantic conservation.

## Test-witness review — assertion ≠ execution

| Census identity | Direct test witness | Assertion actually represented | Essential limit |
| --- | --- | --- | --- |
| 0527 | `tests/conftest.py` | Synthetic Activation Context 3.0 fixture, two distribution bindings, fake digests, generated local directories | A fixture is not a real host handoff, genuine digest or credential |
| 0528 | `tests/contracts/test_appdock_entry.py` | Valid/missing graph, wrong world/surface, unchanged `sys.path`, controlled exit code 2 | Does not boot a live platform, run the UI or prove installed package bytes |
| 0529 | `tests/contracts/test_runtime_contracts.py` | Context 3.0 acceptance, old-version and legacy-field rejection, required workspace field, SHA-256 *syntax* | Digest string syntax is not a recomputed package-byte attestation |
| 0530 | `tests/smoke/test_external_core_dependency.py` | Import of `stratbox` and `FileStore` | Does not invoke any bank/macro operation or confirm version compatibility |
| 0531 | `tests/smoke/test_repository_contract.py` | Connector source/package graph, activation 4.0 and packaging tests | **Contradicts current manifest** on top-level version and package field; also imports `tomllib` despite Python 3.10 support claim |
| 0532 | `tests/unit/test_paths.py` | Dev storage directory creation; AppDock-managed source/system paths | No cross-platform, host remote or permission-policy proof |
| 0533 | `tests/unit/test_scenario_chat_projector.py` | Sender alignment and event projection | UI sorting/placement semantics, not network presence or authorization |
| 0534 | `tests/unit/test_workspace_explorer_service.py` | Local listing ordering and a workspace navigation path | Does not exhaustively prove symlink traversal or OS-level path confinement |
| 0535 | `tests/unit/test_workspace_registry.py` | Loaded default schema has input/output directories | Does not prove disk readiness or persistence |
| 0536 | `tests/unit/test_workspace_resolver.py` | Temporary local workspace creation below selector | Does not prove remote Data Plane, shared writes or interrupted recovery |

Pinned direct source paths: [test directory](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b/tests), [connector manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json), [AppDock entry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/adapters/appdock/entry.py), [Context decoder](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/adapters/appdock/runtime_contracts.py), [Qt-coupled bootstrap](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py).

## Direct inconsistencies and scope

1. **Definite repository smoke contradiction:** the actual manifest says top-level `contract_version=4.0`, with `package_requirement`. Test `test_manifest_declares_connector_3_strategy_box_world` instead asserts `3.0`; several package tests dereference `package_identity` instead. The assertions cannot pass together against that file. The test additionally imports `tomllib` (stdlib since Python 3.11) while `pyproject.toml` declares `requires-python >=3.10`. An external alternative dependency is not provided in that test.
2. **The distinct version numbers are not interchangeable:** Connector Manifest `4.0`, surface Activation `4.0` and runtime Activation Context `3.0` are different contracts, and the Windows 3.0 Context test is not itself obsolete. The [public platform activation implementation](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/src/appdock/contracts/activation/surface_activation.py) defines Activation 4.0; its [runtime Context implementation](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/src/appdock/contracts/runtime/activation_context.py) defines Context 3.0.
3. **Manifest/profile is local:** the pinned manifest declares foreground, local, Windows-targeted execution. AppDock documentation allows future host/delegated modes, but their existence as enum values or future prose is not evidence that this Strategy Box version supports remote jobs.
4. **The handoff adapter checks some invariants, not complete release conformance:** `entry.validate_appdock_runtime_contract()` checks world/surface IDs, package binding IDs, their package names/profiles and same environment; the observed entry function does not check a full installed semantic version matrix or compute digests of package contents. A Context decoder accepts a correctly formatted digest value; that alone is not a verified installed release identity.
5. **Prose-to-code drift is a separate issue:** the pinned platform's small [Connector Manifest conformance note](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/specs/conformance/world/connector_manifest.md) mentions `identity.display_name`, while the actual Windows manifest uses `identity.world_name`. The pinned platform JSON schema delegates identity to another schema and was only partially inspected here. Thus this note establishes documentation ambiguity **not a proved invalid manifest**. Require authoritative resolved schema plus actual admission validator for any release verdict.
6. **The existing Strategy Box knowledge CI checks documentation, not this desktop suite:** successful `stratbox` knowledge-evidence jobs cannot be presented as `stratbox-windows` pytest or the AppDock installed preflight. No platform/Windows runtime test was run in this Work.

## Trace routing and decision boundaries

- These ten test witnesses and four platform contract dossiers route to [Windows Current HOW](../../../../../docs/current-how/windows-application.md) and [candidate activation LDD](../../../../../docs/ldd/integration/activation-contract-verification.md), with source/execution status preserved.
- Actual platform installation, manifest admission, native Windows verification and package-version resolution remain *external/implementation-owned evidence*, not a Product Decision made by documentation.
- The logical reusable application layer is a candidate because current `runtime.bootstrap` still directly constructs a Qt coordinator. Its physical extraction or creation of a repository/service, Web/Android release and remotely durable host require explicit selection, not a smoke-test repair.
- Restricted extension implementations and internal environment identities were not used or admitted.

## Reproducible next checks and assurance status

**Mechanically reviewable tests:** compare the exact manifest JSON values to smoke assertions; run Python 3.10 versus 3.11 test-import preflight; run the existing [Windows contract check script](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/scripts/check_appdock_contract.py) against a pinned AppDock checkout; run domain-independent Windows unit + smoke tests on supported Windows, observing actual pass/fail/skip; verify resolved platform JSON-schema closure and actual admission plus package-byte receipts. All remain **NOT EXECUTED in this continuation**.

**Producer outcome:** **BOUNDED SOURCE-READ AND STATIC CONTRADICTION PASS; RUNTIME/RELEASE PASS NOT ESTABLISHED.** **Independent reviewer:** none. **Global Research lossless and Research Amputation:** open. **Owner of repair:** `stratbox-windows` implementation work under an appropriate separate change authority; AppDock contract owner for any platform-side inconsistency. **Reopen:** updated manifest, tests, full platform schema, a real release conformance run or a Product Decision affecting shared application authority.
