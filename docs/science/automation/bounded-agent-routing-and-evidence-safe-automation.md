# Bounded agent routing, durable automation and evidence-safe analytical tools

**Problem:** Strategy Box may eventually accept work initiated by a human, a schedule, a verified source change or an authorized machine agent. How can they share deterministic analytical capabilities without confusing a model's plan with permission, a trigger with an accepted Job, an artifact with evidence or a notification with an outcome? **Status:** scientific synthesis of an early automation/AI research proposal, direct implementation limits and later conceptual distinctions. No agent, server scheduler, autonomous run, MCP endpoint or remote execution service is claimed to exist.

## 1. Separate three use cases before choosing an AI stack

| Mode | What it actually solves | Required control | What AI does **not** own |
| --- | --- | --- | --- |
| Deterministic automation | On an authorized schedule/event/qualified data change, create an ordinary Run | Trigger evidence, deduplication, run-as identity, overlap/misfire/retry policy | Cron calculations, authorization and bank formulas |
| Conversational routing | Map natural language to one of the *currently available* typed scenarios and proposed arguments | Catalog retrieval, validated IDs/inputs, preflight, explicit consent where policy demands | Execution engine, unbounded script synthesis, data truth |
| Bounded agent | Choose a sequence of existing permitted operations toward an uncertain goal | Goals, effect policy, finite budget, evidence-bound observations, checkpoint and human handoff | Host filesystem, raw credentials, unreviewed destructive effects, formal result acceptance |

The first two often deliver most value with much less failure surface than an open-ended agent. A text command that resolves to `scenario_id`, immutable revision and typed parameters can become an ordinary Job; the LLM need not remain active as the Job executes. A saved AutomationSpec can be proposed through chat once, explicitly approved and then executed every day without any model call. **The instruction used to propose a rule is not its durable schedule or authority.**

The pinned [Windows scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) already sequences step calls and associates Case, event and artifact records. The [Qt coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) allows one active local Run. The [background store](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) changes in-memory flags and timestamps: enablement is **not** evidence of scheduled execution. Existing `ai` actor labels similarly express a model vocabulary, not an actual model-connected controller.

## 2. Six truth boundaries around an automated action

**OperationDefinition** is a curated domain use case with stable typed economic meaning. **Scenario/Scheme** is a repeatable composition or recipe; terminology remains contested, and a cascade can be a presentation category rather than another ontological root. **AutomationSpec** is a versioned rule for potential future triggers. **TriggerOccurrence** is one matched real-world/calendar event with its own evidence. **Job/Run/Attempt** identify admitted work and execution, potentially distinct. **AgentRun** is a bounded record of the external model's task, decisions, tool calls and reasons for stopping; it may create zero, one or several Jobs.

A model's temporary plan is not automatically a saved Scenario. A good observed tool sequence may be turned into a candidate repeatable definition only after human or authorized engineering review of preconditions, retries and hidden source assumptions. Likewise `success` of a deterministic Operation need not mean that the analyst accepted the inferred claim, that the final Artifact was published, or that the scheduled obligation was closed.

Useful common envelope for a capability includes identity/revision, title/intent, input/output schema, semantic assumptions, side effects and risk, resource needs, known determinism/idempotency, cancellation checkpoint, provenance and artifact inputs/outputs. Metadata such as `readOnly`, `destructive` and `idempotent` are descriptive hints; **server-enforced policy and actual code behavior**, not catalog declarations alone, establish safety.

## 3. Trigger classes and edge cases

Time-based schedules require an IANA timezone and a defined DST fold/gap policy; a fixed UTC offset fails when civil time changes. Event triggers require an authoritative event and access scope. Source-change watchers should compare validated source snapshot/version identities rather than treat HTML layout, filename or filesystem mtime as a stable economic change. Data-aware triggers such as missing period, stale artifact, failed validation or classifier revision need *verified inputs* and a separately resolved downstream dependency graph.

Candidate rule policies include:
- misfire: skip / catch-up-latest / catch-up-all / run-once-now;
- overlap: forbid / queue / coalesce / replace / permit;
- retries: classify transient network/rate-limit errors versus invalid data, permission, failed validation and unknown external effects;
- notifications: success silent, failure scoped, partial review, approval-required urgent, new-artifact summary;
- required approval, job owner, resource budget and automation revision.

These are alternatives rather than universally recommended defaults. For periodic source refresh, **coalescing** can avoid duplicate downloads; for regulatory backfills it can lose mandatory historical periods. Likewise catch-up-all can overrun an underpowered Node, while catch-up-latest may skip an externally mandated per-period closure. The correct selection follows the work's consequence and data freshness contract.

