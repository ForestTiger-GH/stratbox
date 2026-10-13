# Implementation handoff and adequacy matrix — scoped LCD construction

**Edition:** 2026-10-12. **Status:** PRODUCER RECONCILIATION / PARTIAL / NOT INDEPENDENTLY VERIFIED. **Purpose:** allow a future implementer to find the correct concrete construction without treating every research concept as a mandated software subsystem. This matrix is a navigation/consumer gate, not a duplicate authority for Product WHAT, Target HOW or decisions.

**Authority:** [Product Commitment Census](../what/strategy-box/commitment-census.md) and [accepted host direction](../what/strategy-box/host-deployment-commitment.md). **Mechanism owners:** [Target HOW](../how/README.md), [architecture](../architecture/README.md), [Low-Level Design](../ldd/README.md) and named individual LCD packages. The independent analytical core, future host authority, Windows/Web/Android surfaces and external AppDock boundaries remain distinct. Current implementation evidence is pinned in [Current HOW](../current-how/README.md).

## 1. Product-bound obligations → construction and verification

The record below distinguishes **accepted** target constraints from **user-goal/candidate** content. A planned host is accepted, while selection of its physical process, storage and API is not.

| ID and product authority | Consumer-visible protected meaning | Concrete target construction or sufficient existing owner | Implementation handoff verdict |
| --- | --- | --- | --- |
| PC-SB-001 — BOUNDARY_ACCEPTED | Independent bank/macro methods callable directly in Python/notebooks | Existing analytic core + [used-input LCD](data/used-input-receipt-construction.md) only where provenance capture is actually admitted | Core architecture **sufficient**; provenance `LCD_CANDIDATE`, no global capture decision |
| PC-SB-002 — BOUNDARY_ACCEPTED | External platform owns installation/node/session, not analytics | [Hosting HOW](../how/hosting/host-and-client-deployment.md) and [platform LDD](../ldd/integration/activation-contract-verification.md) specify an external boundary | Additional invented platform class `NOT_APPLICABLE` until verified integration consumer exists |
| PC-SB-003 — HOST PLANNED/ACCEPTED | Web/domain-host and Windows/AppDock-host with distinct connecting client | [Host/client LCD](hosting/host-authority-and-client-contract-construction.md) + [security LCD](security/host-effect-authorization-construction.md) + [observability LCD](observability/execution-evidence-and-problem-boundary-construction.md) | `LCD_BLOCKED` deployment; physical placement, auth, durable ledger, real endpoint and platform contract need authority/proof |
| PC-SB-004 — BOUNDARY_ACCEPTED | The same domain result meaning across clients | [Local Scenario LCD](application/local-scenario-execution-construction.md), [host LCD](hosting/host-authority-and-client-contract-construction.md), [used-input LCD](data/used-input-receipt-construction.md) | `LCD_CANDIDATE` contracts; actual cross-runtime fixture and domain-equivalence tests UNEXECUTED |
| PC-SB-005 — USER DIRECTION | Portable semantics, optional Android, different native UX | Application/client ports in [host LCD](hosting/host-authority-and-client-contract-construction.md), [architecture](../architecture/application-authority-placement.md) | Client release parity `LCD_BLOCKED` pending feature scope; separate generic Android class catalog `NOT_APPLICABLE` absent implementation consumer |
| PC-SB-006 — BOUNDARY_ACCEPTED | No gratuitous API compatibility; preserve existing user data by policy | [Host migration LDD](../ldd/hosting/host-client-attachment-boundary.md), [artifact LCD](artifacts/local-output-publication-construction.md) | Migration and retention `LCD_BLOCKED`; automatic backward-compatibility framework `NOT_APPLICABLE` |
| PC-SB-007 — BOUNDARY_ACCEPTED | Public-neutral provider contracts, neutral discovery/selection/readiness | [Generic extension LCD](extensions/neutral-provider-binding-construction.md), [LDD](../ldd/extensions/neutral-provider-conformance-vectors.md) and [Science](../science/extensions/provider-discovery-binding-readiness-and-conformance.md) | Typed health/config/duplicate-ID fake checks now executed; real provider trust, package activation and domain-specific conformance `LCD_BLOCKED` |
| PC-SB-008 — COMMISSION ACCEPTED | Standalone, independently checkable complete Knowledge Product | [Publication manifest](../PUBLICATION-MANIFEST.md), [LCD README](README.md) and this matrix | `GLOBAL LOSSLESS_PASS=BLOCKED`; no design artifact can replace independent source verification |

