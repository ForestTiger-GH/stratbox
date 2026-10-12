# Invoke and interpret Strategy Box analytics — Target HOW-A

**Status:** `CONDITIONAL TARGET HOW / NOT A RELEASED MACHINE API`. This application path uses the accepted boundary of independent headless analytical core and the [planned common host direction](../../what/strategy-box/host-deployment-commitment.md). The exact local/runtime contracts still require component-owner implementation and conformance. The [pinned Windows Current HOW](../../current-how/windows-application.md) is a foreground Qt application, **not** evidence of a shipped multi-client host. This page describes implementation/application choices with their evidence limits; it does not admit new Product requirements.

## 1. Direct analytical invocation

A notebook or appropriately authorized Python caller should remain able to invoke a domain operation in the **independent `stratbox` core**, supply explicit input/source selectors, and receive domain results without importing Qt, AppDock session clients or any future HTTP/MCP server. The direct caller owns its ambient process/session safety and any explicit FileStore/provider bindings. A simple analyst who needs a single calculation should not have to create a hosted Work, notification subscription or machine protocol adapter.

A responsible analytical flow:

1. Resolve the actual domain intent, source/period, bank/reporting perimeter, geography or classifier, exact requested metric and output kind; distinguish existence in a *declared catalog* from a callable installed implementation.
2. Bind selected source vintage/bytes and validation where available. Never turn unknown/missing source data into a numerical zero, turn independently rounded published values into exact latent amounts, or equate nominally identical bank labels across incompatible reporting perimeters.
3. Validate typed parameters, effective defaults, effect targets and operational prerequisites. Resolve the installed capability against **actual** available providers, compatible resource versions and current permission policy where an application authority is involved.
4. Execute the semantic operation at the proper owner; preserve its domain-specific result and diagnostic/evidence classes instead of flattening them to `success: true`.
5. Review computation success, partial/unavailable evidence, **artifact byte generation**, publication/availability and final human acceptance as separate states. An output path alone does not confirm an immutable or accessible Artifact.
6. Record qualified outcome with available source/method/classifier versions, and distinguish the original request from retries/physical attempts. Subsequent analysis must be able to tell whether an official published figure, a derived estimate and an unresolved value differ.

The current implementation already exposes different core Request/Result shapes; one universal API, durable provenance manifest and global identity service are *future candidates*, not assertions about every domain today.

## 2. Foreground Windows and planned host-based execution

The existing local Windows Scenario runner and Case/Log/Artifact projections are useful observable interaction patterns. Their current one-active-Qt-worker model, JSON history and lack of actual background scheduler constrain the [pinned Current HOW](../../current-how/windows-application.md). Closing a foreground window may terminate local work. It cannot be used to infer whether a **future** host-owned Run continues.

The accepted planned host direction has two deployment profiles: (a) Web/domain host with authorized browser and optional Windows/Android attachment; (b) Windows/AppDock host-capable installation with a different Windows/AppDock client installation. In either profile the following conditional application path would preserve one authoritative host-run identity:

| Application action | Required owner distinction | Invalid inference to reject |
| --- | --- | --- |
| List current operations | Host filters installed, applicable capabilities by authenticated principal, resource and revision | A cached UI catalog authorizes effects |
| Prepare parameters | Caller submits domain request; host validates schema, source profile, actual binding and output scope | GUI form display proves validity |
| Plan/admit work | Host records accepted intent/Run, idempotency identity, approvals and needed resource restrictions | Submission/retry acknowledgment equals execution outcome |
| Run and observe | Host owns Job/Attempt state and progress evidence; clients consume scoped projections | Client disconnect, elapsed timer or heartbeat proves completed work |
| Inspect results | Core owns banking inference; host binds Artifact publication/availability and evidence references | Calculation success means every file is published |
| Diagnose/recover | Host returns safe problem/recovery reference; restricted technical diagnostics remain under explicit permission | Broad node warning grants full log access |

No particular storage engine, endpoint URL, host process, standalone application repository, universal RPC method or physical scheduler is selected here. Browser, Windows and Android may render distinct UI controls but cannot redefine the accepted Run's domain/effect truth.

## 3. Conditional machine consumer and additional-input contracts