```text
check source → qualified NO_CHANGE          → no new Run required
             → changed + invalid schema     → stop downstream publication
             → changed + validated snapshot → admit refresh Run if policy allows
                                                   → publish verified Artifact
                                                   → notify intended recipients
```

The watcher check itself is an observation, not proof that an economic time series has changed materially; schema evolution and value changes are different signals.

## 4. Request replay, retry and dangerous effects

A client reconnect, scheduler restart, approval retry or agent loop may submit the same intent again. Idempotency requires separate identities for `rule_revision + occurrence`, admitted Job, physical Attempt, external effect and canonical result. Stable input hashes can contribute to equivalence, but cannot by themselves make arbitrary side effects safe. A forced rerun must create a new intentional authority/identity rather than silently bypass deduplication.

The [current FRG plan/apply semantics](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg) illustrate a valuable destructive-work pattern: inspection plan → challenge exact target set → authorize → revalidate preconditions → apply → record every actual outcome. A run plan must bind the planned resource revision so a changed directory or dataset cannot be acted on under an outdated approval. If an external effect may have occurred before a crash, treat it as **outcome unknown** until independently reconciled, never retry merely because no success receipt reached the model.

An agent-readable action proposal should include: exact stable operation ref, parameters with secrets masked, target scope, expected mutations, authority context, risks, estimated cost/budget, intended artifacts and explanation in terms of independently known facts. Human approval is a separately recorded decision with scope, expiry, actor and effect identity. A generic “allow tool” button without a consequence preview is poor protection for large-scale overwrites or deletion.

## 5. Machine discovery without a second analytical core

One business capability can have notebook/Python, Qt, service API, permitted AI tools and scheduler consumers. It does **not** follow that every Python helper is an externally callable tool. Build a curated catalog only for stable meaningful analytical operations with sufficient typed contracts and tested effects. The catalog should expose what is *available to this principal on this Node now*, not every Python import or every aspirational Scenario.

A safe conversational router follows:
```text
user intent → search authorized scenario catalog
            → choose literal existing identity and version
            → construct typed parameter proposal
            → validate semantic and security preconditions
            → execute or request approval through ordinary Job service
            → return stable Job/Case and evidence-bearing results
```
The planner cannot invent an internal operation ID to escape the catalog. API and remote protocol adapters should transform a product-owned capability into the schema required by a transport, not make a protocol's Tool/Task the authoritative Job. Describing an asynchronous Job through a protocol-specific task is a **projection** that may lag, expire, or be visible to a subset of users.

The early research proposed using an external managed platform as an AI gateway and potential broker of model credentials, policies, protocol adapters and remote execution. Later host research more sharply distinguishes product-owned app-level Work/Job authorization from external Node lifecycle. A **valid unresolved architecture split** is whether the platform supplies transport/policy primitives with the application retaining final object authority, versus where the concrete Job scheduler actually runs. Neither an SDK mention nor a future managed-platform aspiration settles that boundary.

## 6. Evidence-bearing Artifact tools and numerical correctness

An AI may need to compare monthly banking indicators, analyze a registry revision or explain a particular source discrepancy. Raw Excel bytes and million-row tables are poor prompt context. A typed artifact query layer can provide a schema, units, period range, missingness, provenance and bounded requested slice. The model selects a *question* and permitted computation; tested domain code produces numeric outputs. The model's explanation must reference the specific result, source vintage and assumption limitations.

A proposed artifact identity can expose content hash, producing Job/Attempt, source snapshot IDs, registry/transform versions, schema, sensitivity, lineage and preview/query capabilities. A path is only one possible storage locator; it is neither an authorization token nor proof that bytes are immutable or published. A summary or suggested analytical conclusion cannot upgrade the underlying evidence tier. Computed values with weak source evidence remain weak, even when explained fluently.

For model-directed actions, a compact decision record may include selected capability, referenced result/Artifact IDs, submitted parameters hash, policy decision, approval ID, consequence summary, time and stop reason. Do **not** require storing hidden model chain-of-thought. A trace must be sufficient for product-level audit of observable actions and evidence while respecting security/retention limits.

## 7. Threat model: tools and source content are both untrusted inputs

An upstream PDF, spreadsheet, HTML page, downloaded source description or tool response may contain instructions addressed to an AI assistant. Those bytes remain **data**, not a new product policy or permission source. Treat protocol tool descriptions as potentially untrusted until the provider and capability are admitted. Credentials stay behind environment-controlled adapters; the agent sees whether an authenticated capability is ready, not the secret value.

