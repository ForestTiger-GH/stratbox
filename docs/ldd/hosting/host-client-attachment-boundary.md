# Candidate LDD — one host authority, two deployment arrangements, multiple connecting surfaces

**Status:** `CANDIDATE / INTEGRATION-DEPENDENT / ZERO REAL HOST TESTS`. **WHAT:** [PD-SB-HOST-2026-10-12-01](../../what/strategy-box/host-deployment-commitment.md). **HOW:** [host attachment profiles](../../how/hosting/host-and-client-deployment.md). This LDD details testable inter-component semantics only; it does not establish a new host repo, Python package, executable, API URL, certificate, AppDock manifest, DB, broker or security protocol.

## Logical ownership and identity rules

One running host owns the accepted logical Run/Case/Job within its served scope. Client instance, app installation, AppDock user/session, network connection, host installation and domain operation are **distinct identities**. The same authenticated user on Windows and browser might see the same authorized Case; another user might see only an audience-safe incident notice. Two host instances must never both claim write authority for one job namespace without a separately proved leadership/fencing protocol. Name of host type (Web or Windows/AppDock) must not change the canonical meaning of a Step, Artifact or effect outcome.

### Minimal proposed boundary methods (not signatures)

1. **Bind:** read host identity, contract major/capabilities and endpoint reachability; compare against the client-supported profile. A version number is not authentication or proof of feature readiness.
2. **Attach:** prove the currently permitted principal and object scope. Web session, Windows-managed attachment and Android session may use different transport/auth adapters; all enforce the same application-side effect policy.
3. **Submit:** create exactly one *logical accepted intention* or return a clear rejection/unknown outcome. A stable idempotency/reconciliation reference should survive lost response; actual retention and conflict semantics require an approved policy.
4. **Observe:** receive an authorized snapshot plus monotonically ordered updates if implemented; stale cursor/gap/permission change returns a qualified resnapshot path, not fabricated continuity.
5. **Fetch:** resolve published Artifact by server-side object authorization and verified byte availability; a local server path is never presented as a directly usable remote-client path.
6. **Disconnect/reconnect:** client lifecycle only changes subscription/view; host Work can continue if its own state and execution policy permit. Host shutdown, crash and external effects require separate recovery handling.
7. **Operate:** health and diagnostic cues distinguish client connection, platform installation, host readiness and individual Job state, with protected local traces and permitted cross-user notice.

## Deployment alternatives and decision economics

| Physical option | Benefit | Hazard/required proof | Disposition |
| --- | --- | --- | --- |
| Windows host and client roles in one repository, separately selectable runtime packages | Shared models and simpler code movement | Packaging may accidentally import Qt in host or conflate service lifecycle with frontend window | `BOUNDED_OPEN` |
| Separate Windows host and connecting client repositories | Independent release/installation ownership, smaller client | Protocol drift, duplicate build/release coordination and AppDock compatibility | `BOUNDED_OPEN`; **not selected** |
| Independent `stratbox-application` package consumed by both host types | Common app semantics under shared release owner | Third package dependency, version/ownership churn | `BOUNDED_OPEN`; not mandatory yet |
| Hosted app semantics implemented entirely in analytic `stratbox` | Fewer distribution artifacts | Corrupts analytic headless core boundary | **Rejected responsibility allocation** |
| External AppDock platform stores app Case/effect truth | Reuses platform lifecycle | Its Node/Session contracts do not prove domain outcome semantics | **Rejected responsibility allocation** |

**Engineering note:** A host may live on Windows and be installed through AppDock without the host being a Qt widget. Its lifecycle must be separately observable from a **connecting** client's window. A host-side local UI may exist and may influence host shutdown through an approved policy; that is different from remote-client disconnect.

## Test and failure matrix (proposals; no results)

