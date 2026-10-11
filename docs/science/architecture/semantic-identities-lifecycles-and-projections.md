# Semantic identity, lifecycles, authority and projection boundaries

**Problem:** the same Strategy Box terms—Operation, Scenario, Case, Result, job, file, user and settings—have been used for different things in domain Python, local Windows presentation, and proposals for shared or machine-driven execution. **Status:** a scientific taxonomy and cross-theme conflict analysis, not a declaration that every named object is a shipped class, table, service or API.

**Pinned code evidence:** [core at `8459dc5`](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580), [Windows at `959e9c4`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). The local app has three visible operations, an atomic Scenario wrapper around enabled operations, one composed Scenario, a Qt-owned coordinator, path-linked Artifact records and separate local JSON histories. These are real narrower implementations, not proof of a durable headless Work or Job authority.

## 1. Semantic identity is earned by an independent lifetime

Before creating a new identifier, ask five questions: **Does its meaning change independently? Does a real consumer address it independently? Does it have distinct permissions/owner? Does losing the distinction corrupt provenance or error handling? Can its behavior be verified separately?** If all five are negative, a field, typed link or projection is usually enough. This prevents both a single giant Case with incompatible lifetimes and a new microservice for each noun.

Fourteen useful orthogonal axes organize the actual domain:

| Axis | Distinction | Common wrong substitution |
| --- | --- | --- |
| Definition / occurrence | Stable OperationDefinition vs particular invocation and OperationRun | Operation ID treated as Run ID |
| Meaning / implementation | Subject capability vs Python callable/provider | `module:function` becomes public semantic ID |
| User intention / execution | Work purpose/requirements vs Run/Job/Attempt | Worker exit closes the user's obligation |
| Plan / observation | Resolved plan and authorized intent vs effect receipt | Planned file deletion counted as applied |
| Logical / physical | ArtifactRef vs bytes/storage location | Path rename destroys provenance |
| Observed / inferred | Source observation vs transformed/reconstructed Claim | Inference promoted to official reported fact |
| Publication / permitted reliance | Snapshot recorded vs economic proposition justified | Hash or official URL proves analytical interpretation |
| Stable identity / version | Measure/source ID vs specific revision | `latest` replaces immutable snapshot |
| Causal actor / authority | Actor and display label vs authenticated principal/grant | AI/user nickname implies permission |
| Durable / ephemeral | Work/Artifact vs online presence and UI focus | Stale heartbeat trusted as live status |
| Value / rendering | AnalyticalResult vs localized/rounded table and styled workbook | Theme changes data or evidence |
| Product / platform | Bank domains and Work/Jobs vs external Node/Session | Platform process state decides bank result |
| Preference / state | User settings vs drafts vs frozen Run parameters | Changing default retrospectively rewrites Run |
| Lifecycle / terminal / assurance | Queued/running vs success/failure/unknown vs evidence strength | One `status` mixes all three |

These are **semantic tests**, not an endorsed ontology engine. Object identity can be UUID, natural key, hash or composite reference as long as its invariants are preserved.

## 2. Six identity and six temporal families

**Definition:** source/measure/operation/composition IDs name enduring semantic types. **Definition revision:** contract, classification, policy or schema version tells which semantics applied. **Immutable snapshot:** source/registry/dataset state, resolved plan and committed output generation identify a frozen basis. **Long-lived work:** Thread/Work/Automation identify user/organizational objectives and mutable history. **Execution occurrence:** Run, Job, OperationRun, Attempt distinguish admitted work, scheduled units and physical tries. **Output/decision:** Result, Claim (where separately material), Artifact and EffectReceipt identify particular verified or qualified outcomes.

A content digest is useful for identifying **bytes**, not sufficient for a logical artifact's author, rights and job context. Equal XLSX bytes from two accepted Works may remain two distinct user-facing Artifacts. Similarly, a display title, timestamp, process PID or pathname is not a stable logical ID.

Time dimensions differ: observed/released/statistical/effective source dates; Work commissioned/admitted/revised/closed/reopened; Job queued/started/terminal/reconciled; Claim assessed/revalidated/superseded; Artifact staged/committed/materialized/retired; Session connected/last-seen/expires. Wall-clock timestamps alone cannot order concurrent accepted changes; an authority revision/sequence is appropriate for shared state. Calendars and future triggers need an explicit timezone and daylight-saving policy, not only a stored UTC timestamp.

**Mutable versus immutable:** Thread title, Work requirements/revisions, schedule and preferences can change under controlled revision; used input snapshot, admitted effective params/plan and committed Artifact generation should not silently change. No backward API compatibility is required as a product constraint, but recorded historical Run input meaning must remain coherent.

## 3. Definition, binding, plan, run and receipt

