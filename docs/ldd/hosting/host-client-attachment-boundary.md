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
