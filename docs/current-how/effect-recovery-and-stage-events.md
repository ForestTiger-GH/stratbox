# Effects and uncertain outcomes

External writes and notification handoffs have deterministic effect identities derived from their logical purpose and actual input basis. The service records an intent as unknown before invoking a mutation. A confirmed receipt establishes the corresponding effect; a lost response does not authorize blind retry.

`lookup_effect()` exposes retained evidence. `reconcile_effect()` accepts verified provider evidence and preserves the same effect identity. `FileEffectState` makes records available after service restart; guarantees beyond the provider's actual persistence contract belong to the host.

Provider replies pass one typed admission path during the initial attempt, an
allowed retry and explicit reconciliation. Supplied identity/kind aliases must
agree with one another and the expected occurrence. Scope, payload and conditional
preconditions must match the retained intent. An unbound positive status cannot
become confirmation by filling missing fields from the request. A qualified
adapter can establish the actual request/response association under its declared
contract.

## Atomic claims and bounded hot evidence

`FileEffectState.begin()` atomically claims an unseen effect in SQLite before an
external action starts. Competing service instances using the same provider
state observe the existing claim and cannot independently perform that action.
An unknown record requires reconciliation; a confirmed record cannot be replaced
with a different confirmation or downgraded into a fresh intent.

`max_hot_receipts` and `max_hot_bytes` bound active receipt bodies transactionally.
`max_receipt_bytes` bounds an individual body and is persisted as the ledger's
receipt ceiling. Each unknown claim reserves that full ceiling for settlement.
`usage()` exposes actual, reserved and effective hot bytes separately. Capacity
rejection occurs before the new claim is retained or its physical action starts.
The reserved room remains available for that occurrence's bounded settlement;
an unrelated new claim cannot consume it. Storage failures still leave the prior
unknown evidence available for reconciliation.

Claim tokens and monotonic receipt revisions bind updates to the exact admitted
occurrence. An obsolete claimant cannot overwrite another settlement. Nonterminal
service lookups read the durable authority again, so another qualified service's
confirmation is visible without discarding the current session. Sharing this
provider does not authorize multiple writers of a single-writer journal.

`page(after=..., limit=..., status=..., archived=...)` returns bounded identity
summaries. `archive(effect_ids)` moves an explicit bounded set of terminal bodies
to immutable cold storage; `get()` still restores their exact evidence. Unknown
effects remain hot and block unsafe reclamation. `compact(pages=...)` reclaims
unused database pages in bounded maintenance work.

Compact identity rows and exact cold receipts persist for idempotency. Removing
them would erase the evidence which prevents duplicate mutations. Missing or
altered archive contents cause a visible failure rather than a fresh execution.
The host schedules archival and owns its storage destination and retention.
Existing unindexed receipt evidence also blocks initialization of an empty
ledger in that directory; it cannot silently become permission to repeat work.

Independent output and scope journal facts remain available even when an effect prevents whole-scenario completion. Storage uses create-only or compare-and-set operations with explicit preconditions.

## Current availability and explicit repair

A receipt confirms a historical occurrence. It does not prove that its destination
still exists. Immutable retention checks current content before returning a usable
reference. A later loss requires a separate authorized repair occurrence, selected
with `repair_id` on `command.artifact.commit`. The old confirmation remains intact.
Named materialization uses its explicit `delivery_id` for a new delivery occurrence.

Artifact reconciliation observes evidence. It does not silently turn a missing
destination into a fresh write. An uncertain move or removal also requires
provider transition evidence; path absence alone cannot establish causation.

HTTP 304 establishes conditional reuse of a representation, not fulfilment of a
local destination. The receive path sends both transferred and reused bytes
through the same destination owner. Asking for a new destination therefore gets
its own actual retention result and effect identity.

## Recovery copies and closed occurrence namespaces

`FileEffectState.export_checkpoint()` includes a consistent SQLite snapshot and
every indexed cold receipt body. Its restore operation verifies those dependencies,
preserves scope and exact receipt IDs, and persists a closed occurrence namespace
before exposing the restored ledger.

An older snapshot can omit actions performed after its cut. Fresh/rejected claims
therefore stay blocked in a restored namespace, including IDs absent from the
snapshot. Existing exact receipts can still be inspected and reconciled. There is
no unconditional reopening switch. A newer authoritative tail or sufficient
provider recovery evidence must resolve the missing knowledge.

The [persistent operating profile](persistent-operating-profile.md) combines this
effect snapshot with journal/projection/outbox cuts, immutable dependencies,
original-writer exclusion and a verified cross-owner recovery manifest.

## Journal archive and consumer retention

`MemoryJournal` bounds fact count, individual encoded record size and aggregate
encoded bytes. Reading does not free records. Register consumers, consume their
certified pages and acknowledge each page after its durable handling succeeds.
`prune(through)` releases only the prefix acknowledged by every registered
consumer and preserves monotonic stream sequence numbers.

`FileJournal` retains fixed-size segments and durable consumer checkpoints.
`archive(through, max_segments=...)` moves closed segments into partitioned cold
storage; lagging consumers can still read them. `prune(through, max_segments=...)`
records an acknowledged prefix and removes its complete segments.
`cleanup_pruned(max_segments=...)` resumes physical deletion after interruption.
Requests below the retained floor fail explicitly as `journal.cursor_expired`.
The tuple-only `read()` convenience method reports `journal.scan_limit` when its
scan budget ends before the requested selection is resolved. Consumers which
need continuation positions use `read_page()`.

The file provider permits one explicit writer lease for a directory. A second
writer is rejected. Read-only instances call `refresh()` to observe committed
writer progress. The caller closes a supplied provider, or uses it as a context
manager, to release its writer lease. Execution-service shutdown leaves
caller-owned journal and storage lifetimes with their caller.
