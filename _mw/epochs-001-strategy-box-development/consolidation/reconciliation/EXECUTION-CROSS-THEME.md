# Execution, automation, planning, and multiuser semantics — bounded cross-theme Research synthesis

**Mode:** post-theme bounded Research corpus synthesis; **Status:** PRODUCER RESULT ESTABLISHED for the 5-source, 164-provisional-unit interface declared here, **NOT** a globally reconciled corpus, maintained Scientific Knowledge, or Product decision.  
**Consumer:** Scientific assembly and Target WHAT Decision owners deciding which conclusions have primary support versus multiple dependent Research restatements.  
**Method basis:** current pinned Research synthesis instruction 10 and its matching example, Knowledge assembly contract, exact source-use and unit ledger.  
**Freeze:** execution Knowledge Work `stratbox@b6456642ca0e115798b8056d2dfa7144dfe26ca5`, original pinned Research commit `8459dc58922b7e8df853cf1d9e8131fa9e132580`, Windows implementation `959e9c4ce1441124af5111c1e025041714e04d3b`. No new external source is admitted by this synthesis.

## Declared five-source corpus and unit boundary

| Original Research source | Exact blob | Provisional units | Contribution and evidence dependence |
| --- | --- | ---: | --- |
| `SB-SRC-0018` | `5ed80eeb3065b60f89d0706bfa49bbfd272fc066` | 21 | Automation/Chat/Job interpretation, directly based on Windows and earlier execution/observability studies |
| `SB-SRC-0024` | `201ca931a09f5bf7bba15e364da50726fdca291f` | 32 | Command–Scenario–Cascade/planner/dedup hypothesis; derived from Windows and other prior work |
| `SB-SRC-0026` | `0cf37ddf3b0b44495a30ec1d31117fc9dfc70671` | 37 | User invocation, parameter profile, cancellation, shared commands; directly overlaps 0018/0024/0030 |
| `SB-SRC-0030` | `c4ec86841e2a92299adbefeb6a6a387b7106f587` | 38 | Observability, physical logs, error/progress and platform problem boundary; shares current Windows code |
| `SB-SRC-0036` | `fb8ffe1b13f5c8718b171e6c7ad3d8a0f06948df` | 36 | Node-shared state, per-user read, ACL, cases/jobs and remote clients; dependent on current Windows/platform studies |
| **Total declared extracted units** | five stable IDs | **164** | All are provisional, **not** five independently verified evidence datasets |

The Work ledgers `units/BASE-STUDY-0018.jsonl`, `0024.jsonl`, `0026.jsonl`, `0030.jsonl`, `0036.jsonl` provide exact material-unit source spans, classifications and open assurance. A source's full-read flag proves the whole original document was inspected, **not** that its final scientific meaning is losslessly published.

## Reconciled problem model: four ownership and truth dimensions

**Analytical meaning** belongs to the headless domain operations. **Product invocation** defines a user's intended task and its resolved parameters. **Execution authority** would track actual admitted work, attempts and effects, and must outlive the client's projection if a true background/shared profile is adopted. **External managed environment** has its own Node/Session/health/activation meaning, distinct from an analytical Job's acceptance or success. The sources agree on a logical boundary, but derive heavily from the same Windows source paths. This is *consistent interpretation*, not five independent confirmations.

The governing cross-theme relation is:

```text
User / permitted machine intent
   ├─ selected user task (Scenario or an approved larger composition)
   ├─ versioned, effective input binding
   ├─ proposed plan of subject operations / dependent commands
   └─ admitted, permission-scoped execution identity
          ├─ Job / technical attempt / effects (only if execution authority exists)
          ├─ durable event and result (only under supported persistence profile)
          └─ permitted client-specific projections
```

This graph expresses candidate roles and dependencies. It **does not** assert that those records, contracts or a host service are already implemented in the pinned Windows application.

## Cross-topic propositions and their dispositions

