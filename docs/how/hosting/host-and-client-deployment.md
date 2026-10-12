# Host attachment and execution profiles — Target HOW-R/A/O

**Scope:** implements admitted Target WHAT [HOST-O1..O7](../../what/strategy-box/host-deployment-commitment.md), baseline `PD-SB-HOST-2026-10-12-01`. **Status:** `CANDIDATE REALIZATION / NOT IMPLEMENTED`. Host existence and both deployment arrangements are planned product direction; physical processes, versioned wire protocol, store, platform manifests and operational guarantee levels remain `BOUNDED_OPEN` or `UNRESOLVED_BLOCKING`. This mechanism must work with the independent analytical Python core and a native Windows surface without folding one into the other.

## Concrete target composition

```text
                        two potential deployment arrangements
   Web-addressable node                           Windows/AppDock host installation
   --------------------                           --------------------------------
   host app authority + core                      host app authority + core
   approved browser endpoint                      approved network/IPC attachment
          |      \                                       |
      browser  Windows/Android                 separate Windows/AppDock client
          \       /                                       |
              client capability and authorized host attachment
```

These are **two modes of hosting the same application semantics**, not two competing sources of Run truth inside a single served workspace. The Windows/AppDock host may itself have local UI; that UI is another client view of the same running host authority. A distinct connecting Windows/AppDock installation must not write the host's local JSON or pretend AppDock session continuity is app-level Job state.

## HOW-R: responsibility and minimum attachment contract

| Unit | Candidate mechanism / boundary | Choice |
| --- | --- | --- |
| Independent analytic core | Existing `stratbox` calculations, source validation, neutral domain output | **FIXED owner** |
| Host application authority | Serve recognized identity/scope, application capabilities, command admission, Run/effect history, authorized results and current state to attached clients | **FIXED semantic role**, module/process/package choice open |
| Host execution adapter | Invoke the same core domain operation used from notebook; isolate blocking work from client transport, track qualified outcomes | **FIXED meaning**, worker/queue engine open |
| Web browser adapter | Website/domain presentation and network transport with authorization and stable object links | **PLANNED profile**, frontend stack and routing open |
| Windows host deployment adapter | AppDock-managed, host-capable installation exposing an authorized attachment boundary | **PLANNED profile**, platform capabilities to validate |
| Connecting Windows adapter | Separate AppDock/Windows installation using permitted host capabilities and local native rendering | **PLANNED profile**, shared vs split repository open |
| Android client adapter | Compatible host capability consumer with mobile-specific UX and scope | **PLANNED client direction**, release timing/features open |
| External managed platform | Install, activate and manage environment/node/session according to its actual versioned public contract | **FIXED external owner**, hypothetical remote APIs excluded |

**Minimal candidate client contract** (semantics, *not* fixed HTTP paths or DTO fields): discover host identity and supported contract/capability profile; authenticate/attach within permitted endpoint; submit a uniquely identifiable operation intention under host-side authorization; receive accepted/rejected/unknown admission and stable logical result reference; query a scoped snapshot, attach to optional ordered updates, fetch authorized published Artifact bytes or a controlled unavailable outcome; disconnect without modifying accepted host execution; reattach only with fresh permission and compatibility checks. Local foreground execution can continue as its own current mode while target migration is in progress, but no read/write scope may simultaneously have two independent authoritative job writers.

## HOW-A: example consumer flows

**Browser at a configured domain:** an operator configures the external reachability and identity boundary, then an authorized analyst opens the site, sees the host and permitted scenarios, submits a statistical collection job, closes the tab, and later queries its result through a new authorized session. Whether the Job continued depends on host execution policy and host survival; tab exit by itself cannot cancel it.

**Two Windows/AppDock installations:** a host-capable installation activates and advertises only its *actually supported* connection method. A distinct client installation connects through approved platform and product boundaries, obtains a compatible application contract, and renders host-owned Cases and downloadable/openable artifacts through Windows-native UI. Local Windows filesystem paths cannot be interpreted as paths on the remote client's machine; copying the same Qt CaseStore does not transfer authority.

**Android and other clients:** a supported client first checks host compatibility/permissions; optional notification, download/open and submit controls reflect available capabilities. Heavy statistical compute remains host/core-side in the host profile. Direct Python notebook use remains independent of all attachments.

## HOW-O: failures, isolation and lifecycle

Host health/readiness, external platform activation, client connection and one domain Job's terminal result are **four separate signals**. If the host service is unavailable, clients display an unavailable/last-known qualified state. If the client loses transport after submission, it reconciles through stable intention identity instead of silently sending a second effect. If the host stops mid-effect, its result is unknown until an authoritative receipt/recovery procedure settles it. No untested exactly-once, zero-loss, process-restart or retained-byte promise is inferred.

A Web-exposed host must enforce actual identity/object/effect authorization and address transport/session/CSRF/reverse-proxy/active content risks. Windows-host attachment requires its own trust boundary even within an AppDock-managed node. Shared errors must be audience-scoped; private technical traces remain protected. Actual storage recovery, background mode, availability targets, identity provider, retention, system monitoring and operator support policy remain owner decisions.

