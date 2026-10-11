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

## 11. Frozen Command/Scenario/Cascade research decisions and rejected shortcuts (36 source items)

The [October 7 source study on Commands, Scenarios and Cascades](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1579-L1887) proposed several distinct execution outcomes and visual/catalog choices. These **36 source-line-traced English interpretations** are preserved to avoid losing negative decisions when only the headline `Command → Scenario → Cascade` is remembered. They are **not approved Product WHAT**, existing machine APIs, proof that every library helper should be public, or authorization to create a new physical Scheme service. The original user annotation supported intuitive grouping but did not independently approve the exact proposed three-level ontology.

| Research-group ID | Proposed semantic distinction, risk or design option | Frozen source |
| --- | --- | --- |
| `SB-SRC-0024/FAILURE_MODE-01` | Stop dependent future work after a material failure | [L1586](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1586) |
| `SB-SRC-0024/FAILURE_MODE-02` | Continue independent graph branches but block failed dependencies | [L1587](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1587) |
| `SB-SRC-0024/FAILURE_MODE-03` | Continue steps with currently satisfied preconditions | [L1588](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1588) |
| `SB-SRC-0024/CASCADE_OUTCOME-01` | All qualified required goals completed | [L1606](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1606) |
| `SB-SRC-0024/CASCADE_OUTCOME-02` | Completed with explicit user-relevant warnings | [L1607](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1607) |
| `SB-SRC-0024/CASCADE_OUTCOME-03` | Some branches succeeded and other results/residuals remain visible | [L1608](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1608) |
| `SB-SRC-0024/CASCADE_OUTCOME-04` | Required condition failed | [L1609](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1609) |
| `SB-SRC-0024/CASCADE_OUTCOME-05` | Confirmed cancellation under admitted effect policy | [L1610](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1610) |
| `SB-SRC-0024/CASCADE_OUTCOME-06` | Outcome cannot be inferred from available execution/receipt evidence | [L1611](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1611) |
| `SB-SRC-0024/REUSE_KIND-01` | Executed afresh during this Run | [L1640](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1640) |
| `SB-SRC-0024/REUSE_KIND-02` | Coalesced equivalent commands inside one plan | [L1641](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1641) |
| `SB-SRC-0024/REUSE_KIND-03` | Reused an eligible previously cached result | [L1642](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1642) |
| `SB-SRC-0024/REUSE_KIND-04` | Reused a prior Case result subject to eligibility and evidence checks | [L1643](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1643) |
| `SB-SRC-0024/ANTIPATTERN-01` | Do not show every technical Command as a primary navigation object | [L1754](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1754) |
| `SB-SRC-0024/ANTIPATTERN-02` | Do not merge all semantic levels into one giant ScenarioSpec | [L1755](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1755) |
| `SB-SRC-0024/ANTIPATTERN-03` | Do not deduplicate solely by command identifier | [L1756](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1756) |
| `SB-SRC-0024/ANTIPATTERN-04` | Do not make background execution a separate parallel workflow system | [L1757](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1757) |
| `SB-SRC-0024/ANTIPATTERN-05` | Do not hide plan optimization and its provenance | [L1758](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1758) |
| `SB-SRC-0024/ANTIPATTERN-06` | Do not model Cascade as a mere list of Commands, erasing Scenario identity | [L1759](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1759) |
| `SB-SRC-0024/ANTIPATTERN-07` | Do not restrict one Scenario to membership of just one Cascade | [L1760](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1760) |
| `SB-SRC-0024/ANTIPATTERN-08` | Do not confuse a UI file-opening action with a domain data workflow | [L1761](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1761) |
| `SB-SRC-0024/ANTIPATTERN-09` | Do not let an AI actor bypass discovered contracts and authorization | [L1762](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1762) |
| `SB-SRC-0024/ARCH_CHOICE-01` | Keep technical Commands out of main user navigation | [L1871](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1871) |
| `SB-SRC-0024/ARCH_CHOICE-02` | One Scenario may have multiple constituent Commands | [L1872](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1872) |
| `SB-SRC-0024/ARCH_CHOICE-03` | One Scenario can belong to several Cascades | [L1873](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1873) |
| `SB-SRC-0024/ARCH_CHOICE-04` | Cascade should not be conflated with the Scenario identity | [L1874](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1874) |
| `SB-SRC-0024/ARCH_CHOICE-05` | Background is an execution mode, not a Scenario type | [L1875](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1875) |
| `SB-SRC-0024/ARCH_CHOICE-06` | Assignment is a task/ownership relation, not a Scenario type | [L1876](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1876) |
| `SB-SRC-0024/ARCH_CHOICE-07` | Build a candidate ExecutionPlan before execution | [L1877](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1877) |
| `SB-SRC-0024/ARCH_CHOICE-08` | Never deduplicate solely by command_id | [L1878](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1878) |
| `SB-SRC-0024/ARCH_CHOICE-09` | Perform equivalent-work deduplication in a planner | [L1879](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1879) |
| `SB-SRC-0024/ARCH_CHOICE-10` | Preserve planner deduplication decisions for inspection | [L1880](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1880) |
| `SB-SRC-0024/ARCH_CHOICE-11` | Planner may parallelize when dependencies and policies allow | [L1881](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1881) |
| `SB-SRC-0024/ARCH_CHOICE-12` | Expose raw Commands to AI only through a separately admitted capability | [L1882](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1882) |
| `SB-SRC-0024/ARCH_CHOICE-13` | Publish high-level Scenario/Cascade and service actions at an external platform boundary | [L1883](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1883) |
| `SB-SRC-0024/ARCH_CHOICE-14` | Future Android semantic client must not depend on Qt/Windows specifics | [L1884](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md#L1884) |

**Counterargument:** the original flat `Command → Scenario → Cascade` proposal helps user discoverability but a domain-only library consumer may need a typed reusable composition without a separate application Scenario. Other Research proposes `OperationDefinition`, `SchemeSpec` and `Work` with different owner boundaries. Do not resolve those by aliasing every term or creating a new package for every noun. The substantive design test is whether a composition has independent user meaning, versioning, effect authority, reuse, scheduling or accepted results. Identity and lifecycle boundaries must follow actual consumer needs.

**Negative assurance:** deduplication by command ID may merge different parameters/effects; reuse from cache is a different claim from deduplication within a single plan, and each requires correct source/method/version/authority scope. `PARTIAL` and `UNKNOWN` are not alternate spellings for failure. These tests and the 14 design recommendations have **not been executed or authorized**, and the rest of the 2,085-line original still needs material disposition.

## 12. Source-topic ontology alternatives and independent identities (16 original rows)

The dated [Topic 01 source](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md) explicitly compared **five competing ontology/engine models** and distinguished a user-facing Cascade category from executable composition and delegated Work. Its favored model is **a source-author Research recommendation, not a Product decision**, and its five-model scorecard is **expert judgment, not a measured benchmark**. The 16 source-addressed English renderings below preserve the alternatives, limitations, and negative implications without silently resolving architecture ownership.

| Source ID | Source-preserving English interpretation | Qualification | Frozen research line |
| --- | --- | --- | --- |
| `SB-SRC-0554/ONT-01` | Model A keeps operations as direct Python functions and human scripts; its low maintenance cost is real, while machine discovery and stable identity remain unprovided. | `ALTERNATIVE_A` | [L214](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L214) |
| `SB-SRC-0554/ONT-02` | Model B assigns independent identities/lifecycles to five overlapping Command/Operation/Scenario/Cascade/Scheme types; repeated semantics and owner drift make this costly. | `ALTERNATIVE_B` | [L222](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L222) |
| `SB-SRC-0554/ONT-03` | Model C lets human Scenario and Cascade own composition and treats Scheme as AI description; it is near the current UI but risks making machine procedure depend on changing UI definitions. | `ALTERNATIVE_C` | [L230](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L230) |
| `SB-SRC-0554/ONT-04` | Model D favors one subject-capability owner, reusable composition and separate human/AI projections, while requiring typed binding discipline. | `ALTERNATIVE_D_PREFERRED_BY_RESEARCH` | [L238](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L238) |
| `SB-SRC-0554/ONT-05` | Model E treats a full external workflow engine/formalism as ontology; rich scheduling trades off platform dependency and overhead for simple Python analytics. | `ALTERNATIVE_E` | [L246](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L246) |
| `SB-SRC-0554/ONT-06` | The five-model comparison was explicitly qualitative expert judgment, NOT an executed benchmark or an established ranking from measured user workloads. | `EVALUATION_LIMIT` | [L254](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L254) |
| `SB-SRC-0554/ONT-07` | A Python import/function name and a stable domain Operation ID are different identities; module refactoring need not change analytical meaning. | `SEMANTIC_STABILITY` | [L337](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L337) |
| `SB-SRC-0554/ONT-08` | A large Cascade UI category does not inherently require a third execution engine beyond reusable compositions. | `ENGINE_NONSEQUITUR` | [L341](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L341) |
| `SB-SRC-0554/ONT-09` | Machine discoverability never grants execution authorization; schema description, principal privileges and effects must be checked separately. | `SECURITY_BOUNDARY` | [L343](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L343) |
| `SB-SRC-0554/ONT-10` | A simple AI-facing Scheme projection of an Operation ordinarily needs no separate Scheme identity; changing button wording does not change economic method revision. | `SCHEME_PROJECTION_CASE` | [L532](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L532) |
| `SB-SRC-0554/ONT-11` | A Scheme identity can be justified by independently reusable method/policy semantics, tests and governance beyond merely rendering one Operation differently. | `SCHEME_INDEPENDENT_OWNER_CASE` | [L549](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L549) |
| `SB-SRC-0554/ONT-12` | A Cascade used only as a named navigational grouping is a collection, not a runnable composition. | `CASCADE_CATALOG_CASE` | [L615](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L615) |
| `SB-SRC-0554/ONT-13` | An executable Cascade can be a shared composition of operations, not an intrinsically different solver or executor. | `CASCADE_COMPOSITION_CASE` | [L617](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L617) |
| `SB-SRC-0554/ONT-14` | A program-level Cascade with delegated independent Work and human reviews would require separate owner/lifecycle evidence; the source called it premature for topic 01. | `CASCADE_PROGRAM_CASE` | [L619](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L619) |
| `SB-SRC-0554/ONT-15` | AI-facing read-only/tool metadata is a declaration, not enforcement of actual effects or permissions at runtime. | `MACHINE_METADATA_NONIMPLICATION` | [L781](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L781) |
| `SB-SRC-0554/ONT-16` | An agent-authored plan is not an admitted execution plan; binding must validate actual capability, input schema, permissions, versions and risk limits. | `AGENT_PLAN_ADMISSION_BOUNDARY` | [L791](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md#L791) |

**Falsifiers and costs:** a common compositional definition is worthwhile only when it has real reused consumers and independent semantic constraints. A single notebook can directly invoke domain functions without a graph database. Five parallel semantic registries can create drift, while a prematurely installed full workflow platform can impose high costs for a one-step calculation. If an AI describes a capability it still does not obtain authorization, and a UI Cascade folder must not be mistaken for scheduled Work. A more powerful Scheme identity requires independent tests, lifecycle and use that justify its storage and governance. Each option remains reviewable under a real product Work scenario.

**Evidence ceiling:** sixteen producer-translated source lines with exact origin and meaning/limit, not a complete or independently verified assimilation of the 1,555-line source or verified system implementation.
