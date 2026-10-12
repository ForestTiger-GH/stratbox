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

## Original Windows Study 0020: future portability and execution options (source packet A)

**Frozen source:** [Windows historical study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`. These 1 dated Research claims represent separately qualified proposed options, *not* delivered features or admitted Product commitments. [Windows current-state owner](../../current-how/windows-application.md) and actual implementation remain decisive for present-tense facts.

| Original address · role | Material historical meaning | Defeater or cost | Exact original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/FUT-01` · `HISTORICAL_CAPABILITY_SCALING_DIRECTION` | The study anticipated more CBR, bank, IFRS/RAS, macro, report and transformation capabilities exposed as operations without moving economic logic into Windows. | A future curated operation catalog is not a promise that every library helper has a stable callable contract, secure parameters or supported Result schema. | [L1382–L1395](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1382-L1395) |

**Conservation boundary:** source-specific producer interpretation only, no native deployment, validated future API, whole-source `LOSSLESS_PASS` or distinct independent reviewer. All source file dispositions remain `unaccounted`.

## Original automation Research 0041 — orchestration comparisons and roadmap basis (source packet A)

**Provenance:** [frozen original automation research](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. Tool names and dated preferences are **competing research examples** rather than installed dependencies, measured tool benchmarks or a commitment to outsource Strategy Box domain authority.

| Material original address | Source-qualified meaning | Countercase, cost or error boundary | Frozen original span |
| --- | --- | --- | --- |
| `SB-SRC-0041/ROAD-01` · `HISTORICAL_ORDERING_PROPOSAL` | The research's first implementation tranche proposed stable domain operation IDs, request/results, structured diagnostics, provenance, effect/risk metadata and Artifact outputs before machine-facing layers. | A proposed sequence is not current Product Authority; direct Python core may remain independently useful without a global catalog or AI runtime. | [L2024–L2037](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2024-L2037) |
| `SB-SRC-0041/RULE-01` · `HISTORICAL_SEMANTIC_OWNERSHIP_PRINCIPLE` | The source's cross-consumer rule put GUI, scheduler, AI, remote API and tests behind one curated Operation/Scenario meaning while keeping numerical business semantics in core. | Consumers can share meaning through typed contracts without sharing process implementation, and the old sketch assigning all runtime policy to AppDock is not binding. | [L2154–L2186](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2154-L2186) |

**Conservation limit:** dated comparative judgment and engineering proposal only; no live evaluation of current third-party APIs/versions, host, worker, schedule or domain service is asserted. Independent original→Science semantic certification remains open, as does full source material accounting.

## Original business-logic refactor study 0016: domain capability, product layer and FRG pilot

**Source character:** [dated historical primary study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md), exact Git blob `d04fece78c89063c2ac2dac775179f1517c7fea9` (1,927 physical lines), with an older in-core GUI layout that was superseded by the independent Windows repository. This source's domain and process proposals are preserved as conditional Science; the adopted application-host scope and existing core/source implementation retain separate authority.

| Source-material address / epistemic status | Original reasoning or candidate | Counterexample / present limit | Primary source location |
| --- | --- | --- | --- |
| `SB-SRC-0016/OWN-01` · `HISTORICAL_DOMAIN_INDEPENDENCE_ARGUMENT` | The historical architectural thesis favored reusable subject-level bank/macro operations consumable from Python notebooks, desktop and future managed run paths, with product presentation layered above. | A broad reusable operation is not arbitrary low-level helpers; direct Python remains valid without an installed client, and runtime-specific sources do not belong in core. | [L3–L24](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L3-L24) |
| `SB-SRC-0016/FRG-01` · `HISTORICAL_OPERATION_DECOMPOSITION` | The source decomposed FRG into scan, latest selection, cleanup planning, cleanup application, Excel export and ZIP bundling as different subject-level actions. | Planning and applying changes have distinct effects and authorization; a simple FRG stage-one return is not a certified mature operation contract. | [L26–L36](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L26-L36) |
| `SB-SRC-0016/FRG-03` · `RESEARCH_SCHEMA_CRITIQUE` | The source criticized returning an untyped dictionary of FRG catalog/latest/dispatch DataFrames as insufficient to express a canonical operation result, artifact and app projection. | Not every notebook requires a heavy record framework; the additional contract is justified when stable machine or app consumers need it. | [L66–L82](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L66-L82) |
| `SB-SRC-0016/ROAD-01` · `HISTORICAL_CAPABILITY_INVENTORY_METHOD` | The research advocated a pre-implementation census separating exported domain use cases, internal parser/registry mechanics and debug/sample entrypoints across FRG, archiver, CBR forms and escrow. | Listing every callable helper as an executable product operation can create unsafe or underspecified machine exposure. | [L520–L543](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L520-L543) |
| `SB-SRC-0016/ROAD-03` · `RESEARCH_OPERATION_MINIMALITY` | The proposed canonical operation shape covered stable ID, typed request/result, parameter validator, optional exporter/artifacts and minimal machine-readable descriptor, after real domain maturity work. | A descriptor is not execution admission, universal validity or capability permission; current APIs do not automatically satisfy the entire proposed contract. | [L576–L613](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L576-L613) |
| `SB-SRC-0016/FRG-04` · `HISTORICAL_PILOT_OPERATION_CANDIDATES` | FRG was proposed as canonical-operation pilot, with clear scan, cleanup.plan and cleanup.execute and optional combined/export operations, rather than exposing only one dict-returning stage function. | The illustrated dot-separated IDs were design examples, not shipped stable operation identifiers or permission grants. | [L1203–L1269](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1203-L1269) |

**Coverage and authority:** the old plan's exact capability names, file paths and suggested sequence are not current public APIs, not guaranteed FRG effect safety and not accepted release architecture. This packet is producer source-position routing only; extensive original remaining material and independent evidence/reverse checking remain open.

## Original Windows Study 0020: executable catalog versus diagnostic-only CLI (source packet C)

This additional **dated Research Source → Science producer** packet preserves material distinctions absent from a generic “portable app” slogan. The original was frozen at `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`, blob `225128f2599f0792422c0b31cb3cbe1437991ced`; direct Windows source is independently pinned to `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. Current-code descriptions are corroborated by the pinned [entrypoint](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/__main__.py), [operation registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/registry.py) and [Scenario registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/registry.py). This is **not** an executed host, approved RPC or complete whole-original certification.

| Source route and epistemic classification | Material original meaning | Countercase / proof limit | Frozen witness |
| --- | --- | --- | --- |
| `SB-SRC-0020/ENTRY-01` · `HISTORICAL_DECLARED_DEPENDENCY` | The pinned desktop distribution declared a specific analytic-core package version alongside a GUI-toolkit dependency; packaging declarations are distinct from the core version independently observed in the later analytic repository. | An old dependency pin cannot prove compatibility with a newer core or identify what a managed platform actually installed. | [L143-L159](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L143-L159) |
| `SB-SRC-0020/ENTRY-02` · `HISTORICAL_CURRENT_BOUNDARY` | The dated platform entrypoint validated activation and both managed Python package bindings before calling the ordinary Windows application entry, without rewriting the Python import path. | Validation of package-binding metadata does not establish a host endpoint, remote execution, shared authority or a successful deployed launch. | [L189-L203](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L189-L203) |
| `SB-SRC-0020/ENTRY-03` · `DIRECT_CODE_CORROBORATED_NEGATIVE` | The dated command-line no-GUI and diagnose paths execute the system diagnostics operation, print a JSON result and terminate; no-GUI here is a diagnostic command rather than a persistent headless application host. | Calling a process headless does not prove that it serves Jobs independently of Qt, a browser, or a connecting client's lifetime. | [L205-L240](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L205-L240) |
| `SB-SRC-0020/ENTRY-04` · `DECLARATIVE_METADATA_LIMIT` | OperationSpec included dangerous, visibility and AI-visibility metadata alongside handler references and presentation fields, making discovery and future policies representable in the catalog. | A descriptive flag or audience label is not an enforceable authorization check on actual data, effect, output or machine action. | [L430-L457](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L430-L457) |
| `SB-SRC-0020/ENTRY-05` · `DATED_CATALOG_SCOPE` | The dated application registry explicitly listed exactly two bank-data business operations and one system diagnostics operation, with handler references and configuration encoded by hand. | Three declared operation specs do not imply automatic exposure of every public Python helper, general discovery or safe arbitrary function invocation. | [L484-L555](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L484-L555) |
| `SB-SRC-0020/ENTRY-06` · `DIRECT_CODE_CORROBORATED_COMPOSITION` | Only enabled registered operations were transformed into single-step atomic Scenarios with a derived stable prefix, while operation and user-facing Scenario were separate semantic layers. | A UI Scenario wrapper does not change the underlying analytic method or establish an independent scheduler, remote worker or distributed Job. | [L562-L575](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L562-L575) |
| `SB-SRC-0020/ENTRY-07` · `DATED_SINGLE_COMPOSITE_EXAMPLE` | The dated full CBR update Scenario was one ordered two-step composition: collect source files, then export escrow history, with explicit Scenario-to-Operation parameter mapping. | This concrete sequential pair is evidence of bounded composition, not of a general DAG engine, branching, parallel execution or a durable host. | [L577-L588](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L577-L588) |
| `SB-SRC-0020/ENTRY-08` · `FUTURE_KIND_VERSUS_RUNNING_SERVICE` | The Scenario schema admitted atomic, composite, background and assignment kinds, but at the frozen source snapshot the actual registry instantiated atomic Scenarios and one composite only. | Schema vocabulary for background or delegated work must not be treated as proof that recurrence, delivery, execution authority or actual assignment processing exists. | [L592-L604](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L592-L604) |

**Reverse-use boundary:** the scientifically useful claim is that a registry item, GUI command mode, Scenario kind and actually admitted execution are different kinds of facts. [Current HOW](../../current-how/windows-application.md) owns exact frozen source behavior; the [host WHAT](../../what/strategy-box/host-deployment-commitment.md) owns the future host requirement; [local application LDD](../../ldd/application/local-scenario-orchestration-boundary.md) holds unexecuted extraction tests. None of the eight descriptions approves new physical repositories, server implementation, automatic tool exposure or prior schema compatibility.

## Original historical refactor 0016 — qualified application seams and negative alternatives

This bounded **frozen historical Research recovery** preserves the original three-selection hypothesis, one-to-many product representation, typed FRG result and exporter alternatives, separated cleanup plan/execute, the *unconfirmed* post-Run failure suspicion, and layered conformance responsibilities. The older source locates UI/application code in its former repository structure; current repository and accepted logical host boundaries follow direct code and Product Decisions instead. No fixed number of physical registries or an additional application repository is implied by this Science.

| Original source-specific assertion | Conserved mechanism | Counterexample / evidence scope | Source |
| --- | --- | --- | --- |
| `SB-SRC-0016/SEAM-02` · `HISTORICAL_ONE_TO_MANY_VISIBILITY` | The original explicitly allowed one domain operation to become zero, one or several user-facing product actions and required publication to external clients to be another narrower selection. | Assuming a one-to-one operation→button mapping exposes internal helpers or hides useful product choices; a visible form still does not grant an external principal authority to execute it. | [L241-L261](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L241-L261) |
| `SB-SRC-0016/SEAM-03` · `HISTORICAL_TYPED_RESULT_ALTERNATIVE` | The FRG example contrasted a bare three-DataFrame dictionary with typed Scan/CleanupPlan/CleanupExecute requests and results, including tables, Artifact descriptions, summary and warnings. | Typed models were proposed rather than shipped: adopting dataclasses alone neither validates source data nor proves outputs are published, and notebooks may legitimately consume tabular internal primitives. | [L343-L363](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L343-L363) |
| `SB-SRC-0016/SEAM-04` · `HISTORICAL_EXPORT_SEPARATION` | The paper urged a distinct workbook exporter over a stable domain result so notebook, application and permitted automation consumers can reuse computation without each implementing Excel serialization. | An exporter must preserve units, formats, source provenance and partial results; separate packaging does not imply identical display semantics or unconditional write permissions. | [L364-L381](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L364-L381) |
| `SB-SRC-0016/SEAM-05` · `HISTORICAL_THREE_FRG_PRODUCT_FORMS` | A proposed FRG pilot split scan, cleanup-plan preview and cleanup-execute with explicit destructive confirmation, while retaining inputs and optional output policy across product forms. | This split is a conditional product-projection pattern, not proof of three installed operations; approval must bind exact target bytes/plan revision and must revalidate when resources change. | [L383-L415](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L383-L415) |

The old proposal must be interpreted as **scientific/historical design alternatives**, not Product Decisions. The accepted Strategy Box application host is a logical responsibility; shared semantic selection and visibility can be provided without prematurely creating physical catalog services, registries or packages. The complete large source `SB-SRC-0016` still has unexamined material and `source_material_state=unaccounted`.

## Historical refactor 0016 — domain-by-domain candidate operation boundaries

A dated whole-product refactor proposal compared **existing reported domain APIs** and optional candidate changes. These Research statements are historical descriptions and design alternatives; the current `stratbox` codebase, tests and independently verified exports own present behavior. A candidate domain operation ID or type is not necessarily a shipped symbol or Product Decision. The original source contrasts proportionate canonical use cases with an indiscriminate global registry, and explicitly resists imposing a universal maximal metadata shape.

| Dated original route | Conserved difference and mechanism | Counterargument or evidence constraint | Frozen original source |
| --- | --- | --- | --- |
| `SB-SRC-0016/DOMAIN-01` · `HISTORICAL_ARCHIVER_PIPELINE_TRADEOFF` | The historical CBR raw-file archiver was judged closest to a typed public domain operation despite still exposing an end-to-end collect/save pipeline; splitting source selection, collection and separate file/ZIP outputs remained optional. | A user-oriented collector can be a valid cohesive operation. Mechanical splitting into every pipeline step increases API and consistency costs without a demonstrated separate consumer. | [L1279-L1323](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1279-L1323) |
| `SB-SRC-0016/DOMAIN-04` · `HISTORICAL_CURATED_DOMAIN_REGISTRY` | The original explicitly rejected registering every parser helper, naming routine, pivot implementation or file picker; only durable, semantically meaningful domain use cases would qualify for notebook/product/machine consumers. | Exposing every callable function through a catalog would confer misleading stability and expand the attack and maintenance surface; curated visibility still does not grant execution authority. | [L1420-L1445](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1420-L1445) |
| `SB-SRC-0016/DOMAIN-05` · `HISTORICAL_DRAFT_OPERATION_ID_ALTERNATIVES` | The early registry listed candidate FRG scan/cleanup operations, one CBR collector, one CBR Forms batch exporter and one escrow history exporter, plus explicitly optional granular collect/export/dataset helpers. | These are unadmitted illustrative operation names, not a tested or installed registry. Optional variants should be materialized only when a distinct stable user, domain or machine contract warrants them. | [L1449-L1499](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1449-L1499) |
| `SB-SRC-0016/DOMAIN-06` · `HISTORICAL_MINIMUM_OPERATION_DESCRIPTOR` | The suggested domain operation contract bundled identity, description, typed request/result, optional Artifact metadata, validation, capability flags and exporter links, while the same source argued against one mandatory megaschema. | A large shared descriptor can create false required fields and semantic drift. Minimal explicit types and real effect tests matter more than universal schema uniformity. | [L1522-L1539](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1522-L1539) |
| `SB-SRC-0016/DOMAIN-07` · `HISTORICAL_REQUEST_RESULT_EXAMPLE_TYPES` | The draft named domain-specific typed Request and Result forms across FRG, CBR raw-file collection, CBR Forms and escrow as examples of explicit public use-case signatures. | Example model/class names are conceptual. They cannot be treated as current importable classes, durable schema revisions or approved interoperability guarantees. | [L1541-L1563](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1541-L1563) |

**Proportionality and authority:** domain type declarations, product choices, authorized external exposure, verified published files and direct notebook consumption are distinguishable even when one physical implementation supplies several. This bounded producer packet does **not** imply a physical `stratbox-application` service, accepted new names, verified runtime support or full-original losslessness.

## Original historical refactor 0016 — final whole-source producer residue

Six additional source-addressed historical meaning clusters make the earlier refactor's file-placement proposal, actual app maturity criticism and source-defined first-stage deliverables explicit. They are **dated Research propositions**, not current code, product-approved architecture, actual deployed managed-platform features or requirements to materialize a repository per logical term. Earlier source-specific FRG, domain-operation, request/result, exports and selective product-projection evidence is retained without duplicating its unit IDs.

| Historical source position | Original meaning | Limiting or contrary evidence | Frozen source location |
| --- | --- | --- | --- |
| `SB-SRC-0016/COMPLETE-03` · `HISTORICAL_PUBLIC_EXPORT_INTERNAL_SEPARATION` | The paper proposed hiding naming, parser/pivot and registry mechanics behind explicit use-case operations and distinct exporters; example scripts would remain consumption examples rather than de facto capability registries. | Public API discipline does not require converting every internal helper into a dataclass or exporting every proposed workbook variant; direct notebooks may still legitimately use intentionally public lower-level utilities. | [L1578-L1631](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1578-L1631) |

The historical proposal is qualified by actual direct owner boundaries: `stratbox` remains independent analytical core; current Windows orchestration must be read from its own pinned code; a shared logical application authority is admitted for future hosted work but physical layout is undecided. Section-level whole-original producer reconciliation is evidence **separate from** this self-contained Science. Independent original-first and destination-backward review is not complete.
