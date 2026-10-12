# LCD — Low Code Design for Strategy Box

**Status:** `OWNER-DIRECTED KNOWLEDGE LAYER / ASSEMBLY IN PROGRESS / NO IMPLEMENTATION-READY CERTIFICATION`. The owner clarified on 2026-10-12 that **LCD means Low Code Design**, not Low-Level Design (LDD). LCD here is a project-specific term for an implementation-near design model, **not** a visual low-code/no-code application platform, code generation promise, executable runtime, or a requirement to model every source-code line.

## Purpose and boundary

LCD addresses a question left open by otherwise sound Product WHAT, Target HOW, Engineering Architecture and detailed mechanisms: **can an authorized implementer realize one defined scope without having to invent materially consequential design decisions while writing code?** Its outcome is a bounded, reviewable realization model and an explicit account of implementation freedom. It does not supersede those upstream owners, current code, Product Decisions, or verification results.

- [Target WHAT](../what/README.md) owns accepted product obligations and declared variants.
- [Target HOW](../how/README.md) owns how the product should work, be applied, operated and recovered.
- [Engineering Architecture](../architecture/README.md) owns cross-component responsibilities, dependency direction and allocation boundaries.
- [LDD — Low-Level Design](../ldd/README.md) preserves existing detailed mechanism specifications, state/contract alternatives and adverse verification vectors. **LDD is valuable input, not an automatically completed LCD.**
- [Current HOW](../current-how/README.md) owns the observed implementation at exact revisions. Its facts constrain brownfield LCD; proposals must not be described as existing code.
- [Science](../science/README.md) preserves explanations, contrary evidence and uncertainty; it is not the implementation handoff.

LCD is **selectively activated** where high consequence, many interacting states/owners, parallel implementers, repeated design drift, cross-platform reuse, data integrity, external effects or expensive correction justify it. A small analytical function with a clear existing contract may proceed from WHAT/HOW directly to coding and tests; record why additional LCD is unnecessary.

## Minimum bounded LCD result

For each activated implementation scope, produce the least sufficient combination of readable, testable models. A separate file is justified only when it has a real downstream consumer.

| Required aspect | What the design must resolve or explicitly leave open |
| --- | --- |
| **Scope and status** | Exact user-visible outcomes; admitted WHAT and chosen HOW/Architecture/LDD revisions; variant, excluded behavior, decision owner and maturity state. |
| **Current-to-target correspondence** | Direct current implementation witnesses; preserved behavior, replacement and migration/data-continuity obligations; unknown current behavior. |
| **Realization decomposition** | Required implementation responsibilities, state owners and dependency direction; concrete module/package/source skeletons when a chosen coding scope benefits materially. |
| **Code-shaped constructions and contracts** | Proportionate concrete classes, interfaces/protocols, annotated function signatures, implementation stubs, records, result/error types, algorithmic/state-transition skeletons and corresponding validation; ownership, storage, concurrency, retries, authorization, artifacts and recovery as applicable. |
| **Material decision closure** | For each consequence-bearing choice, record accepted decision and rationale, allowable implementation variants, testable constraints, owner and blockers. |
| **Implementation freedom** | Mark `FIXED`, `BOUNDED`, `DELEGATED_NONMATERIAL` or `BLOCKED_ON_AUTHORITY_OR_EVIDENCE` per decision. Freedom must be explicit; a speculative API signature is not a decision. |
| **Conformance and handoff** | Acceptance/negative tests, expected observable results, required environments, evidence needed, unresolved risks and stop/reopen conditions; distinguish planned from executed tests. |

A ready model should let a **cold competent implementer** identify its starting baseline, smallest bounded change, protected invariants, allowed choices and falsifying checks using maintained Knowledge alone. An independent reviewer should be able to identify where implementation could still diverge materially. The target is **material implementation-decision closure together with concrete pre-code construction for the declared scope**, not identical code generation from the same text.

## Concrete program-construction deliverables (2026-10-12 owner refinement)