| Material relation | Source-unit routes | Reconciliation, counterargument and status |
| --- | --- | --- |
| Operation, Command and Scenario | `0024:001–008`, `0026:002,011` | Core uses Operation for an analyzable domain use case; a technical Command is a narrower optional planning atom. **Terminology conflict retained:** imposing every proposed Command on core would overfit today's consumers. Product naming/API decision OPEN. |
| Scenario versus Cascade | `0024:004,007–010`, `0026:016`, `0018:002` | The current composed Scenario combines several operations; a future Cascade spanning reusable user scenarios has plausible independent semantics. Alternative: a single typed DAG Scenario may suffice for smaller product scope. **Product boundary not yet selected.** |
| Work/Case, Run, Job, Attempt | `0018:002–003,010`, `0030:006,009`, `0036:013` | Differing lifetimes are a strong explanatory necessity in a durable/remote system. **Current evidence:** a Case/Qt runner exists, not a proven persistent JobManager; Work as long-lived user intent is a further proposal. |
| Background process versus Automation | `0018:008–009`, `0036:017`, `0030:013` | A rule's enabled status differs from active task execution. Current background store tracks status in memory but does not schedule work. Candidate unified executor preferred by Research; exact automation release scope OPEN. |
| ChatThread versus event timeline | `0018:004–007`, `0036:011–012`, `0026:022` | One user thread may display multiple Cases, while events have author/source identity. The current scenario chat is a UI projection, **not** proven multiple durable ChatThreads. Automatic chat creation per schedule is a contested usability decision, not invariant. |
| Effective parameter snapshot versus remembered profile | `0026:013–015`, `0024:010` | Mutable defaults, personal presets, policy-fixed values and actual run parameters differ; a versioned effective snapshot prevents retroactive reinterpretation. The exact precedence requires Product/policy authorization and persistence design. |
| Dedup versus cache reuse versus idempotency | `0024:011–014,016,026,029`, `0018:016` | Same command ID is insufficient to deduplicate different effects. In-plan dedup is about simultaneously requested equivalent computation; caching reuses old results; idempotency concerns repeated logical commands and side effects. All have independent source/freshness/permission conditions. |
| Parallelism and resource conflicts | `0024:015`, `0018:011`, `0036:014` | One global busy flag is safe only locally but can over-serialize work; uncontrolled parallel writers threaten outputs. A resource/effect-aware policy is plausible, **not proof** of distributed locks, robust leases, quotas or concurrency guarantees. |
| Cancellation and ambiguous effects | `0026:017–019,027`, `0030:024,026`, `0036:025` | Cancel request, confirmed cancellation, force termination and actual irreversible effects are separate. An external timeout can leave effect outcome unknown. Existing Qt runner does not demonstrate end-to-end cancellation. A new cooperative-token protocol remains candidate. |
| Node and Session versus product execution | `0036:008–010,016`, `0030:008,015` | A managed Node's health or Session heartbeat is not a product Job's terminal outcome. Upstream platform maturity must be validated on exact contract revision; no remote control is inferred. |
| Shared events, unread and notifications | `0036:011–012,021`, `0030:017–020` | One underlying event can have several **per-user** read/notice states. A global `unread` bool cannot represent both users' receipts. Safe cross-user notices need audience filters, not simple raw event broadcasting. |
| Case/status persistence | `0036:016,024`, `0030:005,017`, `0018:012` | Five JSON projections have no demonstrated atomic shared transition. SQLite local-WAL, server DB or another transaction-backed profile are alternatives; Product requirements on durability/recovery are not yet admitted. |
| Observability versus state truth | `0030:016–022`, `0036:020–021` | Logs are evidence, not authoritative Job state; raw tracebacks must not become shared projections. Observability sink failure must not manufacture successful ProblemRef registration or silently alter domain outcome. |
| Per-actor authority and machine consumers | `0026:023,030`, `0036:022–023,027`, `0030:021` | The existence of actor labels, operation visibility flags or buttons grants no authorization. Effective rights must be checked by a real authority before effects. A permitted machine consumer has no implicit administrator power. |
| Portability and physical packages | `0018:003,018`, `0036:016,026`, `0024:024` | Shared semantics can support distinct Windows/Android/web renderers without copying Qt, but do **not** require a new repository, server topology, common SDK language or production mobile release. |
| Historical roadmap recommendations | `0018:019`, `0024:030`, `0026:035`, `0030:030`, `0036:033` | All five propose engineering order/priority. These are overlapping author interpretations, not five independent owner decisions. Preserve as research history; do not self-commission refactoring. |

