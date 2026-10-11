# Whole-system architecture: authority profiles, physical alternatives and evidence gates

**Scientific scope:** combine a Python analytical library, an already working local Windows interface, prospective persistent application authority and optional Web/Android consumers into one coherent product **without treating names in a diagram as mandatory services**. The question is which semantic fact belongs to which owner, which guarantees a selected profile offers, and what evidence must precede any physical deployment decision. **Status:** dated 2026-10-09 cross-theme research synthesis re-evaluated against later research alternatives; not adopted Product WHAT/HOW, not a working headless host and not a passed assurance release.

**Frozen implementation references:** [core `8459dc5`](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580), [Windows `959e9c4`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). The original Whole-System 03 study used other intermediate public-code revisions and proposed physical roles; every claim below is bounded to actual observed source, research candidate or unresolved choice.

## 1. An analytical product has two interacting truth axes

**Data/Knowledge:** publication authority → specific source bytes/vintage → semantic observations/registry definitions → qualified datasets/methods/results/claims → verified Artifact with provenance. **Work/Execution:** user intent and authorized goal → immutable selected plan → admitted Run/Jobs/Attempts → observed side effects and diagnostics → assessment, acceptance and closure.

Their intersection is **AnalyticalResult + exact evidence + effects + Artifact + Work acceptance**. A genuine official published statistic can still be out of date; a correct calculation may not be authorized for dissemination; a finished workbook may not satisfy the commissioned Work; a successful file write does not prove the model's economic interpretation. Keeping both axes relates their claims without forcing every source, Work, Attempt and file into an independent service.

The same source snapshot may support two analyses, and one result may have several rendering versions. A direct notebook invocation may simply return a typed Result without managed Work or an AppDock session. A managed multi-client Work, conversely, requires one authoritative state/authorization/effect admission point when that mode is released. These are *profiles*, not contradictory banking algorithms.

## 2. Five logical owners define the dependency rule

| Responsibility | Meaningful authority | Proven/current boundary versus candidate |
| --- | --- | --- |
| Economic methods, subject schemas, source/mapping and bounded proof | `stratbox` Python domain core | Independently callable; varied domain-specific Request/Result, no universal public Operation catalog certified |
| Work, Thread, Scenario curation, Runs/Jobs, approval, shared artifact index and collaboration | Strategy Box application authority | Present partially in Windows; future Qt-free host/local service is a strong logical proposal |
| File content, network request, rename/copy/delete and effect receipts | Concrete storage/transport/executor adapter under policy | FileStore and local runners exist; arbitrary backend atomicity and cross-file transactions are **not** proven |
| Installation, managed roots, Node/Session, process supervision and platform problems | External application platform through exact published/verified contracts | Windows local activation observed; future remote host/SDK operations remain separately conditional |
| UI navigation, accessibility, drafts, local OS actions, forms and safe projections | Windows, Web or Android client renderer | Windows Qt current; Web/Android/host consumer not yet certified |

**Dependency direction:** core → no GUI/app/managed-platform internals; application → neutral published core/ports; clients → application command/query/projections rather than direct shared DB; external platform → supported lifecycle and roots; machine consumers → authorized application entry. A platform Node is not a bank Work; Qt `QThread` is not canonical durable Job state; an AI suggestion is not permission or a receipt.

Semantic owners may coexist physically in a modular monolith, local Python host or one managed environment. They must not independently claim incompatible shared mutation outcomes. A physical new repository becomes reasonable only with independent consumer, release cadence, runtime fault domain, security boundary and tests—not because a whiteboard acquired another rectangle.

## 3. Current drift and the real first engineering gate

