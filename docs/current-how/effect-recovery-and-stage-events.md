# Conditional effects, recovery and accepted-stage events

Canonical command execution uses one session effect authority. Physical writes
remain the receiving provider's responsibility: the built-in `store.commit`
command requires immutable create or atomic replacement against an expected
revision. Its identity includes the destination, payload and pinned source/input
revision. A provider must check the revision at the replacement boundary.

## Commit evidence and attempt authority

`Invocation.commit_effect` records an identified unknown effect before calling
the provider. A confirmed receipt permits reuse; a missing reply preserves an
addressable unknown outcome. Repeating the same resource/effect in another run
of the session consults the same physical evidence. An unknown outcome requires
reconciliation before another physical attempt.

The session registers each work attempt. Cancellation or supersession revokes
its authority to start a commit or promote its completion as current. A write
that already crossed the provider boundary can finish afterwards; the retained
receipt still describes that physical result. Actual worker occupancy lasts
until the worker returns. Provider CAS protects against stale replacements;
local attempt authority supplies precommit admission and current-result
qualification.

The session exposes `session.effects.lookup(run_id, scope_id, effect_id)` and
`lookup_effect(resource, effect_id)`. A host can inspect the pinned intent,
receipt, ledger revision and current qualification. After competent provider
read-back, `reconcile(..., expected_revision=record.revision)` accepts an exact
confirmed or failed receipt. Reconciliation checks the effect kind, identity and
ledger revision. Finishing a physical attempt releases its attempt token.
Closing `RunResult` releases that result's effect pins. Known unowned receipts
move to bounded history; unknown effects retain independent recovery ownership.
Reconciliation after the result closes can resolve and reclaim that obligation.
`retain_run(run_id, owner)` and `release_owner(owner)` cover an independent
cache/host owner that needs a receipt beyond the original result lifetime.
`retention_snapshot()` reports live records, history, attempts, runs, unresolved
effects and owner pins.

Computation and saving have separate command results. A failed save can be
prepared again from a retained representation. Extraction and calculation remain
available through their accepted values and do not need to run again.

## Explicit source revision policy

Destination CAS and source freshness have separate contracts. Opaque source
edition strings are compared for equality only. Run submission order and edition
spelling establish no source ordering.

A revisioned publication requires a registered `PublicationRevisionPolicy` for
its receiving resource. The built-in `ExactCurrentRevisionPolicy` admits exactly
one source revision and pinned input basis, selected by their domain/host owner:

```python
from stratbox.core.execution.effects import ExactCurrentRevisionPolicy
from stratbox.core.storage.staging import storage_scope

resource = storage_scope(store, "current.csv") + ":current.csv"
policy = ExactCurrentRevisionPolicy(
    "official.editions", source_revision="edition-Q", input_basis="basis-current"
)
box.session.effects.register_revision_policy(resource, policy)
```

A later invocation carrying another edition cannot replace the product even
with a valid current storage revision. The policy guards source admission and
the conditional provider callback together. The source owner advances the
admitted pair with `admit_current(..., expected_revision=policy.revision)` after
resolving edition semantics. A custom policy can supply a different explicit
rule under the same atomic admission contract. Source admission also applies to
reuse of an earlier confirmed receipt.

## Host replay contracts

`stratbox.core.execution.recovery` defines separate state, artifact and effect
ports. A `RecoveryCheckpoint` pins the plan and input basis, accepted artifact
identities, roles, qualifications and effect records. `inspect_replay` verifies
artifact bytes and consults competent effect evidence. It reports reusable
outputs and unresolved effects without computing values or performing writes.
Changing the input basis rejects reuse of that checkpoint.

`check_state_conformance` exercises create, read-back, compare-and-swap and stale
revision rejection in a caller-owned test namespace. This verifies the state
port's observed atomic behavior. A durable host supplies persistence and its
crash-recovery evidence. The library's in-process session and journals preserve
local execution guarantees for their documented lifetime.

## Accepted values and destination receipts

The orchestration journal exposes two independent sources:

| Source | Retained evidence | Notification topics |
| --- | --- | --- |
| `journal.stream` / `journal.source` | Terminal run transitions | `run.completed`, `run.failed` |
| `journal.facts_stream` / `journal.facts_source` | Accepted named values and confirmed physical receipts | `value.accepted`, `effect.confirmed` |

Accepted stage facts are emitted after semantic scope acceptance, including
required checks and effects. A successful decoder alone does not establish a
successful extraction. Each accepted value records its role, content identity,
source, qualification, completeness and stable acceptance identity. Independent
A→B→A acceptances remain three transitions.

Confirmed effect facts carry their exact effect ID, kind, identity and receiving
guarantee. Destination references are projected as digests. Unknown or failed
receipts cannot become confirmed-effect facts. Notification handoff receipts
produce no recursive notification triggers.

Bind `journal.facts_source` as a `SourceBinding` with authority
`execution.acceptance`, then configure a subscription for `value.accepted` or
`effect.confirmed`. Value subscriptions support stage, role, source,
qualification and completeness filters. Effect subscriptions support kind,
destination digest, guarantee and stage filters. Each subscriber retains its own
checkpoint, revision and replay policy through the existing notification state
port.

Preparing an intent, accepting a handoff and observing channel delivery remain
separate steps. Preparation neither sends a message nor advances another
subscriber's cursor. An unknown handoff uses receipt reconciliation instead of a
second handoff. Explicit replay and backfill retain their subscription policies.

A graph can call `notify.saved` with the actual receipt from `save.product`
and include that call in its `required_effects`. Preparation selects the exact
retained confirmed-effect ID and content identity. `notify.accepted` selects the
current run's accepted facts and can follow a producing scope through an explicit
`depends_on` edge. A previous unrelated fact cannot satisfy a new required
handoff. `source_run_id` explicitly selects a retained earlier run when needed.
Both operations prepare persisted intents and execute `notification.handoff`
through the same session and invocation infrastructure. Their `key` parameter
selects the configured subscription checkpoint. An unknown required handoff keeps accepted
computation and save outputs available. `notify.reconcile` consults the existing
attempt receipt without a second send. Consumer acceptance and external channel
delivery retain separate evidence.

Notification dispatch scanning uses a bounded window controlled by
`max_dispatches` and `after_position`. The independent `prepared` output carries
`next_position` for explicit continuation. A strict required handoff with no
matching intent fails visibly instead of claiming delivery. Intent and
checkpoint transactions remain in their existing notification state store.

## Bounded observation and execution control

Diagnostic records and optional observer callbacks use bounded buffers.
Cancellation and worker completion use the coordinator's separate control path.
A saturated progress buffer cannot consume a worker-completion signal. Optional
observer failure affects observation health while accepted business results
remain available.

Terminal transitions and accepted facts use reserved local retention, separate
from diagnostic eviction. The owner acknowledges evidence only after all
interested consumers finish. Publication failures remain visible in journal
health and pending transitions can be retried with their original identities.
Physical-work and logical-use counters are distinct; an expanding graph reports
an open denominator until membership closes.
