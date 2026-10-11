# Composition identity and human/machine projections of analytical capabilities

**Subject:** when an analytical Python function deserves a public Operation identity; why Composition should be distinguished from presentation; how a user Scenario, grouped Cascade and agent-readable Scheme relate to the same code without becoming five conflicting execution engines. **Status:** comparative scientific analysis and criteria; type names, physical registry, version scheme, catalog UI and interpreter remain unapproved design alternatives.

## 1. Five terms mix seven orthogonal questions

The terms `Command`, `Operation`, `Scenario`, `Scheme` and `Cascade` originated from different needs. They can mean (a) **economic/analytical semantics**, (b) callable implementation, (c) composition of calculations, (d) human discovery and use, (e) machine interpretation, (f) permission to act, and (g) one observed execution. An object combining all seven dimensions inherits unstable names, mutable UI labels, unverified authorization and implementation details. Five separate duplicated catalogs create the opposite failure: inconsistent versions of one financial calculation.

A **Python function** is a reusable implementation, but not automatically a stable product capability. A **domain Operation** is a meaningful, managed subject-level ability with typed inputs/outputs, validity and effect boundary. A **Composition** connects invocable operations and possibly other compositions by explicit typed edges. A **Scenario** presents and curates one Operation/Composition for a person. A **Scheme** is often a machine-interpretable projection of the same semantic definition; a separate object is justified only by its own method/applicability/policy. A **Cascade** may be a catalog grouping, a runnable composition or a longer-lived user Work/Program—these interpretations must not be conflated.

The classifications are conceptual and do **not** require a class/table/repository for each label. A single simple Run can contain an embedded resolved plan and one callable. The earlier [capability definitions discussion](definitions-plans-and-execution-truth.md) explains definition/invocation/execution identity, while this article focuses on the *independence tests* and composition semantics.

## 2. Different atomicities prevent a “one function = one Operation” rule

| Sense of atomicity | What forms the boundary | Counterexample |
| --- | --- | --- |
| Source code | One Python `def` or module | A single useful NPV function may call tens of helpers |
| Subject meaning | A self-contained useful analytical result | A batch CBR download uses multiple network requests |
| Execution/control | Independent permissions, retry, resources, effect receipt | A short `delete` call may deserve tighter supervision than a long pure calculation |
| User workflow | One understandable menu item or request | “Build escrow report” may run download, parse and export |
| Transactional | Observably old/new effect within a supported backend | An Excel publish may be atomic only at one file rename, not across all inputs |

Consequently, **publish a curated Operation** where a stable independent use case exists, a consumer can understand it, input/result and errors can be specified, side effects are distinguishable, and a real owner will maintain conformance. Avoid registering every exported numerical/string/parser helper. There is no requirement for each Operation to have a GUI page, separate database, asynchronous runner, MCP endpoint or stable entry-point filename.

Useful candidate operation roles (not compulsory catalog members): source discovery/fetch/validation; parsing/normalization; domain calculation and modeling; semantic consistency checks; pivot/view/transform; export/materialization; managed workspace scan/copy/cleanup; diagnostics. For example, a general `round()` helper is not automatically an economic Operation. A yearly loan growth calculation specifying missingness, bank perimeter and units may be.

**Command** remains ambiguous between shell command, UI action, user instruction and planner step. It can be an internal technical step where retry/effect constraints demand separate identity, but a public `CommandDefinition` alongside `OperationDefinition` needs a concrete independent consumer. Opening a local file or copying an output path is ordinarily a UI action, not an analytical step.

## 3. Five candidate ontologies and why no name won by default

| Option | Why it is attractive | Fundamental cost / limitation | Research disposition |
| --- | --- | --- | --- |
| **A: Python functions and hand-written scripts only** | Maximum Python/Colab reuse, minimal infrastructure | Uncurated machine discovery, unstable external identity, no common effects/visibility | Essential lowest layer, incomplete as managed catalog |
| **B: five independent Command/Operation/Scenario/Scheme/Cascade models and engines** | Every label can have its own lifecycle | Repeated code/contracts, identity drift and redundant permission schemas | Reject as default |
| **C: Scenario/Cascade own executable chain; Scheme describes them** | Close to today's Windows interface and older hierarchical design | GUI definitions leak into core and machine reuse; typed reusable subgraphs awkward | Bounded transitional approach |
| **D: canonical Operation + typed Composition + user/machine projections** | Reuses one domain implementation, supports nested plans and several consumers | Requires version discipline, explicit typed binding and neutral owner | Strongest *proposal*, not accepted Product Decision |
| **E: CWL/BPMN/external workflow engine becomes ontology** | Mature workflow representations/executor features | Heavy runtime dependencies, domain typing loss and disproportionate overhead | Standards as selectively reusable evidence, not mandatory engine |

