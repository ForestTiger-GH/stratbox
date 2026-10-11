# Compiled domain capabilities: applicability, admission and deoptimization

**Scientific question.** Under what conditions may a repeatedly solved banking/macroeconomic analytical task be lowered to a cheap deterministic program, reusable composition, lookup, specialized solver or other machine path, while remaining discoverable to a future cognitive actor? **Status:** research-qualified engineering synthesis; no released cognitive protocol, self-compiling service, accepted `MachineScheme` schema or installed integration is asserted. Source baselines: [domain/cognition boundary study, 2026-10-07](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md), [machine-readiness study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md), and dated [core baseline](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox).

## 1. “Compiled cognition” is a useful analogy, not a product classification

It is possible for an expensive exploratory method to discover a repeatable procedure and reduce it to Python, SQL, finite-state machines, tables, rules, specialized optimization or a small fitted model. The reduction is often best called **cognitive/skill compilation, materialization, program synthesis or specialization**. In machine learning, **knowledge distillation** more narrowly denotes teaching a smaller model with a larger model's behavior; calling all deterministic business code “distilled LLM cognition” is conceptually misleading.

A core rule normalizing bank identifiers and a domain solver reconciling rounded statistical series may be valuable computational forms of once-cognitive tasks. An HTTP download, checksum, Excel writer and error serializer are frequently ordinary infrastructure or product functions. They should not be rebranded as AI schemes merely because an agent can call them. **Generated-by, semantically-owned-by and executed-by are three independent relations.** A program created by an AI still needs a domain owner and a product-level admission decision; invoking the program through an agent does not make its banking semantics agent-owned.

The benefit of this distinction is operational: a vetted repeatable calculation continues to work when models, agent memory, prompts or remote AI services are down. A first-person natural-language assistant can be an optional consumer without becoming an implicit requirement for core statistics.

## 2. Four channels plus a later admission channel

A transport endpoint alone tells an agent where to invoke a capability. It does not establish what the capability means or when use is justified. A useful conceptual interaction has:

| Channel | Question answered | Cannot certify |
| --- | --- | --- |
| Semantic discovery | Which curated product abilities exist, what goals/subjects they cover, what inputs and outputs they mean | That any one implementation is installed or presently authorized |
| Resolution/composition | Is this ability applicable here; can typed dependencies and effects form a valid plan? | That the worker will run or that world conditions will not change |
| Execution | Which admitted binding actually performs the Operation/Plan? | That a transport acknowledgment is a qualified analytical Result |
| Observation/evidence | What happened; which receipts, source vintages, artifacts, errors and uncertainty substantiate the outcome? | Automatically accepted current Knowledge or an authorized Decision |
| Capability admission (later) | Is a newly generated or altered capability allowed into the catalog? | Semantic validity solely because synthesis or compilation completed |

Python calls, IPC, HTTP, MCP, A2A and deployment-platform actions are **alternative transport projections** across some of these boundaries. The product's canonical meaning is not its transport schema.

## 3. Five distinct objects, not a giant scheme with mutable state

The 2026 studies refine a rough “Operation → Scenario → Cascade” vocabulary into five separable roles. Their exact names and persistence granularity remain decisions.

| Role | Question | Stable versus mutable facts |
| --- | --- | --- |
| **Capability/Operation Definition** | What exactly is the permissible domain transformation or action? | Stable semantic ID, contract, input/result meaning, effect and validity constraints |
| **Scheme Definition** | How do validated capabilities compose into a reusable task? | Versioned graph, type and dependency relationships, branch conditions, invariants, outcome/failure expectations |
| **Activation Binding** | Which manual command, scheduled occurrence, source event or machine proposal requests this Scheme in context? | Rule/trigger policy; independent from Scheme semantics |
| **ExecutionPlan** | Which exact implementations, input/source/registry snapshots, current authorities, resources and branch guards apply *this time*? | Frozen or revision-guarded resolved plan with digest and dependencies |
| **Run/Job/Attempt state** | What is actually being attempted, what effects are known and how does it recover? | Dynamic execution outcomes, checkpoints, resource leases, effect receipts and unknowns |