## Distinct evidence lanes and strongest challenges

**Direct code lane:** pinned Windows source proves a Qt-dependent coordinator, sequential runner, local five-file history, in-memory background-state model, and selected log/exception pathways. It does not prove a distributed outcome, successful fault injection or deployment semantics. **Research and analogous-framework lane:** these five studies elaborate logical alternatives based heavily on shared current-state research, user product interests and external examples. Agreement across five texts is **not** independent experimental validation. **Formal reasoning lane:** a timeout after an external effect cannot itself determine whether the effect occurred; this remains conditional on the stated remote-effect/acknowledgement ordering, not an observed production incident.

Strongest counterarguments and resulting boundaries:

1. **“One universal Command–Scenario–Cascade–Job ontology is obligatory.”** False at this stage. Current product may need only a few executable operations and composed scenarios; introducing all types carries catalog and synchronization cost. Retain both a minimal current model and richer candidate model until a consumer/decision establishes need.
2. **“All shared execution needs a separate server/repository.”** False. Logical authority and physical deployment are different; in-process or node-local service can satisfy smaller profiles if it meets accepted lifetime/isolation obligations.
3. **“SQLite WAL fixes multiuser by putting the DB in shared Data root.”** Unsupported and specifically challenged by storage locality/locking semantics. A local authoritative node DB plus API projection, or a server-grade DB, are conditional alternatives.
4. **“Idempotency/dedup makes external effects exactly once.”** False without a provider-effect protocol and receipt/reconciliation boundary. At-least-once delivery, network ambiguity and unknown effect persist.
5. **“Presence and user notification can be inferred from local Case authors.”** Only local retrospective information; real presence/notification needs a platform session and audience-specific state owner.
6. **“All quality proposals are accepted release blockers.”** No. Relevant negative tests and logic can challenge future Product decisions but require accepted guarantees, scope and profile thresholds.

## Bounded completeness / residue / write-back

**Selected material-unit coverage:** all **164** ledger unit identities in the declared five-source interface have a Source locator, typed concern and an upstream source owner; this reconciliation groups those concerns without copying every candidate API field or example. **Independent unit-to-final-owner conservation remains OPEN**—none of the five sources is certified completely absorbed into maintained Science. Outstanding adjacent Results include original data/registry/artifact studies and unprocessed remaining base studies, plus system syntheses 00–09. This Work does not assert their cross-theme closure.

**Supported downstream use:** scientific assembly can use the separation of source/result evidence, invocation/execution/effect truth, read-state scopes, and the limits of dedup. Product decision owner can review competing candidate models without assuming which one has been chosen.

**UNKNOWNs / reopening:** accepted multiuser profile, package topology, exact authorization and storage scopes, mobile role, cancellation and idempotency windows, registry SourceSnapshot versions, external platform capabilities and real fault-injection evidence. Reopen on new admitted original Research, direct code change, external contract revision, independent semantic-unit audit or Product Decision.

**Work completion verdict:** **BOUNDED SYNTHESIS RESULT ESTABLISHED / GLOBAL SCIENCE UNADMITTED**. This does not independently verify the original claims, repair implementation, or alter the existing Target WHAT/HOW documents.