An authorized AI tool client or automated machine caller should see **only its permitted currently installed operations**, selected typed schemas, safe resource descriptors and bounded results. A machine-oriented projection cannot expose arbitrary Python module paths as execution targets. Trustworthy use still requires checking source/method applicability, parameter semantics, actual principal/object/effect authorization, budgets and approval. A read grant does not grant write/delete permission; a successful calculation does not grant file sharing.

The [Scientific comparison of machine adapters](../../science/capabilities/machine-discovery-bindings-and-adapters.md) distinguishes a *synchronous multi-round-trip request* from an optional *asynchronous task*. If **MCP 2026-07-28** is subsequently admitted as one transport, the adapter needs negotiated-version handling:

- A normal `resultType=input_required` response receives additional input through a retry of the **same logical request** with `inputResponses` and appropriate continuation state. The application must independently reconcile side effects and check current authorization before continuing.
- An extension Task `input_required` is observed through `tasks/get` and answered through `tasks/update`, **not** by blindly replaying the original tool call. Task status and product Run/Attempt/Artifact outcomes remain distinct.
- Absent/unsupported Tasks, unknown extension versions, revoked approvals, changed resource digests, expired task handles and ambiguous prior effects must produce a qualified stop/reconciliation outcome; never fabricate capability support.
- Roots/Sampling/Logging deprecation in the 2026 revision does not prove a deployed client lacks them. An adapter must negotiate actual features, and can avoid legacy dependencies without choosing a specific AI provider or platform runtime.

These are *conditional implementation guards*; they are neither a mandate to implement MCP nor a claim of current AppDock-mediated agent execution. A normal direct Python call and simple local GUI request require none of these transport states.

## 4. Controlled errors and user-visible interpretation

A reliable future adapter/application must differentiate at least: unknown operation identity; schema version mismatch; invalid or inapplicable parameters; source unreachable or unvalidated; missing installed provider; denied principal/object/effect; approval pending/expired; version or plan conflict; budget exhausted; result partially formed; artifact unavailable; canceled-before-effect versus cancellation-requested; and **effect outcome unknown after lost acknowledgment**. Error categories in this paragraph are an engineering *candidate contract*, not a claimed current exhaustive public enum.

Present a safe diagnostic code/reference and next verified action. A technical traceback or filesystem path may be included only in an appropriately scoped diagnostic view. Retry is offered only when an evidence-aware rule determines it is permitted and safe; a changed target or denied authorization invalidates stale approval. A partially created file or a missing network response cannot be silently displayed as either completed business output or confirmed non-effect.

## 5. Variants, tests and unresolved Product Decisions

| Variant or challenge | What needs demonstration |
| --- | --- |
| Local notebook | Core callable without GUI, host session or machine transport; domain result unchanged |
| Local Windows foreground | Window close, partial output and lost log/history tested against actual pinned implementation |
| Web/Windows host with detached client | Authenticated second device observes the same authoritative Run/Artifact state after first client disconnect |
| Android lightweight companion | Authorized status, approval and artifact views without importing Qt/Python bank routines into UI |
| Machine adapter (conditional) | Unsupported protocol versions and Tasks extension rejected explicitly; synchronous/task input paths remain distinct |
| Lost acknowledgment after irreversible write | One effect identity, explicit `OUTCOME_UNKNOWN` until reconciliation; no blind repeat |
| Revocation during input waiting | Fresh permission and current resource/plan revalidation before applying the pending effect |
| Source changed without URL changed | Byte/version/validation differences retained and not mistaken for idempotent sameness |

These are **unexecuted target verification vectors**, not CI passes, independent assurance or a released product. Current concrete host packaging, selected machine transport(s), cross-client identities, consistency storage, exact approvals, notification/read-position policy, operation catalog admission and resource budgets require their rightful Product/Design Authority where applicable. The bounded [host LDD](../../ldd/hosting/host-client-attachment-boundary.md) elaborates actual host/client failure questions without deciding these additional transport options by implication.

**Reopen triggers:** accepted machine API or actual MCP version selection, new installed execution host, real client-device integration, core domain schema changes, source/registry freshness, artifact policy, retention, permission model or a verified interoperability regression.