An accepted Scheme can serve foreground Windows, hosted background automation or a machine client without becoming three definitions. A scheduler trigger must not be baked into its business semantics. A physical thread pool and a semantic dependency graph are not equivalent; they can change independently.

The competing option of keeping all five in one composite record reduces initial types but risks mutable execution and control preferences contaminating the definition. Splitting every noun into a database table has the opposite cost: ceremony before independent lifecycles are proven. **Separate semantic responsibilities first; materialize objects only where consumers, concurrency or evidence justify them.**

## 4. Applicability is three-valued, not a Boolean disguise

A machine can invoke a well-typed endpoint that is wrong for the source vintage or regulatory schema. The capability requires an **applicability/validity envelope**: supported source and schema families, period/perimeter, reference registries, versioned transformation, permitted resource shape, required approvals and known limitations.

```text
APPLICABLE      exact preconditions supported; proceed to admission
NOT_APPLICABLE  proved incompatible; block or choose different method
UNKNOWN         evidence insufficient; inspect source/config or ask an accountable actor
```

`UNKNOWN` must not map to `False`, a guessed compatible version or a “best effort” call that mutates external state. The same capability can be applicable for read-only preview and inapplicable for destructive write under a changed resource revision. Applicability requires fresh checks at actual execution gates, not just at initial catalog discovery.

A compiled path has a bounded **validity horizon**. Invalidation triggers can include a revised source schema, changed bank registry/perimeter, package revision, edited parameter meaning, newly discovered counterexample, failing conformance suite or revoked authority. A green historic test result does not prove fitness for today's data.

## 5. Effects and frame conditions are part of machine meaning

A useful machine contract distinguishes intended domain transformations from physical placement:

- `READ`, `COMPUTE`, `NETWORK_READ`, `CACHE_WRITE`, `ARTIFACT_CREATE`, `ARTIFACT_REPLACE`, `WORKSPACE_MUTATION`, `EXTERNAL_WRITE`, `DESTRUCTIVE`;
- allowed write objects and required **frame conditions** (objects guaranteed unchanged);
- preconditions and postconditions;
- error/unknown/partial/unsupported outcomes;
- authorization and permitted reliance envelope.

A descriptor's `read_only` or `retryable` flag is a **claim needing test evidence**, not enforcement or complete retry policy. For an externally effectful step, retry requires a reconciled previous effect, idempotency scope, stable plan revision and fresh authority. The scheduler can choose “three retries, exponential backoff” only after the domain effect contract says when repeating is safe.

Similarly, semantic branching must expose its predicate and treat unknown predicates explicitly. Parallelism requires verified independence or leased resources; executing two writes on separate threads does not establish safe concurrent semantics. Resume requires durable checkpoints and revalidation of source, registry, plan and authorization revisions; `resumable=True` alone is an unsafe promise.

## 6. Static inspectability and a bounded compilation chain

A discoverable mature capability should be understandable without introspecting arbitrary source code, importing hidden modules or asking an AI to infer effects from docstrings. Candidate information includes:

```text
semantic ID + contract revision
subject/intent + typed inputs/outputs
supported source/perimeter/period conditions
required resources and permissions
effects + frame conditions + failure classes
evidence and conformance profile
binding/implementation revision and current readiness
versioned dependencies + plan digest where activated
fallback/deoptimization and revalidation triggers
```

A source parser, specialized optimizer and Excel formatter require different amounts of evidence. Typed IDs and a catalog are useful only if actual bindings cannot silently substitute a weaker implementation.

**Five distinct version axes** often matter: semantic contract; executable implementation; source/registry/environment dependencies; resolved plan; and test/assurance status. Some source research originally listed four, grouping assurance with other facts. Treating the fifth separately is a deliberate refinement: a successful test suite may be withdrawn while code bytes remain identical.

## 7. Deoptimization and generated-code admission

A valid compiled fast path must have an explicit path out:

```text
discover candidate → verify current applicability → bind exact version
  → test guards at execution → run specialized path
  → if unsupported/stale/failed: stop or downgrade to a separately governed general method
  → preserve previous attempt and effect knowledge
```

