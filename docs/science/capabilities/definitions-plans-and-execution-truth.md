# Analytical capabilities: definitions, composition, plans and observed execution truth

**Scope:** how one domain-analytical Python library can serve notebooks, human Scenarios and authorized machine callers without weakening source meaning, Results, effect boundaries or authorization. **Status:** maintained scientific/engineering conceptual model with competing interpretations deliberately retained. A universal Product ontology and future capability catalog have **not** been approved.

## 1. The minimum semantic ladder

“Operation” becomes overloaded when capability definition, a concrete request, a resolved plan and observed effects are treated as the same thing. A useful **role model**, not a mandatory physical architecture, is:

```text
Authoritative external sources and exact Registry editions
    ↓
Mechanisms: FileStore, HTTP, codec, parser, numerical solver
    ↓
Domain service and reusable analytical Capability
    ↓
Curated domain Operation with an observable contract
    ↓
Optional composition / user Scenario / machine Scheme
    ↓
Concrete Invocation, admitted and resolved ExecutionPlan
    ↓
Run / Attempts / Effects / Artifacts / diagnostics
    ↓
Qualified projections for human UI, direct Python, API or authorized agent
```

An **Operation definition** says what the capability means and which inputs it accepts. An **Invocation** specifies the actual call with resolved parameters and authority. A **resolved Plan** binds the steps, inputs/versions, dependencies and effects to be used. A **Run/Attempt** records what really happened and what was observed. One OperationSpec can have many Runs; the exact history of an earlier Run cannot be reconstructed safely from a later-mutated definition or current default settings.

This ladder describes distinct roles, **not eight compulsory databases**. A small deterministic Python function may only need a regular function signature and a documented result. A separate stable catalog identity becomes useful when there is an independent consumer, versioned plan, authority boundary, reusable cache, effect, audit or lifecycle.

## 2. Direct current implementation facts and extrapolation limits

The current `stratbox` core has multiple kinds of analytical work: retrieving official files, banking reporting forms, industry series, escrow statistics, file-related FRG procedures and SORS statistical reconstruction. Some domains already expose typed Request/Result and staged pipelines; others expose direct functions or DataFrames. This establishes usable domain behavior, **not a shipped universal `CapabilityRegistry` or Scheme compiler**. The pinned [FRG cleanup](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py) contains plan/effectful file handling; [escrow operations](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/escrow/operations.py) illustrate domain pipeline stages. Typed boundaries may be introduced without forcing a full rewrite of every underlying calculation.

In `stratbox-windows`, current operation and scenario definitions are declarative, while the pinned [runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) executes ordered steps **sequentially** with parameter transfer and fail-fast behavior. This does **not** establish a DAG executor, parallel scheduler, distributed queue, fully effective cancellation or durable shared authority. The [BackgroundStore](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) maintains local flags/status, not an autonomous scheduler.

The Windows client depends on the analytical core; a Python/notebook consumer can invoke that core directly. Machine-protocol adapters, UI composers and notebook wrappers are different **access projections**, not a justification to copy banking formulas across frontends.

## 3. Command, Scenario, Cascade and Scheme: an actual ontological competition

At least three Research models compete:

| Research model | Strength | Boundary, cost or counterargument |
| --- | --- | --- |
| **Command → Scenario → Cascade** | Human-readable hierarchy of atomic action, Scenario and larger reusable composition; useful when Cascades have their own naming, saving and sharing lifecycle. | May expose every small Python helper as a pseudo-Command, and multiply lifecycle objects when actual composition needs are limited. |
| **Capability → Machine Scheme → Resolved Plan → Run** | Typed composition, dependency checks and versioned source binding; user Scenario may become a presentation of a machine model. | Relation to user Work/Case, execution rights and independent history is uncertain; requires a type system, planner and perhaps a DSL. |
| **Minimal curated Operation + composed Scenario** | Fits present heterogeneous banking use cases and the observed sequential Windows runner. | May become insufficient for branching, separately scheduled resources, nested compositions and machine planning. |

**Scheme and Scenario are neither automatically identical nor automatically mutually exclusive.** A Scenario can contain a logical plan; one user Work may use several Scheme/Plan versions. A separate “Cascade” card makes sense if it has a genuine consumer, stable identity, versioned use and independent lifecycle; that does **not** imply a second DAG executor.

