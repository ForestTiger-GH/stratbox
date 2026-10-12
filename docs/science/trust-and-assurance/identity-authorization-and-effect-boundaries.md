# Identity, authorization, delegation, and effect boundaries in a shared analytical workspace

**Domain:** identity and access semantics for a personally operated analytical library, trusted small-team node, future remote clients, automation, and machine consumers. **Evidence classification:** current code observations are tied to pinned sources; user intentions are explicitly distinguished from target security proposals; the authentication/enforcement services discussed here are **not claimed as shipped**. Core baseline: `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`; desktop baseline: `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. Related Science: [shared conditions and diagnostic visibility](../collaboration/shared-conditions-and-log-access.md), [effect uncertainty](uncertain-outcome-vs-observed-error.md), [capability definitions and execution](../capabilities/definitions-plans-and-execution-truth.md), and [artifact access](../artifacts/output-identity-publication-and-availability.md).

## 1. Preserving a lightweight team UX without inventing trust

The user intends Strategy Box to be a shared analytical workspace for a small group of familiar people. In normal use, a nickname suffices as the *display name* and colleagues should see shared activity: who started which task, in which conversation, at what time, and which results or failures matter to the group. The product should avoid burdensome profile forms and enterprise IAM machinery for an isolated local installation.

**This does not make the nickname a credential.** In a shared node, two people may choose identical names, one person may reconnect from two devices, or an untrusted client may claim another person's identity. Stable technical identity and trusted session attachment are necessary for attribution and effect permissions. They can be mostly invisible to the ordinary user.

Likewise, “everyone sees the team's work” is a *visibility policy for safe product facts*, not permission to read all parameters, host file paths, password-bearing logs, restricted source bytes, or another person's private resources. Two apparently competing requirements are compatible when **shared event projection** and **actual authorization** are different services.

## 2. Distinct identity and authority concepts

| Concept | What it represents | What it never proves by itself |
| --- | --- | --- |
| **User** | Durable human profile, preferences and memberships | Display name is not authentication |
| **Principal** | Security subject whose grants are evaluated; human or machine | A principal claim supplied in request body is not trustworthy identity |
| **Session** | Time-limited authenticated/attached client connection | One session is not one person; client disconnect does not imply Job completion |
| **Participant** | Team-facing projection of a human in a node/workspace | A displayed online badge does not confer file access |
| **Actor** | Initiator of a recorded action: user, automation, assistant, system | An actor kind or assistant label is not authority |
| **Worker/process** | Actual code running with OS-level privileges | “on behalf of user” metadata does not isolate its filesystem access |
| **Capability definition** | What an installed/registered operation can do | Discoverable/available is not authorized |
| **Permission/grant** | Allowed action and resource/scope under an applicable policy | Generic role is not blanket authorization to all objects |
| **Approval** | Consent to one defined risky plan, object set, version and expiry | Approval is not permanent privilege escalation |
| **Delegation** | Restricted authorization for another actor on behalf of a principal | Delegation cannot exceed the grant ceiling of its owner |
| **Resource** | Work, Thread, Run, Artifact, FileStore namespace, log or node setting | Knowledge of an object ID is not right to read its content |

A human using Windows and Android may share one principal identity across two sessions. A background occurrence can have its own actor while carrying an authorized `on_behalf_of` and restricted delegation. A process that executes the operation is still a separate OS principal. This distinction is crucial: application-grant metadata cannot restrict arbitrary Python instructions running with the same process credentials.

The terms **discoverable**, **available**, **applicable**, **authorized**, **approved**, and **executable now** describe distinct predicates. They need not become separate databases or elaborate UI enums. A safe `ActionAvailability` can explain a disabled control, while a trusted `AuthorizationDecision` is enforced at admission and effect boundaries.

## 3. Threat model must depend on the actual deployment profile

| Profile | Trust assumption | Meaningful protections | Claims that would be premature |
| --- | --- | --- | --- |
| **L0: local user, own machine** | OS account and its process are trusted | Scoped output paths, OS filesystem permissions, safe destructive effects, redacted logs | Shared remote IAM and secure isolation among people using the *same* OS account |
| **L1: small trusted node** | Known users/devices attach to one authority | Stable principals, enrollment/invite or verified platform identity, grants, object scope, action audit and scoped UI views | Nickname-only remote attribution and direct shared-file ACL by UI |
| **L2: managed remote host** | Clients reach host over an authenticated channel | Session/device binding, protected transport, expiration/revocation, host-side object/effect checks | Reliance on an unverified external host service or durable job authority |
| **L3: public Web host** | Unknown network clients can reach APIs | TLS, appropriate OIDC or secure local account policy, CSRF protection, cookie/session hardening, rate limits, server-side object/property/function checks | Public login-free write API protected only by visible UI buttons |
| **M: assistant/automation** | Machine interprets untrusted text and requests effects | Allowlisted typed operations, bounded delegated grants, plan-specific approvals, effect checks and traces | Arbitrary host shell/filesystem access from conversational instructions |

The same conceptual permission vocabulary may span profiles, but **the strength of its enforcement does not**. A malicious administrator on the executing host, or untrusted Python running with unrestricted host privileges, falls outside what a user-level `Permission` field can secure. A genuine sandbox would require OS identities/process separation/container capabilities and provider-enforced filesystem/network restrictions.

[NIST SP 800-207](https://www.nist.gov/publications/zero-trust-architecture) illustrates why mere presence on a familiar internal network is not a sufficient subject/resource authorization decision. [OWASP API Security Top 10](https://owasp.org/API-Security/) distinguishes object-level, property-level and function-level authorization failures that remain relevant even with simple roles.

## 4. What current code proves and does not prove

Current [Windows `OperationSpec`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/models.py) has flags such as `enabled`, `dangerous`, `visibility_policy`, `log_visibility`, and `ai_visibility`. These fields describe presentation/catalog intentions; they are not evidence of a trusted node-wide `can(principal, action, resource)` enforcement point. Similarly [Case author fields](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py) and [OperationalEvent actor types](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/events/models.py) establish stored author/actor metadata, but not authenticating these claims for an untrusted API request.

Two exact **static risk paths** deserve preservation:

1. `ScenarioRunCase.short_params_text()` joins key/value pairs from stored parameters into a string; the [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) uses this in a `case_started` event. In a future shared stream, an unclassified parameter may include a token, private source path, or restricted input. **No production leakage incident is asserted**; the visible code path demonstrates an uncontrolled projection boundary.
2. [`PresenceService.other_online_html()`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/presence/service.py) interpolates `display_name` into an HTML-formatted string. If remote participants could choose untrusted names, the renderer must escape or render them strictly as text. This is a target exposure condition, **not proof that remote exploitability currently exists**.

[`AppContext`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/context.py) receives node/session/user metadata from an activation/session boundary. The presence of identifiers in a context object does **not** by itself establish remote authentication strength, device enrollment or per-file Product grants. Current Windows remains a local foreground application; the shared-host security service is an unimplemented target in this baseline.

The directly callable `stratbox` core is different. A notebook/Colab Python caller executes functions with the environment's OS/process/Filestore privileges; core should not require a Strategy Box GUI login. A future managed command host can wrap those same functions in a trusted authorization boundary. **Library correctness, process privilege, and product-command authorization are different protections.**

## 5. Decision at admission and at material effect

A robust managed execution model has **two meaningful enforcement points**:

**Admission:** Does this trusted session/principal have permission to invoke the selected operation or scenario in this Work/Node? Are parameters within allowed scopes? Is the required provider ready? Does the proposed plan need a separate approval? Is there enough authority to create the intended output?

**Effect boundary:** Just before writing, overwriting, deleting, exposing a file, transferring data, or invoking another external mutation, are *current* grants, object versions, resource claims and approval still valid? A Job may have waited in a queue while its initiator lost membership. `authorized_at_submit=true` cannot grant indefinite authority to mutate future resources.

One conceptual predicate:

```text
allow = trusted_identity
    AND active_membership
    AND action_grant(principal, action, scope, current_policy)
    AND resource_grant(principal, exact_resource, effect)
    AND operation_applicable(environment, params)
    AND plan_specific_approval_if_required
    AND no_explicit_deny
