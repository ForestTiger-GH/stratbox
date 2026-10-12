# Candidate LDD — local scenario orchestration without Qt-owned application truth

**Status:** bounded `CANDIDATE`, not a shipped shared package, standalone host, approved cancellation guarantee, accepted remote API or Product Decision. **Engineering problem:** portable *application semantics*, not a universal workflow framework. **Context:** `TW-SB-2026-10-09-CANDIDATE-1`, `TH-SB-2026-10-09-CANDIDATE-1`, `PA-SB-2026-10-09-CANDIDATE-1`. A second consumer or approved host profile must be demonstrated before a physical `stratbox-application` repository or service is selected.

## Direct observed implementation and failure evidence

Pinned [Windows `runtime.bootstrap`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) creates semantic catalogs/stores, then directly imports [Qt `ScenarioCoordinator`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py). The coordinator owns one `QThread`, one `_active_case` and signal dispatch to stores. [`ScenarioWorker.run`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/workers.py) invokes the application-layer [`run_scenario`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) with callbacks. The model therefore has an existing Qt-free sequential **step runner**, but admission, one-run arbitration, threading and event-to-store projection are coupled to Qt composition. This is a more precise split than saying all scenario execution is Qt-bound.

Observed semantic hazards relevant to any extraction:

- A step gets `success/failed` from `result.ok`; a failing step with non-`fail_fast` policy can leave the final aggregate `case.status=success`. **The case outcome is not always an aggregate of required step outcomes.**
- `run_scenario` constructs ArtifactRecords from **every** output path after both successful and failed operations. A failed operation can return only a log path. An Artifact card must not imply verified business bytes.
- [`run_operation`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) catches arbitrary handler exceptions and puts `str(exc)` into its returned message/details; [Qt worker exception boundary](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/workers.py) also embeds `str(exc)` in the final case message. These are **unsafe-by-default candidates for shared projection**: unreviewed exception text may contain private paths or internal values. Source alone does not establish actual leakage, but no unconditional sanitization is visible at these specific boundaries.
- [`HistoryPersistenceService`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) writes five independent JSON files via `write_text` and silently converts corrupt JSON to empty lists; no atomic multi-record transaction. In its own docstring it expressly limits the role to restoring **recent desktop context**. Do not promote that display cache into a durable Job authority.

All these are **static direct-source findings**, not executed fault injection. The existing [Current HOW](../../current-how/windows-application.md) is the dated implementation owner.

## Smallest portable logical seam

The first viable seam can be **a toolkit-independent application module within the existing codebase**. Its responsibilities are small enough to reason about and unit test without selecting IPC, database, host process, service framework or repository extraction.

| Responsibility | Logical owner | Rule |
| --- | --- | --- |
| Bank/macro computation and domain result | Independent `stratbox` core | Same callable operation and domain evidence work in notebook/headless and GUI paths |
| User scenario definition and parameter mapping | Application semantic layer | Version/identity of ordered steps, inputs, role of required/optional errors |
| Local execution admission and one-active-run guard | Headless local application coordinator | One-run policy is a **local product constraint**, not a distributed lock |
| Step invocation and observations | Existing sequential scenario runner via injected callbacks | Observations never override verified domain Result or publish an Artifact by path existence alone |
| State projection | Application models/read projections | Terminal case outcome derived from step/effect statuses and declared partial policy |
| Technical attempt and GUI signals | Qt worker adapter | Thread scheduling, signal dispatch, window busy state; no independent semantic success rules |
| Recent history | Local cache until stronger policy admitted | Corrupt/partial cache reported or quarantined; absent cache is not evidence of no prior effects |
| Install/node/session/activation | AppDock external platform | Platform availability distinct from application Run and analytic result; use versioned public contracts |

This proposal requires **only the interfaces actually used by one Windows consumer**: request validation, local submission with a stable case identity, a sequential runner invocation, a typed observation stream/callback, a result snapshot and bounded status query. Names and Python method signatures remain design variables. Introducing a full RPC protocol, persistent queue, coordinator/worker fleet or cross-platform serialization now would turn optional research concepts into unjustified construction.