## Target WHAT trace and design gates

| Requirement | Proposed proof point | Status |
| --- | --- | --- |
| HOST-O1 | Host process remains identifiable independent of connecting client shutdown; no Qt client required by protocol acceptance | CANDIDATE MECHANISM |
| HOST-O2 | Browser reaches authorized host through configured site/domain; supported Windows/Android client can use agreed semantics | PROFILE TEST OPEN |
| HOST-O3 | Distinct Windows/AppDock host + client installations can connect; no hidden shared filesystem prerequisite | PLATFORM CONTRACT CHECK OPEN |
| HOST-O4 | Client interruption cannot fabricate Job terminal status or duplicate admission; remote state always host-grounded | FAULT TEST OPEN |
| HOST-O5 | Same core operation callable headlessly and via host; external platform only manages its side of lifecycle | DEPENDENCY TEST OPEN |
| HOST-O6 | Denied principal cannot invoke/read protected effects and objects through any surface | SECURITY TEST OPEN |
| HOST-O7 | Missing Artifact, incompatible contract, inaccessible host and ambiguous effect represented separately | MODEL/INTEGRATION TEST OPEN |

**Blocking choices:** exact client/host network contract, allowed attachment and identity profile, actual AppDock integration, authority durability/recovery, host/client packaging and external reachability. **Bounded-open choices:** HTTP/IPC technology, DB, executor, web framework, notification channel and optional physical `stratbox-application` repo. **Reopen:** Product revision, AppDock verified published capability, selected security/deployment profile, native host/client pilot or actual fault evidence. A detailed [host-attachment LDD](../../ldd/hosting/host-client-attachment-boundary.md) supplies negative vectors without claiming they have run.

## Public AppDock schema vocabulary is not host runtime proof — 2026-10-12

A pinned AppDock Connector Manifest schema has optional `supports_remote_attach` / `supports_delegated_jobs` properties and Surface Activation schema recognizes foreground/background/detached/host-delegated values. The current Windows manifest uses **local foreground desktop only**, with no actual host/client contract. These public schema concepts can inform later AppDock integration design but **do not establish supported live host endpoints, authorization, server persistence or a remote-attach dispatcher**. Validate real AppDock runtime and version before selecting any host AppDock manifests or physical Windows package split. See [direct Windows evidence](../../current-how/windows-application.md).

## HOW-T: host adoption without falsifying former local records

Before attaching a Windows installation as a remote host client, preserve the distinction between legacy **locally executed** Cases and newly **host-admitted** Cases. Any import of local JSON history, existing Artifacts, diagnostic paths, unread flags or saved form values requires a separate explicit product/state and privacy policy. Client switching must not silently resubmit old scenarios, duplicate external effects or translate old guessed path-based Artifact records into verified remote publications. Legacy read-only display and bounded verified copy/ingestion are competing candidates, and a rejected import is a valid outcome. See [HC-17..22 transition cases](../../ldd/hosting/host-client-attachment-boundary.md).

## Verified public AppDock launch boundary — source-first 2026-10-12

[Direct Current HOW](../../current-how/appdock-activation-host-attachment-boundary.md) proves implemented ordinary `foreground/background/detached` process launch at public AppDock `a4d87c6`. `dedicated_server` defaults to background but **does not prove a listening or durable application host**. In contrast, the `host_delegated` launch path explicitly returns `BACKEND_UNAVAILABLE`, despite schema vocabulary. A future Windows-host pilot may evaluate an **ordinary process-bearing entry** and separately implement host readiness, authorized attach and Job state; it cannot assume delegated-host dispatch works on this pinned revision. This observation does not select a repository split, manifest, service, network stack or security policy.

## Host runtime credential policy — source-bound candidate, 2026-10-12

The [pinned core Current HOW](../../current-how/core-runtime-network.md) demonstrates a process-level runtime provider bundle and a local environment-to-interactive `getpass` fallback. Host work executing unattended must instead receive an **explicit noninteractive credential context**. Missing required secret material should produce a safe configuration/permission outcome, never an unplanned blocking terminal prompt. Direct Python/notebook use retains its separate interactive option. The host must define the principal/tenant scope, rotation rules, and trace audience independently of a global provider cache. The physical secret backend remains an owner/security decision; no real credential implementation is specified here.

## Diagnostic resilience and external problem-registration integration — candidate

The admitted host application remains responsible for authoritative Run/effect outcomes even if a **separate** diagnostic recording sink fails or a platform launch succeeds without a working service. The [diagnostic-boundary LDD](../../ldd/observability/host-problem-receipts-and-evidence-degradation.md) specifies a conditional registration receipt state, authentic (never invented) platform ProblemRefs, scoped shared Conditions, bounded bootstrap/crash evidence, audit-before-effect policy and support export; none constitutes a deployed AppDock recorder or approved default retention. A failed diagnostic registration cannot retroactively erase an established domain result; an unknown external recording acknowledgement requires reconciliation before assuming nonacceptance. Application policy must identify which high-risk actions require durable audit as a precondition. Native Web/Windows cross-client, recorder and fault evidence remains mandatory for release.