“Fallback” is safe only when semantics and permissions survive. Switching a failed atomic move to copy+delete silently changes guarantees; switching a flawed SORS restoration to a fluent model guess changes evidence strength. A general cognitive method can investigate the unknown **without** being authorized to fabricate an equivalent official observation.

For a capability generated by a model, admission is a separate path:

```text
repeated problem and observed candidate solution
 → synthesized code/rule/model
 → signed and hashed candidate with explicit generated provenance
 → domain/effect/security/conformance review
 → verify applicability and failure behavior on negative fixtures
 → authority approval and versioned catalog admission
 → future use as ordinary product capability, with no required agent
```

An unreviewed tool call or helpful code patch is **not** an automatically trusted operation. A separate product extension can hold user-specific generated logic; a stable general operation might eventually enter core; neither outcome is forced by its origin. Generated code should not execute from an LLM response directly inside the live product's privileged process.

## 8. Conformance levels are an evaluation aid, not shipped classes

The machine-readiness study proposes a six-level conceptual maturity ladder:

| Level | Meaning | Missing guarantee |
| --- | --- | --- |
| 0 — Callable | A function or command can be invoked | Stable public meaning, scope or effects |
| 1 — Typed Operation | Typed input/output and controlled errors | Catalog-level current availability and permissions |
| 2 — Discoverable Capability | Stable ID, descriptor, binding and policy projection | Reliable multi-step composition |
| 3 — Composable Capability | Typed ports, dependencies, known effects | Full machine scheme guards and replay |
| 4 — Machine Scheme | Reusable conditional graph, validity envelope and outcome contract | Autonomous generation/adaptation |
| 5 — Compilable/Evolvable | Admissible candidate compilation, learning and deoptimization route | Real measured safety without conformance tests |

This is a research vocabulary: Level 5 does not mean the present Python core has a cognitive compiler. A level must be based on demonstrated tests of the exact package and environment. The last stage is especially expensive: verification of synthesized implementations and retirement of stale paths is a continuing product responsibility.

## 9. Countermodels and failed assumptions

**Transport-first API design:** cheap to implement but makes a tool description do the work of an absent semantic contract; cannot resolve source-version applicability or safe effects.

**Run arbitrary Python helpers:** avoids catalog maintenance but leaks implementation internals, authorization scope, file access and unstable signatures.

**One universal cognitive scheme runtime in Strategy Box:** may offer uniform names but duplicates a general cognitive product, changes independent domain operations into an AI subsystem and undermines offline deterministic use.

**Everything is a cognitive schema:** exaggerates compiled cognition and confuses parser/IO primitives with reusable cognitive procedures.

**Every successful solver return is evidence of correctness:** confuses procedural termination with domain postconditions and intended-use evaluation.

**Automatic fallback to a general model:** risks converting unknown data or an unsupported method into an unsupported answer with false confidence.

**An approved capability never needs reapproval:** fails when source schema, risk/effects, dependencies or independent assurance change.

**Capability discovery alone grants authority:** confuses installed, compatible, applicable, selected, permitted, ready, executed and accepted.

## 10. Practical qualification tests

1. Change an upstream form schema while preserving the same download URL: the capability should return `UNKNOWN/NOT_APPLICABLE` or validated migration rather than fabricate comparable numbers.
2. Make two semantic-identical submissions with conflicting effect recipients: deduplication must respect effective scope, not merge distinct authorization.
3. Crash after an external write before response and restart: preserve unknown effect and prohibit blind retry.
4. Test a source-dependent branch with predicate `UNKNOWN`: do not treat unknown as false and choose an unintended branch.
5. Revoke resource rights before a checkpoint resume: refuse or replan.
6. Inject an invalid registry version after plan preparation: invalidate the plan digest or perform explicit revalidation.
7. Replace a supposedly atomic storage backend with a weaker copy+delete implementation: conformance must detect the violation.
8. Show a generated function that passes positive examples but fails a boundary-period fixture: no admission.
9. Disable all AI/machine integrations: a human should still invoke core analytical operations and obtain accurate results.
10. Present the same result through desktop, remote transport and AI text: semantic identity and uncertainty must remain consistent.