### Accepted host outcome contracts, individually

| Host target | Required realization proof | Scope status |
| --- | --- | --- |
| HOST-O1 | One host identity/authority independently running from a connecting client's process, with a true lifecycle test | [Host LCD](hosting/host-authority-and-client-contract-construction.md) `BLOCKED`, native test absent |
| HOST-O2 | Browser through actual configured authorized site/domain, supported client capability negotiation | `BLOCKED` browser transport/security/deployment choices |
| HOST-O3 | Distinct managed Windows host and Windows client installations, real authenticated attach | `BLOCKED` physical AppDock-host capability and integration proof |
| HOST-O4 | Client disconnect does not fabricate host Job outcome; stale view reconciles | Logical snapshot port `CANDIDATE`; real durable continuity `BLOCKED` |
| HOST-O5 | Analytic core remains independently callable and supplies equal domain meaning | Existing core owner plus Scenario/used-input interface fakes `CANDIDATE` |
| HOST-O6 | Actual principal/object/effect authorization at host authority | [Security LCD](security/host-effect-authorization-construction.md): twelve fake-port tests of missing target generation, mismatched actor/plan/target/policy, grant denial and stale resource; actual authenticated provider, approval expiry, conditional write and installed host remain `LCD_BLOCKED` |
| HOST-O7 | Honest unavailable/unknown outcomes for host, bytes, contract and external effects | [Host LCD](hosting/host-authority-and-client-contract-construction.md), [artifact LCD](artifacts/local-output-publication-construction.md), [diagnostic LCD](observability/execution-evidence-and-problem-boundary-construction.md); local `CANDIDATE`, host `BLOCKED` |

### Domain Operation → application offering seam (2026-10-13 candidate)

The [product-offering LCD](application/domain-operation-product-projection-construction.md) closes a missing **design proposal**, not a Product Decision: a separately callable domain operation can be projected into one or more curated product forms without copying core logic into clients. Exact-version binding, unknown/fixed-input rejection, host-resolved defaults, sealed inputs and a narrow safe presentation DTO are specified as typed source skeletons. This complements **PC-SB-001/004, U-01/U-06** and the existing local Scenario/Machine/host LCDs. **Local fake: LCD_CANDIDATE; hosted published catalog: LCD_BLOCKED; blanket reflection catalog: NOT_APPLICABLE.** Actual paired core + application conformance and independent LCD challenge remain UNEXECUTED.

## 2. User-goal scopes remain conditional until admitted