| ID | Test | Required target observation |
| --- | --- | --- |
| HC-01 | Host starts on a Web-accessible node; open configured domain in browser | Authorized client discovers true host identity and usable profile, not an assumed static page |
| HC-02 | One host serves a browser and supported Windows/Android attachment | Same permitted Case/Result semantics across clients, with differing native UI |
| HC-03 | Windows/AppDock installation A hosts; separate installation B attaches | B reads/starts permitted work through host authority; no shared mutable JSON path workaround |
| HC-04 | Kill connecting Windows client during active hosted job | Host execution truth unchanged solely by client process exit; no false terminal status |
| HC-05 | Close browser tab and reconnect with new session | Authorized snapshot/reconciliation, same logical job identity where host remained alive |
| HC-06 | Stop/restart host during external write | Truthful unknown/partial outcome until effect receipt reconciliation; no unproved exactly-once |
| HC-07 | Retry command after transport response lost | No accidental second logical admission under approved key/scope; conflicting payload handled explicitly |
| HC-08 | Attach with incompatible contract/capability | Explicit unsupported/upgrade response, no unsafe implicit fallback |
| HC-09 | Cross-user private artifact/event read | Host enforces object-level access; visible card does not yield private file |
| HC-10 | Revoke permission during active event stream | Subsequent frames/fetches denied or stream revoked; no stale grant |
| HC-11 | Host file exists but bytes unavailable or incomplete | Artifact result is unavailable/unpublished; failure independent from successful domain calculation |
| HC-12 | Two host-capable instances share a workspace without supported fencing | Second writer rejected or intentionally isolated; never silently duplicate case authority |
| HC-13 | AppDock session health says available but host executor is dead | Client displays distinct platform-ready / application-unavailable outcomes |
| HC-14 | Browser-provided server path, forged Host header or CSRF attempt | Fails under real accepted browser threat model; neither filename nor UI disabled control bypasses policy |
| HC-15 | Start host package with PySide6 unavailable where headless profile requires it | Host portion runs or reports explicit declared toolkit dependency; core remains separately importable |
| HC-16 | Windows one-package versus two-package prototype | Compare package size, release ownership, endpoint compatibility and measured failure recovery before physical selection |

**Evidence grading:** HC-01..16 are future tests. Pure fakes may test request identity, status, snapshot boundaries and data models; realistic acceptance of HC-01/03/04/06/09/10/13/14 requires installed, networked, authorized environments and platform-specific evidence. A static manifest, matching class names or green unit tests cannot substitute for the target deployment acceptance.

## Concrete handoff and blocked decisions

The first implementation pilot should prove **one Web-addressable host ↔ one browser** and **one Windows/AppDock host ↔ separate Windows/AppDock client** as distinct observable profiles, with the same core computation meaning and one host-owned state projection, before settling framework/topology. This is a **proposed validation approach**, not a binding development order. Capture exact source SHA, Windows/AppDock version, machine and identity profiles, request/result/event traces, disconnect tests and security constraints. Product owner must select baseline authentication, permission and retention policy; external platform owner must validate actual host/client lifecycle and transport contracts. No new manifest can be derived from the conceptual AppDock role alone.

**Independent assurance:** separate from this author and this design text; neither SCI losslessness nor release security verification is certified by this LDD. Reopen on direct owner decision, actual first pilot, changed external contracts, or host topology evidence.

## Public platform contract qualification — 2026-10-12

The pinned public AppDock schema exposes *declarable* remote-attachment and delegated-work capability fields and background/detached/host-delegated launch modes, but their presence does not prove runtime behavior. For **HC-03**, use two actually installed Windows/AppDock instances and prove authorized host identity, connection and true shared Case authority. For **HC-13**, separately measure AppDock session/activation versus the Strategy Box host process/readiness. No generated manifest, endpoint or release is admitted by this LDD.

## Transition boundary — local Windows history versus new host authority

**Issue:** the pinned Windows application has local JSON Case/Step/Event/Artifact/Log displays, per-record unread booleans, workspace paths and session-facing active-job hints. Under [HOST-O1..O7](../../what/strategy-box/host-deployment-commitment.md) the **new** host owns work it actually accepts. Simply pointing a Windows UI to remote endpoints does not transform old local records into host-verified history. This is a meaningful source-of-truth transition, not just a transport change.

| Existing local item | Host target interpretation and acceptable candidate handling | False migration to prohibit |
| --- | --- | --- |
| Case UUID and scenario/operation/params | A historical **locally executed** Case may remain explicitly local/legacy and read-only, or be imported as labeled historical evidence after validated ownership/consent. | Import as a successfully **host-executed** Job or resubmit an old command automatically. |
| Step and aggregate terminal labels | Retain historical label with source version. A known local `success` after a non-fail-fast step failure requires a qualification; newer host aggregate uses its own verified semantics. | Promote local `success` into verified complete host outcome merely by mapping enum names. |
| ArtifactRecord with path and guessed kind | Path is a historical locator; if bytes are accessible and owner permits, a separate verified host ingestion may publish them, otherwise preserve unavailable/legacy reference. | Convert server or former desktop absolute path into a remote client's own local path. |
| Local log path and raw exception message | Technical diagnostics remain restricted; optional controlled import must sanitize before common Case/Event feed. | Publicly replicate raw stack trace, token-bearing path or diagnostic file merely because it was once in `outputs`. |
| Event `unread: bool` | Retain historical per-event display flag or initialize *new scoped* per-principal cursor policy explicitly. | Pretend one old boolean establishes the read state of multiple remote users. |
| User config and scenario form values | Keep local presentation preferences local unless an approved settings migration exists. Detect sensitivity before any transfer of saved form dictionaries. | Sync raw saved passwords/tokens/secret operation inputs or make local settings into global node policy. |
| Platform session/active_job JSON | Treat as platform/desktop continuity projection only; use host receipt/state to establish actual accepted Job. | Claim a disconnected session means a host Job has succeeded, ceased or is resumable. |

