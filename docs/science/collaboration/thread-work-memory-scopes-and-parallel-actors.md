# Thread, Work, memory scopes and parallel cognitive actors

**Scientific question:** can an analytical chat remain responsive across several concurrent tasks, personal and shared work, long-lived results, a replaceable model and several devices without making the transcript or AI memory the authoritative Work store? **Status:** source-qualified competing product models, not a released chat/agent implementation or an accepted information architecture. Primary source studies: Chat/Work/Schemes, 2026-10-07, host cognitive foundation and the [pinned Windows runtime](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b).

## 1. A conversation is an ingress and history carrier, not a durable execution identity

A user can write “refresh escrow”, later “compare it to Q2”, then “also check corporate loans” within one conversational context. Each message might be a question, constraint, action proposal, correction, authorization, observation, continuation or request for a new Work. No parser, model or user interface should transform every text turn immediately into a new destructive command.

The key distinction is:

| Object | Owns | Does not automatically own |
| --- | --- | --- |
| **Thread/Chat** | Bounded conversational context, messages, selected references, participants, thread-specific navigation | Domain data truth, final Work decision, durable worker execution |
| **Work** | Commissioned goal, relevant constraints, accepted actions/effects, results, blockers, responsibility, residual obligations | All messages in which it was discussed |
| **Run** | One execution of an admitted plan with status/effects/attempts | The long-lived conversation or the success of the whole Work |
| **Artifact** | Managed output/version, contents, provenance, visibility and independent retention | Thread identity, completeness of analysis or user acceptance |
| **Actor/Cognitive Activation** | Identity and bounded attempt at interpretation or action, according to authority | Product database ownership or automatic truth of model response |

One Thread may include several Works, each with several Runs and intermediate Artifact versions. Work A can create evidence that Work B later cites, while the corresponding Threads remain distinct. A Thread can be archived without deleting the underlying Work; an Artifact can outlive the discussion that generated it. The two most common modeling errors are **one Chat = one Run** and **one Case = conversation + Work + Job + Artifact + approval + acceptance**.

The early Windows design is Scenario-first and [Qt-backed](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py), allowing one active foreground Case. That is a current implementation constraint, not evidence that future application semantics require a global one-at-a-time chat.

## 2. Five distinct kinds of “memory”

A prompt window, persistent human conversation, authoritative Work state, user cognitive profile and a shared dataset are not one memory substrate:

| Scope | Examples | Appropriate owner and consequence |
| --- | --- | --- |
| **Message history** | Who said what and when | Access-governed Thread; message history is historical communication evidence |
| **Thread context projection** | Summary, active questions, selected excerpts, references | Rebuildable/replaceable bounded context derived from Thread; can be stale or lossy |
| **Durable Work state** | Exact objective, accepted parameters, decisions, effects, pending approvals, checkpoints, evidence | Product application authority; must survive summarization failure and model replacement |
| **Personal cognitive memory** | User preference, learned reusable procedure, persistent private agent profile | Separate consent/retention/authorization domain; never automatically shared through team Thread |
| **Node/workspace knowledge** | Approved datasets, registries, source versions, shared Artifacts and qualified claims | Domain/data/knowledge owner, accessed by permissions and exact resource identities |

“Fork from here” may create a new Thread and copy **explicitly selected refs** to Messages, Work or Artifacts, while preserving provenance and visibility. It must not silently clone another user's personal cognitive memory, revive expired approval, duplicate a Job, or make a derived summary the original source. New Chat should reset only conversational context, not wipe the user's identity, official source library, consented persistent preferences or already admitted work.

Long conversations require selective context compaction. A summary is a convenience for model attention, **not an authoritative substitute** for pending constraints, approvals, unobserved effects or a Work checkpoint. The correct context builder retrieves only authorized, needed evidence with visible gaps, rather than blindly streaming the full workspace or using the last thousand tokens as truth.

## 3. Concurrent Work without fictional shared progress

The target user may submit A, B and C while A is running. A global composer “busy” lock would prevent legitimate analysis, but removing the lock is only safe if admitted Jobs and resource conflicts are tracked below the UI. Separate **admission concurrency** from **execution concurrency**:

```text
one Thread
  ├─ Work A → Run A1 (running: source read)
  ├─ Work B → Run B1 (waiting: shared output lease)
  └─ Work C → Run C1 (queued: CPU quota)
```

The composer can accept another proposal while the scheduler declines its execution, requires approval or queues it; a Run card shows each actual status. Parallel branches of one Work may collect deposits, loans and profit independently, then fan in under a separate synthesis/evaluation stage. Any sharing of output files, mutable registries or source snapshot generations needs a declared resource/transaction fence; parallelizing two writes is not harmless merely because both calls returned success.

