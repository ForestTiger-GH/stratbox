# Persistent operation, retention and verified recovery

The built-in `LocalProfile` owns one coordinator and one journal writer on one
host. It combines the ordinary SDK with durable effect state, source-state
projection, notification outbox and immutable file/dataset providers. The host
still chooses its finite requests, recurring cadence, scientific scope and
maintenance policy. Opening the profile starts no polling workload.

This profile qualifies cooperative local ownership and the tested SQLite and
filesystem operations. It makes no distributed-writer, remote-filesystem,
machine-failure or power-loss claim. The SQLite database, its sidecars and local
locks belong on the same qualified host. The profile's held operating-system
anchor excludes another profile owner and is released when its process exits.

## Contents

1. Open one explicitly owned profile — providers, budgets and ownership lifetime.
2. Derive readiness for the concrete request — bound methods and deferred evidence.
3. Keep each growing state class explicit — retention, current bases and reserves.
4. Export a coordinated recovery package — a verified cut and exact dependencies.
5. Restore with explicit ownership and occurrence rules — exclusive transfer and evidence.
6. Qualification and application boundaries — the supported operating envelope.

## 1. Open one explicitly owned profile

```python
from stratbox.sdk import LocalProfile, PersistentLimits

limits = PersistentLimits(
    min_free_bytes=256 * 1024**2,
    projection_reserve_records=1000,
    projection_reserve_bytes=16 * 1024**2,
    source_state={"max_records": 200_000, "max_bytes": 512 * 1024**2,
                  "max_archive_records": 2_000_000,
                  "max_archive_bytes": 4 * 1024**3},
    effects={"max_receipt_bytes": 1024**2,
             "max_hot_receipts": 10_000, "max_hot_bytes": 64 * 1024**2},
    notifications={"capacity": 10_000, "history_limit": 10_000},
)

with LocalProfile("state", artifact_root="retained", limits=limits) as profile:
    box = profile.box
    sources = box.sources.list(domain_id="cbr", limit=20)
    usage = profile.usage()
```

These numbers are an example configuration, not a measured universal workload
envelope. Size the receipt ceiling for actual receipts and the recovery reserve
for the chosen concurrency and settlement volume. The effect provider reserves
each unresolved occurrence's maximum receipt body atomically before admitting
its external mutation. Four simultaneous unresolved occurrences with a 16 MiB
ceiling consume a 64 MiB reservation even when their initial intents are small.

The profile supplies the same dataset provider through `datasets`,
`dataset_reader` and `dataset_writer`. Additional providers, such as a notification
transport, can be passed through `providers`. Owned state/provider roles cannot
be replaced accidentally through that extension argument.

`close()` drains the SDK and then closes owned state and journal handles. Result
handles still have their ordinary explicit lifetime; consume or retain required
outputs and call `result.close()`. The profile is a host convenience over the
existing five owners, rather than a separate execution engine.

## 2. Derive readiness for the concrete request

```python
report = box.preflight(
    "command.dataset.query",
    inputs={"reference": retained_snapshot},
)
if not report.admissible:
    for check in report.checks:
        if check.status == "blocked":
            print(check.phase, check.code, check.detail)
```

Preflight uses ordinary preparation and the actual bound commands, selected
immutable domain record, method references, configured providers and supplied
inputs. It introduces no independently maintained support matrix. It performs
no network request or external mutation. Method import checks can be omitted
with `resolve_methods=False`; actual execution still resolves the selected method.

The result exposes the prepared-plan and build identities, provider requirements
and checks with `ready`, `deferred` or `blocked` status. `admissible` means that the
request can be attempted under its stated conditions. It does not certify the
eventual numerical result. Input-dependent source/layout qualification, operand
closure, conditional effect preconditions and final output acceptance remain
deferred until their actual evidence exists.

An immutable domain record declaring a missing reviewed financial model creates
a structured scientific limitation. Published-field extraction remains a
separate supported request. A generic reader, a matching filename or a successful
method import cannot establish reviewed economic meaning. Conditional dispatch
branches retain their conditions; a blocked branch is reported without claiming
that every alternative will execute.

## 3. Keep each growing state class explicit

| Code | State | Owner and bounded treatment | Preserved meaning |
| --- | --- | --- | --- |
| ST01 | Live values/readers | Service ownership, configured admission and result release | Exact values remain usable until their actual owners release them. |
| ST02 | Unacknowledged facts | Registered journal consumers | Pruning cannot outrun an acknowledged durable consumer cut. |
| ST03 | Consumed journal history | Segment archive and explicit prefix pruning | Cold segments stay readable; a pruned cursor expires visibly. |
| ST04 | Current source and processing bases | Source-state current pointers | Distinct material/rule bases stay independently selectable. |
| ST05 | Older projection facts | Explicit hot/cold archive or declared discard horizon | Archiving preserves historical queries; discarding limits their completeness. |
| ST06 | Certificate/acquisition authority | Indexed record dependencies and explicit pins | Surviving accepted data retain their required evidence. |
| ST07 | Unknown effects | Durable claim and maximum settlement reservation | Uncertainty remains an existing occurrence, never a fresh action. |
| ST08 | Terminal effect receipts | Exact cold receipt plus durable identity row | Retries still find the original confirmation or rejection. |
| ST09 | Pending notifications | Transactional subscription/outbox state | Advancing a source cursor does not erase its undelivered intent. |