Likewise `Command` may mean a low-level technical planner action, while a domain `Operation` denotes an economically meaningful analytical task. Renaming objects before examining real consumers and side effects would merely move ambiguity around. Agreement between several related Research texts is not independent experimental validation.

## 4. Capability contracts: material dimensions, not maximal JSON

Where a distinct durable capability contract is actually warranted, its meaningful dimensions include: stable semantic identity and definition revision, human-facing purpose, typed input/result meaning, preconditions/postconditions, concrete implementation binding, authority, touched resources, determinism, network/storage effects, source/Registry freshness, partial failure policy, cancel boundary, retry/idempotency semantics, computational cost, provenance and what outcome can be independently verified.

Fields such as `enabled`, `visible_to_ai`, `destructive` and `can_cancel` **are not themselves enforcement**. Display/discovery only tells an external consumer what it might request. The actual execution authority still needs to verify current Principal, resolved target resource, policy/grant revision and effects, especially for destructive/network mutations.

Safe machine composition does not require arbitrary remote Python-code execution. A bounded set of admitted operations, strict input types, version-pinned references and auditable guard expressions is preferable at a risky execution boundary. A direct local Python API can remain rich; serializable envelopes matter only when actual process/actor transport requires them.

## 5. Rich domain Results and transport representations differ

A domain Result may include DataFrames, several normalized tables, source errors, mathematical intervals, rejected hypotheses, conflicts and evidence references. Flattening all of that into `{ok: true, file: path}` would erase the uncertainty and analytical meaning behind “success.”

On the other hand, transporting giant DataFrames through a generic control-plane API can be expensive. A reasonable alternative is a typed Result descriptor with validated metadata, metrics and provenance; separate dataset/Artifact references for bulky payloads; and native domain objects for direct Python callers. This **does not require** making every domain Result an identical generic object.

Consequently:
- absence of errors must not be conflated with absence of data;
- an uncomputed observation is not numeric zero;
- a partially successful pipeline may have valuable files **and** unresolved failures;
- `Run admitted` is not the same as `Run succeeded`;
- a physical path existing does not prove an Artifact is committed and available.

See [source editions and reproducibility](../data-and-knowledge/source-identity-and-reproducibility.md) and [unknown outcomes](../trust-and-assurance/uncertain-outcome-vs-observed-error.md).

## 6. Composition has multiple relation types

A useful plan distinguishes **dataflow** (output of A feeds B), **control flow** (B executes after A), **authorization dependency** (rights are checked before effect), **resource/exclusivity conflict** (a file/path/key cannot be mutated concurrently without coordination), and **effect ordering** (what must be committed or verified before an irreversible step). Encoding them all as one generic edge can hide failures.

A typed DAG fits finite acyclic computation. Conditions, retries, bounded loops, manual approvals and enduring event-triggered rules require different semantics and explicit expressiveness limits. JSON Schema, workflow DAGs, business processes, AI planning with preconditions/effects and provenance/events each cover different useful subproblems; **no single borrowed standard automatically owns every role**. Syntax, DSL and engine selection remain open.

**Counterexample to unsafe compilation:** two pure steps compute the same sum from one immutable source snapshot. A compiler may share that calculation. If two other steps each intentionally write separate files or notify different recipients, they are **not effect-equivalent** merely because their numerical answers are equal. Effects, actor, target and required multiplicity remain part of semantics.

## 7. Four kinds of reuse have different proof conditions

1. **Algorithm reuse:** different calls invoke one implementation rather than duplicating source code.
2. **In-plan deduplication / common subexpression:** equivalent *pure* computations within one resolved Plan share one execution.
3. **Cache reuse:** a later consumer reuses an existing result only when input snapshot, parameters, implementation/Registry revisions, policy and freshness/applicability justify it.
4. **Idempotent submission/retry:** a repeated message expressing the *same intent* does not admit duplicate Work/Job; external effects still require provider-side identity and independent receipts.

Matching function names is insufficient for steps 2–3. An application-scoped `idempotency_key` does not guarantee exactly-once external mutation without cooperation or reconciliation at the real effect owner. Resolve aliases such as `latest` to concrete versioned snapshots before claiming replay. An incorrect reuse can be more damaging than duplicate CPU work: it may apply another reporting period or skip a necessary side effect.

See [scientific analysis of computational and effect equivalence](../trust-and-assurance/computation-reuse-and-external-effects.md).