**LCD includes concrete pre-coding software construction.** For an activated coding scope, a decision register, narrative design or fault-vector matrix alone cannot count as a complete implementation-near model when classes/functions/source structures would materially help the implementer. LCD may and often should contain **actual target-language declarations**, proposed class hierarchies, functions and method signatures, typed stubs, module and package scaffolds, domain/data/error types, and executable-looking algorithm or state-machine skeletons. This is the owner's intended addition to Low-Level Design; it is not a commercial no-code builder.

A scope-appropriate LCD construction packet should, where relevant, cover:

| Concrete construct | Implementation preparation required |
| --- | --- |
| **Source/package skeleton** | Actual proposed modules/paths and import/export boundaries when they affect ownership, integration, build or change; otherwise leave private file layout flexible. |
| **Classes and protocols/interfaces** | Named, target-language class/protocol/interface sketches with responsibility, lifecycle, important methods and permitted dependency direction. Mark interfaces as approved only after proper decisions. |
| **Functions and methods** | Proposed names, typed parameters, return/result/error contracts, validations and branch conditions. Use function bodies as algorithmic pseudocode or explicit `TODO` / `NotImplementedError` **design-only** stubs. |
| **Data and state** | Typed records, enumerations, error/result types, serialization/schema boundaries, state transitions, mutation authority and invariants. |
| **Algorithms and effects** | Ordered step skeletons, resource lifecycle, concurrency, cancellation, retry, partial failure and recovery paths to the extent that different implementations would change protected meaning. |
| **Tests and handoff** | Concrete test skeletons and negative fixtures derived from accepted observable obligations; label tests `PROPOSED` until actually executed at a known implementation revision. |

Choose a suitable representation for the accepted or explicitly conditional language/runtime (for example Python class/Protocol definitions, typed Rust traits/structs, or TypeScript interfaces). Prefer real target-language sketches over generic prose when the chosen code shape matters. **The selected constructs form a coherent pre-programmed solution**, not a list of disconnected example APIs. The packet must distinguish `FIXED`, `BOUNDED`, `DELEGATED_NONMATERIAL` and `BLOCKED` implementation choices.

### Illustrative declaration only — not an adopted Strategy Box interface

The following is a **syntax illustration**, not a product contract or an instruction to create the named classes in production:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExampleRequest:
    operation_id: str


@dataclass(frozen=True)
class ExampleOutcome:
    accepted: bool
    reference: str | None


class ExampleOperationPort(Protocol):
    def submit(self, request: ExampleRequest) -> ExampleOutcome: ...


class ExampleOperationAdapter:
    def submit(self, request: ExampleRequest) -> ExampleOutcome:
        # LCD CANDIDATE STUB — actual behavior requires an admitted contract.
        raise NotImplementedError