## Local state, failure and effect truth

1. **Before worker start:** a successful local `submit` either returns a case identity accepted by a currently available local coordinator or explicitly rejects a second submission. It does not promise host persistence.
2. **During execution:** step start/success/failure observations carry stable case/step IDs and bounded sequence order. The UI may render them asynchronously, but UI callback delivery is not proof that a durable record was committed.
3. **After each step:** distinguish analytical output, diagnostic log, staged file and published Artifact; an output path is insufficient. A failed required step remains observable even if a partial-policy scenario continues subsequent steps.
4. **Terminal case:** derive the final qualified status from steps and verified effects according to *explicitly admitted* required/optional/partial rules. Until partial policy is approved, do not silently encode an unsuccessful required step as `success`.
5. **Unhandled exception:** record technical details only in a restricted local diagnostic surface, and expose a stable safe failure classification/summary; avoid displaying raw `str(exc)` in any potentially shared case/event.
6. **Window exit, lost callback, crash:** local in-process execution has no durable-resume claim. A stale displayed `active_job`/case is `UNKNOWN` pending evidence, never proof of successful completion, cancellation or clean rollback. Real continuity across UI lifecycle needs separate authority and Product Decisions.
7. **Cancellation:** the current `cancelled` case enum does not implement interruption. UI must hide/disable cancel or clearly communicate `request only` until a bounded cooperative cancellation contract and actual executor behavior exist.
8. **Storage:** if the five-file history remains a recent cache, use safe snapshot writing, explicit corrupt-cache handling and single-writer limitations; full event-store transactions/recovery are separately conditional on admitted durability requirements.

## Validation vectors: separate mocked behavior, platform and native tests

| ID | Setup/negative vector | Expected independently observable result | Evidence posture |
| --- | --- | --- | --- |
| LS-01 | Import headless semantic coordinator without PySide6 installed | Imports, scenario/step semantics and local tests work without Qt | Proposed; current `build_runtime` imports Qt |
| LS-02 | Inject fake domain operation result for notebook and local app | Same domain result values/evidence, no frontend or AppDock dependency in `stratbox` | Proposed |
| LS-03 | Submit two scenarios with one-run policy | Deterministic busy rejection or queued *only if specifically admitted*; no duplicate local acceptance | One-active-Qt guard observed, no test executed |
| LS-04 | Required step fails with continue policy | Aggregate cannot falsely claim unconditional success; records failed step and permitted partial semantics | Direct source **counterexample** observed |
| LS-05 | Failed handler returns log path in `outputs` | Log classified as diagnostic, no published business Artifact | Direct source **counterexample** observed |
| LS-06 | Partial external write or unavailable storage confirmation | Output remains staged/failed/unknown; no completed Artifact before verified receipt | Conditional; no fault test executed |
| LS-07 | Handler raises exception containing sensitive path/token | Shared event/case shows safe class, restricted local log retains necessary trace under access policy | Direct source unsafe raw-exception propagation potential |
| LS-08 | GUI window closes mid-run | If local-only policy, result becomes unavailable/unknown as warranted; never invent durable host execution | Conditional; no actual GUI test |
| LS-09 | Callback lost or arrives out of order | Projection rebuild semantics explicit, no authoritative state transition inferred from UI signal order | Conditional |
| LS-10 | Corrupt one historical JSON among five | Warning/quarantine or explicitly bounded fallback, no presentation as legitimately empty authoritative ledger | Current source silently returns `[]` |
| LS-11 | Cancel before/after an actual side effect | Distinguish requested, acknowledged stop, partial effect and outcome-unknown; no false rollback | Not implemented/current design open |
| LS-12 | Shared Web/Android client proposed against local in-process executor | Mark unsupported until shared authority/auth/deployment exist; avoid synthesizing server readiness | Product Decision outstanding |
| LS-13 | Domain returns a result with source validation failure | Event preserves domain failure; downstream case/UI cannot reclassify as success from file existence alone | Proposed |
| LS-14 | Static import graph scanner checks Qt and independent core | Qt imports restricted to concrete presentation/host adapter; `stratbox` independently importable | Proposed |