### 3.1. Source-state maintenance

`SQLiteSourceState.maintain(stream_id=..., policy=SourceStateRetention(...))`
commits one bounded maintenance page. Hot and cold tables share the same SQLite
transaction, so an interrupted move cannot make a fact disappear between two
independent stores. Hot and archive capacities are separately configured. The
archive still occupies physical storage; reaching its cap requires deliberate
retirement, a larger declared budget or a different qualified provider.

```python
from stratbox.core.storage.source_state import SourceStateRetention

state = profile.providers["source_state"]
checkpoint = box.advance_source_state(max_pages=10, page_limit=1000)
page = state.maintain(
    stream_id=profile.journal.stream_id,
    policy=SourceStateRetention(
        through=checkpoint.applied_through,
        disposition="archive",
        limit=1000,
    ),
)
```

`has_more` permits a later bounded continuation. Each page accounts for record,
authority, link and explicit current-pointer changes. Maintenance never advances
the projection's journal watermark. Capacity failure rolls the entire page back.
`compact(through=..., limit=...)` remains a narrower bounded cleanup of eligible
ephemeral outputs.

`disposition="discard"` explicitly retires historical evidence inside the
selected cut. `history_retained_after` reports the resulting limit. A complete
current projection can coexist with an incomplete full-history request:
`SourceStateSnapshot.complete` distinguishes those cases through its `view`.
Minimum projection freshness still means "at least this watermark", rather than
"state as of this watermark".

Persistent outputs survive ordinary discard. Retiring those index records
requires `retire_persistent=True`. The operation never deletes the retained
artifact itself. The host supplies `protected_accepted_ids` and
`protected_authority` for obligations held outside the projection's own record
graph. Certificate dependencies on a merged, selected or historical value remain
separate from the validator event which originally established certificate
authority. A derived value can keep an existing witness alive without minting
that witness itself.

### 3.2. Retire obsolete current bases deliberately

Changing bytes, scientific settings or build identities can produce several
legitimate current processing bases. Time alone cannot decide which one the host
still needs. The policy therefore accepts `retire_current_accepted_ids` containing
the exact obsolete accepted IDs selected by the host. The watermark and pins
still constrain that request. The latest source observation and unselected
current bases remain available.

```python
maintenance = profile.maintain(
    disposition="discard",
    retire_current_accepted_ids=obsolete_accepted_ids,
    protected_accepted_ids=required_accepted_ids,
    retire_persistent=True,
    max_pages=5,
    page_limit=500,
)
```

This operation closes the growth case where every changed publication or
method produced another permanently current basis. It does not infer a user's
preferred revision or silently replace an intentionally retained analytical
basis with the newest one.

### 3.3. Admission reserves and physical accounting

`LocalProfile` stops new submissions at configured filesystem and projection
low-watermarks. Effect admission additionally respects the effect owner's atomic
reservation. Existing work can settle. Explicit artifact/notification
reconciliation can use its already reserved room even when the general admission
threshold is reached. Pure calculations do not need an unused new-effect slot.

The reserve is an admission policy, not a disk quota against unrelated writers.
The host monitors actual free space, source database/WAL/shared-memory bytes,
logical hot/cold usage, projection lag and unresolved effect age. Bounded foreground
maintenance and a deeper maintenance window have different purposes. Large
SQLite exports hold their owner lock while creating a consistent snapshot;
incremental internal backup pages do not make that whole pause asynchronous.

## 4. Export a coordinated recovery package

```python
manifest = profile.export_recovery(
    "backups/run-2026-11-27",
    timeout=60,
    retained_references=extra_application_owned_references,
)
```

The destination must be new and outside live state directories. Export acquires
the service admission pause, waits for physical generations to settle and brings
the source projection to the journal tail. Open results remain owned by their
callers. The pause does not manufacture confirmation for unresolved effects.

The package contains the exact retained journal suffix/cursors, a consistent
source-state snapshot, effect ledger and cold receipt bodies, notification state
when configured, and retained immutable dependencies. Projected references,
durable confirmed-retention receipts and unresolved retained ancestors contribute
dependencies. A confirmation which survived a later journal failure therefore
keeps its artifact in the package. The caller adds any independent application
reference obligations explicitly.

The manifest binds format/core identity, journal and provider namespaces,
watermarks, retained floors, pending counts, snapshot hashes, dependency inventory,
configured scope and restore policy. A streamed file index and disk-backed
deduplication avoid a single unbounded in-memory manifest. Hashes detect changed
content; they do not turn an untrusted package into an authorized source of
scientific or effect authority.

