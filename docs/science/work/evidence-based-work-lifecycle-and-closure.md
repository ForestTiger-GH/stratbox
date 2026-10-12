# End-to-end work: execution, effects, evidence, acceptance and closure

**Scientific domain:** the difference between receiving a user's intention, accepting responsibility for a piece of work, running an algorithm, changing an external resource, publishing an artifact, validating its scientific claims, accepting the result and closing outstanding obligations. **Status:** a cross-theme explanatory model and proposed verification invariants, **not** an adopted Strategy Box ontology, scheduler, workflow engine, service layout or completed runtime test.

## 1. The central problem: a successful function return is not a completed assignment

Strategy Box already has valuable typed domain results, some source/provenance evidence, staged file operations, and a local Windows scenario/user history. The pinned [Windows scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) maps ordered steps through handlers into `OperationResult.ok`, Case states, events and artifact records. The [operation runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) is an execution boundary, but a boolean `ok` and `outputs=(path,)` do **not** establish remote-effect outcome, exact source provenance, file digest, publication permission, acceptance or Work closure.

[Windows `ArtifactRecord.from_path`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/artifacts/models.py) primarily makes local path-derived metadata; it does not prove bytes were flushed, independently validated or published under a shared authorization. The [five-file JSON history](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) is not an atomic life-cycle record; its error handling can make malformed input look empty. The Qt coordinator still has one active Case and no certified persistent JobManager.

Core, conversely, has specialized high-quality evidence for some banking/statistical tasks—e.g. the SORS distinction between official data and calculated/selected values. Exporting an evidence-qualified result as an Excel workbook cannot strengthen its underlying epistemic tier. The missing common layer is **cross-boundary accountability**, not a reason to replace all specialized domain models.

The compact research principle is **durable accounting / disposable computation / safe effects / bounded acceptance**. This preserves the history of what was admitted and what changed, while allowing the Python worker itself to stop without automatic resumption. Long-lived workflow replay is a separate stronger guarantee.

## 2. Seven independently assessable truths

| Truth | Question | What does **not** establish it |
| --- | --- | --- |
| **Work** | What goal was entrusted, with what criteria, owner and unresolved obligations? | A click, a new chat card or a successful Job |
| **Execution** | Which Run/Job/Attempt was admitted, started, stopped and observed? | UI progress without an executor receipt |
| **Effect** | Which external file/network/destructive action occurred, partially occurred or remains unknown? | No exception or a timed-out response |
| **Analytical result** | Which values and claims are supported by source/method/evidence under which limits? | A syntactically readable workbook |
| **Artifact** | Which bytes/generation were verified, published and are currently accessible? | An output path or catalog entry alone |
| **Assessment/acceptance** | Which result was checked against which criteria and accepted by whom? | A green execution status or merely opening a file |
| **Environment** | Was the required process/Node/storage/network operating under its declared capability? | A statement about economic correctness or task closure |

These axes can coexist in one physical record for a simple task. They should remain conceptually distinguishable so consumers can ask different questions and assign different permissions. A single giant status enum combining all seven creates combinatorial ambiguity; seven mandatory SQL services would be equally excessive.

## 3. Definition, request, work, run and attempts are not interchangeable

A useful *semantic* graph:

```text
Thread / messages ───── context and discussion ────────────────────┐
Intent / request → admissibility decision → Work (when justified)  │
                               │ criteria / accountable owner      │
Operation / Scenario / optional Scheme revision                     │
               └───────── resolved immutable plan                  │
                                    ↓                              │
                                Run → Job(s)                       │
                                        └→ OperationRun → Attempt(s)
                                                ├→ computed Result / Claim / Evidence
                                                └→ EffectIntent → physical action → Receipt
                                                               ↓
                                                       Materialization / Artifact
                                                               ↓
                                                     Assessment / Acceptance
                                                               ↓
                                                  Closure and residual obligations
                                                               ↓
                                               permission-scoped UI projections
```

An **Intent/WorkCandidate** can be rejected before admission. A **Work** is accountable objective and acceptance scope, if its lifetime exceeds a single run; a simple immediate Python calculation may have **no Work object at all**. A **Thread** is where people discuss the job; it may reference multiple Work and vice versa. The present Windows `Case` is closest to a local run card, not proof of a universal Work aggregate.