```

Availability is not permission. A visible operation may be unauthorized; an authorized operation can be unavailable because the storage is disconnected. UI may report safe denial codes (no membership, out-of-scope resource, approval required, stale plan, unavailable operation) without exposing whether a protected object exists.

The effect-level recheck can be risk-adjusted: pure short-lived read-only computations may need one admission check, while long-running reading of private files, remote data transfer and destructive effects need stricter checkpoints. The policy is a Product Decision, not a hidden default embedded in core.

**Approval and permission are separate.** Permission grants the general ability to delete in some scope. Approval confirms a **specific plan**: actor, intended action, exact target set, stable `plan_digest`, expected resource revisions, expiry and policy revision. Approval to delete three files must not silently authorize a hundred after the target set changes. Core's plan/inspect/apply patterns are analogous, not proof of an installed general-purpose approval service.

## 6. Small roles, precise objects, and boundaries of OS access

A practical initial **research candidate** is small RBAC defaults (`member`, `node_operator`; optional `viewer` when a real read-only consumer exists) plus explicit action/resource/scope checks. Roles simplify setup, but their names do not confer blanket rights to private logs, every Work, or destructive operations.

Relevant actions include `thread.read/post`, `scenario.discover/run`, `job.read/cancel.own/cancel.any/retry`, `workspace.read/write/delete`, `artifact.read/publish/delete`, `logs.read.summary/technical`, `assignment.manage`, `approval.grant`, `automation.manage`, and `node.member/settings.manage`. **These are vocabulary candidates, not promised API names.**

Useful resource scopes: `node_shared`, `personal`, `work`, `run`, and `system`. Each scope has a different data audience; the physical storage adapter must enforce the corresponding OS/provider permissions where confidentiality is promised. The [NIST RBAC model](https://www.nist.gov/publications/role-based-access-controls) supports roles as permission groupings; [NIST SP 800-162](https://www.nist.gov/publications/guide-attribute-based-access-control-abac-definition-and-considerations) illustrates contextual resource attributes. Neither mandates a separate general policy engine for a small node.

**Critical negative result:** if every participant can directly mount and read a shared SMB folder, then hiding an Artifact card in UI **cannot make its bytes private**. Either the Data space is explicitly shared at OS level, or a host-mediated/OS-ACL access boundary must match the Product promise. The same applies to `FileStore` root paths: a string prefix check is not containment under `..`, symbolic links, Windows junctions, Unicode normalization, and check/open races. A fully authorized filename can still be unsafe if the resolved target is outside the allowed namespace.

A shared user may have `scenario.run` but lack `artifact.download` for a private target or `workspace.write` for a system directory. An `artifact_id` guessed from a visible URL is not permission to read it. A `node_operator` may troubleshoot shared state without necessarily reading all confidential human Work.

## 7. Shared timeline, sensitive fields, and authorization-aware cursors

The node's canonical event record can contain rich internal Run/Case/resource context. Users and machine clients should receive **server-side prepared projections** based on actual object visibility and field sensitivity. Client-side hiding through Qt flags/CSS is insufficient because the raw data already crossed the trust boundary.

Candidate audiences:

| Audience | Example safe information | Withheld unless separately granted |
| --- | --- | --- |
| `shared_node` | Shared Thread title, user display name, operation name, timestamp, terminal status and node-level condition | Raw parameters, private Work existence when protected, logs, paths and secret-bearing source names |
| `shared_work` | Allowed participants, shared milestones, permitted artifacts and source summaries | Technical details beyond the Work's scope |
| `personal` | Own drafts, personal input-validation errors and private preferences | Unrelated users' records |
| `technical` | Authorized protected per-attempt logs, traceback and incident references | Other unrelated sensitive data and credentials |
| `security_restricted` | Narrow security investigations | Broad public node notifications |

Permissions must be checked **before serialization** of an event and again at artifact/log access. A shared canonical `sequence` can remain internal, while external clients use an opaque, audience-scoped cursor. Otherwise skipped sequence numbers or counts may leak the existence of private Work. Permission changes should invalidate/rescope active subscriptions and prompt snapshot/resync; stale offline cache policy is a separate device-security question.

A shared `unread` bool is wrong when two participants read the same Thread at different times. Per-principal read cursors are distinct from the immutable shared event stream. Notification routing is also separate: one Run failure might appear in a shared timeline but require only one author's alert; an unavailable common Data root may require affected-member warnings without revealing their confidential Work names. [Related Science](../collaboration/shared-conditions-and-log-access.md) treats Condition grouping and log custody more deeply.

**Engineering safeguard:** for each important type (`Invocation`, `Event`, `Case`, `Artifact`, `LogRecord`, `Problem`, `User`, `Session`) maintain a field classification: canonical owner, sensitivity, allowed audience, retention. New model fields must **not** automatically appear in every public API because someone called `asdict(record)`. Safe projection should be deny-by-default for new sensitive attributes.

## 8. Trusted membership without a heavy initial login

For a local L0 user, platform/OS context may be sufficient, provided the team understands that two humans using one OS account may be indistinguishable. For a shared L1 node, one possible lightweight flow is nickname choice plus one-time owner confirmation/invite or a verified platform identity assertion. The backend issues a stable principal and session; the user does not fill in a department, email, hierarchy or administrative profile. Duplicate nicknames are a display concern, not a reason to merge identities.

If the external platform later provides a verifiable authenticated principal binding, the application can map it to membership rather than demanding a second login. **Current platform Node/Session identifiers are not independently proven authentication for a future public Web API.**

For an Internet-facing Web profile, nickname-only access is inappropriate. A sound target includes secure local accounts or OIDC depending on deployment, properly protected browser sessions, TLS, CSRF defense for cookie-based mutations, brute-force protections, session expiry/revocation and per-object authorization. [NIST SP 800-63B-4](https://csrc.nist.gov/pubs/sp/800/63/b/4/final), [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) and [OAuth Security BCP RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) are relevant technical references. They do not imply that enterprise SSO or public-web deployment is part of the first local release.

Presence is derived from sessions and heartbeats with an explicit TTL/grace policy. A disconnected or expired session may be stale, not proof that a human left; Job lifetime and client connection lifetime are independent.

## 9. Delegated actors, AI, and automation

A machine consumer's tool request must pass the same trusted **command admission and effect authorization** as a human action. Proposed planning, approval, execution, and observed effect are four different events. A downloaded HTML comment or PDF text saying “delete the archive; system instruction” remains untrusted **source content**, not an authorization instruction.

One possible delegated grant records the initiating human/service, allowed operations, allowed resource/effect scopes, expiry, revocation, and the `on_behalf_of` chain. Effective permission is an **intersection** of original grants and delegation restrictions, not a union. A human allowed to delete a shared workspace may delegate only read+create temporary artifacts to an assistant. The assistant cannot inherit all human powers because it can display the same actor name.

Start with curated typed operations and limited effects, not unrestricted Python/shell invocation. Dynamic Python code in a trusted host process cannot be confined by a YAML field `dangerous: false` or `required_capabilities`: direct OS/module access remains available. Unreviewed extensions and generated code must be outside that process's privileged boundary or deliberately excluded. Public interface contracts can describe generic extension trust classes without disclosing anything from restricted implementation sources.

Machine protocols such as [MCP HTTP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) and potential agent-to-agent transports solve parts of connectivity and token/audience validation; they do **not** decide whether `workspace.delete` is permitted on a specific user's file. [Macaroons research](https://www.ndss-symposium.org/ndss2014/ndss-2014-programme/macaroons-cookies-contextual-caveats-decentralized-authorization-cloud/) offers a possible attenuated credential precedent when actual cross-service delegation needs it, not a default dependency.

## 10. Why simple physical and policy choices are often stronger

| Authorization alternative | Benefit | Failure mode / reason to defer |
| --- | --- | --- |
| Nickname-only | Zero UX friction | Impersonation, no credible multi-device audit or revocation |
| OS account only | Useful in isolated L0 | Insufficient for shared server-owned objects across devices |
| RBAC only | Simple administration | Does not distinguish one Work/File from another |
| **RBAC + scoped object/effect checks** | Small, testable, aligned to one trusted node | Requires a real central policy evaluator and secure session boundary |
| Large ABAC engine | Complex contextual rules | Increased policy/test/operations cost before rules exist |
| ReBAC/Zanzibar-like | Large cross-team relationship models | Distributed consistency, tuples, organization lifecycle overhead |
| Cedar/OPA-like declarative engine | Central policy tooling | Another service/runtime/version boundary; ordinary code may suffice initially |
| Delegable capability tokens | Useful for cross-service attenuated authority | Bearer token leakage, expiration, revocation and caveat complexity |

[Zanzibar](https://www.usenix.org/conference/atc19/presentation/pang), [Cedar](https://docs.cedarpolicy.com/auth/authorization.html), NIST RBAC/ABAC and Macaroons are **comparative research evidence**, not a mandate to install all systems. A local or headless node-authority process can host a small policy evaluator; it does not require a new repository, microservice fleet or distributed authorization cluster.

One real security distinction is **the location of truth**: in-process Windows UI can govern only its own actions; a shared node needs authorization where all clients submit commands and where bytes/effects are actually accessed. Repo topology is secondary to this logical authority.

## 11. Error reporting, diagnostics, and the boundary to the external platform

Application-specific authorization failures and subject-matter validation belong to Strategy Box's execution authority, while the external deployment platform owns its Node/Session/package and confirmed platform Problem records. The fact that [AppDock's observability implementation status](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) documents certain narrow milestones does not imply a universally ready hosted identity service, generic external ProblemRecorder, or mature remote application transport.

The physical technical log lives on the **actual executing device or host**, in the authorized managed system/private area, not automatically in all users' Data folders. Shared users receive safe error type, actor label, operation/stage, affected scope and necessary action. Another participant's raw traceback, credentials, host paths and detailed parameters require separate permission. A failure of external problem registration does not justify inventing a confirmed external `ProblemRef`; preserve a local record with explicit registration status.

The local user error, shared node condition, and security-restricted event must retain different audiences. They can be causally linked without duplicating the underlying problem or broadcasting every attempt. Technical log retention and user-visible durable outcome history may differ; loss of old log bytes must not erase the historical failure.

## 12. Negative test program and source-qualified unknowns

The following are **proposed verification cases**, not tests already passed:

1. Two principals choose the same nickname; stable identities remain distinct, including across device reattachment.
2. An untrusted client forges `author_id`; authority ignores request-body claims for authentication.
3. An allowed user sees a shared Run with safe metadata, not full parameters or other participants' private source paths.
4. Guessing a private `artifact_id` cannot reveal metadata, preview, bytes or file existence.
5. A hidden UI button's server action is called directly; it is still denied.
6. `scenario.run` permission alone does not permit writing to a different owner's Data scope.
7. A grant is revoked after Job admission but before destructive commit; current effect policy is rechecked.
8. Approval binds an exact plan; a target set modified after approval is rejected/re-approved.
9. A delegated AI asks for effects beyond its grant; permission is denied despite the human having broader rights.
10. Prompt-injection text inside an analytical source is treated as data and cannot issue an effect.
11. Two authorized Runs write the same file; resource conflict/conditional overwrite prevents silent corruption.
12. A local bad form parameter does not create a global alarm; a common Data root outage does affect the team.
13. Shared event and support summary remove secret sentinels, raw paths, credentials and sensitive values.
14. Request to fetch another person's technical `log_ref` is denied without technical-log grant.
15. Device disconnect does not fabricate a confirmed Job outcome or fresh online presence.
16. External problem recorder unavailable: keep local event, no fabricated platform reference.
17. Subscription's access changes: later events and opaque cursors do not reveal hidden Work.
18. A user-provided HTML-like nickname renders as harmless escaped text.
19. Absolute-path, traversal, symlink and junction escape attempts are stopped at actual file access.
20. Corrupt state or expired audit evidence reports a degraded state, not a fresh empty user history.

Acceptance requires a real trusted authority and negative execution tests. For L3 public-web security, additional browser/session/rate-limit/CSRF testing is necessary. Object, function and **field** authorization must be verified separately. Tests cannot certify confinement of arbitrary Python code inside a privileged process without isolation.

**Open decisions:** membership/enrollment mechanism, minimum roles and object granularity, operator access to personal Work, whether a private Thread can exist, grant revocation timing, per-effect approval thresholds, cross-client offline cache, direct SMB access vs host-mediated confidentiality, raw-log retention, agent delegation, host process lifecycle, Web identity provider, policy engine need and external platform contract versions. None is settled by this paper; no code implementation or security certification occurred.

**Main conclusion:** the scientific model can honor an informal, transparent small-team experience **and** trustworthy effect boundaries, provided it separates display names from principals, shared summaries from protected evidence, and capability discovery from authorization at the moment the effect is performed.

## Source topic 05: twenty threat-profile and effect-authorization distinctions

The dated Permissions, Security and Collaboration source evaluates closed-user, managed-node, hosted-Web and machine-actor deployment profiles separately. Its **20 bounded original-to-English interpretations** preserve cases that are unsafe to collapse into one nickname or UI checkbox. They remain **research arguments and qualified future assurance criteria**, not proof of implemented identity services, Internet-facing protections or actual user-granted policy. No site-specific or restricted implementation is described here.

| Original item | Materially distinct interpretation | Research disposition | Source line |
| --- | --- | --- | --- |
| `SB-SRC-0558/SEC-01` | Permission strength should follow the actual threat profile, not a generic claim that the application is internal. | `DEPLOYMENT_THREAT_SCOPE` | L165 (`#L165`) |
| `SB-SRC-0558/SEC-02` | A trusted small team still needs stable principal IDs and object/action checks; nickname collisions and shared file writes are meaningful risks. | `KNOWN_TEAM_NOT_UNBOUNDED_TRUST` | L170 (`#L170`) |
| `SB-SRC-0558/SEC-03` | A public Web endpoint needs independent authenticated sessions, CSRF/XSS/object authorization and bounded request rates beyond internal nickname UX. | `PUBLIC_WEB_DIFFERENT_GUARANTEE` | L172 (`#L172`) |
| `SB-SRC-0558/SEC-04` | An AI/machine caller needs scoped delegation and effect admission rather than unconditional script or filesystem access. | `AGENT_DELEGATION_LIMIT` | L173 (`#L173`) |
| `SB-SRC-0558/SEC-05` | An attacker with host administrator powers or arbitrary in-process trusted Python is outside the protection of an application-only role table. | `OS_PROCESS_BOUNDARY` | L175 (`#L175`) |
| `SB-SRC-0558/SEC-06` | Membership in the internal network is not sufficient proof of individual/device trust or permission to perform specific actions. | `NETWORK_TRUST_NONIMPLICATION` | L179 (`#L179`) |
| `SB-SRC-0558/SEC-07` | A user-selected display name is presentation metadata, not a secure principal identity. | `DISPLAY_NAME_NOT_SECURITY_KEY` | L245 (`#L245`) |
| `SB-SRC-0558/SEC-08` | A publicly reachable client requires authentication and revocable sessions; nickname-only login is an incorrect authority shortcut. | `REMOTE_IDENTITY_PROFILE` | L249 (`#L249`) |
| `SB-SRC-0558/SEC-09` | Admission should check the actual authenticated principal and exact requested operation/resource scope before execution. | `ADMISSION_AUTHORIZATION` | L265 (`#L265`) |
| `SB-SRC-0558/SEC-10` | Long-running effectful work may need authorization rechecked at the actual mutation boundary, after queued policy changes. | `EFFECT_TIME_AUTHORIZATION` | L275 (`#L275`) |
| `SB-SRC-0558/SEC-11` | Capability applicability is independent of access grant: technically possible operations can still be unauthorized. | `APPLICABILITY_PERMISSION_SEPARATION` | L293 (`#L293`) |
| `SB-SRC-0558/SEC-12` | UI flags such as enabled or dangerous are descriptor hints and cannot enforce policy against another client/API path. | `UI_METADATA_NOT_ENFORCEMENT` | L299 (`#L299`) |
| `SB-SRC-0558/SEC-13` | Revoking a grant after enqueue cannot be ignored for a later shared-file mutation; the actual effect right has separate timing. | `REVOKED_RIGHT_RECHECK` | L308 (`#L308`) |
| `SB-SRC-0558/SEC-14` | Approval must bind an exact destructive plan and relevant versions; authorizing three deletes does not authorize a later hundred-file plan. | `PLAN_BOUND_APPROVAL` | L320 (`#L320`) |
| `SB-SRC-0558/SEC-15` | Shared-team incident notifications should convey safe participant/action/stage information without broadcasting full diagnostic dumps. | `SCOPED_ERROR_NOTIFICATION` | L483 (`#L483`) |
| `SB-SRC-0558/SEC-16` | Detailed error evidence and logs stay in an appropriately permissioned operational store rather than in every shared chat. | `RESTRICTED_DIAGNOSTICS` | L484 (`#L484`) |
| `SB-SRC-0558/SEC-17` | Rendering untrusted display-name text into rich HTML is a conditional future injection risk, not proof of an observed current remote exploit. | `CONDITIONAL_RENDERING_RISK` | L596 (`#L596`) |
| `SB-SRC-0558/SEC-18` | String-prefix checks on a workspace path do not establish resolved filesystem containment under traversal or symlink races. | `PATH_AUTHORIZATION_FENCE` | L685 (`#L685`) |
| `SB-SRC-0558/SEC-19` | Run-specific output names and controlled compare-and-replace avoid shared file-write races more cheaply than global arbitrary Python locking. | `CONCURRENT_EFFECT_POLICY` | L702 (`#L702`) |
| `SB-SRC-0558/SEC-20` | Internal diagnostics must distinguish missing, denied and unavailable data even if a public endpoint deliberately hides private object existence. | `INNER_OUTER_ERROR_PROJECTION` | L712 (`#L712`) |

