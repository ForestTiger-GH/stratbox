# Bounded delegation, peer Work and causal reconciliation

**Scientific question:** when one actor or Node asks another to perform analytical Work, how can Strategy Box preserve the original purpose, authority, source and evidence boundaries while permitting useful parallelism and avoiding shared mutable cognition, duplicate effects and false consensus? **Status:** independently readable research synthesis of the frozen [host-cognition foundation original](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_foundation_research_2026-10-07.md) and [multi-Work interaction original](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md), with conceptual analogies from interoperable agent-task and durable workflow systems. **No actual federation, model adapter, remote peer service or sharing protocol is certified for today's Strategy Box.**

## 1. Delegation exchanges bounded obligations, not shared consciousness

One participant may know a source the requester cannot reach, have specialist experience, own a larger compute resource or be assigned an independent verification. That can justify handing off a bounded question or action. It does **not** justify copying an entire personal agent memory, unrestricted workspace, credentials or unbounded conversation into a shared pool.

A delegated offer should therefore state *what result is requested* and enough permitted context, while preserving the responsible owner:

```text
Originating Work + source/plan revision
  → bounded Work Offer (purpose, material scope, inputs, limits, evidence, expiry)
  → recipient's explicit accept/reject/counterproposal under own grants
  → distinct peer Work identity and local execution
  → candidate Result + Artifact/Evidence references + actual effect receipts
  → originating owner reconciles, evaluates and accepts for intended use
```

“Peer accepted Work” means a commitment to an agreed task scope, not that its result has been established. A completion notice is a **delivery** and perhaps a local Job outcome, not necessarily upstream Work closure.

## 2. Identity classes and authority must not collapse

| Identity | Stable meaning | What it cannot establish |
| --- | --- | --- |
| Principal | Human/service security subject on an installation | Model persona, method quality, business acceptance |
| Actor | Accountable human/cognitive participant with a scoped identity | Automatically elevated access to another user's data |
| Cognitive Activation | One isolated solver/task execution, budget and transient scratch | New permanent actor or independently verified conclusion |
| Work/Child Work | Commissioned and delegated result obligation | A Job or transport-message delivery |
| Run/Job/Attempt | Product/adaptor execution and concrete physical try | Domain effect confirmation or decision authority |
| Peer/transport message | Source-addressed payload, causation/correlation and delivery | Consent to the enclosed action or source-evidence independence |
| Artifact/Evidence reference | Qualified materialized output/ground with ACL and version | Public availability or permission to rely for every claim |

A proposed peer transport can project internal Work onto protocol Task and Thread onto protocol Context, but the product cannot make a protocol field its canonical Work owner. Internal lifecycle/authorization can be stronger or more granular, and transports may change. An adapter is therefore an anti-corruption layer between protocol objects and Strategy Box's domain/work semantics.

A “one personal persistent actor, many activations” model reduces cross-principal memory confusion but is only a useful research candidate, not a mandate for one agent per user. Permanent independently delegated actors are warranted by distinct authority, memory lifecycle, accountability or external peer responsibility, not by parallel thread count.

## 3. Envelope: enough to do the task, not an entire workspace

A candidate **WorkOffer** can carry:
- stable offer and message IDs, `parent_work_id`, originating and recipient actor/principal context, dates, expiry and request revision;
- expected Result/acceptance criteria, uncertainty and scope/perimeter;
- needed exact authorized SourceSnapshot/ArtifactRefs and redacted parameters;
- permissions for disclosure, processing, publishing and effects;
- deadline, effort/resource/cost limits, safe cancellation and retry/unknown-effect rules;
- causal/correlation IDs for replay and diagnostic continuity.

The recipient's acceptance should bind the specific offer revision and disclose any changed conditions. If an underlying source is revised or access revoked before execution, new qualification/admission is required. A signed offer cannot extend a credential scope the sender never possessed.

Transfer minimal source subsets and hashes; for large files a permissioned reference or scoped materialization is safer than embedding bytes in every message. A receiver's personal draft remains private even when the parent Work has shared status. Full prompts and raw completions should not be logged by default due to privacy and exposure.

## 4. Same Work, different execution topologies

**Local fan-out for throughput.** One actor splits independent banks or periods among transient activations; it uses one Work owner, immutable task-local baselines and separate read/write/effect sets. Returned candidates reconcile against the originating Work revision, not a mutable shared notebook.