An **OperationDefinition** names a subject capability; a **ScenarioDefinition** is a curated user-selectable composition; a **Scheme** may be a typed machine representation of a plan; a **Cascade** may have its own user identity if it has independent reuse/lifecycle. No separate engine or database is justified merely because older studies used different nouns. An **ExecutionPlan** fixes resolved params, source/definition/method versions, output target/effects and authorized basis; it may be embedded in the Run rather than having an independent table.

One Work may have multiple Runs; one Run can contain one Job or multiple scheduling units only when independent resources/retries warrant them. One logical operation may have several Attempts. Each physical retry creates a **new Attempt identity**, preserving earlier outcomes. One attempt may create effects even when its final process status is failed. A domain result may create zero or several artifacts; an artifact may have several materializations/versions. Acceptance refers to a particular qualified result, criteria revision and decision, not the UI's global lifetime.

## 4. A family of state machines with guarded transitions

The following are illustrative named states, not accepted enums:

| Track | Important transitions | Evidence and authority guard |
| --- | --- | --- |
| Intent/admission | Proposed → Admitted / Rejected / Needs clarification | Authenticated source and scope, permission, idempotency, accepted criteria |
| Work | Open → Active / Blocked / Review → Accepted / Rejected / Terminated / Closed with residue | Work owner, assessment and unresolved obligations |
| Run | Requested → Admitted → Planned → Executing → Awaiting effect/assessment → Disposed | Frozen effective plan, accepted snapshot and effect status |
| Job | Queued → Claimed → Running → Finishing → Terminal | Worker resource claim, start/finish receipts, lease/fence where relevant |
| OperationRun | Pending → Dispatched → Executing → Result reported / Outcome uncertain | Operation revision and actual Attempt lineage |
| Attempt | Created → Start requested → Start confirmed → Stop requested? → Ended/Lost | Distinguish sender intent from worker observation |
| Effect | Intended → Authorized → Attempted → Confirmed / Definitely not applied / Partial / Unknown → Reconciled | Target/precondition, provider receipt or sufficiently strong postcondition |
| Artifact | Proposed → Staging → Bytes written → Verified → Publish pending → Published / Aborted / Unknown | Correct bytes/digest plus validated catalog/access |
| Analytical claim | Produced → Checked / Qualified → Valid for scope / Invalid / Inconclusive / Stale | Publisher/snapshot/method and domain-specific validation |
| Assessment | Pending → Pass / Fail / Inconclusive / Authorized waiver | Criteria revision, evaluator, evidence |
| Acceptance | Pending → Accepted / Rejected / Conditional | Authorized recipient/policy and exact result |
| Closure | Open → Proposed → Closed / Closed with residue / Terminated with residue / Reopened | Explicit disposition with obligations and responsible owner |
| Platform environment | Ready / Degraded / Unavailable / Unknown | Separate external platform health owner |

**Admission ≠ start.** A submitted request may be only a message; admission means the authority has accepted responsibility to process/reject under the declared persistence profile. A claimed Job may not yet have entered the handler; loss of start acknowledgement may require `start_uncertain`.

**Cancel requested ≠ cancelled.** The worker may have already committed a file. Cooperative stop can prevent future stages but cannot undo past effects. Force-killing a process is not rollback. A cancelled *attempt* does not imply no external effect; the effect track remains independently assessed.

**Timeout ≠ failure of effect.** It may be a known computational failure, or the effect may have succeeded while its acknowledgement was lost. `UNKNOWN` is a meaningful safety state until reconciled, not an ugly exception to remove for UI simplicity.

**Partial ≠ warning.** A domain may collect 8 of 10 official sources, with real output coverage and known omissions. A warning might instead be informative and not reduce required coverage. A domain-qualified result must preserve the actual missing inputs/assumptions rather than converting everything to a boolean success.

**Criteria change over time.** A Work/plan/assessment uses the criteria revision it accepted. A later change creates a new decision/context; it does not rewrite old attempts as though they had met future requirements.

## 5. Eighteen proposed invariants and their conditions

These are *candidate conformance criteria for an activated managed profile*, not requirements already implemented:

1. One logical writer accepts authoritative Work/Run transitions per scope.
2. A potentially external effect has a durable intent before the boundary **or is explicitly unmanaged**, with a weaker guarantee.
3. Submitted/admitted/started/cancel-requested/stopped are distinct.
4. Attempt IDs are never reused after a physical retry or worker takeover.
5. `UNKNOWN` persists until authorized evidence establishes the effect outcome.
6. Current action/resource/effect permission is checked immediately before risky effect.
7. Repeated requests cannot silently duplicate unacceptable effects; use scoped idempotency or inspect-before-retry.
8. Resource lock, worker lease and publication fencing are different; stale workers cannot publish.
9. Computation, effect, artifact, assurance, acceptance and Work closure each require separate grounds.
10. Managed publication requires verified bytes and a visible authorized record, not `Path.exists`.
11. A failed catalog commit must not automatically destroy the sole recoverable verified candidate.
12. Closure follows criteria, competent authority and explicit residual obligations.
13. Viewer-safe projections are narrower than physical operation logs.
14. New reconciliation evidence adds a current disposition without erasing historical timeout/failure observations.
15. Lost projections can be rebuilt; corrupt history must not become an invented empty authoritative history.
16. Statistical claims preserve exact source/registry/method identity, units and uncertainty qualification.
17. A trivial pure calculation must not be forced into universal approvals/evidence service topology.
18. A backend with weaker confirmed guarantees either lowers the promise or prevents the corresponding effect.

The proof burden scales with risk. A pure DataFrame calculation might need pinned inputs and typed result, whereas deleting the sole copy of a directory merits immutable target-set review, current rights and a verifiable effect plan. AppDock process health does not satisfy the latter.

## 6. An effect taxonomy and safe retry boundaries

| Class | Example | Retry/replay conditions |
| --- | --- | --- |
| **PURE** | Parse/normalize/statistical transform on immutable data | Reusable when inputs/method/params and assumptions match |
| **READ_EXTERNAL** | Fetch a publication, list a workspace | Retry subject to freshness, quota, access, changing source versions |
| **WRITE_STAGED** | Build temporary XLSX bytes | Retry with a new staging identity; isolate partial output |
| **PUBLISH_IDEMPOTENT** | Commit an immutable result generation | Same effect key + digest, verify one visible generation |
| **MUTATE_REVERSIBLE** | Controlled rename/move with proven backend semantics | Check before/after and preconditions; compensation may still be needed |
| **DESTRUCTIVE / IRREVERSIBLE** | Directory removal, overwrite unique input, nonreversible external call | Never blindly retry; explicit target review/authorization and proof |
| **UNVERIFIABLE_EXTERNAL** | External endpoint with no operation lookup or dependable ack | After ambiguity, stop, record unknown and seek authorized manual reconciliation |

Do not confuse **ReplayRun** (new evaluation on specified basis), **RetryAttempt** (another physical try), **ResumeFromCheckpoint** (reuse validated partial work), **ReconcileEffect** (investigate outcome without new effect), **RebuildArtifact** (produce a replacement) and **ReassessResult** (reevaluate a claim without necessarily recomputing it). One user menu may contain them but the semantics are different.

A candidate effect boundary is: validate scope/plan → durable effect intent → attempt one action → collect provider-specific receipt → verify postcondition → append confirmed/partial/unknown disposition → advance only when guards allow. If the provider lacks CAS/fencing and multiple writers cannot be safely excluded, restrict the deployment to a single physical writer instead of pretending distributed safety.

**Negative evidence has preconditions.** Absence of a file proves nonapplication only if the correct namespace/version was queried with adequate permissions, a reachable backend and sufficient consistency/propagation guarantees. `listdir` failure, stale replica view or access denial cannot be treated as an empty directory. Compensation adds a new corrective effect; it does not make the original disappear. Rollback only applies within a real transaction; repair, reconcile and retry are distinct.

## 7. Atomicity and recovery stop at real boundaries

Different claims need different mechanisms:

| Boundary | What can be true | What remains outside |
| --- | --- | --- |
| Python return/exception | In-process computation or fault observation | Durability, external effect truth |
| Validated append or atomic state-file replace | One bounded journal record/snapshot consistency on a tested filesystem | External file and remote backend transaction |
| Local same-filesystem rename | Atomic visibility under concrete backend guarantees | Universal power-loss durability and network share semantics |
| Transactional database | Coherent state records inside that DB | Physical XLSX bytes and third-party APIs |
| Verified storage publication | Object/path generation according to provider receipt | User acceptance and semantic calculation validity |
| Multi-file output | Staging + manifest/barrier/verified generation | Magical atomicity of unrelated files |
| External platform status projection | Platform process/Node/session facts | Product Work/Run/effect state |