Tests LS-01–07, LS-10, LS-13 and LS-14 can begin with pure fakes and local fixtures. Native Windows AppDock/Qt integration and process-stop tests are separate acceptance evidence; no green result claimed here. Risk of durable state or multi-user authorization requires a different specialist verification plan. The author of the candidate does not qualify as independent assurance reviewer.

## Alternatives, costs and decisive Product Questions

**Candidate path A:** keep one Windows consumer and refactor orchestration into pure application code with a Qt bridge. Few new moving parts, but no cross-device execution. **Candidate path B:** move proven portable application logic to a separately versioned `stratbox-application` package when Web/Android and Windows must share a real contract; test release ownership first. **Candidate path C:** introduce a host execution service only after an admitted persistent/shared-node requirement with authentication, storage, reconciliation and support-budget evidence. **Rejected default:** folding Qt/application execution into analytic `stratbox`, or delegating Strategy Box domain state truth to AppDock.

Open Decision subjects: whether any scenario persists after client exit; partial/fail-fast policy; cancellability and effect classes; artifact publication/retention/access; concurrency beyond one local run; shared-host identity/authorization; physical module/package/repository, host and API. A platform launch manifest is a **separate** decision surface and must not be inferred from this LDD.

**Reopen:** a second concrete consumer, accepted lifecycle/effect requirement, current source change, independent negative test result or relevant AppDock contract version change. This design intentionally stops at the sufficient local seam and remains **not certified for implementation or release**.

## Source-executed local Case and handler diagnostics: target safeguards (LS-15..22)

**Evidence division:** six **current-code** Linux/offline Python behavior characterizations passed at pinned Windows SHA in [CI 38190957120](https://github.com/ForestTiger-GH/stratbox/actions/runs/38190957120), detailed in [Current HOW](../../current-how/windows-application.md). The following **LS-15..22** are **unexecuted** prospective target acceptance/failure vectors. A passing current defect reproduction is not a passed target fix.

| Target vector | Fault / input | Required conditional future behavior |
| --- | --- | --- |
| LS-15 | Required step fails under a policy named `continue_with_warnings` | Aggregate result clearly signals partial/warning/failure under the accepted outcome algebra; cannot say fully `success` without semantic qualification |
| LS-16 | Explicit optional step fails with `fail_fast` | Accepted required/optional contract controls propagation; if optional has no special semantics, do not claim it does in schema or UI |
| LS-17 | User supplies a synthetic parameter resembling a credential | Shared Event projections omit/redact protected values before persistence, AI visibility or remote-stream publication; safe diagnostic receipt preserved |
| LS-18 | An error path returns a technical `.log` path in the normal outputs tuple | File/log class and intended audience are checked; log path must not be promoted to a remotely fetchable generic Artifact without separate authority |
| LS-19 | Operation raises before structured result, after Step started | Authoritative Run/Case/Attempt must finish or explicitly remain `UNKNOWN/INTERRUPTED` with causal evidence; pending Step and error event cannot silently disappear |
| LS-20 | Workspace unavailable after FileHandler attached | Handler is closed/removed on every exit, including early return, exception during construction and repeated operation |
| LS-21 | Same synthetic Case with two optional/required failures and then reconnect | Step, aggregate status, user-facing card and persisted history agree on partial/unknown distinctions; no stale projection asserts complete success |
| LS-22 | Two concurrent attempted operations use a case/step/log filename alias | Preserve distinct Attempt evidence and avoid truncation/collision, with OS/process-appropriate log ownership |

**Owner and authorization:** these are design/assurance candidates requiring application implementation review, acceptable partial/failure policy and resource/audience choice. The old GUI current-state flaw does not mandate a broad framework, an extra repository or breaking retention of old legitimate user files. Real Qt/native and actual shared-host tests are required before acceptance; **none** of LS-15..22 was run.