**Bounded transition gates (conditional, unexecuted):** (HC-17) attach new Windows remote client while legacy local read-only history remains intact; (HC-18) inject misleading local `success` record with failed step and verify it is labeled legacy/qualified rather than host success; (HC-19) old Artifact path points to missing or changed file and cannot be remotely opened without a verified hosted copy; (HC-20) import attempts of saved form values redact/deny unknown sensitive fields; (HC-21) reconnect after client crash cannot create a second host namespace or replay an old local command; (HC-22) host and old local UI cannot concurrently write the same shared case namespace without declared exclusive ownership.

**Product decisions:** legacy data retention/import eligibility, user/admin consent, host storage/identity and retention policy, local mode after host rollout, continuity requirements and deprecation strategy. Compatibility of old **Python APIs** is not required by default, whereas authenticity, ownership and safe handling of retained **user files** still need explicit Product decisions. None of HC-17..22 or migration routines has run. The old Windows data remains current-source evidence, not assumed migrated content.

## Additional launch versus hosted-service tests — public AppDock revision (unexecuted)

| ID | Condition | Required qualified outcome |
| --- | --- | --- |
| HC-23 | `host_delegated` launch at pinned `a4d87c6` | Explicit `BACKEND_UNAVAILABLE`, never a fabricated host attachment. |
| HC-24 | `dedicated_server` background child exits during initial startup grace | Startup failure, no host readiness claim. |
| HC-25 | Background child passes startup grace but never exposes a listening authorized service | Launch may succeed; host readiness/attachment must fail independently. |
| HC-26 | Detached wrapper exits 0 but actual host absent | Handoff success, not evidence of a surviving host or Job. |
| HC-27 | Browser URL opens but remote site is unreachable or lacks authentication | Browser action is not host service readiness or application success. |
| HC-28 | Manifest Boolean advertises remote/delegated support with no executable attach backend | Declaration cannot satisfy actual authenticated connection. |
| HC-29 | Host process exists but its identity/contract disagrees with second Windows client | Attach rejects/quarantines mismatch; PID is insufficient. |

**No HC-23..29 were executed**. [Current public platform launch evidence](../../current-how/appdock-activation-host-attachment-boundary.md) is static source-only; the seven tests remain candidate verification work.

## Generic core-runtime host failure vectors — unexecuted

| ID | Injected condition | Candidate conformance |
| --- | --- | --- |
| HC-30 | Unattended host operation needs missing secret | Explicit safe configuration/permission failure; **no implicit `getpass` terminal prompt**. |
| HC-31 | Distinct attached user contexts need distinct authorities | Per-principal authorization remains correct regardless of cached process-level providers. |
| HC-32 | Approved runtime credential rotates during in-flight Jobs | Qualified snapshot/change handling; no secret appears in common Event/Case/Artifact text. |
| HC-33 | Notebook invokes the same analytic core with explicitly allowed interactive credentials | Core works without running AppDock or host; application policy does not contaminate independent domain API. |

These are planned host verification vectors grounded in [core Current HOW](../../current-how/core-runtime-network.md). They have no execution result. No real secrets or environment-specific extension internals belong in test fixtures or this LDD.

## Host-side suspended input and optional machine-adapter boundaries — unexecuted

**Scope:** this is an addendum to the accepted *logical* host direction, grounded in [Scientific machine-protocol distinctions](../../science/capabilities/machine-discovery-bindings-and-adapters.md) and [conditional application HOW](../../how/application/invoke-and-interpret.md). It assumes **neither** an admitted MCP endpoint **nor** an accepted distributed task protocol. The public host's ability to accept one durable Run and recover an approval after client disconnect remains a target requiring actual Product policy and implementation. External protocol adaptation is conditional on an independently approved machine consumer.

A user confirmation, credential bootstrap, resource selection or conflict resolution pause has at least four separable identities: **application Run/Attempt**, **pending input request under a stable versioned plan**, **principal who may answer**, and **actual authorized effect**. A transport Task ID is only an adapter reference. A supplied form answer changes proposed input and can require a new plan or rights check; it cannot retroactively legitimize an old destructive write. Shared UI must distinguish `WAITING_FOR_INPUT`, `AWAITING_APPROVAL`, `AUTHORIZATION_DENIED`, `NEEDS_REPLAN`, `OUTCOME_UNKNOWN` and actual business result, as candidate state concepts rather than falsely claiming the present Windows enum already supports them.

