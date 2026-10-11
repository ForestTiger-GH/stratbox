# Headless analytical hosts, browser security, and state persistence trade-offs

**Scientific scope.** This article examines when a local analytical desktop application needs a separately running application authority, how browser and remote clients can observe the same Work without becoming its owner, and which persistence, security and deployment models are proportionate. **Status:** research-qualified architectural comparison, **not** an approved host repository, public deployment, API, database product choice, or implemented feature. The directly observed Windows baseline is [stratbox-windows at 959e9c4](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b).

## 1. The actual boundary: a client lifetime is not a Job lifetime

An analytical operation in a foreground Qt process can be useful without a server. The [current Qt coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) owns one QThread-backed active Case and rejects another concurrent submission. Its [runtime bootstrap](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) directly imports that Qt coordinator. The [five JSON history projections](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) persist recent cases, events, artifacts, logs and assignments. Their implementation explicitly disclaims database-grade durability; a failed JSON decode returns an empty list, and writes do not use a coordinated cross-file transaction.

These facts support **local foreground execution**, not claims about detached Jobs, concurrent remote users, automatic restart recovery, a shared transactional history or web authentication. The [pinned installed manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) advertises a Windows-local foreground desktop surface; remote service support cannot be inferred from its presence or artifact declarations.

A truly detached job requires an authority that survives browser-tab shutdown and disconnect, claims work independently of the UI request, records each execution transition durably, reconstitutes state after failure and exposes access-scoped snapshots. A proposed acceptance witness is: submit one Job, close every client, observe server-side progress, reopen through another authorized client, resolve the same immutable Job identity and final verified output, then repeat across a host crash with outcome uncertainty represented rather than silently converted to success.

## 2. Four competing arrangements and their actual cost

| Arrangement | Legitimate benefit | Failure boundary | Appropriate conditions |
| --- | --- | --- | --- |
| In-process desktop executor | Minimal deployment, immediate local access, no server operations | The UI process and Job share fate; single-client state and cancellation limitations | Personal interactive analyses with openly stated foreground-only semantics |
| Desktop with a local companion service | Process independence; durable local Job authority is possible | Extra IPC, installation, upgrade, service recovery and migration work | Local runs must survive GUI closure; no external browser promised yet |
| One product-owned headless application host | Shared Work/Job/Artifact authority, server-side permissions and multi-client projections | Authentication, persistence, worker isolation, backup, migrations and incident response become first-class | Actual remote or web multiuser product need |
| Remote desktop/GUI streaming | Reuses existing Qt UI with minimal product-API design | Inherits GUI/session lifetime, accessibility and filesystem assumptions, weak cross-device semantics | Administrative access or narrowly scoped interim workaround, not a browser product |

A separate repository or service boundary is justified by **independent lifecycle and authoritative state**, not by the word “host”, the existence of Linux, or the desire to draw a new component diagram. Source research proposed distinct host and browser codebases; the organizational boundary remains a Product Decision. No additional source tree should be treated as existing solely because this design appears plausible.

A second disagreement concerns ownership. An external managed platform can provision a Node, install distributions, supervise process uptime, inject permitted environment bindings and route health without thereby becoming the authority for a Strategy Box Work acceptance state, bank result, application permission or artifact publication. Conversely, a product host must not reinvent distribution, machine management or external platform account control. A useful test is: **who may issue and reconcile the final app-level mutation when two clients disagree?** That is the application authority.

## 3. Work identity and client-neutral contracts

Shared identity must be independent of display name, process PID, browser connection and physical path. Distinct identities can include Thread/Work, Run, Job, Attempt, event sequence, artifact version and the actor who actually requested an effect. These distinctions do not force a new table for each concept: their persisted separation is justified when ownership, retry safety, visibility, lifecycle or recovery differs.

The browser should send a typed command against an authoritative resource revision and then read a qualified representation. A suggested **candidate**, not implemented API, is:

```text
command: submit known capability + validated parameters + principal + idempotency key
result: accepted / rejected / input_required / unknown, stable Work and Job refs
read: access-scoped snapshot at sequence N
stream: authorized changes after N, or explicit resynchronization
artifact: opaque ID + permitted actions, never an unverified server path
```

A client-disabled button is not authorization. Each mutation requires current object-level authorization and revision preconditions; each artifact download must recheck visibility. A stable idempotency key constrains *admission duplication* only within a declared retention and backend contract: it does not prove exactly-once execution of uncoordinated external effects. Distinguish client request replay, Job deduplication, Attempt retry, side-effect receipt and domain acceptance.

