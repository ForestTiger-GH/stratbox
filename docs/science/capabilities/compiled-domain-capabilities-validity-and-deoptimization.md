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