The original study scored these alternatives with **expert qualitative symbols rather than benchmarks**. Relative preference for D cannot establish runtime throughput, ergonomic success or actual platform compatibility.

## 4. Separate Scenario and Scheme identities only when meaning differs

The default case: one Python function `calculate_growth` is exposed as Operation `banking.portfolio.growth.calculate`; a user Scenario has a label and controls; an AI-facing Scheme describes scope, input, units, errors and effect. **There is one semantic Operation revision**. Changing localization or an icon must not issue a new scientific method version. Machine transport has its own *projection-schema revision* without manufacturing a new algorithm.

A Scenario can merit its own stable identity when it is a separately curated offering with audience, presets, publication/withdrawal lifecycle, human-review criteria or deployment availability. Several distinct Scenarios may point to the **same** Composition or single Operation. A Scenario may be `draft → reviewed → published → hidden/deprecated → withdrawn` while its underlying operation revision stays constant. Earlier Runs retain the definition version actually used.

A Scheme can merit a *separate* identity when it introduces independently applicable methodological rules: selecting an analytical method given evidence tiers; an independently versioned reusable composition invoked by multiple clients; separately qualified decision policies or interpretations beyond an input JSON Schema. It can often be modeled more clearly as `CompositionDefinition` or `Method/DecisionScheme`, avoiding duplicated executor code. A change only to tool name, MCP transport, agent prompt wording or language localization does **not** satisfy this criterion.

Use a five-part independence test: independent semantic change; independent consumers/references; separate owner/lifecycle/version/grant; correctness or traceability harmed if fused; separately testable validity. A new label for AI fails this test.

| Example | Separate Scenario identity? | Separate Scheme identity? |
| --- | --- | --- |
| One Operation exposed in UI and MCP with identical scope | Optional generated view | No |
| Two named user workflows on one underlying typed composition | Yes, when separately curated | No |
| Reused five-operation DAG with independent version/conformance | Optional views | Composition ID, not necessarily Scheme |
| Decision methodology with evidence rules and alternative acceptable approaches | Possible | Yes if truly independent semantics |
| Different transport, English title or fixed UI icon | No | No |
| A monthly preset on the same procedure | Maybe distinct user Scenario | No |

## 5. Three interpretations of Cascade must stay distinct

**Catalog Category/Collection:** a “Banking reporting” folder with several Scenarios but no combined execution. It is *navigation*, not Composition.

**Runnable composite product:** “Refresh all CBR source groups” binds multiple admitted capabilities under a single versioned plan, with top-level parameters, partial failure policy, time/cost budget and user-facing result. It is a **Composition** presented as a Cascade, perhaps with its own catalog identity.

**Long-lived coordinated Work/Program:** cross-user approvals, different runs and responsibilities over time. That exceeds a simple composition and belongs to actual Work lifecycle/authority only when an approved product profile needs it.

A separate Cascade ID becomes meaningful when the user deliberately selects the entire runnable task, needs a stable revision and result summary, schedules or delegates it, and controls its aggregate quality and resource policy. Merely having many nested steps, a third menu level, or one heavy SORS solver does **not** justify an independent engine.

N-level **acyclic composition** with pinned definitions is more expressive than rigid `Command→Scenario→Cascade`: one user Scenario can refer to a reusable subcomposition used by two larger Cascades. A code-compiled flattening is acceptable when the subgraph has no independent version, rights, evidence or result. Keep a named subcomposition addressable when it is reused/tested/versioned, carries its own effect/approval/checkpoint boundary or is diagnosable independently.

For compound outcomes, distinguish execution completed, user goal satisfied, known partial result, required criterion failed and external outcome unknown. A final step returning `ok=True` after only 18 of 20 required downloads does **not** establish goal satisfaction.