## 4. HTTP and event transport: why simple may be stronger

Ordinary command/response HTTP plus server-to-client event streaming fits the dominant traffic: Job admission and cancel are occasional mutations; progress, messages and completion are server-originated observations. [Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) provide event IDs and automatic reconnect semantics in browsers. But an event ID or `Last-Event-ID` alone does not guarantee lossless replay, valid authorization after rights change, infinite retention or ordered multi-tenant delivery.

A robust consumer route is **authorized snapshot at sequence N → filtered event subscription after N → detect cursor expiration, authorization change or missing sequence → obtain a fresh scoped snapshot**. The server must define ordering scope: a globally increasing internal sequence need not disclose activity by other users. A filtered, opaque cursor may be safer than exposing global event counts; links to events should be reauthorized after access revocation.

WebSocket is valuable for genuinely bidirectional low-latency collaboration or a terminal-like interactive stream. For status and occasional mutations it adds connection authentication, reauthentication, reconnect, backpressure and protocol complexity without proving better consistency. Similarly, browser offline state is a *possibly stale projection*. Show the last authorized snapshot as stale and restrict shared mutations until connectivity and authorization recover rather than silently merging writes.

## 5. Authentication is not authorization

For a separately published browser host, an authenticated session must be enforced for every sensitive resource and state change. An OIDC identity provider can establish **who** has logged in; Strategy Box separately decides what that principal may do with a specific Work, Node, dataset, log or artifact. Local-account management is a competing air-gapped profile and creates its own password bootstrap, MFA, recovery and audit burden.