A sensible **logical** persistence spine records admitted request/pinned plan, principal/correlation, Attempts, effect intents and receipts, artifact publication references, terminal outcomes, assessment/closure and residual obligations. High-frequency progress ticks can be evicted. Journal/snapshot integrity requires schema, sequence, checksum/framing, one writer, a clear durable acknowledgement boundary and explicit corruption handling. Even a successful fsync-like call requires checking the target OS/filesystem/storage profile.

A crash does not require automatic continuation of a Python stack frame. After recovery, distinguish interrupted execution, unknown effect and confirmed completed work. One-time legacy history import should mark old path-derived Artifacts as **legacy unverified**, rather than upgrading them silently into verified publications. Backup existence without demonstrated restore is weaker than recovery proof.

For stronger storage reasoning see [authority/durability](../state-and-recovery/authority-durability-and-recovery.md); for publication see [artifact identity](../artifacts/output-identity-publication-and-availability.md).

## 8. Five different claims at result handoff

A user who receives an XLSX may actually need to establish:

1. **The operation ran:** Run/Attempt identity, worker start/end evidence and pinned params/version.
2. **An effect occurred:** an authoritative receipt and sufficiently strong verified postcondition.
3. **The analytic result is valid for a declared purpose:** domain schema, source versions, units, method, assumptions, proof/calibration and error bounds.
4. **An artifact is materially available:** verified content digest/size/generation, publication commit, visibility/access checks.
5. **The Work is complete:** authorized assessment against pinned acceptance criteria and recorded residual obligations.

Evidence is a **relation** among claim, source, check, scope and uncertainty. A file called `evidence.json` is not automatically strong evidence. Different records have different strength: a domain proof ledger can support a bounded statistical inference; an effect receipt supports a provider action; a state transition event supports the fact that the authority recorded a transition; sampled progress and technical log lines are useful diagnostic observations; an acceptance record proves a human/policy decision, not universal truth.

An illustrative compact `WorkResultAssessment` may include exact subject (Run/result/artifact generation), criteria revision, observed computation/effect/artifact/coverage outcomes, evidence refs, authorized assessor, decision (accepted/rejected/conditional/inconclusive), limitations and owned residual obligations. It may be embedded within Work, not an extra service.

**Approval is not acceptance.** Approval authorizes a future risky action on a particular plan revision. Acceptance assesses the *actual produced result* and the current criteria. Automated acceptance is conceivable if explicit measurable criteria and policy authority have been approved. Work can legitimately end with a disproved hypothesis, insufficient evidence or justified refusal when those outcomes satisfy the original commissioned question.

## 9. Closure is a governed decision, not a terminal process event

Candidate dispositions:
- **CLOSED_ACCEPTED:** required result is accepted and obligations have been discharged.
- **CLOSED_WITH_RESIDUE:** bounded result accepted with explicit remaining obligations transferred to an owner.
- **TERMINATED:** work is intentionally ended without the requested result.
- **BLOCKED / OPEN_RECONCILIATION:** critical unknown effects or unassessed results prohibit closure.
- **REOPENED:** new requirement, discovered defect or evidence supersedes a prior decision while preserving its history.

The key product question is whether **unknown effect** can coexist with `CLOSED_WITH_RESIDUE`: for dangerous shared effects this should normally block closure, while a low-risk explicitly assigned follow-up might permit a qualified closure. The threshold depends on risk policy and acceptance scope, which are not yet decided.

A later confirmed receipt may upgrade the present effect disposition from unknown to confirmed. It should **not** erase the historical fact that the earlier attempt timed out. Reassessment or Reopen can be an additional event rather than retroactive falsification.

## 10. Concrete failure cases that the model must preserve

The source study records 24 fault locations; they collapse into six distinct families *without erasing source nuances*:

| Fault family and cases | Safe interpretation / repair |
| --- | --- |
| **Admission/start F01–F03:** process dies before admission; admitted but not started; worker start ACK lost | Separate submitted/admitted/start confirmed, redispatch only with correct identity and evidence |
| **Pure and partial inputs F04–F05:** parse failure or 8/10 sources received | New safe Attempt under pinned basis; retained partial coverage and hashes |
| **Uncertain remote effects F06, F09, F12, F14:** lost API ACK, publish ACK, destructive partial directory action, cancellation after effect | `UNKNOWN/PARTIAL`, effect lookup and manual policy, never silent replay |
| **Artifact windows F07–F11, F13:** incomplete staging, verified bytes before publish, catalog gap, UI gap, stale worker overwrites newer generation | Quarantine/verify/manifest reconcile, authorized version pointer and fencing |
| **State/lifetime F15–F18:** GUI close, host disconnect, corrupt JSON, no disk for effect intent | Real foreground/host distinction; reject risky action without durable precondition; no empty reset |
| **Changing basis/authority F19–F24:** changed official sources, classifier, weak SORS tier, platform degraded, permissions revoked, late receipt | Pin exact data/method/criteria, reauthorize, preserve domain evidence and historical status |

A high-value destructive directory test is: scan → immutable target list → approval bound to plan digest → revalidate live scope → copy/stage candidates where relevant → verify total target set → publish/commit → delete only with explicit per-target receipts. This makes partial execution inspectable and prevents an exception from being misconstrued as “nothing happened.”

A concrete banking report slice: one host/local Run takes official monthly source snapshots; one source is unavailable, so the domain result is qualified partial; a workbook is assembled in staging and verified; a publish ACK is lost, so the artifact cannot yet be called published; the effect is reconciled; an assessor checks the original completeness criteria, possibly rejects the partial result; Work remains open with an assigned missing-source obligation. At no stage does an apparently successful Python step automatically decide Work closure.

## 11. Falsifiable invariants and tested versus untested boundaries

Thirty candidate probes cover direct Python execution, a complete staged export, multiple Runs within one Work, duplicate submit, conflicting retry payload, lost start ACK, cancellation before/after effects, safe recomputation, staged/catalog crash, corrupt snapshot/journal, stale worker fencing, permission revocation, damaged source snapshot, SORS claim strength, declined user acceptance, missing required output, remote client detach, agent/automation policies, reopening and real backup restore.

Some particularly discriminatory invalid states:
- `Run.SUCCEEDED` plus mandatory `Effect.UNKNOWN` with no qualification.
- `Artifact.PUBLISHED` while verified bytes are missing or the pinned digest differs.
- `Work.CLOSED_ACCEPTED` when only an execution *plan* was accepted.
- `Attempt.CANCELLED` based only on button press.
- `Job.FAILED` reinterpreted as “remote effect definitely not applied” after timeout.
- A client viewing another participant's private traceback without authorization.
- A stale worker publishing an old generation after another worker took over.
- A re-run silently using new source bytes with the old snapshot identifier.
- Corrupt history resetting real accepted obligations to “there were no jobs.”

The source explicitly states **no full GUI test, installed platform E2E, genuine lost-ACK experiment, power-loss fault injection, verified artifact publication or independent user acceptance was executed**. A “planned test vector” is not a passed test. Proven readiness requires exact effect/property evidence on the chosen supported local/host platform.

## 12. Proportionality, methodology transfer and open decisions

The formal modeling of Work, object identity and claim evidence is aligned in the source study with distinct methodological classes: durable work semantics, reproducibility, actor/authority, evidence strength and proportional assurance. These are **instruments for questioning Strategy Box**, not ready-made product tables or acceptance rules. The cited external MADAR `spec/` was an Editor's Draft; Stage 3 A/B papers were nonnormative research. Product Engineering cannot silently adopt every methodological entity merely because a cross-project research analogy is persuasive.

The source identifies **20 unapproved Product Decisions**, notably: mandatory Work identity for one-off runs; physical application authority; file journal vs transactional store; GUI-close behavior; headline UI statuses; cancellation semantics; retry defaults; artifact generation/bundle strategy; manual/automatic acceptance; authority to close with residue; Job granularity; core/method versioning; shared artifact index; team notices; evidence/log retention; machine/automation permissions; offline client writes; legacy history import; resource budgets; exact external platform contract.

Eight further inquiry areas remain empirical: smallest user-facing Work, strong proof of negative effect on different storage backends, publication barrier for multi-file outputs, right to accept/close, safe migration of old path-based history, actual shared-node integration, domain-specific acceptance risk profiles and cost/usability of the proposed model.