## 6. A typed composition is more than a sequence of shared parameters

The existing Windows [`ScenarioSpec`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py) and [registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/registry.py) provide three atomic wrappers and one multi-step sequential Scenario. The [runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) transfers user parameters to step calls; it does not demonstrate a general typed dataflow DAG, resource-concurrent planner or arbitrary nested graph interpreter.

A small candidate Composition needs **stable ID and revision; purpose/owner; typed global inputs; typed node inputs and outputs; references to exact Operation/Composition versions; explicit directed dependencies; required/optional status; valid partial/failure behavior; result ports; declared effect/precondition/resource classes; cycle and missing-capability rejection**. An interpreter might start with a linear DAG and bounded nesting. Rich `DataFrame`/NumPy remains in direct Python memory or passed via typed dataset references to a remote consumer; control schemas need not serialize millions of banking cells into JSON.

Example dataflow:
```text
source.fetch : DownloadBatch
      ↓ typed binding (not just an implicit output pathname)
parser.normalize : CanonicalTable
      ↓
analytics.growth : DomainResult
      ↓
workbook.stage : MaterializedBytes
      ↓ verify
artifact.publish : ArtifactRef + Receipt
```
A graph node refers to `steps.<id>.outputs.<port>` or a semantically equivalent stable binding. Invalid port type, missing version/capability, unauthorized destructive operation or dependency cycle should cause **pre-execution validation failure**, not runtime discovery after half the outputs were written.

Conditional guards, `foreach`, limited retries, nested graphs and parallel branches may later be justified by real source-consumer examples. Unlimited arbitrary Python snippets in a serialized Scheme make tool exposure a remote-code execution and assurance hazard. Scientific optimizer/solver iterations should remain inside the trusted domain Operation, not explode into a million catalog steps.

**Composition vs packaging:** connecting Operation A's result to B's input changes what executes. Publishing an existing Operation in a form, CLI help or MCP descriptor changes only how a consumer discovers or invokes it. Treating a machine projection as its own execution graph is a frequent source of semantic duplication.

## 7. A neutral operation contract with independently checked binding

An admitted `OperationDefinition` (candidate schema, not existing API) can carry `operation_id`, semantic `definition_revision`, title/summary, typed input/output contracts, applicable sources and periods, effect profile, domain result policy, optional dependencies/resources, owner, examples, and implementation binding. User/admin/AI visibility is a *projection*, not an authorization grant. Binding can change under verified semantic compatibility; the old Run still needs exact code/build identity for reproducibility.

A machine consumer needs sufficient **domain meaning**, not only `{"name":"build_report", "args":{"period":"2026-09"}}`: required source/perimeter/units, missing data behavior, complete/partial and uncertainty, write/destructive profile, downstream outputs and actual host availability. `readOnlyHint`, `effect_class=read_only` or a UI enabled flag **does not enforce an effect boundary**. Machine-generated plans are proposals until their operation IDs, types, versions, grants, resource scope and effect budgets are resolved by a real authority.

Distinguish (1) **typed Python API** (rich dataclasses, DataFrames, numerical results in Jupyter/Colab) and (2) **generic invocation contract** (safe/serializable descriptors, Run/ResultRef, permitted host execution). A future machine-facing adapter should never require internal private source imports, credentials, raw stack traces or unrestricted access to all package functions. Different Colab/network/filesystem circumstances alter **environment binding**, not the meaning of the operation.

Operation/composition/Scenario/Scheme may have distinct versions from the implementation build and binding/provider. Example: `operation_id@semantic_revision`, `composition_id@revision`, `scenario_id@publication_revision`, `projection_schema_version`, `implementation_binding@build`. Filename and localized title are not canonical IDs. The “no old API compatibility” rule does not permit old Run history to be rewritten with today's definition.

## 8. External analogies: evidence of separable roles, not a mandate to install frameworks

