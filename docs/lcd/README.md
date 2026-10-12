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
| **Realization decomposition** | Required implementation responsibilities, state owners, effects, module/interface seams and dependency direction; physical file layout only if material. |
| **Concrete contracts** | Input/output types and errors, lifecycle and state transitions, storage/consistency, concurrency, cancellation, retries, authorization, artifacts, external interfaces and recovery **as applicable**. |
| **Material decision closure** | For each consequence-bearing choice, record accepted decision and rationale, allowable implementation variants, testable constraints, owner and blockers. |
| **Implementation freedom** | Mark `FIXED`, `BOUNDED`, `DELEGATED_NONMATERIAL` or `BLOCKED_ON_AUTHORITY_OR_EVIDENCE` per decision. Freedom must be explicit; a speculative API signature is not a decision. |
| **Conformance and handoff** | Acceptance/negative tests, expected observable results, required environments, evidence needed, unresolved risks and stop/reopen conditions; distinguish planned from executed tests. |

A ready model should let a **cold competent implementer** identify its starting baseline, smallest bounded change, protected invariants, allowed choices and falsifying checks using maintained Knowledge alone. An independent reviewer should be able to identify where implementation could still diverge materially. The target is **material implementation-decision closure for the declared scope**, not identical code generation from the same text.

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

## Whole-Knowledge completion relation

An end-to-end Knowledge Product review must check that every admitted implementation-relevant target scope has a sufficient realization route: either a justified LCD result with its exact readiness grade, or a reasoned `NOT_APPLICABLE` disposition. Open Product Decisions and conditional deployments remain visible and owner-routed. Complete scientific conservation, current-state evidence, target coverage, architecture coherence, LCD decision closure, independent checks and publication integrity are **distinct gates**. A final publication may remain `PARTIAL / BLOCKED` when a genuine independent assurance or owner decision is unavailable; no agent may self-award that proof.