A detached host may continue Jobs after browser shutdown, whereas a local foreground Qt profile may have weaker lifetime guarantees. The UI must communicate the actual profile. Switching Threads should never itself change a Job's lifecycle. Cross-device users should resolve the same stable Work/Run refs only through their current permissions; stale snapshots and disconnected clients must be labeled.

## 4. Persistent actor, cognitive profile, activation and solver are four identities

A proposed cognitive system distinguishes:
- **Actor:** long-lived principal/profile holder, perhaps a user's opted-in cognitive counterpart, with grants and accountability.
- **Profile:** repeatable configuration or operating envelope (e.g. light local analysis versus rigorous independent challenge).
- **Activation:** one isolated transient execution/context with its own ID, scratch space, budget and Run links.
- **Solver:** physical mechanism, deterministic algorithm, local/remote model, retrieval, human or composition.

One actor may spawn several Activations of the same profile for speed, independent from each other's transient state. Creating a new permanent “agent identity” for every parallel request increases authority, memory, audit and retention complexity without establishing task isolation. True separation is achieved through per-Activation state/leases, distinct attempt identifiers, access policies and result reconciliation.

A delegated **child actor** or independent Work is justified only when separate authority, durable responsibility, remote lifecycle, persistent memory scope or explicit third-party commitment is necessary. The distinction mirrors durable child workflows in systems such as [Temporal](https://docs.temporal.io/child-workflows), but that precedent does not prescribe a Strategy Box deployment.

## 5. Replicas increase throughput more easily than evidence quality

Several identical solvers can partition workloads by bank, period or source safely if they share no mutable scratch state and the domain operation is correctly isolated. Such replication is **performance scaling**. If all models share one prompt, weights, source bundle and method, their mistakes may be correlated; three responses do not create three independent supporting documents.

Candidate diversity or independent verification requires deliberate change of model, evidence universe, method, adversarial hypotheses, time vintage or verifier. Even then, evidence independence must be tested at the **source and method lineage** level. A failure to identify a contradiction across clones is not validation; repeated AI narratives do not upgrade a reported datum or weak restoration to an official fact.

A valuable fan-out/fan-in contract stores every candidate Result and its provenance separately, then delegates reconciliation/acceptance to the appropriate Work/evaluation owner. The model deciding how to split a task cannot silently become the actor authorized to accept all outputs.

## 6. Host sovereignty at the cognitive ingress boundary

The safest proposal path is:

```text
human text / trusted trigger / authorized peer request
→ IngressEvent with principal, actor, channel and references
→ bounded cognitive interpretation (optional)
→ WorkCandidate / ActionProposal with assumptions and uncertainty
→ product checks current capability ID, parameter schema and rights
→ explicit admission or user/authorized approval
→ ordinary Work → Run/Job → deterministic operations
→ typed outcomes, artifacts, diagnostics and evidence
→ optional AI explanation that cannot change final outcome
```

A user clicking a deterministic Scenario skips model interpretation and reaches the same product admission boundary. In a degraded/offline mode the product should still support permissible direct core operations. The cognitive adapter consumes a minimally sufficient host projection and returns proposed actions—not raw DB mutations, unmanaged shell commands, expired approvals or fabricated success.

Model-inferred intent has finite authority. “I think the user meant cleanup” must become an inspectable proposal when destructive effects may follow. An uncertain `continue Work` should request disambiguation or inspect Work refs; it must not open a new Run with stale source parameters solely because a text model predicted the scenario title.

## 7. Personal versus shared Threads and collaboration

Shared Node history is not the same as shared private model memory. A Thread has its own access policy and participant membership; each ArtifactRef has scope and permitted actions. Work can be team-visible with one participant's personal draft kept private. Assignments, approvals and actor authorities persist as independent app-level objects rather than disappearing on message deletion or session logout.

Presence is a momentary projection from authorized session/heartbeat information. Being online does not prove availability, acceptance, ownership or capability to approve. Read/unread state belongs to each principal and should not mutate the underlying Event truth for other users.

For external delegation, transport identities such as A2A context/task can map to Thread/Work, but **the product internal IDs remain owners**. Remote peers receive scoped work proposals and permitted artifacts, not a shared mutable transcript or unchecked ability to issue effects.

## 8. Artifacts deserve several navigational surfaces, not several owners

A result can be discoverable:
1. inline as an Artifact card beside an execution;
2. in the Thread’s Artifact shelf with all linked versions;
3. in a selected current Working Set for bounded context;
4. in a global access-scoped Artifact library with search by Work/Run/type/source/status.

These are **projections of one managed artifact identity**, not independent copies whose title or publication status may diverge. A current Working Set reference can be removed from prompt context without deleting bytes or revoking a published Artifact. Closing or deleting a Thread does not automatically imply the deletion of source snapshots or independently retained report files.

The user should see exact producer Run, status, release/verification, lineage, version and permissioned next actions. The presence of an Excel file in the timeline is not a machine-grounded answer if the Artifact was only partially written, rejected or superseded.

## 9. Competing UX and data models

| Model | Benefit | Limitation |
| --- | --- | --- |
| Scenario-first one Case per chat | Simple prototype and obvious run selection | Cannot naturally preserve several Works, real human collaboration or concurrent execution |
| Thread-first with embedded Run cards | Human continuity and bounded context | Can hide cross-node operational failures without a separate Runs view |
| Work-first navigation | Better accountable objectives and closure | High overhead for a simple one-off query or quick spreadsheet export |
| Four-area Work/Explorer/Scenarios/Runs | Balanced discovery, status and artifacts | Heavy Team/Inboxes users may need an independent task/approval surface |
| AI-only conversational shell | Fast demonstration | Model memory becomes accidental execution state and direct deterministic path may disappear |

The studies strongly favor **semantic separation** over one universal navigation structure. Whether Work is the home screen, an AI composer exists, how “Fork” behaves, and how to expose parallel cognitive activations remain Product Decisions.

## 10. Negative tests and unresolved decisions

Proposed tests: submit three requests while one is executing and check Job ID uniqueness; reconnect two clients under different grants; fork a Thread but revoke access to one attached personal Artifact; run two Activations with shared profile and check isolation; kill a worker before side-effect receipt; replay an edited old message after approval expiry; delete a Thread and confirm Work/Artifact retention; swap AI providers and preserve Work status; attempt to use an archived stale summary as current instruction; run independent candidate verification with a shared contaminated source; maintain keyboard/readable progress through 1000 concurrent items.

**Observed:** the dated Windows implementation has a useful scenario chat/Case history and one QThread-driven active execution; no multi-Work durable Job/Thread service, independent cognitive agents, A2A federation or cross-device shared memory is certified. **Research result:** Thread, Work, Run, Artifact, Actor/Activation and memory scopes require different truth owners if these use cases are adopted. **Open:** persistence profile, canonical UI navigation, identity/delegation contracts, cognitive memory consent, concurrency quotas and inter-user visibility.

Related Science: [Work-context navigation](../surfaces/work-context-navigation-and-authorized-actions.md), [work lifecycle](../work/evidence-based-work-lifecycle-and-closure.md), [authorized event cursors](authorized-streams-read-cursors-and-private-work.md), [work-state continuity](../state-and-recovery/shared-state-backup-generation-and-retention.md), [automations](../automation/bounded-agent-routing-and-evidence-safe-automation.md), and [portable clients](../surfaces/semantic-portability-and-client-authority.md).

## 11. Original competing chat-first proposals and anti-patterns (30 exact study items)

The original Chat / Work / Scheme study (`#L2504-L2864`), blob `fe99e04aa38ac7b59fbf8419fa29d6018028ae80`, concluded that a cognitive-first future interface should be Thread/Chat-first while the semantic application remained Work-first. It also explicitly rejected nine failure patterns. These precise propositions and candidate design choices are preserved below as **research findings/proposals, not accepted navigation, actor-cardinality, permission, runtime or protocol requirements**. In particular, a competing operational-first navigation model and an epistemic navigation model are preserved in the documented architecture disagreement.

### Nine original research anti-patterns with English-rendered reasons

| Item | Source heading | Reason translated into English | Original line |
| --- | --- | --- | --- |
| `SB-SRC-0033/ANTIPATTERN-01` | Scenario-first forever | The user is forced to understand internal machine taxonomy before doing work. | L2506–L2508 (`#L2506-L2508`) |
| `SB-SRC-0033/ANTIPATTERN-02` | Chat = source of truth | Material state lives only inside chat messages. | L2510–L2512 (`#L2510-L2512`) |
| `SB-SRC-0033/ANTIPATTERN-03` | One global agent loop | All commands pass sequentially through one active model session. | L2514–L2516 (`#L2514-L2516`) |
| `SB-SRC-0033/ANTIPATTERN-04` | One busy flag | Any Run blocks the entire interface. | L2518–L2520 (`#L2518-L2520`) |
| `SB-SRC-0033/ANTIPATTERN-05` | Shared mutable AI memory | All parallel agents mutate the same shared scratch state. | L2522–L2524 (`#L2522-L2524`) |
| `SB-SRC-0033/ANTIPATTERN-06` | One Case = all semantics | Case expands into a combined Thread, Work, Run and Artifact container. | L2526–L2528 (`#L2526-L2528`) |
| `SB-SRC-0033/ANTIPATTERN-07` | Clone agent = independent evidence | Identical agent copies are incorrectly counted as independent experts. | L2530–L2532 (`#L2530-L2532`) |
| `SB-SRC-0033/ANTIPATTERN-08` | Every event creates chat | Background processes create unnecessary Chat threads and clutter the UI. | L2534–L2536 (`#L2534-L2536`) |
| `SB-SRC-0033/ANTIPATTERN-09` | Schemes hidden completely | Manual supervision and debugging of Schemes become impossible. | L2538–L2540 (`#L2538-L2540`) |

### Twenty-one explicit design recommendations (historical candidate, not universal target)

| Item | Original question/choice translated | English-rendered research recommendation | Original line |
| --- | --- | --- | --- |
| `SB-SRC-0033/UX-CANDIDATE-01` | Primary user-facing object | Thread / Chat | L2844 (`#L2844`) |
| `SB-SRC-0033/UX-CANDIDATE-02` | Primary semantic object | Work | L2845 (`#L2845`) |
| `SB-SRC-0033/UX-CANDIDATE-03` | One concrete execution | Run | L2846 (`#L2846`) |
| `SB-SRC-0033/UX-CANDIDATE-04` | Reusable machine procedure | Scheme | L2847 (`#L2847`) |
| `SB-SRC-0033/UX-CANDIDATE-05` | Atomic capability | Operation | L2848 (`#L2848`) |
| `SB-SRC-0033/UX-CANDIDATE-06` | Persistent cognitive actor identity | Actor | L2849 (`#L2849`) |
| `SB-SRC-0033/UX-CANDIDATE-07` | Parallel local cognition | Independent Activations | L2850 (`#L2850`) |
| `SB-SRC-0033/UX-CANDIDATE-08` | Durable output | Artifact | L2851 (`#L2851`) |
| `SB-SRC-0033/UX-CANDIDATE-09` | The Cascades section | Remove as a separate top-level concept | L2852 (`#L2852`) |
| `SB-SRC-0033/UX-CANDIDATE-10` | The Scenarios section | Move to a capability library / picker | L2853 (`#L2853`) |
| `SB-SRC-0033/UX-CANDIDATE-11` | Right-hand inspector | Retain and enhance for Artifacts and Work | L2854 (`#L2854`) |
| `SB-SRC-0033/UX-CANDIDATE-12` | List of Chats | Persistent side panel, preferably the existing left secondary panel | L2855 (`#L2855`) |
| `SB-SRC-0033/UX-CANDIDATE-13` | Global busy composer state | Remove | L2856 (`#L2856`) |
| `SB-SRC-0033/UX-CANDIDATE-14` | One request necessarily creates a new Chat | No | L2857 (`#L2857`) |
| `SB-SRC-0033/UX-CANDIDATE-15` | One Chat is necessarily one Work | No | L2858 (`#L2858`) |
| `SB-SRC-0033/UX-CANDIDATE-16` | One Work is necessarily one Scheme | No | L2859 (`#L2859`) |
| `SB-SRC-0033/UX-CANDIDATE-17` | One Scheme is necessarily one agent | No | L2860 (`#L2860`) |
| `SB-SRC-0033/UX-CANDIDATE-18` | Same Scheme across N copies | N Runs / Activations | L2861 (`#L2861`) |
| `SB-SRC-0033/UX-CANDIDATE-19` | Shared mutable AI memory | Disallow by default | L2862 (`#L2862`) |
| `SB-SRC-0033/UX-CANDIDATE-20` | Multi-user organization | Federation of Actors | L2863 (`#L2863`) |
| `SB-SRC-0033/UX-CANDIDATE-21` | A2A relationship | Transport adapter, not internal domain model | L2864 (`#L2864`) |

### Boundary notes on the original candidate design

The nine failure modes are not symmetrical bans on capabilities: a curated user Scenario catalog can still be a correct manual power-user entry point; a single active Job may be a valid resource limit for a lightweight standalone deployment; one persistent actor per user is only one possible identity topology. Their failure status is **conditional on requiring multiple concurrent Work, durable state, independent users, replaceable cognition and shared provenance**. The original argument against one global busy flag is particularly strong for these multi-Work requirements, but alone does not justify unlimited parallelism or preemptive cancellation without effect reconciliation.

The 21 proposed choices should be experimentally checked against user journeys: novice direct analytics, analyst reproducibility, team permissions/approvals, artifact retrieval, keyboard accessibility, disconnected clients and phone-sized screens. If an operational Work/Explorer/Scenarios/Runs layout performs better for a deterministic deployment, choosing it need not violate Thread/Work semantics. Store what is product-owned independently from where the desktop places tabs.

**Conservation status:** 30 original research choices/anti-patterns now have stable source IDs and **English-rendered** textual destinations with precise links to the frozen Russian source wording. Translation is an editorial producer operation, not verbatim transcription or independent semantic attestation. The remainder of the 2,995-line study, including conditional concurrency and distributed identity details, is not thereby proven fully preserved or independently verified.
