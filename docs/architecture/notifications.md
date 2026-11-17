# Qualified notifications

Stratbox prepares structured events for an explicitly configured consumer. The source is a verified journal position. The topic states which registered schema, fields and event identity are eligible for disclosure. The consumer owns presentation, destination settings and its own external effects.

## Sources and evidence

A host binds each stream and partition to a source authority and one of two profiles. A closed collector snapshot supplies bounded process-local positions. An immutable publication index and a checked segment or another competent provider supply resumable positions. A cursor names the scope, stream, partition, epoch and last accounted offset. It is independent of timestamps and invocation sequences. Reads use one pinned head. Incomplete capture, damaged storage and uncertain observation of the real source are distinct.

For a file source, a host supplies the published index of segment descriptors. Each read checks the namespace, segment digest, length, record count and ordered record IDs in one bounded buffer. The journal manifest continues to qualify one observation generation. A trusted provider and its storage boundary establish the provenance of the index and its relationship to the underlying events.

A domain owner can commit its fact with its business transition or relay it from its own authoritative outbox. Source discovery, a change in downloaded bytes and a committed version are three different propositions. An unsuccessful source check cannot establish that the source remained unchanged.

## Topics, policies and versions

A notification topic refers to versioned data schemas in the observation registry. The projection specifies the exact structured output and the separately permitted metadata. The subscription selects one topic, version and projection in a declared scope. The host supplies current authority for source access, filter fields, the route and disclosure. Filter operands are typed and use equality, membership and existence. Scope and permission checks precede evaluation. Service events and executions of notification operations are ineligible as notification triggers.

Revisions are immutable. An activation takes the current head of each partition as its cut. A live read covers later positions. Catch-up reads multiple pages of the same live range. Replay has an independently authorized range, snapshot and checkpoint. A filter change takes effect from the existing checkpoint and triggers a fresh admission decision on pending work. Disable and reactivation apply a new live cut and prevent unsent work from the earlier activation from being dispatched. A privileged, audited checkpoint amendment records a waiver or replacement cut.

## State and consumer effects

The partition cursor advances in an atomic transaction that records outcomes for its contiguous prefix, any new intents, and the corresponding audit obligations. Each intent freezes the bytes and their digest. The dispatch key identifies the authority, logical event, subscription, scope and route. An attempt has an independent ID and fence.

A handoff begins only after confirmation of its stored claim. The runtime refreshes admission before the call. The consumer checks the current binding and the attempt at acceptance. A resumable consumer must accept the same dispatch and payload idempotently into a durable inbox. A qualified receipt binds the dispatch, attempted route revision, attempt and payload identity. An unknown result goes to lookup for that attempt. A clock or expired lease makes the need for reconciliation visible. A retry needs evidence that the prior attempt did not take effect and can no longer take effect. Revocation affects the next acceptance decision. The history retains any prior accepted effect.

Subscription, preparation and attempt transitions queue immutable audit records in the same transaction as their state. The host can publish them to the journal and acknowledge the batch once publication is confirmed. Consumer acceptance is a separate stage from downstream transport acceptance, delivery and reading. A consumer can register a receipt for any stage it can actually attest. A downstream outcome has its own evidence and does not change the core handoff outcome.

[Use the Python APIs](../current-how/notifications.md)