A capability says **what the product can potentially do under declared validity/effect constraints**. A published Operation is a curated subject use case. A Scenario is a user-facing offer, which may project an Operation or a Composition. A Scheme or Cascade receives independent identity only when it owns a genuinely independent method, version, validity, user need or review obligation. These terms do not prescribe five execution runtimes. See [composition identity](../capabilities/composition-identity-and-user-machine-projections.md).

The binding selects a verified implementation/provider in a particular environment, and the resolved ExecutionPlan freezes actual inputs, source/registry revisions, parameter snapshot, effects and permissions relevant to the Run. The plan does **not** imply an effect occurred. The application may reject an invocation without scheduling any Job.

```text
Capability/Operation semantic definition + version
  → published user Scenario or machine projection
  → proposed intent and policy/admission
  → immutable effective parameters / binding / ExecutionPlan
  → Run → optional Job(s) → OperationRun(s) → Attempt(s)
  → effect observations and durable receipts
  → qualified Result / Artifact(s)
  → Work assessment, acceptance and residual closure
```

A short direct Python read may have no Work, Thread or managed Job. An accepted multiday banking investigation can have multiple Runs, several independently retried Attempts, partial outputs, a human review and closed-with-residue status. A Run finishing with `SUCCEEDED` does not mean its scientific Claim was supported or the client accepted the whole Work. See [end-to-end closure Science](../work/evidence-based-work-lifecycle-and-closure.md).

## 4. Thread, Work, Case and provenance cardinalities

A **Thread** is discussion/context with messages, participant projections and links. A **Work** is an accountable objective with scope, requirements, review and closure conditions. One Thread may discuss several Works; one Work may be reviewed in two authorized Threads. Deleting a UI conversation is not permission to delete a Work record or its evidence. A message suggesting an action becomes a WorkCandidate/invocation only after interpretation, validation and authorization.

A **Run** is one concrete trajectory of realizing the Work. A **Job** is a schedulable/claimable unit under that Run, which may be absent for a pure direct call or unnecessary as a separate record for a one-step task. An **OperationRun** denotes one domain operation invocation within a plan. An **Attempt** denotes a physical try; retry creates a new Attempt. One Attempt can have many external effects with different outcomes, and one file can represent several Results. This cardinality should be tested rather than assuming one of each.

The actual Windows `ScenarioRunCase` presently combines run identity, a UI card, steps and history. It is a current convenience type, **not evidence** that a permanent independent first-class Case must exist above Work and Run. The proposed `CaseView` is a projection; retained Case-specific user meaning would need proof of a separate consumer. Current [history persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) lacks one transaction over its five collections and cannot certify shared durable Work.

Six lineage families are independently valuable: original **source**; exact **transformation**; actual **execution**; **evidence/claim** argument; **authorship and responsibility** (requester, executor, reviewer, publisher); and **artifact representation/materialization**. A single `provenance: true` field does not represent them.

## 5. Outcomes and unknowns live in separate typed namespaces

| Namespace | Example states | Owner/meaning |
| --- | --- | --- |
| Work | candidate/active/awaiting review/completed/closed/reopened | Accountable objective |
| Job | queued/waiting resource/running/finalizing/terminal/reconciling | Executor/scheduler |
| Execution terminal | success/partial/failure/cancelled/outcome unknown | Observed attempted work and effect checks |
| Capability applicability | supported/unsupported/unknown | Resolver and version/implementation constraints |
| Evidence support | supported/contested/insufficient/withdrawn/unknown | Domain evidence assessor |
| Source validation | validated/rejected/needs review | Source/domain validator |
| Currentness | current for use/historical/stale/unknown | Contextual revision assessment |
| Approval | requested/granted/denied/revoked/expired | Authorized effect decision |
| Acceptance | pending/accepted/rejected/conditional | Result consumer and pinned criteria |
| Presence | online/idle/unavailable/stale/unknown | Ephemeral session state |

All names are illustrative, not current API enums. `UNKNOWN` may mean “an external side effect might have happened” or “the economic claim lacks evidence.” They have incompatible remedial actions; do **not** let a common UI enum silently merge them. `PARTIAL` means a qualified subset, not merely a warning banner. Cancellation request, worker stop, effect rollback and Work closure have separate evidence.

## 6. User, actor, principal, participant and permission

A **User** is a person/account. A **Principal** is the authenticated or otherwise admissibly verified security context under which an action is authorized. An **Actor** is the causal agent who produced a message, event or action (human, automation, system, external model). A **Participant** is scoped involvement in a particular Thread/Work/Session, possibly with a mutable role. **Session** is a time-limited client connection; **Node** is the managed deployment context; **Host** is its physical/virtual executor environment. None is the same by virtue of sharing a display name.

