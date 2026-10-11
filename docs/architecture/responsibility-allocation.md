# Strategy Box — engineering responsibility allocation

**Product baseline:** [`PD-SB-HOST-2026-10-12-01`](../what/strategy-box/host-deployment-commitment.md): host capability **accepted as planned**, with Web-accessible and Windows/AppDock host-client installation profiles. **Architecture status:** protected logical ownership, conditional physical realization (`PA-SB-2026-10-12-HOST-ALLOCATION-CANDIDATE`). **Current reality:** [pinned Windows application](../current-how/windows-application.md) provides a local foreground Qt-run model; this page does not claim a delivered host or a released network protocol.

## Distinct semantic owners

| Responsibility | Authoritative owner or planned role | Control and failure boundary |
| --- | --- | --- |
| Bank/macro publications, classifiers, method, analytic calculation and evidence qualification | **Existing** independent `stratbox` analytic core | An operation can be called directly from Python/notebooks. Browser/Windows/mobile transport must not change domain correctness or mislabel source failure as absent economic data. |
| Neutral file, network and provider ports | **Existing** `stratbox` core + supplied backend | Transport failures, file bytes and storage effects must remain distinguishable from domain validation. |
| Application scenario/operation composition and user-facing parameters | **Planned host application authority** for remotely hosted work; existing Windows local app still owns its own historical local cases | The *same* semantic operation should run in both allowed host profiles. A UI widget or generic client cannot independently redefine effect/step outcome. |
| Accepted Run/Case/Job intention, step state, authoritative result and effect reconciliation | **Planned Strategy Box host** (one application truth per served namespace) | Connecting-client disconnection must not change host-owned truth. Job host-stop recovery, cancellation, retry and guarantees remain policy/design choices. |
| Application identity, scoped object access, approvals and audience-safe event projections | **Planned Strategy Box host** for remote/shared profile | Host checks the actual principal, object and effect at mutation and read. Visual disabled controls, actor display names and AppDock session hints do not authorize data access. |
| Web-accessible endpoint and browser UI | **Planned Web host deployment** and a Web presentation owner (physical repo undecided) | Host is reachable through its configured authorized domain/site; actual TLS, login/session, browser security and deployment need separate approval and native tests. |
| Windows/AppDock host-capable installation | **Planned Strategy Box host role**, packaged/managing via **external AppDock** only as supported by released contract | Host can be part of a Windows installation, without using a connecting Windows window as the sole execution authority. Actual process/service and AppDock manifest are undecided. |
| Distinct Windows/AppDock connecting installation | **Planned Windows client role**, code owner `stratbox-windows` or separately selected successor | Client renders authorized host-owned cases/results; it cannot interpret a host's absolute file path as its own local path. One versus two Windows repositories remains open. |
| Android remote client | **Planned client direction**, owner and feature range undecided | Semantically compatible permitted host access and mobile UI; no assumption of local Python runtime or an existing release. |
| Client-native visual controls, layout, access to OS-local files and clipboard | **Each surface owner** | Device/browser-specific code may differ; no UI owns authoritative host Run/Job state. |
| Product Artifact references, availability and permitted sharing | **Planned host application authority** for remote scope, neutral storage/backend for bytes, **core** for analytic evidence | Source input identity, verified result, staged bytes, committed Artifact and rights are different; missing bytes are not an empty valid report. |
| Diagnostics, safe incident distribution and technical logs | Core for domain diagnostics; host for scoped app/events; external platform for install/node diagnostics | Only audience-safe notices are broadly projected. Restricted log paths and raw exceptions require narrower rights. |
| Node/install/package lifecycle, local runtime activation, platform-defined Data roots, platform health | **External AppDock**, to the extent explicitly supported by its released versioned contracts | AppDock does not own Strategy Box domain calculations, Case terminal meanings, host authorization or validated Artifact publication. |