**Counterarguments:** a fully featured Internet IAM stack is disproportionate for single-user local analytics; a local OS user identity and a closed-team principal enrollment may suffice for their real threat models. By contrast, a public remote service cannot rely on UI-only disabling or nicknames. Authorization and confirmation of a particular harmful effect are distinct even when issued by the same user. A hidden per-user artifact may require an intentionally vague public 404-like response, while internal diagnosis must retain the real permission/availability cause. In-process execution of untrusted code cannot be safely restricted by a descriptive capability flag alone; any credible isolation claim requires separate operating-system enforcement and tests. Policy choices, platform contracts and observed end-to-end conformance remain open.

**Scope limit:** twenty material source lines, not the complete 1,206-line threat study; no independent security audit, pen test or acceptance of a universal identity schema.


## Real local filesystem path behavior versus host-owned authorization — 2026-10-12

The [pinned neutral `LocalFileStore` Current HOW](../../current-how/local-filestore-missingness-and-publication-limits.md) now includes **five actually executed local temporary-filesystem characterization tests** ([CI 38188491459](https://github.com/ForestTiger-GH/stratbox/actions/runs/38188491459)). They show that setting a local adapter `root` does not itself prevent an absolute path, a relative `../` traversal or an in-root symlink from reaching a path outside that root; missing/empty/wrong-type directory listings return the same `[]`; and a producer failure after `open_write` may leave the prior file truncated to partial new content.

A **local Python FileStore root is an address-resolution convenience, not a capability or permission proof**. Keeping a general-purpose adapter permissive for trusted notebook calls can be intentional. A future Web/Windows/Android-attached host has a different trust boundary: an authenticated requester must be authorized for the *effective object and operation*, with path resolution and symlink policy at the actual effect point, independent of whatever string was shown in a UI or prepended in an unguarded FileStore. Logical `WorkspaceRef`, `ArtifactRef`, an authenticated `Run` and physical path are separate identities.

**Counterarguments and applicability:** a simple realpath-prefix check is vulnerable to time-of-check/time-of-use races where a directory or symlink changes before file access; the correct approach depends on supported OS handles, backend sandbox semantics, canonical locator restrictions, storage delegation and actual actor scope. For a local single-user notebook, demanding remote ACLs and a full server would impose cost without protecting a present trust boundary. For a shared host that accepts untrusted file operations, assuming that `LocalFileStore(root=...)` is a sandbox would be a **false assurance claim**. Exact path escape and interrupted writer behaviors were exercised only in disposable Linux CI directories, not in Windows/AppDock, SMB, Web or network filesystem profiles.

**Target design status:** identity-scoped object permissions, authorized path resolution, staged publication and crash consistency remain candidate realization mechanisms under the already accepted host requirement. They do not follow automatically from the fact that the neutral core can create directories and rename files. Whole-Research semantic conservation and security-release acceptance remain open.