Examples of failure:
- a spreadsheet note says “delete previous source files”—must not modify the Run plan;
- a tool description asserts it has elevated write permissions—must be checked against actual application grants;
- a successful text explanation precedes failed workbook publication—must not make an artifact appear published;
- a permitted `read` tool accepts a raw server pathname—should be restricted to authorized object refs;
- a model loops on transient failures, consuming memory and network resources—must stop at a budget boundary;
- a machine client receives a sensitive full log in place of a safe problem summary—must be access-controlled and redacted.

A bounded AgentRun needs explicit maximum tool calls, steps, elapsed wall time, provider cost, artifacts read and external requests; a deadline; effects/approval policy; and stop reasons such as complete, needs input, approval pending, policy blocked, budget exhausted, tool failure, cancellation or no safe next action. Resource limits are necessary even when every individual tool is ostensibly allowed.

## 8. Why the simpler orchestration alternatives remain important

| Analog | Useful property | Why it is not automatic Strategy Box infrastructure |
| --- | --- | --- |
| Lightweight Python scheduler | Date, interval and civil-calendar trigger integration | Scheduler is not a durable distributed Work/Attempt protocol |
| Broker/worker queue | Task routing and horizontal execution scale | Extra broker operations, duplicate-delivery semantics and runtime complexity |
| Durable workflow engine | Crash-resilient state, long waits, explicit signals/retries | Significant deployment and adoption cost; can conflict with product authority |
| Asset-centric data orchestrator | Materialization, dependency checks, data-change automation | More general data-platform primitives than early Strategy Box requires |
| Event-automation platform | Compound/sequence triggers and action rules | Trigger semantics must follow source identity and authorization, not the engine DSL |

The engineering conclusion is **adapter and profile selection after real workload evidence**, not mandatory dependence on any named package. A single process plus transactional durable Job store may suit one Node; horizontally distributed multi-worker execution requires stronger leases and observability. A scheduler in a Qt widget is not independent of GUI shutdown and should not be advertised as detached.

A single bounded agent with curated tools is a sensible starting comparison against multi-agent decomposition. Multiple models or “reviewer agents” can increase candidate diversity but also add coordination cost, latency and correlated hallucination; two model outputs based on the same flawed source are not independent evidence. Evaluate more complex agents only against quality, safety and cost improvements under reproducible tasks.

## 9. Evaluation: do not equate plausibility with validated operation

Suggested router evaluation: exact scenario-selection accuracy, parameter extraction, invented IDs, unauthorized proposals, needless confirmations and correct action refusal. Agent evaluation: factual/numerical grounding, correct Artifact selection, tool-call policy, loss/retry recovery, budget adherence, approval integrity, loop rate, latency and economic cost. A regression corpus should contain ordinary source refresh, changed classifier, reporting-form export, a missing source, an untrusted document instruction, an unauthorized personal Artifact, a destructive cleanup plan and a Job whose external effect is unknown after a crash.

An existing stable scenario makes a useful evaluation oracle; self-reported agent success does not. End-to-end verification must check actual side-effect and result identities, not merely whether the model produced a confident final message.

## 10. Scientific conclusion and decision frontier

The strongest source-supported direction is **one set of deterministic analytical operations with several governed consumers**. The weakest leap would be to assert that an AI router, scheduler, MCP/A2A service or distributed Job host exists today because corresponding roles or fields appear in a prototype. A separate agent workflow is justified only when the task cannot be answered with a single approved scenario and the expected benefit outweighs an additional privilege, budget and recovery surface.

Open decisions: product-owned scheduler and Job authority versus platform-provided runtime services, scope of machine discovery, model-provider trust, first autonomy level, approval and retention policies, whether any machine transport is enabled externally, resource quotas, reuse/compilation of successful plans, and the tests required for financial-output reliability. None is adopted by this Science article.

Related subjects: [trigger occurrences](trigger-occurrence-identity-and-governed-execution.md), [machine tools](../capabilities/machine-discovery-bindings-and-adapters.md), [artifact publication](../artifacts/output-identity-publication-and-availability.md), [effect boundaries](../trust-and-assurance/identity-authorization-and-effect-boundaries.md), [Job admission](../work/admission-planning-resource-scheduling-and-recovery.md), and [external integration contracts](../architecture/semantic-ownership-and-contract-boundaries.md).