**Preferred research route, not an engineering order:** specify one pure and one file-producing vertical case; establish precise scope/criteria/permission and idempotency; test staging, digest, lost ACK and recovery; build a minimal Qt-free runner with a single writer; test user acceptance and residue; expand to host only after explicit need. The first actual proof of completeness is whether, after interruption, the product can still answer *what was entrusted; what started; what may have changed outside; what is confirmed; what files remain safe; and which human action is still outstanding*.

**Negative conclusion:** a single Work/Run/Job/OperationResult `status` and filesystem path cannot represent this level of accountability. Conversely the scientific distinction of these truths does **not** justify a service, database table and queue for each named concept.

## 13. Thirty original end-to-end failure and recovery probes from Topic 12

The frozen Topic 12 original, §13 (`#L610-L645`) proposes **thirty distinct system-level tests**. Each row below preserves a dated original identifier, an English rendering of its setup and the claim to be falsified. **These are research proposals, not passed conformance tests, not Product decisions, and not proof that a durable hosted Work engine exists.** Local direct-Python operations, a trusted desktop team and an authenticated hosted multiuser product have different relevant subsets and actual guarantees.

| Source identity / problem | Fault injection or user action | Qualified expected outcome | Frozen research line |
| --- | --- | --- | --- |
| `SB-SRC-0564/T01` — **Standalone pure parse** | Invoke Python core with no GUI or platform and a typed parse request. | Return qualified Result/Failure with provenance; no artificial Job or Chat dependency. | L616 (`#L616`) |
| `SB-SRC-0564/T02` — **Complete Windows workbook path** | Admit a user command, compute a domain result, write bytes, validate/publish and assess. | Prove each transition separately; a successful handler alone is not published or accepted Work. | L617 (`#L617`) |
| `SB-SRC-0564/T03` — **One Work, two sequential Runs** | Retry/revise execution for the same accepted goal. | Preserve Work objective and two distinct Run/revision/outcome identities. | L618 (`#L618`) |
| `SB-SRC-0564/T04` — **Double-click duplicate submit** | Send the exact same admission key and plan digest twice. | Deduplicate accepted admission under its defined scope; prevent duplicate effect. | L619 (`#L619`) |
| `SB-SRC-0564/T05` — **Reused key with changed parameters** | Submit different parameters using an existing idempotency key. | Reject as a conflict before physical execution. | L620 (`#L620`) |
| `SB-SRC-0564/T06` — **Crash before worker begins** | Commit admission then kill process before an Attempt starts. | Preserve accepted Work/Run without inventing worker-start evidence. | L621 (`#L621`) |
| `SB-SRC-0564/T07` — **Cancel safely before effect** | Request and confirm a stop before any external mutation. | Record stopped Attempt and effect definitely not applied only with supporting evidence. | L622 (`#L622`) |
| `SB-SRC-0564/T08` — **Cancel during remote publish** | Request cancellation during an in-flight externally committed write. | Keep cancellation requested and effect UNKNOWN/confirmed as observed; do not fabricate cancelled outcome. | L623 (`#L623`) |
| `SB-SRC-0564/T09` — **Pure compute worker interrupted** | A worker dies during effect-free mathematical calculation. | Record interruption, leave Work open and admit a new Attempt only by applicable policy. | L624 (`#L624`) |
| `SB-SRC-0564/T10` — **Lost acknowledgment after publication** | Remote output commit succeeds but ACK is lost. | Reconcile effect state using stable identity; never blindly repeat an ambiguous write. | L625 (`#L625`) |
| `SB-SRC-0564/T11` — **Partial multi-file export** | Some outputs are written while others fail. | Do not claim a completed collection; qualify partial publication under explicit bundle policy. | L626 (`#L626`) |
| `SB-SRC-0564/T12` — **Crash between file bytes and catalog** | Output bytes reach storage but catalog transaction is incomplete. | Recover or quarantine and never issue a false published Artifact receipt. | L627 (`#L627`) |
| `SB-SRC-0564/T13` — **Corrupted authoritative snapshot** | Read a damaged state snapshot on restart. | Replay verifiable journal if available or report explicit corruption; no silently blank new history. | L628 (`#L628`) |
| `SB-SRC-0564/T14` — **Corrupted journal tail** | Detect invalid event sequence at the end of a durable log. | Stop at verified prefix and flag potentially affected effects UNKNOWN. | L629 (`#L629`) |
| `SB-SRC-0564/T15` — **Concurrent artifact generation writers** | Two workers attempt committing the same generation. | One accepted write; the other conflicts or is serialized with revisions/fencing. | L630 (`#L630`) |
| `SB-SRC-0564/T16` — **Stale worker after takeover** | Worker A resumes after its lease was replaced by B. | Reject A's stale publication through fencing or generation-version proof in multiworker profile. | L631 (`#L631`) |
| `SB-SRC-0564/T17` — **Revoked delete permission** | Plan deletion, revoke authorization, then run the plan. | Re-evaluate permission immediately before effect; no deletion proceeds on stale grant. | L632 (`#L632`) |
| `SB-SRC-0564/T18` — **Invalid data root at startup** | The platform data root is absent or read-only. | Expose degraded diagnostics; refuse effectful Job without losing accepted state. | L633 (`#L633`) |
| `SB-SRC-0564/T19` — **Platform health changes mid-run** | External environment reports degraded health during domain computation. | Keep platform Problem separate from domain Job state; do not overwrite analytical result. | L634 (`#L634`) |
| `SB-SRC-0564/T20` — **Cross-user unauthorized Case read** | Principal A requests private Case of principal B. | Filter or deny according to actual ACL, including sensitive diagnostic logs. | L635 (`#L635`) |
| `SB-SRC-0564/T21` — **404 and timeout source input** | An external data source fails to respond or reports HTTP 404. | Distinguish unavailable/fetch-failed from publisher-confirmed absence of an official series. | L636 (`#L636`) |
| `SB-SRC-0564/T22` — **Input publication revised after Run** | Source bytes change after an issued analytical result. | Retain prior vintage and derived result, update currentness/reliance separately. | L637 (`#L637`) |
| `SB-SRC-0564/T23` — **SORS weak-tier export** | Publish a reconstructed statistical result relying on non-unique inference. | Preserve evidence tier, bounds and assumptions even when output workbook is valid. | L638 (`#L638`) |
| `SB-SRC-0564/T24` — **Valid calculation, rejected by user** | The method runs correctly but a reviewer rejects its result. | Execution may succeed while acceptance fails; Work remains open under stated criteria. | L639 (`#L639`) |
| `SB-SRC-0564/T25` — **Invalid output workbook digest** | A written Artifact fails a checksum or validation rule. | Quarantine or reject publication; preserve any previously valid generation. | L640 (`#L640`) |
| `SB-SRC-0564/T26` — **Successful Job lacks required file** | Worker reports SUCCESS but a required result file is missing. | Qualify Job/Artifact outcome, require review; do not auto-close parent Work. | L641 (`#L641`) |
| `SB-SRC-0564/T27` — **Windows disconnects from hosted Run** | An admitted host continues while its Windows UI disconnects. | Reconnect to actual host authority and show verified Run progress; no fake local resume. | L642 (`#L642`) |
| `SB-SRC-0564/T28` — **Scheduled or agent-initiated execution** | Trigger a command through schedule or AI rather than UI. | Apply the same effect/authorization/admission policy, with no implicit privilege elevation. | L643 (`#L643`) |
| `SB-SRC-0564/T29` — **Requirements change after closure** | Modify success criteria after an earlier Work was accepted. | Create an auditable successor/revision and preserve prior closure; never rewrite past approval. | L644 (`#L644`) |
| `SB-SRC-0564/T30` — **Backup recovery rehearsal** | Restore archived state and check its operational meaning. | Verify coherent Work, effects and artifact catalog, not just the existence of copied files. | L645 (`#L645`) |

### How to evaluate, without inflating runtime obligations

A test may legitimately be **NOT APPLICABLE** to a direct, pure Python computation without a shared Job manager. A real hosted, effect-bearing command must instead supply observation of admission, authorization, Attempt ownership, external effect receipt and publication outcomes. CI source-table traceability establishes only that these *test intentions* have not been lost; the experimental status remains **NOT EXECUTED**. Independence and actual scenario/fixture coverage require a separate reviewer, genuine fault injection and versioned source/environment inputs. This table does not require a dedicated repository or one physical microservice per truth axis.