| Intent (source in Commitment Census) | Consequential coding consumer and current construction | Status and why detail is bounded |
| --- | --- | --- |
| U-01 Discoverable operations, scenarios, cascades and optional Schemes | [Domain-to-offering construction](application/domain-operation-product-projection-construction.md) plus sequential Scenario semantics and model in [local LCD](application/local-scenario-execution-construction.md); curated [machine LCD](capabilities/curated-machine-operation-adapter-construction.md); conditional [trigger-occurrence LCD](automation/trigger-occurrence-and-scheduling-construction.md) where scheduled use is admitted | Scope bounded to *existing* sequential steps and conditional trigger evaluations; new universal DAG/workflow engine `NOT_APPLICABLE` until an approved consumer demonstrates its need |
| U-02 Local foreground stops reasonably with window, without misreporting effect | [Local execution LCD](application/local-scenario-execution-construction.md), [diagnostics LCD](observability/execution-evidence-and-problem-boundary-construction.md) | `LCD_CANDIDATE`; verified process stop/cancel/effect guarantees require Product Decision/native test |
| U-03 Reliable state without speculative infrastructure | [Host LCD](hosting/host-authority-and-client-contract-construction.md); local history remains correctly classified as a cache | Host storage/durability `LCD_BLOCKED`; automatic SQL/event sourcing mandate `NOT_APPLICABLE` |
| U-04 Chat output and ordinary user-controlled Data files | [Artifact LCD](artifacts/local-output-publication-construction.md) and relevant [LDD](../ldd/artifacts/staged-publication.md) | Local `LCD_CANDIDATE`; stronger immutable catalog/retention is conditional |
| U-05 Legible team identity and safe shared failure notices | [Security LCD](security/host-effect-authorization-construction.md), [diagnostic LCD](observability/execution-evidence-and-problem-boundary-construction.md) | Host sharing policy `LCD_BLOCKED`; UI nickname cannot substitute identity |
| U-06 Direct Python + GUI + authorized machine client | Existing independent core, [Scenario LCD](application/local-scenario-execution-construction.md), [machine LCD](capabilities/curated-machine-operation-adapter-construction.md), [machine LDD](../ldd/capabilities/machine-operation-adapter-conformance.md) | Source-extracted fake gateway tests separate no-Run denial from uncertain ACK and require stable invocation key; actual machine transport, client auth and host idempotency store still `LCD_BLOCKED`; unrestricted Python reflection `NOT_APPLICABLE` |
| U-07 Website and possible Android companion | [Host LCD](hosting/host-authority-and-client-contract-construction.md) | Web host direction accepted; client/mobile release scope `LCD_BLOCKED` |
| U-08 Concurrent independent work in threads | Local single-flight is **present** current limitation; [host LCD](hosting/host-authority-and-client-contract-construction.md) defines future shared authority; [trigger-occurrence LCD](automation/trigger-occurrence-and-scheduling-construction.md) bounds conditional recurring work | Shared scheduling, fencing, overlap and parallel-effect strategy `LCD_BLOCKED`; no claimed concurrent executor or deployed scheduler |
| U-09 Source observation/provenance | [Used-input LCD](data/used-input-receipt-construction.md) | Synthetic source-fragment guards now test mutable payload sealing, acquired/consumed digest equality, explicit format witness, domain validity and UTC representation; **actual core domain pilot remains `LCD_CANDIDATE`/UNEXECUTED**, mandatory catalog/raw retention and host capture policy `LCD_BLOCKED` |
| U-10 State physically located with the executor that owns effects | [Host authority LCD](hosting/host-authority-and-client-contract-construction.md), [diagnostic LCD](observability/execution-evidence-and-problem-boundary-construction.md) | Local/host authority separation fixed in meaning; host process/storage selection `LCD_BLOCKED` |

### Conditional automation scope

A future rule is distinct from a real TriggerEvaluation, unique Occurrence, admitted Run, physical Attempt and user notification. [Automation LCD](automation/trigger-occurrence-and-scheduling-construction.md) provides a bounded **candidate** interface and duplicate/unknown-admission guards. It is **not** a new Product commitment, installed scheduler or approved recurrence SLA. Calendar DST gap/fold policy, misfire/overlap/catch-up rules, trusted source-event evidence, storage durability and run-as authorization remain owner-held decisions. The planned host may run ordinary admitted Scenarios without supporting unattended schedule rules in its initial release.

## 3. Specialized risk slice: plan/effect integrity

[FRG cleanup LCD](application/frg-cleanup-effect-plan-construction.md) translates a directly observed source-specific destructive-file hazard into an executable **candidate** plan model. It is not a new universal user requirement and does not mandate freezing all source datasets. Cross-slice effect state must agree with [security authorization](security/host-effect-authorization-construction.md), [Artifact publication](artifacts/local-output-publication-construction.md) and [Scenario outcome](application/local-scenario-execution-construction.md): a valid user approval, a prepared plan, an attempted file write, a verified published Artifact and a completed Run are **five different truth-bearing events**.

### Exactly consumed input: the scientific boundary is stronger than a typed field

The input receipt seam must bind the **same immutable bytes** into the parser and the captured digest, with a separate claimed format verdict and a domain validation result. A mutable buffer, forged `CapturedPayload`, or a decoder that returns a value without an actual format witness cannot satisfy the provenance promise. A UTC field name alone cannot turn a naive client clock into a valid observation. The [used-input LCD](data/used-input-receipt-construction.md) demonstrates these as small candidate bodies and fake negative tests. These checks are **not** a publisher-authenticity proof, full HTML/XLSX parser conformance, true bank methodology validation, streaming performance benchmark, actual raw retention or R3/R4 replay. Those consumers remain separately governed.

### Destructive approval needs a target revision and an actual effect fence

