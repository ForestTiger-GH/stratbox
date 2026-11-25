# Journal subscriptions for capability results

Subscriptions select retained journal records for commands, operations, scenarios
and cascades. Named output acceptance, capability completion and confirmed storage
are separate events. Notification preparation reads that journal, commits immutable
intents and hands them to the configured consumer through the shared notification
runtime.

## 1. Select the event and its exact coordinates

| Topic | Journal record | Meaning |
| --- | --- | --- |
| `value.accepted` | `value.accepted`, data version 2 | One accepted named output at any capability level, including technical outputs with no data role. |
| `capability.completed` | `capability.finished`, data version 1 | The terminal outcome of one command, operation, scenario or cascade. |
| `effect.confirmed` | `effect.confirmed`, data version 2 | A confirmed external effect receipt, independent of computation acceptance. |
| `run.completed` | `run.finished` | Completion of the complete submitted run, from the run journal stream. |

`CapabilitySelector` compares the supplied coordinates exactly. Omitted coordinates
place no restriction; a specified coordinate missing from a journal record fails
the match. Scope paths preserve individual occurrences of reused capabilities.

```python
from stratbox.core.notifications import CapabilitySelector, SubscriptionSpec

accepted = CapabilitySelector(
    capability_id="extract.observations",
    capability_kind="operation",
    scope_id="monthly/extract",
    output_name="observations",
)

spec = SubscriptionSpec(
    scope_id=stream.scope_id,
    subscription_id="monthly-extract",
    owner_id="owner",
    streams=(stream,),
    route=route,
    topic_id="value.accepted",
    topic_version=1,
    projection_id="accepted_value",
    projection_version=1,
    selector=accepted,
)
```

Use `journal.facts_stream` and `journal.facts_source` for accepted outputs,
capability completion and confirmed effects. Configure and enable the subscription
with the existing `configure_subscription` transaction. Enabling fixes an activation
cut; historical replay uses its explicit replay contract.

For a capability completion subscription, select `capability.completed` and the
`capability_summary` projection. Supply `capability_id`, `capability_kind` or an
exact `scope_id`; `output_name` applies to named output acceptance. This works for
all four kinds through the same journal and subscription implementation.

## 2. Fulfil a complete handoff obligation

| Capability | Obligation |
| --- | --- |
| `notify.required` | Complete selected dispatch set for the configured journal topic. |
| `notify.accepted` | Accepted-output topic only: `value.accepted`. |
| `notify.saved` | Confirmed-effect topic only, matching the supplied exact storage receipt. |
| `notify.reconcile` | Lookup and qualify unresolved handoffs without blindly sending them again. |

```python
result = box.run(box.prepare("monthly.analysis", inputs=inputs))
notified = box.invoke(
    "notify.required",
    parameters={
        "key": checkpoint_key,
        "source_run_id": result.run_id,
        "max_dispatches": 128,
    },
)
```

An accepted-output obligation can follow its producer inside a prepared graph.
A capability-completion subscription observes the corresponding terminal journal
record after that capability finishes. A root capability's own completion is
consumed after its run; its internal steps cannot wait for their enclosing
capability to have already completed.

Required preparation freezes a source head, catches the checkpoint up to that
head, scans every relevant dispatch page and returns a complete immutable dispatch
ID set. `max_dispatches` controls page size. `max_pages` bounds source preparation,
`max_scan_pages` bounds retained-history scanning, and `max_selected_dispatches`
bounds the selected set. Exhausting a bound fails the obligation before any
consumer handoff; a prefix never counts as successful delivery. Completed required
batches have `complete=True` and `next_position=None`.

A caller can instead provide exact `dispatch_ids`. Every requested identity must
exist and meet the other explicit criteria. `source_run_id`, an optional request
`selector`, the subscription selector and an exact saved receipt intersect. An
explicit saved receipt identifies its original producing run when no run filter
was supplied.

The lower-level inspection and state-scan APIs retain explicit pagination for
history browsing. Required operations always select from the beginning; their
contract does not ask the caller to advance `after_position` manually.

## 3. Preserve evidence through acknowledgement and recovery

Each prepared intent pins its verified event identity and minimal selection
coordinates. Completed unrelated dispatches use their own saved evidence during
history selection, so releasing their old source records cannot block a new
notification. Pending first handoff still rechecks the current subscription,
authority, source evidence and bound recipient.

A lost consumer reply leaves an addressable unknown attempt. Reconciliation looks
up that exact attempt and qualifies its saved receipt; accepted attempts are
idempotent and cause no second send. Consumer acceptance and external channel
delivery retain separate evidence.

A competent external producer can journal an accepted occurrence whose content
identity is unavailable. That record states `identity_status="unavailable"` and
carries no content hash; subscriptions select its logical occurrence without
claiming content equality. Canonical core managed values retain their own
requirement for a supported canonical identity: arbitrary Python handles are not
admitted simply because the journal can describe an external occurrence.
Technical output roles may be `None`; supported roleless outputs remain eligible
for accepted-output subscriptions.