**Capability exists → implementation available → user applicable → explicitly authorized → plan approved if required → effect attempted → effect observed** is a set of checks, not one `enabled=true`. An installed module might be undiscovered, an available provider could fail validation, a valid operation may be unauthorized for a specific Data root, and an approved destructive plan may become stale before execution. `actor_kind=ai` provides no permissions by itself. A planned Approval authorizes a future bounded effect, whereas Acceptance assesses the actual Result after work.

An **Assignment** captures responsibility or review due from a participant; it is not a scheduled Job. A **ReadCursor** is per participant and Thread; a shared `unread` bool cannot serve several users. A **Notification** is the delivery of relevant attention with an audience, not a source event. **Presence** is TTL-based activity projection, not an identity or permission proof. Private technical logs and safe node warnings must be segregated from shared chats. See [authorization Science](../trust-and-assurance/identity-authorization-and-effect-boundaries.md).

## 7. Automation, triggers and background are different identities

**AutomationSpec** is a durable, revisioned rule identifying a target operation/composition, trigger, run-as principal and schedule/coalescing/approval/resource policy. A **TriggerSpec** defines once/calendar/interval/source-change/event/dependency conditions, a **TriggerOccurrence** is an observed actual match. One rule may produce zero, one or many WorkCandidates, Runs or newly commissioned Works according to an explicit *admission policy*. “No new publication found” may conclude a lightweight check with no new Work if the user commissioned “notify only on change.”

A **background execution mode** only says execution is independent of the currently viewed window under the selected runtime profile; it does not create a BackgroundScenario object with its own scientific semantics. A live scheduler may have no active jobs; a user-launched Job may run with the UI hidden without being scheduled. Disabling an AutomationSpec typically prevents future triggers, but does not automatically cancel a Run already admitted unless that policy is expressly defined.

A **ConditionWatcher** repeatedly checks a bounded condition; a **LongRunningListener** is a service producing occurrences. Neither automatically implies an endless user Work. An externally driven reasoning or proposal cycle may have its own bounded `CognitiveActivation` identity, but it is not a second AI-specific banking executor. Machine-originated work must still pass the same admissible operation/permissions/effect boundary. Persistence of speculative cognitive state is a separate optional pilot question.

## 8. Five kinds of settings and their owners

Calling everything `Settings` would create harmful state coupling:

| Category | Meaning and typical examples | Who may write it |
| --- | --- | --- |
| **UserSettings** | Durable theme, constrained accent, output-style default, approved personal preferences | User preference owner in that scope |
| **SurfaceState** | Current tab, window geometry, selection, sidebar widths, filter/focus | Device/surface client, often reconstructible |
| **DraftState/RecentState** | Unsaved parameters and remembered recent choices; potentially sensitive | User/device scoped, with cleanup/expiry |
| **RunParameters/ParameterSnapshot** | Immutable resolved values actually used by a specific admitted Run | Application/execution admission authority |
| **ManagedPolicy** | Organization/deployment-required behavior, permissions and limits | Verified platform/product policy authority |

Workspace/Data root and activation binding are **not ordinary preferences**: a valid managed Node/Session/Data resource assignment is a separate runtime capability. A user choosing another color must not change the actual database or rewrite historical Run parameters. A stale remembered form default is not an authoritative approved input.

## 9. Extension, provider, binding and client surface semantics

A neutral **PluginDescriptor** describes a package/version/API/dependencies/declarations; a **Provider** implements a named extension slot; a **ProviderBinding** selects/validates/activates the provider for an actual capability and scope. **StyleProvider** supplies validated declarative font/palette/template resources for artifact rendering, but does not acquire arbitrary access to modify shell UI or business formulas. The stages `installed → discovered → validated → activated → bound → usable` have independent status and error reasons; availability and authorization may still be false.

A **Surface** is Windows Qt, prospective Web or Android rendering capability. **ViewModel/Projection** turns a shared semantic Thread/Work/Job/Artifact into client-specific cards, lists, inspectors or notifications; it is not a competing data owner. A `CaseView` and a JobCard can both refer to one Run, which remains identified independent of any particular Qt widget. Neutral public contracts and safe capability metadata suffice for this analysis; internal implementations belonging outside public code are neither required nor described.

## 10. The 22 retained cross-theme conceptual conflicts

The dated canonical research enumerates **22** material collisions; here their analytical outcomes are kept rather than simply repeating labels:

| Source IDs | Collision | Interpreted disposition |
| --- | --- | --- |
| S01–S05 | Technical Command vs domain Operation; automatic Scenario for every function; background Scenario kind; Cascade/Scheme and Scenario/Scheme identities | Curate user-meaningful Operations and Scenarios, treat background as execution mode, leave independently governed Scheme/Cascade cardinality open |
| S06–S09 | Current Case vs Work/Run; Run/Job/OperationRun/Attempt; Thread vs Work; machine memory/chat vs Work | Preserve distinct lifetimes and origins; no compulsory Case entity or full graph engine |
| S10–S12 | Result vs Artifact; Execution success vs Work acceptance; FileStore vs ArtifactCatalog | Separate scientific result, durable output and user acceptance from mere file operation |
| S13–S16 | Snapshot vs Observation; Dataset vs DataFrame; distinct registries; published vs inferred number | Preserve semantic input, scope, code and proof tiers, not filenames/dataframe shape as truth |
| S17–S20 | Node/Session vs product identity; platform scheduler; installed extension vs usable capability; settings vs running state | Respect external-platform boundary, staged capability validation and multiple settings/state scopes |
| S21–S22 | Public domain core depending on environment internals; multiple Windows/Web/AI/background execution engines | Keep neutral contracts and one semantic execution spine with surface/client-specific projections |

Some are **different abstraction levels**, not genuine incompatible alternatives (Definition vs Run, FileStore vs ArtifactStore, UI Widget vs projection). Others are real unapproved choices: independent Cascade, threshold for Work admission, Run/Job cardinality, separate ClaimStore, source-release identity, and physical event/DB semantics. Later late-series sources also admit **atomic-file first versus SQLite first** as alternatives; a high-confidence semantic distinction cannot approve a physical backend.

**Historically superseded shortcuts:** one Case that is simultaneously chat/goal/run/evidence; user Scenario generated for every helper; background as its own scenario ontology; parallel AI runner; Qt local JSON as shared host authority; transport success as verified data; file overwrite as versioning; mtime as semantic freshness; exception string as sole typed error; installed extension as grant; new repo per noun. Their origin can be documented without being reproduced as target requirements.

## 11. Independent challenging examples

Fifteen exact question families survive, each a proposed **conformance scenario, not a tested pass**:

1. Same official URL and reported period but changed bytes: old and new source snapshots must remain distinct.
2. Two reports with identical measure label but IFRS-group vs standalone RAS scope: bridge or explicit incomparability.
3. SORS inferred hidden value: published bucket and method/evidence tier remain different.
4. XLSX successfully written, faulty formula discovered: execution outcome and Work acceptance disagree legitimately.
5. Lost ACK after destructive effect: UNKNOWN/reconciliation, no blind retry.
6. Three users on one Node: common Work/Run with separate sessions/cursors/grants and no automatic cancellation power.
7. One daily AutomationSpec: many TriggerOccurrences, no automatic infinite Work or running rule.
8. Windows and a machine consumer invoke one Operation with different actor/origin/permission but same economic semantics.
9. One workbook includes results of two analyses and then moves: Artifact lineage and physical path remain distinct.
10. An enabled schedule is turned off while a Job runs: future triggers stop; existing Job requires separate decision.
11. Theme and ArtifactStyleSet change: the numeric Result and claim evidence remain unchanged.
12. Approved destructive plan becomes stale before use: new revision must be checked against approval's scope/digest.
13. “No new data found” after a defined source check is a **qualified negative result**, not the value zero.
14. One Work discussed in two authorized Threads remains one Work identity.
15. Optimized implementation of the same Operation must demonstrate semantic equivalence and preserve binding revision.

The original retains **25 Product/Engineering questions**, notably: when Work should exist; necessity of Run and Job for simple work; Job vs OperationRun in a DAG; durable Case; Scenario↔Scheme/Cascade cardinality; minimum result/outcome and unknown-effect closure; durable Claim/Basis; Dataset vs Artifact and source-release identity; measure/perimeter bridge; currentness; Thread↔Work access; who accepts/closes; principal delegation; definition-version multiplicity; capability curation; required v1 artifact/source/result identities; human terms; technical CommandSpec; optional EvidencePackage/DecisionInput entities; cognitive activation; and secure cross-object search. None is automatically resolved by selecting a compelling noun in Science.

**Cross-referenced detailed Science:** [source observation/comparability](../data-and-knowledge/observation-semantics-comparability-and-claims.md), [dataset lineage](../data-and-knowledge/dataset-versions-lineage-currentness-and-retention.md), [capability semantics](../capabilities/definitions-plans-and-execution-truth.md), [Work closure](../work/evidence-based-work-lifecycle-and-closure.md), [shared state recovery](../state-and-recovery/authority-durability-and-recovery.md), [client portability](../surfaces/semantic-portability-and-client-authority.md).

**Reopen:** accepted actual consumer use cases, source/implementation revision, external platform contract, recovered data loss, negative exact conformance result or Product Authority's published decisions. Every proposed type's existence and persistence must be proven in an executable vertical slice before a “complete canonical ontology” claim.