```

Real LCD must replace this example with **source-reconciled, scope-specific** construction. For instance, a candidate Qt-independent scenario extraction should establish which existing code is reused, which class or protocol owns admission/execution, exactly where Qt callbacks are converted to neutral events, what request/outcome types and errors mean, and which tests will falsify the proposal. Names and signatures remain candidate until their proper authority has approved them.

Each code-shaped fragment needs a clear label: `ILLUSTRATIVE`, `CANDIDATE_DESIGN`, `ACCEPTED_DESIGN_CONTRACT` or `OBSERVED_CODE_AT_PINNED_REVISION`. **Documentation-only LCD source skeletons are never shipped implementation.** Do not insert unfinished stubs into `src/stratbox/`, `stratbox-windows` or another product owner without a separate implementation commission. Static syntax checks can show a stub parses; they cannot certify functional behavior, business correctness, host existence, security or a product release.

When a schema or IDL is the canonical owner, generated class/interface boilerplate should be treated as a projection, with one editable owner and explicit generated/manual boundaries. Stop elaborating when additional model detail would merely duplicate private code rather than remove a material implementation ambiguity. A cold implementer must nevertheless see **what concretely needs to be coded**, not only why a high-level architecture might work.


## Status and release semantics

- `LCD_CANDIDATE`: a coherent scoped model exists, but product choices, realization decisions, evidence or conformance are open.
- `LCD_BLOCKED`: a named authority, missing prerequisite, external contract or unverified assumption prevents closing a material implementation choice. Publish the safe candidate and route the decision; never invent the answer.
- `LCD_READY_FOR_IMPLEMENTATION`: the exact scope and adopted baselines have appropriate authority; materially consequential decisions are fixed or bounded; permitted residual freedom is demonstrably nonmaterial; implementer cold-read and independent design challenge have passed **where claimed**.
- `NOT_APPLICABLE`: additional implementation-near modeling adds no material value for a precisely defined scope; record the reason and its existing sufficient realization contract.

`LCD_READY_FOR_IMPLEMENTATION` **does not** mean code exists, runtime tests passed, installation works, production deployment was approved or full Strategy Box is release-ready. A single ready slice cannot close unresolved adjacent Product WHAT or Research-to-Science obligations. An unapproved target can have a useful `LCD_CANDIDATE`, never an implicitly accepted readiness verdict.

## Initial materialization priorities — not approved implementation plans

1. **Qt-independent application orchestration:** clarify portable scenario admission, execution, outcomes, observation and failure/effect semantics using [local orchestration LDD](../ldd/application/local-scenario-orchestration-boundary.md); do not presume a new repository already exists.
2. **Host and client attachment:** refine the [planned host target](../what/strategy-box/host-deployment-commitment.md) and [host attachment LDD](../ldd/hosting/host-client-attachment-boundary.md) for each admitted delivery profile; physical package, transport, storage and authority-policy choices remain open.
3. **Source-to-result and Artifact integrity:** when implementation scope is admitted, combine [used-source evidence](../ldd/data/used-source-receipt-boundary.md) with [Artifact publication](../ldd/artifacts/staged-publication.md); avoid automatic global source registries or guarantees unsupported by the chosen backend.
4. **AppDock boundary:** distinguish [observed activation contracts](../current-how/appdock-activation-host-attachment-boundary.md) from [conditional integration conformance](../ldd/integration/activation-contract-verification.md); a manifest belongs to a deployable package/World authority, not to every conceptual client by default.

These are **candidate pilot routes**. Their associated mechanisms and test vectors remain at their existing statuses until independently challenged and authorized. Do not create a mandatory LCD file per Scenario, Python module or Research topic.

## Scoped software-construction packets — 2026-10-12 continuation

Ten concrete, **documentation-only** packets now complement the assembly contract. Their program skeletons are candidates, not source changes, independently verified implementations, or accepted APIs.

- [Local Scenario execution, independent of Qt application truth](application/local-scenario-execution-construction.md) — `LCD_CANDIDATE`. Source-reconciled sequential plan, typed Python requests/results, one-run gate, execution reducer, safe observations, Qt bridge and negative test stubs; aggregate-outcome, privacy and effect policies still need decisions and actual tests.
- [Host authority and client attachment](hosting/host-authority-and-client-contract-construction.md) — `LCD_BLOCKED` for deployable Web/Windows-managed host. Typed logical host/client ports, intent admission, scoped views and artifact access; physical owner, authentication, durable dispatch, host recovery, transport, and external managed-platform integration remain unresolved.
- [Local output verification and Artifact publication](artifacts/local-output-publication-construction.md) — `LCD_CANDIDATE` for a scoped local design and `LCD_BLOCKED` for universal atomic or remote semantics. Typed staging, byte-verification, publish intent and reconciliation models with explicit backend proof requirements.
- [Exact actually-used input byte receipt in neutral analytical core](data/used-input-receipt-construction.md) — `LCD_CANDIDATE` single-consumer core pilot; `LCD_BLOCKED` for compulsory cross-domain receipts and replay. Defines acquired versus used bytes, typed identity/validation, a byte-preserving decoder handoff, attempt/coverage outcomes and proposed tests, with no full source catalog implied.
- [Causal execution evidence, local Attempt logs and optional Problem receipts](observability/execution-evidence-and-problem-boundary-construction.md) — `LCD_CANDIDATE` for local evidence segregation and `LCD_BLOCKED` for hosted/durable shared problems; typed audience, evidence planes, safe event and external-registration ports with recovery and fault skeletons.

- [Host command/object/effect authorization](security/host-effect-authorization-construction.md) — `LCD_BLOCKED` deployed security policy, `LCD_CANDIDATE` scoped fake/port prototype. Separates trusted principal, phase-specific grants, plan approvals, resource version, effect receipts and safe field-level read projections.
- [FRG cleanup plan and file effects](application/frg-cleanup-effect-plan-construction.md) — `LCD_CANDIDATE` narrow local plan; `LCD_BLOCKED` backend-safe hosted mutations. Specifies source family/period plan normalization, generation-checked staging, guarded deletion and archive-member byte choice using direct FRG failure evidence.

- [Curated machine-operation discovery and invocation](capabilities/curated-machine-operation-adapter-construction.md) — `LCD_CANDIDATE` local adapter and typed result; `LCD_BLOCKED` external authenticated machine access, delegation and data-page contracts. Machine visibility and installed handlers are not authority.
- [Public-neutral provider discovery and binding](extensions/neutral-provider-binding-construction.md) — `LCD_CANDIDATE` generic descriptor/selection ports; `LCD_BLOCKED` public SDK adoption, trusted activation/resource lifetimes and release conformance. Provider presence and readiness are not successful domain results.
- [Conditional trigger evaluation, occurrence identity and scheduler admission](automation/trigger-occurrence-and-scheduling-construction.md) — `LCD_CANDIDATE` bounded pure evaluation and unique occurrence ledger; `LCD_BLOCKED` real host scheduler, timezone/misfire/overlap policy, durable admission and autonomous effects. Existing Windows background UI labels are not an execution service.

See also the [Product obligations → concrete LCD handoff matrix](implementation-handoff-and-boundary-matrix.md) for admitted HOST-O1..07, PC-SB-001..008, conditional user goals U-01..10, justified `NOT_APPLICABLE` classifications and cross-packet residual requirements. This matrix is a derived consumer guide, not a new Product/Decision owner.

**Assurance boundary:** all ten are producer-authored pre-code designs. Limited code-fragment/fake-port probes have actually run as scoped evidence below; full target acceptance/native/security/fault suites remain `UNEXECUTED`. They consume existing [Low-Level Design](../ldd/README.md) rather than replacing it. A distinct implementer cold-read and specialist/independent conformance challenge must precede any `LCD_READY_FOR_IMPLEMENTATION` claim. Source ↔ Science completeness and blind Research Amputation remain separate open gates.

## Executable candidate-fragment probes — 2026-10-12

The Knowledge CI now **parses** the concrete documented LCD construction files and **executes selected allowlisted Python AST definitions extracted directly from all ten maintained LCD packets (current edition; earlier runs tested fewer)**, using deterministic synthetic schedulers, ledgers, projections, optional recorders and in-memory output bytes. [CI run 38206600725](https://github.com/ForestTiger-GH/stratbox/actions/runs/38206600725) completed **SUCCESS** at `stratbox@16fbe7acd5d1b817c4613247cad902f38aa4160c`. Its bounded checks exercised the proposed local Scenario outcome reducer and one-run admission guard, host intention replay/conflict, and external Problem acknowledgment uncertainty. An extended [run 38206780515](https://github.com/ForestTiger-GH/stratbox/actions/runs/38206780515) at `2c6d41499a4d789e913e9896ceae8b3021ed79f0` additionally passed seven synthetic Artifact publication fault scenarios and eight simultaneous Python submission attempts against the documented local admission lock. These checks do **not** run production modules, actual bank domains, native Qt, remote hosting, durable/OS storage, real external platform integration or a security acceptance suite. The eight-thread fake submission test is bounded Python locking evidence, not host or native Qt concurrency conformance. A further [run 38207007244](https://github.com/ForestTiger-GH/stratbox/actions/runs/38207007244) (**SUCCESS** at `13d1939dd415a5a027c5bb51b4bcd933e3140067`) additionally exercised the optional Trigger/Occurrence service with duplicate evaluations, unavailable source evidence, disabled rule, stale revision and uncertain admission; it does not certify DST/calendar correctness or a running scheduler.

**Conditional automation correction:** the first occurrence service draft left no persisted distinction between a confirmed host **no-Run** rejection and a lost Run/ledger acknowledgment. The updated [trigger/occurrence construction](automation/trigger-occurrence-and-scheduling-construction.md) and exact extracted-code tests preserve both cases separately. [CI 38207269986](https://github.com/ForestTiger-GH/stratbox/actions/runs/38207269986) at `b7d44e72099e30dfc8ccb91a9631c2ca76bbb08b` completed **SUCCESS** after the candidate and fake ledger were reconciled. These are bounded tests of documentary algorithms, not an approved scheduler/retry policy or actual host transaction.

**Sixth source-integrity design probe:** the [used-input receipt LCD](data/used-input-receipt-construction.md) now contains an executable typed guard which seals mutable provider payloads before hashing, confirms the exact count/digest again before domain parsing, requires **explicit positive format validation with an evidence reference**, and rejects naive/non-UTC observation time. The bounded [CI run 38208597059](https://github.com/ForestTiger-GH/stratbox/actions/runs/38208597059) at `01a693f95ff82e43a826ea72329a87bc3046b416` **SUCCESS** executed the source-extracted candidate with fake mutating buffers, forged receipts, decoder-format mismatch, domain uncertainty, transport exceptions and naive clocks. The later nonempty format-witness and module-fence corrections also passed exact pinned [CI 38208888612](https://github.com/ForestTiger-GH/stratbox/actions/runs/38208888612) at `3f69d9faaf153d3fc7c1907e83c99294d4974863`. The scientific source is already represented in [source-vintage Science](../science/data-and-knowledge/source-observation-vintages-and-replay.md), including all eighteen original proposed negative cases. These candidate tests prove no actual official publisher provenance, economic validity, installed core path, durable replay or independent code handoff.

**Seventh security-effect design probe:** primary 2026-10-10 security Research and its maintained [SEC-01..30 LDD](../ldd/security/scoped-authority-and-privacy-vectors.md) exposed two fail-open possibilities in the originally drafted [host effect guard](security/host-effect-authorization-construction.md): `DELETE/OVERWRITE` could reach a before-effect intent without any resource revision, and an approval port's result could be accepted without confirming its exact principal, target set or policy generation. The revised candidate now refuses those absent/stale fields; [CI 38209119817](https://github.com/ForestTiger-GH/stratbox/actions/runs/38209119817) at `540f9db5d35fc6ed4e77020d5291295ad47e3a20` **SUCCESS** executed twelve bounded allowed/denied cases using *literal documented classes/functions* with fake ports. These tests do **not** authenticate real actors or secure actual destructive mutations. The storage adapter's compare-and-effect race, approval authenticity/expiry and host policy/transport remain `LCD_BLOCKED`, and independent security release verification is still `UNEXECUTED`.

**Shared-event field safety within the same seventh packet:** [CI 38209367354](https://github.com/ForestTiger-GH/stratbox/actions/runs/38209367354) at `5c9f074ac885eeeea86238e16901b186e3f7e568` **SUCCESS** exercises the literal [AudienceProjection](security/host-effect-authorization-construction.md) with a fake trusted schema: an input's self-declared `SHARED_SAFE` label can no longer force publication of a raw exception, token-bearing text, private path, unsupported field or HTML-like payload. Authorized safe fields are returned, denied resource access refuses projection and unexpected field-name remapping fails. The adapter's actual **field owner/sensitivity/audience/retention** schema, its token/HTML validation, shared state access policy, and native/Web/Machine serialization remain `LCD_BLOCKED` and independently `UNEXECUTED`. At that historical checkpoint this remained **seven distinct LCD packets** under fake behavioral tests; the projection was an additional test within the same Security packet, not a new package or a second security engine.

**Artifact byte-generation repair (same existing packet):** the literal [Artifact publisher](artifacts/local-output-publication-construction.md) previously hashed one staging read, validated a second unfenced read and finalized by mutable staging path; it could therefore associate three different byte versions with one claim. The [source-first 0557 challenge](../science/artifacts/output-identity-publication-and-availability.md) requires one confirmed materialization generation. A new `StagingSeal` and `seal_closed_staging/read_sealed_staging/finalize(seal)` port contract bind both reads and conditional finalize to one backend generation; an exact count/digest match is checked and final bytes inspected. [CI 38210403685](https://github.com/ForestTiger-GH/stratbox/actions/runs/38210403685), exact `stratbox@2f0ced57e7cbc14cd9a9c8c3ac47283121b30b5b`, **SUCCESS** exercised nine synthetic cases (including two newly injected staging mutations between reads/commit). A real backend must independently enforce **immutable or CAS-fenced generation**; checking a pathname/mtime cannot. This remains the *same* previously counted Artifact LCD packet and does **not** increase the seven distinct fake-tested packet families.

**All ten candidate packets now have a bounded source-fragment execution probe:** [CI 38210737310](https://github.com/ForestTiger-GH/stratbox/actions/runs/38210737310), exact `stratbox@27c0ee1341576a3bd67026fed0112c391f3570bc`, completed **SUCCESS** after the 8th curated-machine and 9th generic provider probe, plus the 10th specialized FRG executor probe were registered. Machine tests distinguish known admission REJECTED from accepted Run and lost/contradictory ACK **OUTCOME_UNKNOWN** (never silently turn unknown into safe new retry); later null-admission fixture also passed [CI 38210805644](https://github.com/ForestTiger-GH/stratbox/actions/runs/38210805644), exact `10d1bc0534ef12b4ff0b4abcc6cc94cdbe06a14c`. Public-neutral provider tests require typed health `BindingStatus` and explicit required configuration and reject duplicates/incompatible/missing providers. FRG tests run the *literal documented executor* with a stubbed `source_witness_matches`, fake authorization, frozen source/target records and staged effects: changed source and staging rejection do not claim verified target; lost effect acknowledgment becomes UNKNOWN. **Ten tested documents does not mean ten importable programs or ten independent completed conformance suites.** FRG plan normalization, actual storage generation/fencing, provider code-trust, real managed session, machine schema and Run backend remain `LCD_BLOCKED`. These fakes are producer-authored and do not discharge the external independent cold-implementer gate.

**FRG frozen-plan admission hardening (same 10th packet):** a `FrozenAction` type alone does not prove that the action belongs uniquely to an approved `FrozenCleanupPlan`. The [FRG LCD](application/frg-cleanup-effect-plan-construction.md) now rejects an absent/duplicated/replaced action, a digest inconsistent with the complete plan, a source/target crossing the approved root, and a delete with no generation/byte witness **before creating a pending effect intent**. Its delete path re-reads current file evidence and recognized family/period rather than accepting any file that merely carries a previously recognized path. The Work-only candidate harness now injects forged actions, duplicate IDs, changed plan digest, foreign scope, lost byte generation, changed delete source, and family substitution. A separately pinned native FileEffectPort must still enforce **compare-and-delete** during the actual mutation; the structural checks by themselves establish no authorization/OS safety.

**Evidence tier:** `PRODUCER_EXECUTED_DESIGN_FRAGMENT_TEST` — stronger than source-syntax parse, weaker than a code implementation and distinct from an independent reviewer. It does not promote `LCD_CANDIDATE` to `LCD_READY_FOR_IMPLEMENTATION`; all listed blockers remain. A changed candidate requires this test and appropriate independent conformance to run again at the new exact revision.

## Cross-packet construction consistency (producer challenge; not independent)

These five packets share **semantic constraints**, not one prematurely selected data model. A real implementation must make the following inter-packet adapters explicit and test the same negative scenarios end-to-end.

| Boundary | Concrete handoff expected | Consistency condition and status |
| --- | --- | --- |
| Neutral consumed-byte receipt → domain Result → Scenario Operation adapter | Source/method/registry identities from the *actual* bytes consumed; a typed domain result retains both values and validation qualifications | A successful download is not a successful domain claim; host/app receipt linking is `CANDIDATE`, raw retention policy `BLOCKED` |
| Local Scenario Outcome → future host Run Outcome | A step/run identity mapping that preserves required-step failure, partial/unknown effect and explicit terminal evidence | Do not map any historical local `success` after failed required step to verified host success; schema migration and outcome policy `BLOCKED` |
| Operation output reference → local publisher → host Artifact fetch | A restricted output candidate may become a published Artifact only with a backend-specific finalization and verified receipt; host fetch additionally checks object access and current byte availability | A log path is never an Artifact receipt; local publisher `CANDIDATE`, host publication `BLOCKED` |
| Curated machine call → host authorization/execution | Definition/version validation and trusted binding precede machine submit; host admission returns a Run reference, never a valid bank result by itself | An operation appearing in a machine catalog does not authorize its effect; remote gateway `BLOCKED` |
| Automation trigger → host Run admission | Unique qualified occurrence is derived from a versioned rule and actual event/time/source evidence; a host Run is separately accepted with its own effect authorization | A repeated evaluation, rule-enabled switch or lost host acknowledgement cannot fabricate Job success, schedule duplicate effects or change client-owned execution truth; deployed scheduler `BLOCKED` |
| Generic provider binding → domain operation | Exact compatible provider is selected by declared policy; runtime capability readiness/failure is distinct from current caller authorization and domain/source validity | No first-import wins, hidden fallback, fake empty success or implicit package installation; published API `BLOCKED` |
| Local diagnostic evidence → host problem/read projection | Attempt-scoped restricted log and safe failure code link to accepted Run; only an acknowledged external problem occurrence gains a confirmed external reference | Telemetry failure does not alter domain outcome; audience/recorder/retention `BLOCKED` |
| Host principal/approval/effect guard → FRG file mutation | Admission and approval bind a versioned plan + concrete target set; the actual FileStore effect must be conditional on the same generation and authorized scope | Preflight success cannot permit later unauthorized delete or stale replace; both hosted authority and backend atomicity `BLOCKED` |
| Client disconnect/Qt lifecycle → future host authority | A client refreshes an authorized scoped snapshot by host-owned identity; a local-only process has no hosted continuity claim | Qt callback, active-client hint and AppDock health never decide hosted Run terminal truth; real host/client deployment `BLOCKED` |

**Cold implementer proof required:** construct one synthetic collector→domain→two-step Scenario with a failed required step, a diagnostic-only log, interrupted Artifact finalization and missing external Problem acknowledgment. The same logical input must yield differentiated acquisition/domain, Run/effect, Artifact and diagnostic states; neither the Qt local view nor a host-client fake may show unconditional success, published bytes or an acknowledged Problem without receipts. A second adversarial case must revoke access between a displayed artifact card and a byte fetch. These are **proposed integration tests, never executed**. The separate source-to-Science independent reviewer and Research Amputation remain unstarted by this producer check.

## Whole-Knowledge completion relation

An end-to-end Knowledge Product review must check that every admitted implementation-relevant target scope has a sufficient realization route: either a justified LCD result with its exact readiness grade, or a reasoned `NOT_APPLICABLE` disposition. Open Product Decisions and conditional deployments remain visible and owner-routed. Complete scientific conservation, current-state evidence, target coverage, architecture coherence, LCD decision closure, independent checks and publication integrity are **distinct gates**. A final publication may remain `PARTIAL / BLOCKED` when a genuine independent assurance or owner decision is unavailable; no agent may self-award that proof.