| Analogy | Useful semantic contribution | What it does not establish |
| --- | --- | --- |
| [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/) | Typed structured input/output and reusable constraints | Execution ordering, domain validity or grant |
| [CWL 1.2](https://www.commonwl.org/v1.2/Workflow.html) | Typed ports, subworkflows, scatter/gather | A suitable always-on runtime for pandas/desktop |
| [Workflow Patterns](https://www.workflowpatterns.com/) | Sequence, branching, resource and exception patterns | A fixed 3-tier product ontology |
| [HTN planning](https://aaai.org/papers/01123-aaai94-173-htn-planning-complexity-and-expressivity/) | Nested decomposition and applicability | Bounded-cost autonomous planning by default |
| [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | External AI descriptor/call shape | Core ownership, trustworthy annotations or job recovery |
| [A2A](https://a2a-protocol.org/v1.0.0/) | Delegated agent task interaction | Identity/effects of a bank domain operation |
| [W3C PROV](https://www.w3.org/TR/prov-o/) | Inputs/activities/outputs/actors and lineage | Mandatory RDF store for each XLSX |
| [Celery Canvas](https://docs.celeryq.dev/en/stable/userguide/canvas.html) | Chain/group/chord of reusable tasks | Reason to run broker and workers for three Windows operations |
| [Prefect](https://docs.prefect.io/), [Dagster](https://docs.dagster.io/), [Temporal](https://docs.temporal.io/) | Contrasting flow, asset and durable workflow models | A universal solution for domain validity and UI |
| [Python entry points](https://docs.python.org/3/library/importlib.metadata.html) | Installed provider discovery under namespace | Automatic trust/admission or public promotion of any callable |

An external standards comparison may be dated, and no current full conformance is certified. Use only applicable semantics and versioned external contract tests. A protected optional provider may implement a neutral public contract; public Science must not expose any private implementation details.

## 9. Fifteen prospective invariants and negative probes

The original identifies 15 independent candidate constraints. In semantic form:

1. A valid direct core Python Operation needs no GUI/platform import.
2. One domain algorithm has a canonical meaning owner across renderers.
3. Registered Operations carry stable semantic ID, revision, owner and binding.
4. Inputs and outputs are checkable without erasing rich domain Results.
5. Machine compositions resolve exact compatible definitions and reject cycles.
6. Effect metadata and tool visibility do not substitute permissions or receipts.
7. Localization/icon/transport changes do not change algorithm identity.
8. Scenario/Cascade can be projections without duplicate execution code.
9. Mandatory failed steps cannot be displayed as full completion.
10. Old Runs retain pinned definition/binding versions.
11. New persistent nouns are justified by independent identity/lifecycle.
12. AI discovery exposes a curated permitted subset, invocation still authorized.
13. Source, registry, cache and artifact identity differ from Operation definitions.
14. External effect uncertainty survives until verified; blind retries are unsafe.
15. A composition interpreter can be Qt-free when a cross-surface consumer exists.

Falsifiers include: Qt imports required by a notebook operation; code changes when a UI title is edited; a typo in `step.outputs` silently accepted; cycles allowed to run; dataflow types miswired; a new `latest` source silently replacing old pinned bytes; a machine tool guessed into existence; destructive action admitted from annotation alone; identical branch execution counted as completely successful despite a required failure; old Case rendered with new definitions; and multiple consumers duplicating one economic formula.

**Decisive identity experiment A:** create one Scenario and derive its machine descriptor; change only the UI label/locale. If machine semantic behavior is unchanged, independent Scheme identity is unnecessary.

**Experiment B:** define a reusable methodology/composition with several separately named Scenarios and an independent conformance/evidence policy. If version changes and tests have meaning beyond any Scenario, an independent machine Method/Composition may be warranted.

No such end-to-end interoperation experiment has been executed here. Implementation-specific conformance, workload and human UX tests still govern actual adoption. The research's staged roadmap is one candidate (inventory → curated Operation → one typed composition → Scenario/Cascade/machine views → advanced features only after consumers), not a release plan.

## 10. Open Product decisions

Still open: canonical Operation granularity and who maintains catalog IDs, how Composition is stored, whether Scheme owns independent policy, whether Cascade is a separate published Work/Definition, whether technical Command belongs in public API, how many UI tabs and categories users need, which Python schemas deserve serialization, approval/retry/control in graph interpreter, package location and future Web/Android/agent consumers. Adding a new repository solely because a logical `Composition` type exists is premature.

**Conclusion:** user-friendly Scenarios/Cascades, Python functions and machine-readable Schemes may all coexist over **one domain capability semantics and a limited, extensible composition model**. Identity is earned by independently governed meaning, not by the number of words in a sidebar or the number of protocol adapters.
