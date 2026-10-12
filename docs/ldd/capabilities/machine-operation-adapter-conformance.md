# Machine operation adapter conformance: twenty-five executable intentions

**Evidence status:** `CANDIDATE / UNEXECUTED`. The test catalogue is intended for a Strategy Box-owned application capability interface and qualified machine consumers. It does not claim any existing MCP server, A2A runtime, authenticated remote API or installed headless host. Direct Python use of the core remains independent and is **not** subject to invented application-platform prerequisites.

## Distinctions that every adapter must preserve

The analytical Python core owns business formulas and data/operation semantics. A **curated domain operation** differs from a helper import or implementation binding; a **machine catalog projection** differs from both an authorization grant and an executor; a **transport schema** differs from a rich internal typed `Request/Result`; an accepted **Run** differs from a published Artifact, successful external effect and agent Task. The executable binding must be resolved on the trusted side, not injected via handler strings supplied by a model. Remote clients should use stable resource references rather than server-local absolute paths.

The proposed two-level machine discovery model can expose a small permission-filtered search/describe list and bounded callable operations without turning every internal Python function into a tool. A large table is represented by a typed `DatasetRef`, safe summary and authorized pagination, rather than serialized as a whole LLM prompt. Concrete catalog version, host API and transport choice still require Product admission.

## Complete candidate negative and equivalence vector set

| Vector | Concern | Adverse or equivalence stimulus | Falsifiable required outcome | Evidence status |
| --- | --- | --- | --- | --- |
| MAC-01 | Domain: core independence | Import a real central-bank collector from headless Python without a desktop installation | Core operation available without Qt, Windows surface or external platform runtime | `UNEXECUTED` |
| MAC-02 | Domain: input strictness | Machine sends unknown field or invalid source period and enumeration | Reject before external transport; typed input error includes no secret-bearing raw text | `UNEXECUTED` |
| MAC-03 | Domain: domain equivalence | Call same domain function via direct Python and machine adapter with fixed source snapshot | Equivalent domain data, quality levels and provenance; transport may differ | `UNEXECUTED` |
| MAC-04 | Catalog/revision: curated discovery | A helper method exists in Python but is absent from approved domain operation inventory | Helper never appears as an AI tool through automatic reflection | `UNEXECUTED` |
| MAC-05 | Domain: binding injection | Caller includes executable handler or arbitrary dotted function path in request | Server ignores or rejects handler; only trusted binding registry resolves execution | `UNEXECUTED` |
| MAC-06 | Trust/integration: remote object scope | Invocation supplies traversal, absolute path or symlink outside approved workspace | Application boundary rejects access and actual mutation; client path does not confer permission | `UNEXECUTED` |
| MAC-07 | Domain: large result projection | Domain operation returns a large DataFrame | Adapter returns bounded summary and typed DatasetRef, with separately authorized paging | `UNEXECUTED` |
| MAC-08 | Domain: missingness | One publisher observation is unavailable while another observed value is exactly zero | Separate unavailable/unknown/observed-zero statuses and supporting source identity | `UNEXECUTED` |
| MAC-09 | Domain: backend unavailable | Optional solver or source provider absent | Explicit binding_unavailable/resource_unavailable; no silent fallback to another method | `UNEXECUTED` |
| MAC-10 | Catalog/revision: version collision | Same operation ID registered at distinct semantic contract versions | Resolver selects exact allowed revision or rejects; never mixes request/result signatures | `UNEXECUTED` |
| MAC-11 | Catalog/revision: principal-specific listing | Two principals have different allowed tool scopes | Deterministic, authorization-filtered catalog projections for each principal | `UNEXECUTED` |
| MAC-12 | Trust/integration: stale invocation | Previously discovered tool is called after permission or provider state changes | New admission, version and availability checks before binding | `UNEXECUTED` |
| MAC-13 | Execution/effects: external timeout | Timeout after destructive write/delete may have started | Return outcome_unknown and require reconciliation, not automatic duplicate effect | `UNEXECUTED` |
| MAC-14 | Execution/effects: idempotent replay | Identical invocation identifier with identical request digest is retried | Dedup policy maps to original logical Run/effect evidence when contract supports it | `UNEXECUTED` |
| MAC-15 | Execution/effects: idempotency collision | Same invocation identifier with altered request payload digest | Explicit conflict, never a hidden second mutation | `UNEXECUTED` |
| MAC-16 | Execution/effects: late cancel | Cancel arrives after an irreversible effect commit | State and receipt report effect, never cancelled_without_effect | `UNEXECUTED` |
| MAC-17 | Execution/effects: staging crash | Worker crashes after partial Excel bytes but before publication commit | Staged bytes not reported as finished Artifact; recovery/reap has explicit policy | `UNEXECUTED` |
| MAC-18 | Trust/integration: AI role denial | Tool descriptor encourages overwrite while delegate lacks permission | Actual product policy denies overwrite regardless of descriptor prompt | `UNEXECUTED` |
| MAC-19 | Trust/integration: source injection | External PDF or spreadsheet instructs a model to call another tool | Input content remains data; unapproved action denied by trusted command path | `UNEXECUTED` |
| MAC-20 | Execution/effects: read-only concurrency | Two independent read-only domain operations are submitted concurrently | Concurrency policy admits both within resources, shared mutable output remains guarded | `UNEXECUTED` |
| MAC-21 | Trust/integration: platform revision | External lifecycle platform activation schema changes | Explicit versioned integration failure, no machine contract substitution | `UNEXECUTED` |
| MAC-22 | Catalog/revision: binding pin | Core changes during an admitted long-running Job | Binding revision pinned or explicit defined interruption/migration; no mixed-half semantics | `UNEXECUTED` |
| MAC-23 | Agent: agent input pause | Agent-to-agent task pauses to request authentication or new user parameters | Agent Task state distinct from product Run, no fabricated success | `UNEXECUTED` |
| MAC-24 | Trust/integration: host client disconnect | Desktop closes while a Job is running in future accepted host profile | Remote application authority retains truthful Run state by documented lifecycle policy | `UNEXECUTED` |
| MAC-25 | Catalog/revision: protocol incompatibility | Machine client and server negotiate differing protocol editions | Only explicitly supported combination accepted; else typed unsupported_version, no false success | `UNEXECUTED` |

