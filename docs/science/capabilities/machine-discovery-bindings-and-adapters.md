# Machine discovery, capability bindings, and protocol-independent analytical operations

**Scope:** describing and invoking the same bank/macroeconomic analytical capability from a Python notebook, desktop interface, authorized service API, local/remote AI tool client, or agent-mediated workflow. **Status:** source-qualified scientific and engineering explanation, not a released capability API or a decision to implement any machine endpoint. **Current code baselines:** [core @ beb3e484](https://github.com/ForestTiger-GH/stratbox/tree/beb3e4842614b153ba0c0ccc1e33ae4d50698821), [Windows @ 959e9c4](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b), [external platform @ a4d87c6](https://github.com/ForestTiger-GH/AppDock/tree/a4d87c643e620e54e04083d4d0b8d867513e7065). Related maintained Science: [capability definitions and execution truth](definitions-plans-and-execution-truth.md), [effect authorization](../trust-and-assurance/identity-authorization-and-effect-boundaries.md), [artifact identity](../artifacts/output-identity-publication-and-availability.md), and [source snapshots](../data-and-knowledge/source-observation-vintages-and-replay.md).

## 1. Invariant semantics versus different consumer channels

The developer's machine-consumption requirement names **seven distinct paths**, not seven established applications: (1) a human invoking desktop or prospective Web/Android analytics; (2) direct Python from Colab/Jupyter; (3) an AI on another device invoking a host through remote MCP; (4) a local AI invoking a local MCP tool; (5) one independent AI delegating a goal via A2A to a host-side agent; (6) an agent embedded in Strategy Box invoking curated operations; (7) an external A2A actor delegating to that embedded agent.

Only a bounded local Windows scenario/execution UI and directly importable Python subject functions are demonstrated by the pinned code. **No current Strategy Box MCP endpoint, A2A agent, embedded intelligence, remote host, general Web/Android client, cross-device JobManager, or associated security/interop certification has been established**. A future external management platform may provide transport and identity capabilities, but its package/activation model does not already implement these Strategy Box services.

The reusable invariant is the **semantic operation**: what is requested, typed inputs and their economic meaning, actual source/method versions, known effects, qualified result, errors and evidence. What deliberately differs is transport, session ownership, protocol negotiation, orchestration, authorization, result transfer, and lifetime. Direct Python with DataFrames and local process rights does not become remote host execution merely because both channels use the same domain operation.

## 2. The catalog is curated; an importable function is not automatically a tool

Six useful roles:

| Role | Meaning | Wrong equivalence |
| --- | --- | --- |
| **Python Callable** | Low-level or public domain function callable within a trusted Python environment | Every importable helper is remotely publishable |
| **OperationDefinition** | Stable bank/macroeconomic use case with semantic inputs/results, effects and qualification | A UI button or transport method |
| **CapabilityDefinition** | What the system can potentially do under declared preconditions | Installed binding, authorization or actual availability |
| **ExecutionBinding** | Specific trusted installed implementation and adapters selected by application authority | Arbitrary `module:function` chosen by an external tool caller |
| **ToolProjection** | Permitted description and request/result schema for one caller/protocol | New, competing business algorithm |
| **Scheme / Scenario / ExecutionPlan** | Reusable composition and the resolved, version-pinned plan for a specific invocation | An AI's prose plan, successful execution or A2A Task |

These are **semantic distinctions**, not a mandate for six databases or registries. The competing models “Command → Scenario → Cascade” versus “Operation/Capability → Scheme → Plan” remain open: a user Scenario may refer to a technical Scheme, contain an internal plan, or be a distinct versioned workflow. Tool exposure need not settle this entire ontology. `ExecutableDefinitionRef(kind, id, revision)` is one candidate neutral reference, not an accepted API.

**Catalog inclusion test:** is there a stable external analytical intent; inspectable typed input/result; documented validation and effects; workable execution/retry/resource semantics; at least one actual consumer and owner? Helpers for parsing filenames or manipulating raw FileStore paths should generally remain Python-only. Curated examples worth piloting include listing official sources, collecting raw files, building/exporting escrow history, viewing FRG plans without applying destructive cleanup, and obtaining a bounded SORS run status/result reference. The IDs suggested in Research are **illustrative future names**, not aliases guaranteed by current Windows.

The contrary alternatives both fail: publish every helper (tool explosion and privilege expansion), or offer a single `run_anything` with arbitrary Python/handler/path (opaque validation, unbounded effects, unsafe trust). A hybrid catalog with a small number of actual domain operations and small stable meta-tools may be better, subject to measured consumer performance.

## 3. What the implementation actually contributes

The [core collector operation](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_file_collector/operations.py) uses a typed request and result and can run as a Python library with an injected FileStore. [Escrow operations](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/escrow/operations.py) have distinguishable construction/export stages. [FRG](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/frg/api.py) exposes rich data and staged file effects; [SORS](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_sors_restoration/operations.py) is a heavy computation with meaningful evidence/assumptions. These are useful **different adapters**, not proof that a universal registry already exists.

The pinned [Windows operation registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/registry.py) explicitly defines **three** operation specs: `cbr_file_collector.collect`, `escrow.history.export`, and `system.diagnostics`. [OperationSpec](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/models.py) contains title, params, `handler='module:function'`, `dangerous`, enabled/visibility hints, and expected artifacts. [ScenarioStepSpec](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py) is ordered composition; the [runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) performs local sequential execution. These are real present capabilities, but not strict machine-facing JSON input/output contracts, independent auth, async host service, versioned semantic bindings, or a DAG compiler.

The [Windows AppDock manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) declares a local foreground desktop surface with manifest contract `4.0`; this is **not** a remote MCP/A2A server declaration. Exact installed package and runtime versions require independent verification: earlier source inspection flagged release/manifest documentation and declared dependency revision drift, but no installed-environment failure was demonstrated. Runtime truth cannot be inferred from a README alone.

## 4. The smallest transport-neutral contract with enough semantics

A curated operation may need a stable semantic ID and contract version; input and result schemas; source/format applicability; meaningful output types and units; effect class and target scope; expected duration/resource profile; idempotency, cancellation and partial outcomes; provenance/method references; owner, documentation, installed binding and compatibility. **Not every entry needs dozens of persisted fields on day one**, but absent effect data must never silently be interpreted as `read_only`.

Separate the **semantic definition** from the **execution binding**:

```text
OperationDefinition: operation_id, contract_version, semantic IO,
                     preconditions, effects, evidence, domain owner
ExecutionBinding:   authorized concrete implementation revision,
                     trusted callable, input/output adapters,
                     execution profile, verified environment identity
Invocation:         principal, canonical request, idempotency scope
ResolvedPlan:       exact bindings, source/registry versions, resources,
                     effect policy, plan digest and approvals
Run/Attempt:        actual accepted work, observations, receipts, outcomes
```

The client sends a **curated operation ID**, not arbitrary `module:function` or executable code. An installed/approved binding is selected by the trusted runtime. `fixed_param_values` in a UI is only a convenience until the authority itself enforces them. `ai_visibility` and `dangerous` describe intended exposure, not authorization.

A practical capability view distinguishes `known`, `installed`, `available`, `applicable`, `authorized`, `approval_required`, and `executable_now`. Availability should have a safe reason (missing input, resource exhausted, environment unavailable, unsupported transport, denied scope, unknown), not just a bool. Tool listing is always a filtered **projection**; a cached list may become stale, and execution must re-check current rights and conditions.

## 5. Typed transport without erasing domain evidence

[JSON Schema 2020-12](https://json-schema.org/draft/2020-12/) supports structural request validation and can be used for a machine boundary. It does not replace Python dataclasses, pandas/numpy/Decimal, domain numerical evidence, provenance or source semantics. Useful wire conventions are research candidates:

| Domain meaning | Candidate serialized representation | Essential invariant |
| --- | --- | --- |
| Exact money/decimal | Decimal string + explicit unit/currency/scale | Do not round silently via binary floating-point |
| Reference date / fetch instant / reporting period | Different typed date, UTC timestamp, `PeriodSpec` objects | Data period is not publication/fetch time |
| Bank, region, OKVED/industry code | Namespace/version-qualified string ID | Leading zero and historical code revision survive |
| Input path or stored result | `WorkspaceFileRef`, `SourceSnapshotRef`, `ArtifactRef` | Avoid remote host absolute paths and traversal |
| Short numerical summary | Value + status + unit + missing/suppressed reason | `0` is distinct from unavailable or undisclosed |
| Large table/DataFrame | `DatasetRef` + schema/size + bounded preview/page/export | Do not place full frames in an AI context window |
| Resulting XLSX/CSV/ZIP | `ArtifactRef` + format, availability, digest evidence when captured | Created bytes differ from merely proposed path |
| Error and evidence | Typed problem/status + safe details + restricted evidence ref | Do not serialize raw exception/credentials |

An auto-generated JSON Schema from Python typing is at best a **starting point**. It cannot infer the effect of a method, whether overwrite needs approval, scope of a workspace, solver budget, fallback semantics or domain treatment of partial data. Manual semantic annotations, bound provider validation and contract tests remain necessary. A `WorkspaceLocationRef` with `relative_path` needs actual host-side containment and permission checks; schema syntax alone is not authorization.

**Lossless boundary requirement:** keep domain-specific proof grids, source conflicts and SORS assumption qualifications in the native result or addressable evidence. Do not flatten a meaningful `not_observed` and observed `0` to the same JSON `null`; do not treat an enormous DataFrame or original XLSX as text to be injected into an AI prompt. Transport projections are deliberately smaller than the authoritative domain result without hiding omitted detail from authorized retrieval.

## 6. Seven invocation paths, mapped to different trust and lifecycle boundaries

| Path | Actual semantic route | Evidence status |
| --- | --- | --- |
| Human Windows / future Web/Android | Surface → application admission → optional plan/approval → Run/Job → core → projected result | Current Windows local path exists; common server or mobile not demonstrated |
| Direct Colab/Jupyter/Python | Native core import → typed Request/Result and domain FileStore | Already possible in principle, subject to local environment and network/input availability |
| Remote MCP → host | Authenticated resource-scoped MCP transport → filtered tools/call → host admission/Job → core → safe result refs | Target only; no published Strategy Box MCP endpoint proven |
| Local MCP → same machine | Stdio/loopback/in-process tool adapter with local policy → same admission | Target only; localhost does not waive effect restrictions |
| External A2A → host-side independent agent | A2A task/agent skill → real hosted agent → authorized operations → underlying Run evidence | Target only; requires a separate actual agent runtime |
| Embedded AI → application port | Embedded reasoning component → filtered catalog/approval → same application execution | Target only; does not require a self-call over HTTP |
| External A2A → embedded agent | A2A boundary → embedded agent goal/task → internal governed operations | Target only; may share A2A contract with host-agent variant |

MCP and A2A solve **different problems**: tool/function discovery and invocation versus collaboration/delegation among actual agent runtimes. A2A `Task` is not automatically one domain `Run`: the agent can use several operations, request input, or revise its plan. Even a transport-specific asynchronous MCP Tasks extension should be an adapter to the canonical Run/Job state, not the owner of user history. Agent Card skills should describe broad agent competence, not duplicate every raw Python function in a second domain catalog.

**Protocol version qualification:** the late research source compares a July 2026 MCP specification/release with older client/session semantics and a separately versioned A2A specification. Those are **date-bound protocol reports**, not a guarantee that every present or future client supports the same features. Deployment needs verified official specification revisions, pinned SDK, a supported-version/negotiated-feature matrix and interop tests. MCP's tools/resources/prompts may map to distinct access forms; changes in transport protocol cannot silently redefine financial period/units or effect semantics.

[OpenAPI](https://spec.openapis.org/oas/latest.html) is a sensible future HTTP interface description for Web/mobile/non-AI clients, but HTTP verb/path is not the canonical bank-operation ontology. [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) applies to HTTP error responses, not to the application's long-lived problem record. A custom generic JSON-RPC or mandatory gRPC/Protobuf stack adds complexity without a demonstrated first consumer.

## 7. Machine discovery is a retrieval-and-permission problem

Two catalog pathologies are real: an overly large list of low-level tools creates ambiguity and context overhead; a single universal `run_anything` forces a model to guess opaque operation IDs, parameter schemas and risk semantics. A conditional **two-tier view** avoids duplicating registries:

- **Small stable meta capabilities:** catalog search/describe, submit/get Run, fetch limited artifact metadata, optional approved cancel/preview.
- **Selected direct domain tools:** a small set of frequently used read/collect/build/report functions with exact schemas.

This is **not** a mandate to implement nine named endpoints immediately. The choice should be evaluated with 20–40 repeatable banking tasks, fixed source/catalog revisions, and metrics: selection accuracy, argument errors, extra discovery calls, token/metadata overhead, end-to-end latency, actual resource load, unauthorized-effect attempts, provenance completeness and timeout recovery. Research on tool choice ([Toolformer](https://papers.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html), [ReAct](https://mlanthology.org/iclr/2023/yao2023iclr-react/), [AnyTool](https://proceedings.mlr.press/v235/du24h.html), [ToolLLM](https://proceedings.iclr.cc/paper_files/paper/2024/hash/28e50ee5b72e90b50e7196fde8ea260e-Abstract-Conference.html)) motivates evaluation, but does **not** establish benchmark accuracy or safety for Strategy Box.

Actual exposure depends on semantic definitions ∩ installed bindings ∩ node resources ∩ authenticated subject/delegation ∩ transport capability. Cached client `tools/list` is not a grant; `tools/call` reauthorizes. Tool descriptions should explain expected source/periods, effects, result, duration, required approval and provenance at human-readable level, but actual enforcement must use structured runtime checks.

## 8. Admission, effect truth, retries and concurrency

`tools/call` or an HTTP `200` can mean **rejected**, **accepted and pending**, or **terminated with success/partial/failure/unknown** depending on the contract. The synchronous response does not prove that a file was published or an analyst accepted its conclusion. One canonical invocation should retain stable Run identity across reconnect and retries, and an explicit distinction between a domain calculation, staged bytes, confirmed ArtifactRef, and end-user acceptance.

A candidate idempotency scope is caller/operation/request digest/contract version plus a provided invocation key:
- same key and canonical request within the accepted window → return existing logical Run;
- same key with different digest → conflict;
- lost acknowledgement after external write → **OUTCOME_UNKNOWN** until reconciliation; generating a new request ID and blindly retrying may duplicate the effect;
- reusing a previous completed result is a **different** claim from deduplicating a submitted command.

Execution preflight checks installed compatible packages, data root, dependencies, memory, network and format. Plan validation/compilation checks dataflow, typed params, resources, effects, approved versions and policy. Both can become stale before effect execution; destructive mutation requires effect-time recheck and a plan-bound approval where configured.

Several independent read-only jobs may execute concurrently with bounded budgets, rate limits and worker resources, while a shared output destination needs a resource claim or conditional publication. A single global busy flag is insufficient for multiple chats/agents, but unrestricted parallel writes are worse. Shared computation reuse requires compatible source snapshot, freshness, data scope, entitlement, method and effect classification; matching source URL or operation name is not enough.

Common error categories should distinguish invalid request, unauthorized action, approval required, binding unavailable, source unavailable, data invalid, resource exhaustion, failed execution, partial result, unknown external effect and unavailable artifact. In an MCP adapter a protocol/JSON-RPC error is not identical to a tool's analytical error; A2A Task state is not identical to each underlying Run outcome.

## 9. Six independent revision axes

A reproducible external invocation may need:
1. Stable semantic Operation ID.
2. Operation **contract version**: units, periods, effects, request/result interpretation.
3. Exact implementation binding/build identity (not merely a code import path).
4. Capability catalog revision/visibility snapshot seen by the caller.
5. Source, registry, methodology and resolved plan revisions.
6. Protocol revision and negotiated optional features.

Semantic contract changes include a default switching from read to overwrite, `period` changing meaning from reporting month to publication month, missing data silently replaced with zero, a unit changing from thousand to million, a partial result becoming unqualified success, or an ArtifactRef being replaced by a public filesystem URL. Such shifts are material **even with unchanged Python signatures**.

Capture the selected binding, canonical request digest, authorization/approval and plan identity at admission; capture actually used source snapshots, attempts, output revisions and receipts during execution. Updating an installed implementation during a long-running Run must not silently substitute a new implementation mid-flight. Backward compatibility of deprecated APIs is not a project constraint, but historical Run provenance and valuable state remain worth migrating or preserving when authorized.

## 10. Physical alternatives and unresolved decisions

| Physical arrangement | Advantage | Principal cost and boundary |
| --- | --- | --- |
| Put machine servers and Job state in domain core | Small initial component count | Forces every notebook import to carry GUI/auth/transports; violates core portability |
| Put everything in Windows/Qt | Builds on working local prototype | GUI lifetime, one-worker coordinator and Windows-specific dependencies; poor cross-client truth |
| **Neutral application execution authority with protocol adapters** | One admission/Run/effect contract, multiple permitted consumers | Requires later owner decisions on process lifetime, storage, package organization and deployments |
| Large distributed service stack | Potential fleet scale | No evidence that a first release needs brokers, microservices or federated auth |

Logical separation of core, application authority and adapters does **not** mandate a new repository or immediate service process. A small in-process adapter may prove one operation first. Create a persistent host only when an actual second consumer requires shared durable execution. The external platform remains the deployment/node/runtime integrator where verified, **not** the source of banking operation definitions or the authority on domain evidence.

Open decisions include: the stable public machine operation subset; definition owner; independent Scheme vs Scenario vs Cascade identity; effect/approval classes and AI autonomy; local/remote MCP versions and tasks behavior; whether any actual hosted agent warrants A2A; bindings/host lifetime and storage; immutable source/artifact transport; application/API authorization; SDK interoperability; resource budgets and whether a split physical repository is justified.

## 11. Falsification and verification matrix

| Proposed test | Failure it would expose |
| --- | --- |
| Direct typed Python import with no GUI/platform | Hidden application/Qt dependency in core |
| Extra JSON fields, invalid periods or IDs | Tool adapter weak validation |
| Domain Python call versus curated adapter on identical snapshots | Changed banking semantic result in transport |
| Low-level helper visible as AI tool | Uncurated/tool-explosion surface |
| Client supplies `module:function` | Arbitrary handler execution route |
| `../`, absolute path, symlink/junction escape | No true workspace containment |
| Large DataFrame result | Unexpected LLM context overload instead of DatasetRef/preview |
| Missing source versus observed zero | Semantic evidence silently lost |
| Installed dependency unavailable | Incorrect success or fallback |
| Operation ID under changed contract revision | Version conflation |
| Cached tool list after grant revocation | Policy bypass at actual call |
| Network timeout after external write | Blind retry, duplicate effect |
| Same invocation key with altered request | Hidden request collision |
| Cancellation after irreversible publication | False “cancelled with no effects” |
| Partial XLSX before finalize | False ready ArtifactRef |
| Untrusted source asks AI to delete files | Data becomes authority (prompt injection) |
| Concurrent independent reads/shared file writes | Over-serialization or output collision |
| External platform version changes | Unnoticed activation/transport contract drift |
| Implementation updated during Run | Silent method change and non-reproducible output |
| A2A agent waiting for input | Incorrectly successful bank operation |
| GUI closes during host Run | Client lifetime incorrectly used as Job lifetime |
| Older/newer MCP clients | False compatibility without explicit version/feature support |

These are **research-proposed tests**, not a passed local MCP/A2A interoperability suite, installed host trial, or actual model evaluation. Required evidence is both correct numerical/domain outputs and safe behavior at the effect, authorization and result-transfer boundaries.

**Negative finding:** Neither a universal machine-language schema nor an external management platform automatically establishes authorized, reproducible analytical execution. Durable outcome truth, curated capability semantics, source evidence and correctly bounded physical effects are prerequisites to making any future machine endpoint trustworthy.