Direct dated source inspection revealed:
- Core distribution metadata claimed `0.8.0`, while the studied Windows dependency and AppDock manifest required `stratbox==0.2.1`.
- Windows manifest contract revision `4.0` differed from smoke tests expecting `3.0` with earlier field names. This is a **static logical assertion mismatch**, not an independently executed failure result.
- Windows [bootstrap](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) assembles a Qt-specific coordinator, and [scenario execution](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) is sequential/one active foreground context rather than a tested shared scheduler.
- [Five history JSON collections](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) are independently overwritten, and malformed history can appear empty. Background/presence/assignment classes contain useful surface scaffolds, but do not demonstrate real multiuser delivery, signed auth or durable automated work.

These form a concrete **baseline sanitation candidate**, not evidence that the entire desktop is unusable. The exact Windows and core package/test/manifest/release contract needs reconciliation and clean-install/CI smoke on the chosen environment. API backward compatibility can be intentionally broken under the project policy; separately retained valuable user records need an explicit one-time migration/export or authorized disposition.

## 4. Logical state and physical hosting are separate decisions

A future local Qt-free application authority could be:
- **Embedded local application module:** one process with a Qt adapter and a neutral application layer; honest when UI closure interrupts execution.
- **Independent local headless process:** same semantic service with its own lifecycle, state, IPC and worker admission; can outlive a GUI if actually installed and supervised.
- **Team host with authorized clients:** one authoritative Node/workspace/tenant scope serving Windows/Web/Android through safe remote API and actual authentication/object ACL, potentially multiple workers.
- **Distributed workers/HA:** conditional on fault/throughput/availability needs; adds leases, fencing, failover, partition behavior, coordinated recovery.

The historical Topic-09 synthesis preferred a small local headless service, then a second browser consumer, and later Android. It also discussed a possible separately named host repository. **Neither a new host repository nor a mandatory client-package/design repository has been accepted.** A new dedicated `stratbox-host` process is different from an AppDock platform host and from the existing desktop; naming alone cannot establish installed service readiness.

A repository/package/process comparison asks: who owns the semantic contract, who can be deployed and restarted independently, which dependencies differ, who trusts whom, who tests it, and who pays the complexity. An executor may be a subprocess without its own Git repository; a shared client DTO package may have no always-on process.

Avoid launching broker, distributed workflow engine, graph database, microservice mesh, global CAS and scheduler service by default. They may be useful after concrete cross-client load/security measurements, but are not architectural invariants.

## 5. One authority with different kinds of persistence

The application maintains durable accepted Work/Run/Job/effect/approval/Artifact catalog truth; reconstructible projection/event-feed indexes; and disposable/personal client state. Statistical source/registry snapshots and their rich evidence remain domain responsibilities, with physical bytes held by a verified provider.

The historical original recommended **local SQLite/WAL metadata authority** with a possible future PostgreSQL server profile and transactional current state+events+outbox. This is a coherent *candidate*. Later user-oriented storage studies explicitly allow a **single-writer atomic file state or append-only journal/snapshot** first, using the external platform's managed storage provision. These are **competing physical recommendations**, not two voted implementations. Both must meet their *claimed* revision, idempotency, corruption, backup/recovery and effect-intent guarantees; if provider capabilities are weaker, downgrade the service promise or block the risky effect.