## 8. Distinct lifecycles cannot be represented by one status flag

At minimum distinguish:
- **Capability definition:** proposed, validated, available, deprecated or revoked; this records published-tool meaning and trust in a revision.
- **User Work/Case:** prepared, admitted, waiting on human input, under review, completed; this denotes the commissioned analytical task.
- **Run/Attempt:** admitted, running, interrupted, succeeded, failed, outcome unknown; these are facts about actual execution and observations.
- **Automation definition:** enabled/disabled rule, schedule and policy; an **Occurrence** is the concrete trigger of a potentially new execution.
- **Artifact:** planned, staged, verified/published, missing or retired; physical output and meaning have distinct life cycles.
- **Read/presence projection:** per-user read cursor and short-lived availability.

`automation.enabled=true` does not prove a worker is running. `cancel_requested` is not `cancelled`; terminating a thread cannot roll back an already committed external action. Lease expiration does not prove the old worker has stopped; fencing and reconciliation matter for dangerous commits.

Closing the local GUI may interrupt a locally owned Job. With an actually installed independent host authority, client disconnection should not automatically kill that host-owned Job. These two deployment profiles are compatible under explicit executor identity and recovery promises. See [Science of authority and durability](../state-and-recovery/authority-durability-and-recovery.md).

## 9. Domain meaning across different consumers

The same underlying capability may be consumed:
- in a Python notebook through a native typed Request/Result;
- on Windows through form definitions, scenario chat and a local execution adapter;
- in a future Web/mobile client through serializable commands and access-scoped Result projections;
- by an authorized machine consumer through limited discovery and governed invocation.

A shared **semantic contract** does not mean shared Qt Widgets, identical filesystem paths, identical background-job controls, a full mobile UI or an already operational remote endpoint. The currently observed Qt client provides a fixed, limited operation set; server/client/agent topologies remain proposals.

## 10. Negative conformance cases and knowledge changes

A later independent assurance cycle should investigate:

| Boundary | Falsifying scenario |
| --- | --- |
| Definition → Invocation | A new default silently changes the stored parameters of an old Result. |
| Plan → Run | A visually convincing planned DAG is presented as actual executed steps. |
| Authorization | An external consumer gains write authority solely from discovery/visibility. |
| External effects | A file deletion repeats after timeout without checking the first effect. |
| Source version | Cached July 2026 data is presented as fresh August data through alias `latest`. |
| Typed result | A generic JSON payload silently destroys domain DataFrame/evidence meaning. |
| Composition | A required output write disappears because a planner deduplicated a pure calculation. |
| Cancellation | The user sees “cancelled” even though an irreversible mutation committed. |
| Shared-state authority | Two UIs both write the same local authoritative JSON without conflict checks. |
| Lifecycle | Enabled automation is presented as an active worker despite no scheduler. |
| Provenance | A finished workbook cannot identify its exact source bytes/revision and method. |
| Fidelity | A decoded DataFrame is wrongly advertised as a byte-faithful DBF conversion. |

**Material negative result:** the researched baseline does not establish a working universal Scheme compiler, independent multiuser/host/AI executor, complete accepted API/permission contracts or measured economics of a global source/Registry catalog. Several studies derive terminology from common earlier materials; agreement may be evidence of **shared lineage**, not independent validation. Research on raw DBF fidelity raises additional engineering questions without demonstrating a shipped universal source-preserving converter.

## 11. Unadmitted alternatives and reopening conditions

Still open: whether Scheme and Cascade need independent identities; Command semantics for technical steps; what merits a stable public Operation; the owner of pure planning versus managed execution; resource scheduler necessity/concurrency budget; typed composition syntax; machine-facing API scope/timeline; effect classes; Artifact/Result retention; true Web/Android consumer scope; tested external platform remote contracts; governance and operational assurances.

**Research-favored but unapproved sequence:** identify one real consumer and end-to-end Work; extract stable domain Request/Result; determine exact source/effect/authorization boundaries; validate one necessary composition; then assess whether an always-on catalog/DSL/compiler earns its complexity. This is **not an automatically accepted Product roadmap**.

**Direct implementation witnesses:** [sequential Windows runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py), [local background flags](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py), and [core FRG file effects](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py). Formal negative effects/reuse examples remain **hypothetical countercases**, not deployed incidents. Changes to pinned implementations, real consumers, independent conformance findings and Product Decisions require renewed review.