**Independent methodological challenge.** Two different actors/solvers examine one claim with deliberately different evidence, methods or assumptions. Merely spawning copies of the same model on the same underlying input makes failures correlated and does not create two independent witnesses.

**Specialist delegated Work.** A remote owner accepts a separate obligation, perhaps running its own local process. Parent and child have different permissions and completion semantics; parent reconciliation and evaluation remain necessary.

These are different topologies with different guarantees and costs. Parallel execution can actually be slower if transfer, shared locks and fan-in exceed saved computation, and more replicas can amplify one contaminated source.

## 5. Causality, deduplication and backpressure

Distributed messages can arrive twice, out of order, after expiration or after the caller has cancelled. A useful envelope carries `message_id`, `causation_id`, `correlation_id`, sender/recipient scope, contract version, parent/child Work references and an idempotency/effect key where appropriate. The product defines **deduplication scope and retention**: “same message received twice” is not necessarily “effect happened twice”, and an acknowledgment is not an effect receipt.

A delegated execution must be resource-bounded:
- maximum fan-out and delegation depth;
- per-peer active Work quota and request rate;
- maximum parallel children and generated artifacts;
- deadline/TTL and explicit expiry semantics;
- cancellation propagation only where safe;
- no uncontrolled auto-resubmission on unknown external effect;
- limiting or refusing recursive delegated offers.

These limits prevent feedback-loop job storms and resource starvation. A source watcher should not create a separate shared Thread for every unchanged polling tick, and a failed delegated branch should not automatically invalidate unaffected independent branches.

## 6. Shared state under partitions needs one current owner

During a network partition the remote recipient may continue strictly local authorized work. The originating Node must show its view as stale/unconfirmed rather than merge independent writes or assert a globally synchronized state. When connectivity returns, reconcile by exact Work/plan/source revisions, effect receipts, updated permissions and dependency lineage.

A peer may send a candidate table and a locally “successful” status while its source vintage no longer matches the parent. Reconciliation outcomes should distinguish:
`ACCEPT`, `ACCEPT_WITH_LIMITATIONS`, `REVALIDATE`, `COUNTERPROPOSE`, `REJECT`, `RECONCILE_EFFECT`, and `UNRESOLVED`.
These are **illustrative semantic classes**, not a new approved enum. Validating a candidate is distinct from **accepting** the parent's Result for a consequential use.

Fan-in is evidence reconciliation, not majority voting. An answer “3 peers favor increase, 2 decline” is a statement about peer outputs, not proof of the future of bank lending. Compare direct sources, method dependence, definition/perimeter, time vintage and actual computations.

## 7. Verification challenges

1. Duplicate the same remote WorkOffer under a retry after a lost ACK. No second unauthorized effect; match admitted identities and previous effect state.
2. Change the parent Work to revision 20 while a child works from revision 17. It cannot silently overwrite the updated Result.
3. Revoke personal artifact access during a share. The next download must honor current permission, not a cached chat membership.
4. Network partition after a remote destructive effect. Report `UNKNOWN` pending reconciliation instead of `FAILED` and blind retry.
5. Fork 20 identical model candidates based on one flawed source. Assert 20 outputs, **not 20 independent evidence sources**.
6. Exceed delegated depth or cost. Stop recursion with an explicit resource outcome, preserving remaining Work obligations.
7. Accept a task whose deadline has already expired or source schema is now incompatible. Requalify or reject instead of starting stale work.
8. Cancel the parent after a child starts. Track pending effect and callback/race outcome; cancellation request alone is not proof of termination.
9. Receive peer result with correct data but wrong bank/group perimeter. Require semantic bridge or reject for this parent claim.
10. Drop terminal peer message after an artifact was published. Reconcile actual artifact bytes, metadata and ACL without inventing a second generation.

The scientific conclusion is bounded: **federation can be valuable when independent ownership and specialized capabilities matter, but local correctness, authorization, effects and recovery must precede distributed scaling**. Detailed protocol schemas, multi-node conflict resolution, persistent cognitive memory, personal actor identities and release thresholds remain future Product Decisions.

Related maintained topics: [Thread/Work memory scopes](thread-work-memory-scopes-and-parallel-actors.md), [authorized streams](authorized-streams-read-cursors-and-private-work.md), [work admission and recovery](../work/admission-planning-resource-scheduling-and-recovery.md), [machine capability semantics](../capabilities/compiled-domain-capabilities-validity-and-deoptimization.md) and [artifact publication](../artifacts/output-identity-publication-and-availability.md).