The candidate [security effect guard](security/host-effect-authorization-construction.md) now explicitly refuses destructive requests without a declared resource generation and refuses a returned plan approval whose actor, target set, requested plan digest or policy generation disagrees with the current trusted decision. This is a **necessary synthetic precondition** and can be exercised without choosing IAM or storage technology. However, a real shared FileStore or OS path may be replaced *after* a separately read generation: exact authorization remains `LCD_BLOCKED` until the concrete mutation primitive proves compare-and-effect/fencing, ACL, signed approval expiry and audit receipt across failures. Source role and `SEC-09/SEC-10/SEC-27` evidence remain distinct; passing a class method against fakes is **not** permission to deploy destructive shared writes.

### A shared-safe label cannot authorize a shared field

The [security projection candidate](security/host-effect-authorization-construction.md) also requires a **server-owned schema and value check** for every field exposed in a shared event. A field named `raw_exception` cannot become public solely by arriving with `SHARED_SAFE` metadata. Approved schema fields still require object-level read permission, safe structured serialization and inert native/Web rendering. The source's field-owner/sensitivity/audience/retention distinctions remain Product/security owner decisions; the fake [CI 38209367354](https://github.com/ForestTiger-GH/stratbox/actions/runs/38209367354) validates only the documented projection algorithm against a synthetic schema, **not** real policy correctness or leakage resistance.

### Artifact digest, validation and physical finalize must refer to the same staged generation

The [Artifact publisher](artifacts/local-output-publication-construction.md) requires a backend `StagingSeal` carrying a generation and exact count/hash, enforced on every verified read and on the final effect. Computing a SHA from one open stream and validating another under the same *path name* cannot substantiate a publication receipt. Faked mutation of staging before second read or after intent is now explicitly denied/marked unknown by the documented algorithm; the actual generation-fenced FS/object primitive and user-facing storage guarantees are **LCD_BLOCKED** until implementation-specific conformance and independent review.

### Every LCD packet is now behavior-probed, without resolving its physical implementation gate

The [LCD index](README.md) now records ten **separate source-extracted, fake-port executable groups** spanning local Scenario, logical host admission, Artifact publisher, exact used-byte bridge, Problem recording, Security effect/projection, FRG effects, curated machine gateway, public-neutral provider binding and conditional occurrence handling. Their tests cover specific invariants of the *documented candidate algorithms*. The new machine wrapper returns `OUTCOME_UNKNOWN` after a host admission ACK loss or malformed result rather than collapsing that state into a false `REJECTED`; typed provider readiness rejects arbitrary truthy health. The FRG executor fake assumes a supplied witness comparison and conditional FileEffectPort, and does **not** implement its unfinished plan normalizer or prove real legacy file deletion safety.

**Blockers remain a design property**, not an administrative afterthought: each future port must be selected under its real implementation owner, filled with executable modules, validated against current source behavior, actual bank/source semantics, native Windows/SMB/POSIX/object effects, real AppDock/host boundaries where applicable, and separately reviewed by a competent independent implementer. The successful artificial tests do not settle accepted product choices or turn a narrative request into a host release.

### FRG: only an exact approved plan member may reach file-effect execution

The [FRG LCD](application/frg-cleanup-effect-plan-construction.md) now enforces a conservative pre-effect membership boundary before the authorization and pending-intent calls. The passed `FrozenAction` must match **one unique action** inside the approved `FrozenCleanupPlan`; the canonical action-set digest must correspond to current plan content; source and destination scopes must match the approved root; a delete needs an actual generation/hash witness. Immediately before a delete, the selected original must still match the current source evidence and the same recognized family/period. An unrecognized or changed source is a **known stale-plan refusal** when no backend effect started, while a conditional backend effect that loses its acknowledgment is still `OUTCOME_UNKNOWN`. Actual OS/path containment and the compare-and-delete primitive are unresolved physical implementation obligations.

This prevents a future host adapter from treating arbitrary DataFrame rows or a typed `FrozenAction` as proof of acceptance. It cannot constrain an unrestricted direct-core Python caller, certify signed human approval or eliminate physical time-of-check/time-of-use races by itself.

### Physical storage evidence is now stronger than fakes but limited to a Linux local profile