For SQLite WAL, local-host storage and API-mediated clients differ from multiple clients directly opening a DB across a network share; see [SQLite WAL limitations](https://www.sqlite.org/wal.html). For a file store, `rename()` on an abstract interface is not automatically crash-atomic on every provider. No SQL transaction commits an independent XLSX/remote REST effect automatically. Publication needs staging, byte integrity, a catalog visibility boundary, receipts and possible reconciliation.

A backup of metadata alone cannot prove that every referenced source/Artifact byte was retained. Cross-store restore needs a coherent backup epoch and verified manifests; a clone that reuses the old Node/job identity risks duplicate scheduled/destructive effects and may need a new authority generation/fencing. Read models must not turn history corruption into an invented empty state.

## 6. A minimal cross-boundary contract map

| Contract family | A bounded responsibility and discriminator |
| --- | --- |
| **Domain Operation and typed Request/Result** | Stable subject meaning, units, applicability, source provenance, explicit partial/missing/error/effect profile |
| **Source/Registry/Dataset version** | Exact observed publication content, definition/mapping/effective time and qualified derivation |
| **Scenario/Scheme and resolved ExecutionPlan** | Curated human use or typed reusable composition versus frozen params/sources/bindings/effect set at one launch |
| **Admission/Run/Job/Attempt** | Verified principal, idempotency/revision, resource claim, start and terminal evidence distinct from user intention |
| **EffectIntent/Receipt and ArtifactRef/Manifest** | Physical modification confidence, committed byte generation, current materialization and authorized publication |
| **Authorization/Approval** | Principal × action × object × effect, plan revision and real pre-effect revalidation |
| **AutomationSpec/TriggerOccurrence** | Due/source/event/condition identity, timezone/DST/misfire and associated ordinary Run, not invisible second executor |
| **Projection/ActionDescriptor** | ACL-scoped object/ref, status, available actions, reason, revision and opaque event cursor, not UI truth |
| **Problem/diagnostics** | Coded domain/execution failure versus platform health/problem, correlation and audience-safe references |
| **ExtensionDescriptor/Binding** | Installed/discovered/compatible/selected/activated/bound/ready/granted states with per-kind conformance |
| **Platform activation and health** | Only exact external Node/Session/Data/lifecycle contracts actually implemented and validated |

All names are **roles and provisional shapes**, not a published HTTP route set. JSON Schema can validate control-envelope structure but cannot prove source authenticity, economic meaning, side-effect idempotency or current authorization. Changing an Operation semantic revision and changing its package build are different events; an in-flight Run retains the effective plan/binding it accepted.

## 7. Thirty-two cross-system invariants and their proof categories

The original proposed **INV-01–INV-32**. Their content spans:
- **01–08 identity/owners:** single authority per scope, Qt-free domain, managed execution lifetime, one managed spine, distinct definition/Run/Attempt, Work vs Thread, curated Scenario and independent acceptance.
- **09–15 uncertain effects and trust:** explicit UNKNOWN, backend unavailable not empty, destructive partial safety, idempotency, live authorization, staged provider readiness and no false sandbox claims.
- **16–21 statistics and output:** immutable source vintages and epistemic tiers, versioned Artifact identity/verified publication and qualified cache/provenance.
- **22–26 collaboration/diagnostics:** per-principal read markers, permission-safe reconnect, platform Node distinct from product Work, revision-protected mutation and protected incident projections.
- **27–32 interfaces/evolution/machines:** UI tokens and animation cannot create Job truth, native rendering, safe schema change, justified process boundaries, no AI/automation permission amplification and no elevation of tentative forecasts to official facts.

For a true shared-node host, the original flags as high-priority proof the owner, remote lifecycle, execution spine, result/effect distinction, UNKNOWN/backends, destructive and published-output safety, current authorization, and source/Artifact linkage. **These are proposed release-blocker candidates, not signed product requirements and not passing conformance tests.**

Fifteen **TQ-01–TQ-15** security/operability checks test unavailable FileStore, partial Excel writes, DB/publish gaps, duplicate commands, lost worker after effect, unauthorized cross-user Work, revoked approvals, extension upgrades, GUI crash during real host Job, clone restore, stale Android, revised official source, changed registry, principal confusion and actual accessible keyboard/reduced-motion interaction. None was executed as an installed integration suite in the original study.

The source also contains **43 D01–D43 Product/Engineering Decision rows** and **28 CF-01–CF-28 conflict rows**, each requiring separate disposition. A high-confidence semantic consensus may be a good input to a Product Decision, but it is not approval, runtime proof or independent conservation. Only the exact chosen profile can answer which of these tests apply.

## 8. A historical source-timeline contradiction: Topic 08

The 2026-10-09 Whole-System authoring report explicitly stated that an independent Topic-08 Trust/Safety/System Qualities original was **not found at the time**, so its own §12 was a *provisional bridge*. The frozen research tree inspected during this consolidation **does contain** a separately filed [Topic-08 original](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md). The two statements must be interpreted temporally, not flattened into the claim that Topic 08 is currently absent.

The current §12 provisional trust synthesis cannot certify that later independent source, nor replace its source-specific conflicts and test obligations. An **independent primary reading of Topic 08 remains required** before claiming a fully reconciled Trust/Safety/Qualities corpus.

## 9. A staged evidence route, not a binding implementation plan

The historical 03/09 sequence proposed eight stages with gates:

| Stage | Proposed proof | What a document alone cannot establish |
| --- | --- | --- |
| **G0 baseline sanitation** | Clean package graph, manifest/test alignment, reproducible wheels/import CI and public-neutral contracts | “Supported” package compatibility |
| **G1 domain pilot** | Same source→typed domain Operation→qualified Result/provenance in direct Python and one managed synthetic consumer | Universal operation SDK |
| **G2 independent application authority** | Qt-free admission/Run state and independent client lifetime under selected profile, duplicate/cancel guards | Durable host merely named in diagram |
| **G3 artifact/effects/recovery** | Lost ACK/partial write/corruption/concurrent effect safety and real restore | Cross-store atomicity |
| **G4 authorized collaboration** | Two actual principals, private/shared Work, ACL/fencing, subscriber integrity and restricted logs | Social UI labels as security |
| **G5 second consumer** | Windows and Web use same semantic Work/Run/Artifact despite different renderers | Source portability assumed from Python classes |
| **G6 automation/machine** | Due occurrence/DST, safe typed scheme, agent delegated scope, one execution owner | Production scheduler/AI endpoint |
| **G7 Android and operations** | Native adaptive/offline/notification/file-share tests plus actual performance/backup budgets | APK functionality implied by Qt package |

These gates are **a research-proposed ordering**, not a set of completed milestones. A small local direct-Python user may need G0/G1, but not every Web/Android/distributed invariant. Future acceptance must specify actual deployment profile, user roles, data/result risk class and measured device constraints.

## 10. Contradictions worth retaining rather than resolving by repetition

- **SQL-first vs proven file-first:** later source clarifies that physical backend is open; one-writer/verified recovery semantics remain meaningful.
- **Headless service needed vs independent repository immediately:** logical/process separation can precede Git repository split.
- **Universal ClaimStore/Knowledge graph vs light domain evidence:** risk-proportional domains need different depth; a global store requires actual consumers.
- **Mandatory physical CAS vs versioned immutable ordinary storage:** content identity useful, back-end architecture unapproved.
- **Scenario=Scheme=Cascade vs differentiated composition and UX:** independence follows version, semantic scope and genuine consumer.
- **Qt code reuse vs native client ergonomics:** one semantic DTO may be shared with different renderer source.
- **Installed provider vs authorized available capability:** discovery is not trust, operational readiness, object ACL or effect receipt.
- **Platform process health vs domain/Work terminal outcome:** AppDock and product signal owners differ.
- **UI-only settings vs managed policy and frozen Run params:** preference changes must not rewrite economic history.
- **Exactly-once Run admission vs external effects:** dedup command can still leave a remote write outcome unknown.
- **No backward API compatibility vs data integrity:** retiring old handlers is acceptable; valuable committed Work/Artifact and source history require explicit disposition.
- **Research consensus vs Product admission:** repeat studies strengthen rationale but do not create installed contracts.

**Operational reopening conditions:** a new direct core/Windows commit, approved Product profile/Decision, actual external platform release/API change, reproducible fault-injection outcome, measured slow-PC/mobile budgets, a new primary Topic-08 finding or independently detected omitted source meaning. Until then this article is a bounded integrated scientific hypothesis with open evidence gates.