These are proposed negative probes, **not completed production tests**.

## 11. Decision frontier

The robust scientific position is independent domain capabilities with machine-readable meaning and reversible, evidence-governed use. However, the product has not decided whether `MachineScheme` deserves a new independently persisted type, whether a generic source/registry-driven compiler is economical, which protocol exposes capabilities, or who operates a future cognitive engine. A new repository, ontology package, workflow DSL or “Level 5” service must not be inferred from research alignment alone.

Related maintained Science: [machine discovery](machine-discovery-bindings-and-adapters.md), [composition identity](composition-identity-and-user-machine-projections.md), [effectful execution](../work/admission-planning-resource-scheduling-and-recovery.md), [evidence claims](../data-and-knowledge/semantic-promotion-firewalls-and-bounded-reliance.md), [portable clients](../surfaces/semantic-portability-and-client-authority.md) and [authorization boundaries](../trust-and-assurance/identity-authorization-and-effect-boundaries.md).

## 12. Research-source qualification and machine-readiness inventory (not an admitted standard)

This source-preserving matrix matters because dropping the qualifiers would silently turn a research proposal into a supposed implementation guarantee. Its original owner is [machine-readiness Research #31 and #37](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2112-L2169), blob `a0a1212e394b57792ec3b4f05066d5dbf540d21c`. **MUST/SHOULD/MAY below are the _source's proposed priority words_, not accepted Strategy Box obligations.** Every row is presented as a question or candidate conformance dimension. An individual item may be conditionally irrelevant, require a stronger specialist check, or be rejected in a future authorized contract; that disposition must be explicit rather than silently omitted. The 22-point checklist is a research-proposed human review aid and **not an executed acceptance test or official release gate**.

The inventory is separate from the maturity-level ladder above. It cannot be aggregated into one “AI-ready percentage”: e.g. a missing authority fence or unsafe destructive retry is critical even when 68 other fields pass. Nor does a richer descriptor prove its own content, its implementation's behavior, numerical validity, product rights, deployment readiness, or evidence freshness.

### Original 24 core prerequisites

| Original item | Source-exact research wording | Frozen source line |
| --- | --- | --- |
| `SB-SRC-0032/MUST-01` | Stable semantic identity. | [L2116](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2116) |
| `SB-SRC-0032/MUST-02` | Exact contract version. | [L2117](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2117) |
| `SB-SRC-0032/MUST-03` | Semantic input/output types. | [L2118](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2118) |
| `SB-SRC-0032/MUST-04` | Serializable machine schema for public capability boundary. | [L2119](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2119) |
| `SB-SRC-0032/MUST-05` | Applicability with `UNKNOWN`. | [L2120](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2120) |
| `SB-SRC-0032/MUST-06` | Explicit effects. | [L2121](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2121) |
| `SB-SRC-0032/MUST-07` | Explicit outcome/failure semantics. | [L2122](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2122) |
| `SB-SRC-0032/MUST-08` | Distinction semantic contract / implementation binding. | [L2123](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2123) |
| `SB-SRC-0032/MUST-09` | Exact implementation revision in provenance. | [L2124](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2124) |
| `SB-SRC-0032/MUST-10` | Determinism class. | [L2125](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2125) |
| `SB-SRC-0032/MUST-11` | Idempotency semantics where retry/effects matter. | [L2126](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2126) |
| `SB-SRC-0032/MUST-12` | Concurrency semantics. | [L2127](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2127) |
| `SB-SRC-0032/MUST-13` | Cancellation semantics for long operations. | [L2128](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2128) |
| `SB-SRC-0032/MUST-14` | Artifact identity beyond path. | [L2129](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2129) |
| `SB-SRC-0032/MUST-15` | Source/registry/version provenance. | [L2130](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2130) |
| `SB-SRC-0032/MUST-16` | Immutable capability/scheme definition. | [L2131](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2131) |
| `SB-SRC-0032/MUST-17` | No hidden mutable global semantic state. | [L2132](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2132) |
| `SB-SRC-0032/MUST-18` | Capability lifecycle/admission status. | [L2133](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2133) |
| `SB-SRC-0032/MUST-19` | Validity envelope. | [L2134](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2134) |
| `SB-SRC-0032/MUST-20` | Invalidation trigger. | [L2135](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2135) |
| `SB-SRC-0032/MUST-21` | Fallback/deoptimization for compiled fast path. | [L2136](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2136) |
| `SB-SRC-0032/MUST-22` | Capability discoverability without reading Python. | [L2137](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2137) |
| `SB-SRC-0032/MUST-23` | Tests/evidence for admitted capabilities. | [L2138](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2138) |
| `SB-SRC-0032/MUST-24` | Strategy Box standalone execution without PROTOS. | [L2139](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2139) |

### Original 15 conditional strengthening measures

| Original item | Source-exact research wording | Frozen source line |
| --- | --- | --- |
| `SB-SRC-0032/SHOULD-01` | Resource/cost/latency class. | [L2143](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2143) |
| `SB-SRC-0032/SHOULD-02` | Capability Envelope as first-class projection. | [L2144](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2144) |
| `SB-SRC-0032/SHOULD-03` | Typed relations between capabilities. | [L2145](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2145) |
| `SB-SRC-0032/SHOULD-04` | Hierarchical discovery. | [L2146](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2146) |
| `SB-SRC-0032/SHOULD-05` | AI visibility profile. | [L2147](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2147) |
| `SB-SRC-0032/SHOULD-06` | Canonical serialization + content digest. | [L2148](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2148) |
| `SB-SRC-0032/SHOULD-07` | Checkpoint/resume contract for long Scheme. | [L2149](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2149) |
| `SB-SRC-0032/SHOULD-08` | Effect receipts. | [L2150](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2150) |
| `SB-SRC-0032/SHOULD-09` | Frame conditions. | [L2151](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2151) |
| `SB-SRC-0032/SHOULD-10` | Outcome verification contract. | [L2152](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2152) |
| `SB-SRC-0032/SHOULD-11` | Generated docs from canonical contracts. | [L2153](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2153) |
| `SB-SRC-0032/SHOULD-12` | Conformance linting. | [L2154](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2154) |
| `SB-SRC-0032/SHOULD-13` | Property-based tests for invariants. | [L2155](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2155) |
| `SB-SRC-0032/SHOULD-14` | Type-first planner compatibility. | [L2156](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2156) |
| `SB-SRC-0032/SHOULD-15` | Static effect/resource derivation for Scheme. | [L2157](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2157) |

### Original nine later/optional transport and evolution directions

| Original item | Source-exact research wording | Frozen source line |
| --- | --- | --- |
| `SB-SRC-0032/MAY_LATER-01` | MCP projection. | [L2161](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2161) |
| `SB-SRC-0032/MAY_LATER-02` | HTTP/IPC transport. | [L2162](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2162) |
| `SB-SRC-0032/MAY_LATER-03` | CEL-like predicate language. | [L2163](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2163) |
| `SB-SRC-0032/MAY_LATER-04` | CloudEvents projection. | [L2164](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2164) |
| `SB-SRC-0032/MAY_LATER-05` | PROTOS-specific adapter. | [L2165](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2165) |
| `SB-SRC-0032/MAY_LATER-06` | Dynamic Scheme generation. | [L2166](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2166) |
| `SB-SRC-0032/MAY_LATER-07` | Automatic compile-down. | [L2167](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2167) |
| `SB-SRC-0032/MAY_LATER-08` | Remote federation. | [L2168](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2168) |
| `SB-SRC-0032/MAY_LATER-09` | Learned small-model bindings. | [L2169](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2169) |

### Original 22 capability review questions

| Original item | Source-exact research wording | Frozen source line |
| --- | --- | --- |
| `SB-SRC-0032/CHECK-01` | Is the semantic identifier stable? | [L2447](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2447) |
| `SB-SRC-0032/CHECK-02` | Can a machine consumer understand the purpose without reading Python source? | [L2448](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2448) |
| `SB-SRC-0032/CHECK-03` | Are the semantic inputs clear? | [L2449](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2449) |
| `SB-SRC-0032/CHECK-04` | Is the semantic output clear? | [L2450](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2450) |
| `SB-SRC-0032/CHECK-05` | Is the applicability context defined? | [L2451](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2451) |
| `SB-SRC-0032/CHECK-06` | Is an UNKNOWN applicability outcome expressible? | [L2452](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2452) |
| `SB-SRC-0032/CHECK-07` | Are the effects explicit? | [L2453](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2453) |
| `SB-SRC-0032/CHECK-08` | Are preconditions and postconditions explicit? | [L2454](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2454) |
| `SB-SRC-0032/CHECK-09` | Are failure meanings clear? | [L2455](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2455) |
| `SB-SRC-0032/CHECK-10` | Is retry safety known? | [L2456](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2456) |
| `SB-SRC-0032/CHECK-11` | Is concurrency behavior known? | [L2457](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2457) |
| `SB-SRC-0032/CHECK-12` | Is cancellation behavior known? | [L2458](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2458) |
| `SB-SRC-0032/CHECK-13` | Is recovery/resume behavior known? | [L2459](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2459) |
| `SB-SRC-0032/CHECK-14` | Is provenance available? | [L2460](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2460) |
| `SB-SRC-0032/CHECK-15` | Is supporting evidence available? | [L2461](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2461) |
| `SB-SRC-0032/CHECK-16` | Is the validity envelope defined? | [L2462](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2462) |
| `SB-SRC-0032/CHECK-17` | Is there an invalidation trigger? | [L2463](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2463) |
| `SB-SRC-0032/CHECK-18` | Is fallback or deoptimization defined? | [L2464](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2464) |
| `SB-SRC-0032/CHECK-19` | Is admission/lifecycle state explicit? | [L2465](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2465) |
| `SB-SRC-0032/CHECK-20` | Can the capability be discovered without scanning Python imports? | [L2466](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2466) |
| `SB-SRC-0032/CHECK-21` | Can the capability execute without a particular external cognition framework? | [L2467](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2467) |
| `SB-SRC-0032/CHECK-22` | Can the implementation be replaced while preserving semantic identity? | [L2468](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L2468) |

### How a future owner should actually qualify this inventory

1. **Specify the exposed scope.** A local pure transform, an effectful storage mutation, a specialized multi-step Scheme and a remote agent-accessible command require different subsets and depths. The source's label does not authorize exposing every helper function.
2. **Pin exact subject and versions.** Record semantic ID, definition version, implementation bytes and installed environment, source/registry vintages, plan digest and assurance evidence independently.
3. **Derive observable counterexamples.** For `UNKNOWN` applicability use a changed official schema; for idempotency inject ACK loss after external effect; for concurrency race competing output writes; for recovery revoke rights after checkpoint; for result verification inject a physically successful but semantically wrong workbook.
4. **Reject false positives.** A self-declared `deterministic=True`, `read_only=True`, `safe_parallel=True`, `resumable=True` or “tests pass” is not enforcement or current proof. The scope and negative fixtures of tests are necessary.
5. **Proportionality and ownership.** Some capabilities do not need background, cancellation or state checkpoints at all; a private deterministic expression need not implement all optional wire adapters. The public domain owner, application/host executor, deployment platform and any external cognitive participant retain distinct authority.
6. **No silent acceptance.** This checklist may inform future Product/Implementation acceptance only after an owner defines a scoped conformance profile, expected negative fixtures, status/reporting model and a reproducible result for each adopted requirement.

**Preservation status:** all **70 original item identities and their material questions/priorities** in this section are source-addressed; **48 priority items retain original English source wording**, while **22 review questions are English translations** of the original Russian. This is a **producer line-addressed source-to-Science transfer of 70 material items, with 22 explicitly translated review questions**, not independent verification of their technical soundness, complete coverage of the 2,744-line source or an assurance that the rest of Research is already conserved. The general Science article remains problem-space oriented rather than a normative machine API specification.