For a first-party sensitive browser interface a server-side **backend-for-frontend** session is a defensible default: access/refresh tokens remain on the server; the browser holds a short-lived opaque session cookie with `HttpOnly`, `Secure` and an appropriate `SameSite` policy. The [OAuth 2.0 for Browser-Based Applications BCP, RFC 10017](https://www.rfc-editor.org/rfc/rfc10017.html) distinguishes BFF, token-mediating and browser-only OAuth architectures, with different threat trade-offs; it is not evidence that any one implementation is already shipped. Cookies still require CSRF controls on mutations, trusted origins, careful proxy headers and session invalidation. TLS, authorization tests, upload and error protections remain mandatory.

External exposure should fail closed if authentication, public-origin validation or TLS-edge policy is absent. Reverse proxy, certificate management and allowlisted forwarded headers are *deployment responsibilities*; any claim that an external platform supplies them is conditional on a specific implemented contract. A private loopback development profile has a materially smaller exposure surface than a LAN or public hostname.

## 6. SQL profile debate and storage authority

The concrete requirement is durable, transactional application metadata: principal/session bindings, Work and Job admission, Attempts/leases, accepted events, approvals, read receipts, artifact references and recovery markers. Large Excel/PDF/CSV/ZIP objects and large operation logs have distinct byte-storage, retention and scanning concerns. Putting both in one database merely to have one file is not a semantic requirement.

| Model | Strength | Important limitation |
| --- | --- | --- |
| Existing JSON projections | Transparent, easy prototype inspection | Malformed-file ambiguity, no multi-file atomic transaction, no concurrent claiming |
| Host-local SQLite behind a single authoritative service | Embedded deployment, ACID transactions, minimal infrastructure | Must consider writer contention, backups, host-local file ownership and process topology |
| Host-managed PostgreSQL | Multi-process write concurrency, operational tooling and mature transactional service boundary | Installation, upgrades, administration, resource consumption and backup coordination |
| Database file directly mounted by remote clients | Apparent convenience | Network filesystems can violate locking/latency assumptions and bypass application authorization |

The [SQLite network-filesystem guidance](https://www.sqlite.org/useovernet.html) describes hazards of shared database access over a network filesystem; [SQLite's appropriate uses guidance](https://www.sqlite.org/whentouse.html) supports embedded/single-host designs. Choosing PostgreSQL merely because the client is a browser is an **over-strong inference**: workload, writer topology, availability and administration determine the appropriate engine. Both are candidates; their observed transaction behavior and restore drills matter more than name recognition.

Use one application-facing state contract even if multiple implementation profiles are eventually authorized. Avoid silently divergent consistency semantics between embedded and managed deployments. Durable Job claims need tested lease expiry, fencing against old workers, interruption recovery and a distinction between **outcome unknown** and **definitely failed**.

## 7. File rooms and artifact identity

A single unrestricted shared folder leaks personal uploads; a fully personal folder scheme duplicates common official datasets and inhibits collaboration. The research proposed four logical scopes, which may be implemented using different physical backends:

| Scope | Purpose | Default safety concern |
| --- | --- | --- |
| Shared/node | Approved common inputs, datasets, published results | Group visibility, conflict, publication rights |
| Personal | Drafts, uploads, private analyses | Per-user ACL and separation from global indexing |
| Run | Temporary work, partial exports, staging and provenance | Cleanup, cancellation and partial-publication controls |
| System | Internal state, caches, service logs and secrets references | Never a public Explorer root |

The client refers to `FileRef`, `WorkspaceRef` or `ArtifactRef`; the host validates the authorized scope then resolves a physical storage backend. Free-form absolute server paths, directory traversal (`..`), symlink escape and unauthenticated static `/workspace` mounting are separate threats. Uploads require content validation beyond filename and `Content-Type`, size/decompression limits and untrusted-parser isolation. Previewing active content inside the logged-in web origin can create an XSS boundary; sanitize or isolate previews, and fall back to download where safe rendering is unavailable.

A temporary output, a successful calculation, a readable file and a **published Artifact** are four different states. Publication should validate content, hash and metadata, reconcile the storage move and catalog transaction, and preserve orphan cleanup evidence. Host restart must not declare a partially written document published simply because a filename exists.

## 8. Reliability, backup and security failures

| Failure | Correctly scoped behavior | Disallowed inference |
| --- | --- | --- |
| Browser closes after submit | A detached accepted Job continues where supported | Every foreground Qt Job survives client closure |
| Worker crashes during effect | Record Attempt loss; reconcile effect receipt and source state | Unknown effect means safe automatic retry |
| Database temporarily unavailable | Node/application degraded; protect confirmed state | Empty history means nothing happened |
| Artifact metadata commit fails after bytes appear | Unpublished/orphaned bytes are reconciled | Output exists, therefore visible and accepted |
| Event stream loses cursor or permission | New authorized snapshot, with gap visible | Timestamp sorting reconstructs all events |
| Restore from split DB/byte-store backups | Reconcile generation IDs, hashes and manifests before unfreezing | Separately successful backups form one consistent snapshot |
| Shared upload contains malicious archive | Quarantine and bounded expansion/scan/parse | Extension or MIME header guarantees safety |
| Permission changes mid-stream | Reauthorize reads, revoke active streams if necessary | Login at subscription start authorizes indefinite access |

Health needs separate process liveness, application readiness and degraded component status. Logs for requests and effects require correlation IDs but should redact credentials, raw session tokens, sensitive parameters and unneeded contents. Security audit of rights changes is distinct from user-facing event cards and debugging traces. Retention differs for long-lived case conclusions, medium-lived logs and short-lived worker scratch/presence.

## 9. Operational simplicity is a testable quality, not an aesthetic slogan

An ASGI-like Python host with isolated workers is one plausible integration with Python analytical core. Choosing a particular web framework, proxy, broker, container or orchestration suite before an acceptance profile creates deployment cost without increasing semantic correctness. A single-node durable-job table and leases may suffice before a message broker; high worker count, independent services or cross-node demands may justify a broker later. A container is a delivery method, not evidence of application isolation or transactional effects.

Useful falsification tests: (1) disconnect and reconnect during fast events; (2) crash between external effect and receipt persistence; (3) revoke artifact permissions while its preview is open; (4) two clients race to cancel a job and edit an assignment; (5) run disk-full, DB corruption and restore mismatch; (6) attempt traversal, symlink escape, CSRF and malicious archive upload; (7) measure CPU/memory and administrative footprint at one-user and multiuser loads. Reference checklists such as [OWASP ASVS](https://owasp.org/projects/asvs) are control frameworks, not substitutes for threat-specific execution tests.

## 10. What remains unresolved

**Observed:** only a local foreground Windows surface and an independently importable core are evidenced by the pinned implementation. **Research-supported conditional conclusion:** a separately living product application authority becomes valuable when detached Jobs, multiuser history and remote clients are actual requirements. **Product Decision required:** host ownership and repository/lifecycle, authorization profiles, external platform division, whether local desktop is always host-backed, SQL engine per deployment profile, browser exposure policy, guarantee levels, user file scopes and backup retention. **Negative conclusion:** remote desktop is not equivalent to a browser product; a public web interface, BFF session, OIDC, SSE and PostgreSQL are not proven merely by describing them.

Related maintained explanations: [semantic portability](../surfaces/semantic-portability-and-client-authority.md), [authorized event cursors](../collaboration/authorized-streams-read-cursors-and-private-work.md), [shared-state backup epochs](../state-and-recovery/shared-state-backup-generation-and-retention.md), [artifact publication](../artifacts/output-identity-publication-and-availability.md), [execution recovery](../work/admission-planning-resource-scheduling-and-recovery.md), [permissions](../trust-and-assurance/identity-authorization-and-effect-boundaries.md). Reopen this article on a real host baseline, accepted deployment profile, proof of platform capability, new access-control semantics or fault-tested recovery evidence.

## Original Web/host failure doctrines: twelve source-addressed cautions

The frozen [2026-10-07 Web/self-hosted research, §§144–155](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2526-L2576), original SHA `cd5a3126fdf1f3a0eafd1f96d20e97e86616fd6a`, proposes twelve design pitfalls. Their meaning is retained below as **source-row-traced English research**, not proof that the relevant Web host, identity provider, message broker or client is already deployed.

| Original source item | Research failure mode | Scope and interpretation | Original heading |
| --- | --- | --- | --- |
| `SB-SRC-0038/ANTI-144` | Embed production web server inside a Qt window | Runtime lifecycle and background truth would collapse into a closable UI process | [L2528](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2528) |
| `SB-SRC-0038/ANTI-145` | Treat JSON history files as the authoritative shared database | No coherent multiuser mutation, revision or crash durability is established | [L2532](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2532) |
| `SB-SRC-0038/ANTI-146` | Expose absolute server filesystem paths directly to browser clients | Violates logical workspace/object authorization and portability | [L2536](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2536) |
| `SB-SRC-0038/ANTI-147` | Publish the entire workspace directory as static web content | Bypasses per-artifact visibility and intended access enforcement | [L2540](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2540) |
| `SB-SRC-0038/ANTI-148` | Keep access credentials in browser localStorage by default | Increases script-accessible token exposure; use appropriate session/cookie threat analysis | [L2544](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2544) |
| `SB-SRC-0038/ANTI-149` | Trust a disabled or hidden frontend action as permission enforcement | Server must authorize principal/object/effect at actual operation | [L2548](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2548) |
| `SB-SRC-0038/ANTI-150` | Hard-wire a Linux host into the domain algorithm model | Domain core should remain independent of deployment OS | [L2552](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2552) |
| `SB-SRC-0038/ANTI-151` | Create a separate execution engine for background jobs | Shares need for one governed Work/Run/effect and idempotency authority | [L2556](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2556) |
| `SB-SRC-0038/ANTI-152` | Broadcast all failures to all users on a node | Cross-user problem notice must filter and redact by audience | [L2560](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2560) |
| `SB-SRC-0038/ANTI-153` | Expose raw traceback and internal paths to regular users | Diagnostic evidence has a stricter reading and retention policy | [L2564](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2564) |
| `SB-SRC-0038/ANTI-154` | Choose WebSocket solely because progress appears realtime | SSE/long-polling may be sufficient; choose transport against actual interaction needs | [L2568](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2568) |
| `SB-SRC-0038/ANTI-155` | Deploy Kubernetes, Redis or Kafka before workload evidence warrants them | Operational complexity and failure modes increase without independent benefit | [L2572](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md#L2572) |

**Material disagreement:** the original preferred a separately persistent headless host and eventual additional repositories; the primary annotated developer response still treats closing a **local foreground** client as ending its local computation and makes the physical repository plan tentative. These are separate operating profiles. 'Kubernetes/Redis/Kafka too early' is proportionality guidance, not a permanent rejection when load or distributed authority eventually justifies one. 'Never localStorage' is security policy advice tied to a browser-threat model; it does not replace concrete tested cookies/tokens/session/CSRF choices. WebSocket may be appropriate for bidirectional streaming later, but a basic progress feed does not itself require it.

**Required future proof:** demonstrate authenticated Web profile, authorization before effect, filtered event stream/reconnect, correct Artifact download, resource/queue ownership after client disconnect and diagnostic redaction under tested faults. This 12-item register is not equivalent to full conservation of the 2,923-line original.