Only a verified package is published at its final destination. Missing retained
content, a dependency in the wrong provider scope, a changed owner cut, an exceeded
limit or a corrupted snapshot prevents a complete export. Immutable packages can
then be copied to an independently chosen backup location by the host.

The export applies the remaining aggregate budget before copying each owner.
SQLite snapshot page counts, journal segments, cold receipt files and dependency
streams have size checks during their respective copies. File inventory and
content hashes are verified again before publication. Temporary indexes and
filesystem metadata still consume separate working space; a package-size limit
does not reserve physical free space against unrelated processes.

## 5. Restore with explicit ownership and occurrence rules

```python
from stratbox.core.recovery import (
    validate_recovery_package,
    restore_recovery_artifacts,
    restore_recovery_package,
)

manifest = validate_recovery_package("backups/run-2026-11-27")

# Required only when immutable dependencies need physical restoration.
restore_recovery_artifacts(
    "backups/run-2026-11-27",
    providers=original_artifact_providers,
    state_directory="recovery-operations",
    occurrence_id="approved-recovery-2026-11-27",
)

restored = restore_recovery_package(
    "backups/run-2026-11-27",
    "restored-state",
    providers=original_artifact_providers,
)
```

The original journal writer must be stopped. The same-host restore verifies its
stream identity and acquires its writer anchor. It verifies the retained overlap
and segment geometry, imports any surviving authoritative suffix and actually
replays the source projection to the recovered tail. The returned `recovery`
metadata distinguishes `original_cut_tail`, `recovered_tail` and
`source_state_applied_through`. Host-defined live journal consumer names and
their retention barriers survive the transfer.

The restore also captures the surviving effect ledger when available, checks its
scope and monotonic agreement with the backup, and preserves its exact receipts.
The notification database is recovered as one coherent cursor, consumed-evidence
and outbox snapshot. Keeping only a newer delivery receipt beside an older queue
could lose a newly prepared intent or resurrect an acknowledged one. Missing or
conflicting known receipt/queue authority and missing or divergent journal
suffixes reject restoration before the writer is transferred.

A successful transfer permanently closes the old journal's write namespace
while leaving its evidence readable. The same source namespace can transfer to
one destination; a completed transfer cannot be repeated into a competing live
owner. The new state directory has a resumable in-progress marker bound to its
package and destination until every provider is verified. `LocalProfile` refuses
an incomplete restoration. A returned source-state provider and journal remain
caller-owned and must be closed. Temporary verification snapshots are cleaned
separately from those returned handles.

The built-in restore preserves original artifact provider scopes. Copied state
files and cold effect receipts can move to a new state directory. An immutable
artifact or dataset is reverified through its original provider scope before
reusable state is exposed. Arbitrary artifact relocation requires an explicit
provider relocation/reverification contract; changing a historical receipt's path
is not that contract. The same-host restoration API also requires the original
journal ownership anchor. A lost host or inaccessible original ownership scope
requires a separately established exclusion procedure.

When a verified dataset provider is supplied, the restored SDK provider map binds
`datasets`, `dataset_reader` and `dataset_writer` to that same owner. Conflicting
aliases are rejected within this qualified local profile.

Artifact restoration is its own explicit occurrence. It records a durable claim
in a separate recovery ledger and uses qualified immutable create-if-absent
operations. Repeating that restoration after a lost response is safe under this
provider guarantee. Losing the bytes again after its confirmation requires a new
`occurrence_id`. Named deliveries and notifications stay on their ordinary
effect-specific reconciliation/repair routes.

### 5.1. A backup cut does not include later external actions

After restoration, the original effect occurrence namespace is closed to fresh
or rejected claims. Existing exact receipts remain readable and can be reconciled
with competent provider evidence. Every unknown occurrence remains unknown.

An action missing from the restored ledger might have occurred after the backup.
That absence cannot authorize its replay. The default fence therefore also
protects identities absent from the snapshot. Importing a surviving local tail
preserves available evidence; it does not unconditionally reopen action authority.
Establishing any further completeness or provider-supported reconciliation remains
an explicit recovery obligation. Assigning a new ID to the same uncertain prior
action bypasses the required evidence. The current generic checkpoint API
deliberately supplies no unconditional "reopen namespace" switch.

## 6. Qualification and application boundaries

Local tests establish source-state archive/retirement behavior, authority
dependencies, receipt reservation, journal consumer safety, process-death lock
release, backup corruption detection, exact dependency restoration and fenced
rollback. A benchmark or generated fixture establishes only its measured workload.
Scientific claims still require reviewed publisher material and the selected
method's actual semantic admission. The application layer consumes these SDK
contracts and qualifies its own lifecycle, packaging and platform separately.

See [execution and result lifetime](capability-session.md),
[selective processing and histories](selective-processing-and-restart.md),
[effect evidence](effect-recovery-and-stage-events.md) and
[scientific coverage](independent-domain-data-routes.md).