[Eight actual POSIX race/no-clobber probes](../science/artifacts/output-identity-publication-and-availability.md) ran with disposable local files and kernel-backed syscalls at [CI 38221344760](https://github.com/ForestTiger-GH/stratbox/actions/runs/38221344760). They challenge the false assumption that a checked path, open inode, consistent size or plain atomic rename are enough for the Artifact/FRG effect guarantees. A Linux create-only name/link offers a bounded no-clobber route, *not* a safe replace/delete strategy on every FileStore. Therefore the actual selected backend still needs negative tests for name/link/reparse-point traversal, changed source/target generation, retained old output under failed publication, crash recovery, read-time privilege changes and cross-store catalog reconciliation. These native tests do not certify a Windows/SMB implementation or lift its `LCD_BLOCKED` grade.

### Host Run read and permitted event-feed contracts

A client-visible Run snapshot must be a qualified object, rather than the storage ledger's unfiltered record. The [Host LCD](hosting/host-authority-and-client-contract-construction.md) now requires an exact Boolean grant, a checked Run identity/status, and an authorized event projection with an opaque viewer-scoped cursor and explicit generation. It excludes an internal node sequence from the returned Run DTO. A typed `ObservationPage` **does not make its source trusted**: a real host must implement authenticated per-event and per-field visibility, cursor binding/invalidation, and coherent snapshot-to-stream recovery. Source-derived [HC-52..59](../ldd/hosting/host-client-attachment-boundary.md) document the unexecuted adverse cases. A producer fake-port test passed, but the complete host/security release gate is still `LCD_BLOCKED`.

## 4. Explicit NOT_APPLICABLE boundaries

A distinct LCD is **NOT_APPLICABLE** now for: every trivial utility function already exposed by the independent core; a generic component per theoretical entity (Work, Thread, Attempt, Job and Artifact do not automatically require five SQL tables); a blanket Android source-code clone of Python/Qt; an unapproved AI orchestration fleet; a mandatory content-addressed data lake and full-history artifact backup; a custom UI theme class for each setting; a separate desktop-host repository before release ownership is decided; a universal file format/parser registry merely because format variation exists. Each may be reopened only when an accepted consumer, consequence or cross-owner requirement makes the additional construction material.

`NOT_APPLICABLE` means **no separate source-shaped document adds value in the present scope**; it does not claim those capabilities do not exist, are rejected forever or need zero engineering work after future Product Decisions.

## 5. Whole-chain cross-construction challenge

For a single permitted public-source acquisition feeding a two-step analysis and a file export, an implementer should be able to trace:

~~~text
actually downloaded bytes (transport evidence)
→ actually consumed input bytes and parser revision (domain evidence)
→ typed domain result (calculation and validation)
→ admitted Scenario Run and required-step statuses (application truth)
→ approved scoped file effect and pending intent (security/effects)
→ staged then verified output bytes (storage)
→ committed Artifact publication record and later availability (application)
→ optional safe diagnostic event and authentic external Problem receipt (observability)
→ authorized host snapshot and client rendering (presentation)
~~~

**Adversarial variants:** same URL changes content; required step fails but a later step succeeds; source is valid but Excel staging fails; final filesystem swap happens but acknowledgment is lost; one client disconnects during Run; authority revokes artifact access after card rendering; optional log writer fails; external problem recorder returns an unconfirmed identifier. The expected output must preserve each distinct uncertainty and success separately.

**Evidence status:** original core and Windows behaviors have selected executed synthetic characterization; the **future mechanisms and cross-LCD system are UNEXECUTED**. Producer review of code snippets and parse-only CI cannot qualify an independent implementer handoff. Release admission requires owner Decisions, specialist/native tests and an independent cold-reader reviewer.

## 6. Blocker closure route — no invented Product Decision

A future coder cannot select these materially consequential choices by silent convention: host/client physical packaging, actual principal/session provider, permission object and effect-time revocation policy, durable Run and event store, idempotency retention and transaction/outbox strategy, Windows managed host attach, website security, Artifact byte-retention and file backend crash tier, partial/required-step meaning, cancellation/retry guarantees, machine delegation and support-log audience. The current safe state is `LCD_BLOCKED` for every real deployed integration requiring those choices.

A decision is made only by its rightful Product/security/platform/operations owner. A technical probe may narrow candidate choices but cannot grant itself product authority. Resume on a new owner act, updated direct code, independently passed negative suite or contract change; otherwise the candidate slices remain useful for bounded prototype/fake test work without falsely claiming system completion.
