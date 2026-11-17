# Use qualified notification subscriptions

The Python API is available in `stratbox.notifications`. It works with a closed in-process collector or with a registered resumable source, transactional state and durable consumer selected by the host. The offline example exercises a real acquisition, save, parse, journal snapshot and in-process handoff.

## Choose the source and the topic

Use `RecordMemorySink` with ordinary execution calls for local capture. When the collector is finalized, bind a `SnapshotJournalSource` to its stream and epoch. For archive-backed use, pass a pinned `JournalHead` and `IndexedSegment` descriptors to `FileJournalSource`. External sources can implement `JournalSource` directly. The provider returns `JournalPage` with contiguous offsets, entry identities and a positioned problem when applicable.

The initial catalog includes the following topics.

| Topic | Source | Projection v1 |
| --- | --- | --- |
| `operation.completed` | Actual terminal execution event, including failed and cancelled outcomes | `operation_summary` |
| `operation.failed` | Actual terminal execution event with a failed outcome | `operation_summary` |
| `material.stored` | Confirmed new storage effect with its effect ID | `stored_material` |
| `source.bytes_changed` | Registered source transition between different byte digests | `bytes_change_public` |
| `publication.committed` | Owner-committed dataset version with an artifact identity | `publication_summary` |

Register a `RecordDataSchema` extension and a `NotificationTopic` to expose an additional domain event. New data declares `data_version` explicitly. A projection uses closed `FieldRule` and `ValueRule` definitions. `accessible_topics` shows projections for a proposed subscription scope and route. A commit event with `mode=backfill` requires an explicit subscription filter for that mode.

## Operate the subscription

1. Compose `NotificationRuntime` with the catalog, current authority, state provider, and specific `SourceBinding` and `ConsumerBinding` instances. The managed execution context supplies scoped bindings for `notification_authority`, `notification_state`, `journal_source` and `notification`.
2. Call `configure_subscription(SubscriptionChange("create", spec), runtime=runtime)`. Enable the disabled subscription with the current revision. For new subscriptions the initial checkpoint is the verified head of the source.
3. Call `prepare(PrepareRequest(key), runtime=runtime)`. Pass `mode="catch_up"` and a page count for a bounded catch-up. Use `inspect` with an `InspectRequest` for a read-only preview. To work over the records of an existing bounded snapshot, register a replay with its range and expiry, then prepare its separate key with `mode="replay"`.
4. Call `notification_health` for the bounded queue and due dispatch IDs. When the scan is truncated, pass `next_scan_after` as `after_position` for the following slice. Call `deliver(DeliverRequest(scope_id, dispatch_id), runtime=runtime)` for a due item. On `restore_evidence`, inspect `DispatchStatus.evidence_problem`, restore the original source position, then call `deliver` again.
5. For an unknown or expired in-flight claim, call `reconcile(ReconcileDeliveryRequest(scope_id, dispatch_id, attempt_id), runtime=runtime)`. Use the stored retry schedule after a qualified retryable refusal. The consumer supplies `final_rejection=True` only after it can attest that the original attempt never took effect and is now fenced against acceptance.
6. Use `flush_audit` to publish pending audit records with a bound `RecordWriter`. Unconfirmed or mismatched receipts keep the obligations pending. Configure `NotificationRuntime.audit_gate=RequiredJournalGate(writer)` at composition time when the host requires journal publication before every handoff. Without that setting, the host can publish the transaction's queued audit asynchronously.

An in-process caller can use `MemoryNotificationState`. For a resumable runtime provide a `NotificationStateStore` with an atomic comparison of subscription, checkpoint and dispatch revisions and a read-back for exact commands. `encode_state_mutation` and `decode_state_mutation` expose a bounded v1 representation for provider-managed persistence. Source and state consistency remain claims of the bound providers. A durable inbox must compare the current grant and subscription revision, the route revision, fence, attempt and payload digest at its accepting boundary. It must leave enough evidence to resolve the exact attempt after process loss.

For retention, keep origins needed by pending dispatches alongside live checkpoints and active replay ranges. `oldest_pending_source_positions` in `notification_health` reports the first still-needed offset per epoch among the rows covered by the current page and its inspection grant. Compute retention from a coordinated inventory of all relevant subscriptions, checkpoints and replay ranges at the host. The health view is useful for inspection, since permission filtering, pagination and concurrent preparation can limit its coverage. Resolve source gaps at the source. When the competent owner approves a new cut, call `amend_checkpoint` with the expected cursor, snapshot reference, reason and evidence reference.

The current output is structured JSON. `record_external_delivery` represents a separate owner-qualified channel receipt. `project_downstream` shows independent stage and attempt outcomes from those registered observations. A recipient can format, route and store its own downstream effects.

## Changes in 0.13.0

The Python contracts for preparation, delivery and qualification are version 3, and reconciliation is version 2. Preparation accepts a subscription and checkpoint key. Direct preparation from standalone publication, storage and diagnostic objects is replaced by registration and qualified journal reading. The portable journal record remains v1 and the manifest remains v2. A new finish-linked operation summary uses data schema v2 and a separate record identity. Older summaries remain readable.

Run the example with a recorded fixture.

```sh
python examples/acquire_store_parse_notify.py tests/fixtures/universal_core/offices-basic.html /tmp/stratbox-offices.html
```

[Architecture and evidence boundaries](../architecture/notifications.md)