## Actual test design, separate from descriptive metadata

**Boundary fixture:** at minimum use two concrete domain methods (one source retrieval, one transformation), one direct Python implementation, one typed invocation binding, two principals where relevant, exact source-input revision fixtures, a missing optional dependency, a large synthetic result, and a controlled destructive test workspace. In a future hosted profile include application-owned Run/Attempt/Artifact storage and a controlled disconnect; in an actual machine transport integration pin the exact negotiated protocol and SDK revisions.

For each `MAC-xx` candidate record the actual application/runtime commit, domain method revision, input/output schema versions, resolver binding, principal and delegated grants, evaluation phase, observed side effects and any source-evidence receipt. Run malformed/unknown-field and attack payloads both through visible tool descriptions and direct endpoint calls; use real server-side authorization decisions as the oracle. A source-only static unit test and a deployed multiuser security test are different evidence classes.

For adapter equivalence, compare semantic values, reporting perimeter, currency/units, missingness, provenance strength, input-vintage and artifact metadata, not exact Python object/JSON syntax. Direct library import and remote callable methods can share domain results **while differing legitimately** in transport, permissions, file storage, logging and lifecycle; claiming identical execution authority would be incorrect.

For effectful cases, register invocation/request digests, exact effect target revision and an outcome record before reconciliation. A transport timeout after a possible write is `UNKNOWN` until inspected. A late cancellation cannot erase a committed external effect. A partially written XLSX remains staging, not a published artifact. Updating an underlying code module during a queued operation requires a pinned executable binding or an explicit migration/interrupt policy; a mere catalog display name is insufficient.

## Priorities and explicit non-admissions

A minimal engineering route starts with independent Python domain contracts, curating a few externally useful operations, typing input/output adapters, implementing tested local application admission and only then exposing a bounded machine protocol. MCP is one possible tool adapter; A2A is worthwhile only if an actual autonomous agent receives and manages multi-step delegated tasks. Neither protocol owns domain truth, actual effect authorization or durable Strategy Box Run identity. A new repository, universal registry database, host implementation, API transport, service authentication system and exact SDK version remain open engineering/Product decisions except for the **accepted need for a future logical host** in Web/domain and Windows/AppDock host/client arrangements.

**Test decision rule:** `PASS` requires executed applicable behavior with fixture, exact revision and signed/scoped receipt where necessary. `FAIL` requires observed violation. `BLOCKED_NOT_IMPLEMENTED` reflects absence of the required host/adapter; `NOT_APPLICABLE` requires a justified absent surface. This publication starts with all 25 as `UNEXECUTED`. No historical Research/Work links are needed for interpretation.