| Conditional test | Injection / client sequence | Required truthful observation | Current evidence |
| --- | --- | --- | --- |
| HC-34 | Host accepted a Run, Windows client disconnects while approval is pending, browser reconnects under same authorized principal | The host resolves exactly the same pending intent and authorizable scope or clearly reports expiration; client loss alone neither rejects nor approves it | `UNEXECUTED`; no shipped host |
| HC-35 | Approval was drafted, target resource contents/permissions changed before user presses confirm | Former proposed digest/permission is stale; host rejects or explicitly replans/re-authorizes before side effect | `UNEXECUTED`; approval contract open |
| HC-36 | Conditional MCP 2026 multi-round-trip `input_required` with a lost response | The adapter resumes with a version-valid logical request/continuation and checks unknown prior effect, never blindly executes a second destructive effect | `UNEXECUTED`; transport unselected |
| HC-37 | Conditional MCP Tasks extension reports task `input_required`; client retries original `tools/call` instead of `tasks/update` | Adapter detects protocol mismatch/duplicate intent; host does not create a competing Run | `UNEXECUTED`; extension unselected |
| HC-38 | External Task says `completed` while stored Artifact bytes fail validation or are inaccessible | Host reports computation and publication statuses independently; transport terminal status does not supersede product result | `UNEXECUTED`; host/Artifact store absent |
| HC-39 | Client advertising only deprecated/old protocol primitives attaches to newer optional adapter | Explicit version/capability negotiation and safe unsupported state, with no invented Roots-based filesystem authority or machine grants | `UNEXECUTED`; client matrix undecided |

**Implementation boundary:** host execution authority should expose one internally stable pending-intent/Run reference and protect the actual effect. If machine adaptation is later admitted, protocol-specific ordinary multi-round-trip requests and task-level `tasks/get`/`tasks/update` remain distinct adapters, never two independent Job databases. The analytical core remains usable through direct Python without adopting this machinery. Avoid a standalone “approval microservice” or extra machine-specific Job subsystem unless a measured independent lifecycle/ownership need justifies it.

**Evidence and admission gates:** no HC-34..39 is a performed test. An actual pilot needs at least two independently authenticated consumers, real permission revocation, persistence/restart and network partition injection, an authentic source/Artifact effect, exact runtime/spec versions, and a separate competent security/conformance reviewer. Product Authority still determines the acceptable approval and persistence obligations, while any machine transport is an open option. A green documentation/route CI cannot approve this design or the runtime.


## Pinned local Explorer/path/projection fault evidence and candidate host conformance (HC-34..39)

Sixteen or more current local UI state labels are not a host FileStore access policy. The specific relevant **executed source behaviors** are [WEX-10..14](../../current-how/windows-application.md): direct external Explorer navigation is rejected while symlink entry is not recontained, and synthetic Case/Artifact fields are copied into an incoming visual card. The [direct code](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/workspace/explorer_service.py) supplies proof only for a pinned local Python service. The following **HC-34..39 are unexecuted proposed tests for any real future host/client profile**.

| Candidate negative case | Input or contested transition | Required conditional result |
| --- | --- | --- |
| HC-34 | Client submits a direct absolute path or `../` referring outside the authorized server workspace | Host rejects before enumeration/open; client-side `location_for_path` denial alone is insufficient |
| HC-35 | Authorized workspace child is a symlink/junction/alias outside the same grant scope | Every enumerate/enter/open/reveal operation rechecks effective resolved target under actual server authority; no outside file is exposed by alias |
| HC-36 | File alias target changes between listing and opening | Race is resolved through appropriate handle-based / OS-scope enforcement, or command fails with explicit uncertainty; stale earlier directory validation is never treated as a durable grant |
| HC-37 | Shared Case carries a synthetic sensitive parameter or local absolute path | Per-recipient projection redacts/omits sensitive fields and presents an authorized Artifact/Log ref, not the host path or raw private user inputs |
| HC-38 | Client reconnects while Case aggregate says success but child Step is failed | Client reflects accepted truthful composite terminal semantics and actual Step results; it must not falsely erase a mandatory failure or invent a valid final Artifact |
| HC-39 | A normal folder is chosen as Data selector under `derived_from_selector` schema, while a separate host migration assumes nested `Strategy Box Data` root | Workspace identity and actual input/output locations are resolved from the executable branch; migration must not move or duplicate user files using the historic overgeneralized path rule |

**Risk/cost qualification:** these protect boundaries that become security and data-integrity relevant **only if** a remote shared host is deployed. Current local browsing under a trusted operating-system identity has different capabilities. A bounded implementation may simply disable arbitrary host filesystem Explorer and expose approved Artifacts only; that is a valid competing way to satisfy the risk. Full symlink-junction, Windows reparse-point, ACL, race and native-browser failure tests remain **UNEXECUTED**, and no host architecture, transport or storage decision was made here.
