# Current HOW — Windows application, runtime, scenarios, history and background state

**Evidence status:** a bounded **static implementation review** of `ForestTiger-GH/stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`; no deployed AppDock session, real Qt client, runtime integration run or passing smoke-test suite was demonstrated in this study. Direct contract declarations, code behavior, and absent guarantees are distinguished from proposals for future Windows/Web/Android profiles.

## Declared delivery, not necessarily delivered capability

The [AppDock manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) declares one interactive `desktop` surface, default view `scenario_chat`, two linked Python distributions under the `world` runtime environment, **Windows-local foreground execution**, `--diagnose` through the same entrypoint, and high-level `supports_artifacts`/`supports_presence` flags. These are **manifest declarations**, not proof that each abstract capability is backed by a live scheduler, collaboration service or transactional Artifact Store.

**Version precision:** top-level Connector Manifest `contract_version=4.0`, surface activation contract `4.0`, `world_version=0.1.0`, Windows package requirement `0.1.0` and requested analytical-core package `0.2.1`. Neither manifest field by itself establishes the installed core package version or the independent version of every Activation Context field. The external runtime owner must attest its actual installed bindings and activation data.

## Activation and platform boundary

The [adapter entrypoint](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/adapters/appdock/entry.py) parses supplied Activation Context, checks the intended `world_id`/`active_surface_id`, verifies two installed package bindings and their environment relation, and then invokes the application entry. Invalid configuration raises a controlled `AppConfigError`, with exit code 2. This is Strategy Box consuming a versioned external execution context, not the platform installer/repository manager or a guarantee that the platform actually launched.

A platform-owned session, health condition, workspace and installation path must be interpreted according to that external provider's verified contract. The analytical core remains the owner of subject-matter computations.

## Runtime composition currently imports Qt

[`build_runtime(context)`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) creates application operation/scenario catalogs and local stores for cases, events, artifacts, logs, assignments, background state and preferences. It loads recent JSON history and then directly imports/constructs `ScenarioCoordinator` from `presentation.qt_desktop`.

**Direct implication:** application runtime composition is **not yet free of Qt toolkit dependencies** at this source baseline. A portable application-service or Android client must separate semantic orchestration ports from the Qt presentation adapter. This is an engineering direction, not an existing shared Android runtime.

## Sequential scenario execution and one active Qt worker

The [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) sets a case `running`, emits structured events, walks scenario steps in order, applies parameter mapping/overrides, calls operation handlers, turns output paths into artifact display records, and records operation log objects. For `error_policy=fail_fast`, subsequent steps are skipped after failure; other policies may continue to later steps. A terminal case status/event is emitted under the runner's rules.

The [Qt ScenarioCoordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) keeps one `QThread` and one active case. `is_busy` blocks acceptance of another simultaneous case. Its worker is asynchronous relative to the GUI event loop, **not** a durable multi-Job scheduler with independent concurrency/leases. A `cancelled` vocabulary item in a case model does not prove a functioning cancellation token, cooperative interruption path or safe external effect reversal.

## Five JSON projections are not an authoritative event database

[`HistoryPersistenceService`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) stores cases/events/artifacts/logs/assignments in **five separate JSON files**. `load_into` decodes each view into the corresponding local store; failed source read/JSON decoding can return an **empty list** rather than a recoverable error. Individual file writes use a normal text write without a verified atomic five-file transaction, versioned migration policy or cross-process locking.

This serves convenient **recent desktop context**. It does not establish a durable Work/Result truth source, crash-safe all-object commit, server multi-user state or independently audited history. A corrupt stored history that appears as an empty legitimate history is a concrete current-state risk. Future remedies are candidate controls subject to materiality and host ownership.

## Background state, collaboration and artifacts: model versus effect

[`BackgroundProcessStore`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) manages configured background records and `enabled/status` values in memory. It can mark `running/warning/error` and return active records; **no scheduler loop, persisted trigger identity or worker dispatch** is established by this class. Enabling the UI toggle is therefore not evidence that monitoring actually started.

The pinned source research also describes local participant/presence and assignment projections whose UI presentation currently exceeds the demonstrated network/authorization backend. A presence badge or user attribution is not a verified distributed notification, consent, durable delegated Work or evidence independence. An artifact view with an output path is not a content-verified published Artifact.

## Confirmed static contract/test mismatch

At the same pinned Windows Git revision:
- [`appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) specifies top-level Connector Manifest `4.0` and each package declaration uses `package_requirement`.
- [`tests/smoke/test_repository_contract.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/tests/smoke/test_repository_contract.py) asserts top-level `contract_version == '3.0'` and accesses `package_identity`.

Those assertions **cannot both pass** against the checked-in manifest. This is a directly verified static incompatibility, not a claim that pytest was executed in this session. A released system should require the test to follow the actual accepted manifest contract, plus an installed integration test for the external platform's accepted version.

## Additional source-quality and portability caveats

The dated detailed source survey at this exact revision reports tracked generated runtime/bytecode files and a documentation/manifest drift risk. Such statements need separate fresh Git-tree verification before being classified as the *current* condition of a later revision. A commit title mentioning a statistical method is not proof that the Windows repository actually contains its implementation; inspect the actual changed source file and package import.

A platform-neutral runtime model requires separation of UI geometry, semantic action identity, execution owner, event projection and actual permission/data contracts. The Windows Qt rail can be one rendering; a browser or Android client must not import Qt merely to reuse a shared Work/Run meaning.

## Unexecuted falsifying tests and re-open conditions

| Negative test | What its outcome would establish |
| --- | --- |
| Launch under verified manifest `4.0` and smoke contract | Whether the contract/test drift was actually fixed and externally accepted |
| Start two independent cases while one Qt worker runs | Present coordinator rejects the second; no fair queue should be inferred |
| Kill the process during one of five history-file writes | Evaluate empty-on-corruption, mixed versions and user-visible loss |
| Enable background monitoring and leave the client running | Verify actual scheduled operations; in-memory toggles alone are insufficient |
| Revoke another user's artifact permission while a chat view remains open | Remote principal authorization must apply at access, not merely by screen membership |
| Force an operation to write partial bytes then fail | Output-path discovery must not be promoted to a verified publication |
| Construct a core/app runtime without Qt | Determines real Android/Web portability and whether toolkit dependencies have been removed |
| Deliver an external effect, lose acknowledgement, then retry | Distinguish `UNKNOWN` from safe idempotent repeat and confirmed success |

**Bounded conclusion:** the pinned Windows baseline provides a recognizable local Scenario UI, sequential execution, local history and projection scaffolds, but **does not prove** a durable scheduler, remote presence service, working cancellation, authoritative shared Work, fully portable orchestration or hosted Web/Android client. Reopen on code/manifest/test changes, platform-contract revision and installed fault-injection evidence. These implementation limits are independent from product-admission decisions.