A host is an **admitted product capability** and a **logical owner role**. A separately named `stratbox-application` repository, host process, single or split Windows deliverables, database and transport are **implementation allocation variables**. New physical components should be justified by independent deployment/release, availability, trust or lifecycle demands rather than merely replicating conceptual entity names.

## End-to-end owner and failure examples

**Domain operation from notebook:** user invokes `stratbox` directly, obtains typed domain result or bounded exception; no host UI, AppDock session or Web API prerequisite. This preserves the current independent-core boundary.

**Browser submits hosted statistical job:** Web view obtains a permitted host capability and submits a logical intention. Host owns admission and its result; execution adapter invokes `stratbox`, file backend supplies bytes, and host reports the actual published/partial/missing Artifact state. If browser tab closes while host remains operational, the host-owned outcome does not become `cancelled` simply because the client disappeared.

**Windows/AppDock installation B attaches to installation A:** A owns authoritative host state; B shows a Windows-native projection and may download permitted bytes. The platform manages the installations/activation in its actual supported scope. A running AppDock session or manifest flag is not itself proof that A serves a working authenticated host endpoint.

**Technical failure:** publisher rejects input, analytic result fails, Artifact save lacks confirmation, host becomes unavailable, client loses network and external platform reports degradation are **separate** observations with separate owners. A technical log can exist while an Artifact was never published. Ambiguous external write must stay unknown until a valid reconciliation fact exists.

**Historical local Case:** the existing per-event `unread` boolean, UUID Case status and guessed file paths are legacy local records. A host upgrade must not silently import them as host-authoritative work or replicate stored form-value dictionaries without sensitive-field policy. [Host LDD HC-17..22](../ldd/hosting/host-client-attachment-boundary.md) outlines conditional transition tests.

## Protected allocation decisions and test obligations

| Choice / concern | Status | Evidence/decision needed |
| --- | --- | --- |
| Host is necessary; both Web/domain and Windows/AppDock host-client profiles are target | **PRODUCT_DIRECTION_ACCEPTED** | Product owner direct decision `PD-SB-HOST-2026-10-12-01`; remains **NOT IMPLEMENTED** |
| Independence of analytic core and separation from external platform ownership | **FIXED ARCHITECTURAL BOUNDARY** | Core import/test and exact public platform contract verification |
| Host logical application state owner vs individual connecting client | **TARGET ROLE FIXED** | HC-03/04/05/12/13 and actual hosted acceptance tests |
| One Windows repository with role-selectable host/client versus two repositories | **BOUNDED_OPEN / PRODUCT DECISION** | Real two-installation prototype, release coordination, AppDock support and operational comparisons |
| Host process, separate package or service and `stratbox-application` physical extraction | **BOUNDED_OPEN / PRODUCT DECISION** | Headless import, independent lifecycle, multiple consumer, version and failure ownership evidence |
| Identity provider, remote connection protection, security labels and host exposure | **UNRESOLVED_BLOCKING FOR RELEASE** | Security owner policy and tested authenticating/authorizing live endpoint |
| Durable Job schema, multiuser audit/retention, crash-after-effect, host shutdown and restart | **UNRESOLVED_BLOCKING FOR GUARANTEES** | Product/Risk decisions and crash/fault/restore test evidence |
| Exact AppDock host/client manifests, detached runtime support and remote attachment | **EXTERNAL CONTRACT DEPENDENCY** | Schema support is insufficient; verify real platform runtime and versioned conformance |
| Complete migration of local file/Case history | **OPTIONAL / OWNER DECISION** | Explicit legacy/current identity/consent and source-of-truth transition policy |

**Verification meaning:** HC-01..22 in [host client-attachment LDD](../ldd/hosting/host-client-attachment-boundary.md) are unexecuted candidate tests; the existing CI structural Research check cannot certify hosted execution. Reopen on a changed Product Decision, source code or platform contract, real security profile, failure tests or meaningful second consumer prototype. This page allocates WHAT/HOW concerns without claiming physical implementation.
