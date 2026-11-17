# Qualified notifications

Stratbox prepares structured events for an explicitly configured consumer. The source is a verified journal position. The topic states which registered schema, fields and event identity are eligible for disclosure. The consumer owns presentation, destination settings and its own external effects.

## Sources and evidence

A host binds each stream and partition to a source authority and one of two profiles. A closed collector snapshot supplies bounded process-local positions. An immutable publication index and a checked segment or another competent provider supply resumable positions. A cursor names the scope, stream, partition, epoch and last accounted offset. It is independent of timestamps and invocation sequences. Reads use one pinned head. Incomplete capture, damaged storage and uncertain observation of the real source are distinct.

For a file source, a host supplies the published index of segment descriptors. Each read checks the namespace, segment digest, length, record count and ordered record IDs in one bounded buffer. The journal manifest continues to qualify one observation generation. A trusted provider and its storage boundary establish the provenance of the index and its relationship to the underlying events.

A domain owner can commit its fact with its business transition or relay it from its own authoritative outbox. Source discovery, a change in downloaded bytes and a committed version are three different propositions. An unsuccessful source check cannot establish that the source remained unchanged.

### Source retention

Handoff re-admission reads the original stream, epoch and position again and compares the exact record ID and byte identity. The host's retention and epoch rotation policy keeps that evidence readable while a dispatch can still be attempted or reconciled. This policy also accounts for unread live positions and authorized replay ranges. A source implementing `EpochJournalSource` can supply a retained head through `head_for_epoch` while publishing a newer live epoch. A source with a single readable epoch keeps that epoch bound until the associated pending work is resolved or a compatible archive takes over reads.

Missing evidence records `notification.evidence_unavailable` together with the journal diagnostic. The dispatch stays pending and the next action is `restore_evidence`. Recovery resumes admission against the same pointer without spending a handoff attempt. A returned record with conflicting identity is quarantined. The existing lifetime still governs new attempts.

## Topics, policies and versions

A notification topic refers to versioned data schemas in the observation registry. The projection specifies the exact structured output and the separately permitted metadata. The subscription selects one topic, version and projection in a declared scope. The host supplies current authority for source access, filter fields, the route and disclosure. Filter operands are typed and use equality, membership and existence. Scope and permission checks precede evaluation. Service events and executions of notification operations are ineligible as notification triggers.

Revisions are immutable. An activation takes the current head of each partition as its cut. A live read covers later positions. Catch-up reads multiple pages of the same live range. Replay has an independently authorized range, snapshot and checkpoint. A filter change takes effect from the existing checkpoint and triggers a fresh admission decision on pending work. Disable and reactivation apply a new live cut and prevent unsent work from the earlier activation from being dispatched. A privileged, audited checkpoint amendment records a waiver or replacement cut.

A changed topic version or projection applies to new preparation and cancels any incompatible unsent intent upon re-admission. The history of accepted handoffs is retained. Replay within the same subscription uses the existing logical dispatch key, including for cancelled dispatches. Publishing historical events under a new projection requires a new subscription identity and an authorized replay.

## State and consumer effects

The partition cursor advances in an atomic transaction that records outcomes for its contiguous prefix, any new intents, and the corresponding audit obligations. Each command writes at most one value per checkpoint, dispatch, source record identity and audit record key. Its command identity includes the exact encoded bytes of its audit records. Each intent freezes the bytes and their digest. The dispatch key identifies the authority, logical event, subscription, scope and route. An attempt has an independent ID and fence.

A handoff begins only after confirmation of its stored claim. The runtime refreshes admission before the call. The consumer checks the current binding and the attempt at acceptance. A resumable consumer must accept the same dispatch and payload idempotently into a durable inbox. A qualified receipt binds the dispatch, attempted route revision, attempt and payload identity. An unknown result goes to lookup for that attempt. An expired lease makes the need for reconciliation visible. `not_accepted` qualifies when the consumer provides evidence and sets `final_rejection=True`, attesting that the exact attempt was never accepted and can no longer be accepted. `retryable` then controls whether a new attempt is permitted. Pending, missing or provisional receipts require reconciliation. Revocation affects the next acceptance decision. The history retains any prior accepted effect.

Subscription, preparation and attempt transitions queue immutable audit records in the same transaction as their state. In a resumable runtime, the provider's confirmation covers recoverability of both state and audit obligations across restarts. A host that requires journal publication before the consumer call sets `NotificationRuntime.audit_gate`. The configured gate applies on every call and takes precedence over a per-call gate. Otherwise the resumable path requires the confirmed durable audit obligation before the handoff and can publish it asynchronously.

`flush_audit` removes obligations only when the confirmed receipt matches the exact scope-bound segment, ordered record IDs, hash and byte length. The state provider compares the same record bytes with the current pending entries before acknowledging the batch atomically. Retrying the same ordered batch against the same writer uses the same segment ID.

Consumer acceptance is a separate stage from downstream transport acceptance, delivery and reading. A consumer can register a receipt for any stage it can actually attest. A downstream outcome has its own evidence and does not change the core handoff outcome.

[Use the Python APIs](../current-how/notifications.md)
