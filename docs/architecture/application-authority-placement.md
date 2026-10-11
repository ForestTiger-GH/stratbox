# Application authority: logical portability before physical extraction

**Status:** `PA-SB-2026-10-09-CANDIDATE-1` supplement; engineering hypothesis, **not** an accepted deployable `stratbox-application` repository, service, installer or AppDock manifest. The [responsibility allocation](responsibility-allocation.md) remains the parent boundary and [Windows Current HOW](../current-how/windows-application.md) remains dated direct evidence.

## Problem and non-negotiable boundary

Today the Windows repository owns scenario specs, case transitions, step execution, local history and Qt GUI. Its `runtime/bootstrap.py` constructs a Qt `ScenarioCoordinator`: application runtime can execute local work, but is not currently proven toolkit-independent or durable beyond the Windows process. The analytical `stratbox` library must remain importable and usable directly by Python/notebooks, with bank/macro computations and neutral data contracts independent of any client. AppDock independently owns packaging, node/session/activation and its own availability/diagnostics, never the semantic outcome of domain calculations.

Future Windows, Web and Android clients may need the **same meaning** of operations, runs, permissions, artifact identity and effects. Shared semantic meaning is more important than sharing widgets or forcing a universal UI.

## Competing placement models

| Model | Benefit | Cost/failure mode | Admission posture |
| --- | --- | --- | --- |
| A. Keep all application semantics in Windows, copy to each client | Fastest for a single local UI | Case identity, effect logic and recovery diverge across Web/mobile; duplicated security checks | Viable only while one independent local runtime is the accepted scope |
| B. Extract toolkit-independent application module inside the existing Windows repo | Minimal distribution/packaging change; explicit ports and tests can prove separation | New consumers have repo/package ownership coupling; a Web host still needs an execution authority | **Preferred smallest pilot hypothesis**, conditional |
| C. Shared installable `stratbox-application` package/repo | One reusable application API/version and tests across clients | New release owner, dependency graph, versioning and cross-repo coordination | Conditional on a real second consumer and stable contracts; no repo created |
| D. Shared host service as application authority with remote clients | Durable jobs, access control, consistent outcomes and attachment | Authentication, storage, host lifecycle, ops/support and network failure economics | Conditional on accepted shared-node/Web work and actual provider contract |
| E. Put application orchestration inside analytical `stratbox` or AppDock | Superficially fewer moving parts | Collapses domain independence or transfers product semantics to external platform | **Rejected as default responsibility allocation** |

## Decision tests before materialization

- **Direct Python pilot:** a domain operation executes via `stratbox` without importing application or Qt; exactly the same domain result and provenance can be consumed by a local Windows application adapter.
- **Qt-free semantic pilot:** import and test operation specifications, a scenario executor and case model in a headless environment without PySide6 or an AppDock running session.
- **Lifecycle pilot:** closing a Windows client ends or preserves a job according to a separately admitted *local versus hosted* profile. A disconnect is not automatically `CANCELLED`.
- **Effect/authority pilot:** two hypothetical clients issuing the same effectful request have explicit ownership of one admission/retry/receipt decision; absence of a shared authority is detected rather than silently solved by copying in-memory stores.
- **Failure containment:** platform health, executor failure, source failure, incomplete Artifact and user acceptance retain separate statuses and cannot be translated into a single success boolean.
- **Cost/proportionality:** compare maintenance cost of portable module vs separate package/service only after one concrete second consumer and a representative workflow exist.

## Conditional responsibility contract

`stratbox`: official source and domain facts, semantics, calculation, export, neutral FileStore/provider contracts. **Logical application authority (candidate):** user Work/scenarios, admitted Run/Attempt/Job if needed, lifecycle, effect accounting, app-level permissions and Artifact catalogue references. **Windows/Web/Android clients:** UI projection and platform-specific input/output without independently inventing authoritative case outcomes. **AppDock external:** source/install/node/session/activation/host readiness and publicly proved integration contracts.

No physical `stratbox-application` host or repo is selected. A single-process module may be enough initially; a host service follows only when accepted requirements demand persistence across clients, central authorization, or remote execution. AppDock remote capabilities are verified per exact published version and deployment, not assumed from a conceptual feature list.

**Product Decisions required:** which cross-client behaviors to ship, lifetime after client exit, user/node scopes, externally observable concurrency/cancel/retry promises, data retention and permissions, ownership/packaging/versioning, and host reliability targets. Maintain the candidate while these choices remain open; do not block source-first Science or current-state validation.

**Reopen:** real second UI/host consumer, accepted WHAT/operation requirements, headless smoke failure, actual shared-state counterexample or changed external contract.
