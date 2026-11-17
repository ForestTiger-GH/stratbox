# Stratbox observability: qualified events, evidence, storage, and recovery

`stratbox.core.observability` is an **optional, storage-independent Python facility** for capturing, inspecting, serializing, and recovering events and qualified facts. `stratbox.core.execution.run` remains the single operation runner. Importing this module does not inspect host identity, create files, open network connections, or start threads. Normal business operations retain their full result and receipt semantics with no observer.

## 1. Six independently qualified propositions

| Proposition | Competent source | What it establishes | What it does **not** establish |
|---|---|---|---|
| Operation outcome | `OperationResult` | The outcome reported by the operation contract | Completeness of its emitted event stream |
| Domain fact | Domain owner and its evidence | An assertion in a named source, version and semantic scope | Publication, delivery or persistence of the fact |
| External effect | Owner's `EffectReceipt` / `StoredBytesReceipt` | Owner-qualified `confirmed`, `failed`, or `unknown` effect | That its journal record has been persisted |
| Journal write | `JournalWriteReceipt` after immutable write and read-back | Exact bytes matched the claimed digest at observation time | Producer authenticity, power-loss durability, or directory `fsync` |
| Capture coverage | Actual collector observations and qualified producer counters | Event capture within a **named** scope and bounded producer range | Events that producer did not emit or could falsify |
| Provenance / authority | A separate host or runtime attestor, if any | Host-bound identity under that attestor's authority | Domain truth, even when correctly signed |

A file hash and a manifest held in one writable namespace provide **internal consistency**, not independent authentication or resistance to coordinated replacement of that entire namespace. Do not infer successful execution of an external effect from a `finished` event or from a confirmed pre-action audit intent.

## 2. Records, identifiers and minimizing data

- `ExecutionEvent` v3 describes `operation.started`, `operation.stage`, `operation.progress` and `operation.finished`; it is owned by `execution`.
- `DomainFact` has a semantic `fact_id` and a separate `observation_id`. Rechecking an identical state creates another observation of the same fact, **not** a new release by itself.
- `JournalRecord` schema **v1** is the frozen, portable, bounded envelope. Its semantic contents and event IDs survive encode/decode round-trips. `ObjectRef` identifies a domain object rather than a filesystem path.
- `record_from_result` without `finished_event` represents a **new observation** of a result, with its own observation ID and `time_basis='observation'`. With a matching actual `operation.finished` event it produces one deterministic `result_final` ID and `time_basis='producer_finished_event'`.
- `OriginClaim` is a **claim**. `OriginAttestation` is a separate host-supplied evidence type. Merely constructing a claim never establishes a verified host identity.
- `PayloadLimits` and schema validators bound nested nodes, strings, numbers, record/segment sizes and permitted fields. All built-in adapters emit explicitly named metadata fields. Arbitrary exception text, raw parameters, paths, environment variables, secrets, DataFrames and document contents must remain outside portable records.

Built-in schemas live in `field_policy.py`. Consumers may instantiate their own `FieldSchemaRegistry` with schemas for additional kinds; this is a **local, explicit** registry, not a global permission service. The ordinary summary projection is more restrictive than the technical record. A `technical` presentation selection does not grant filesystem access, roles or user authorization.

## 3. Three distinct connection modes

### 3.1 Optional best-effort event collection

```python
from stratbox.core.execution import ExecutionContext
from stratbox.core.observability import CapturePolicy, RecordMemorySink, build_operation_history

collector = RecordMemorySink(CapturePolicy(progress=False, max_records=10_000))
# result = existing_domain_operation(request, context=ExecutionContext(sink=collector))
# collector.capture_result(result)  # optional *observation*; never re-executes the business operation
# coverage = collector.coverage_for(result.invocation_id, producer=result.observability)
# history = build_operation_history(collector.records, result.invocation_id, coverage=coverage)
# observer_health = collector.health_snapshot(producer=result.observability)
```

A producer may call a best-effort sink and proceed even when the sink fails. `CaptureDisposition` differentiates accepted, policy-filtered, dropped, failed and unknown collection. A false return from an unknown third-party collector cannot be classified as intentional filtering. A counter or a missing record, without actual observation of the event kind, cannot prove that a gap was harmless progress filtering.

`FileEventSink(BufferedFileJournal(writer))` also implements optional `EventSink`. Its `accepted` means **buffer accepted**. Call `flush()`/`close()`, inspect write receipts and the read-only `health_snapshot()` to determine storage state. An unknown flush retains pending records and requires explicit reconciliation. The sink cannot become mandatory through configuration.

### 3.2 Explicit verified publication of a batch

```python
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.observability import FileJournalWriter

store = LocalFileStore("/path/chosen/by/caller")
writer = FileJournalWriter(store, "journal", writer_id="writer1")
# receipt = writer.write_batch(records)
# if receipt.state == "unknown":
#     receipt = writer.reconcile(receipt)  # same namespace + one bounded read
```

`FileJournalWriter` requires an immutable-create-capable provider (`stage_write(...).commit('immutable', None)` or `create_if_absent`). An overwrite-only file store does not qualify. A logical root is **relative** and restricted to its single writer namespace; `reconcile_write(store, receipt, namespace=writer.namespace)` rejects other locators. Underlying physical path confinement remains the responsibility of the caller-supplied, correctly scoped FileStore.

`JournalWriteReceipt.state` is `confirmed`, `failed` or `unknown`. The write is checked through a bounded read-back; `reconcile_write` verifies digest **and** decoded record IDs against one and the same read buffer. The writer does not promise `fsync` of the containing directory, independent disaster recovery, exactly-once effects or indefinitely stable bytes after verification.

### 3.3 Required pre-action journal barrier

```python
from stratbox.core.observability import RequiredJournalGate

# intent_record = construct_explicit_effect_intent(effect_id, approved_metadata)
# result, intent_receipt = RequiredJournalGate(writer).execute_after_record(
#     intent_record, action=lambda: owner_performs_effect(effect_id)
# )
# Owner's *separate* EffectReceipt confirms or qualifies the resulting effect.
```

`RecordWriter` declares the canonical `json` or `jsonl` format it uses for receipt identities. A confirmed receipt attests the read-back hash and byte length of the ordered `encode_records` output and its ordered record IDs. If the caller supplies a segment ID, the writer confirms that segment. A provider can use its own storage layout while attesting the same canonical representation.

`RequiredJournalGate` compares the receipt with the exact intent record before running the action. A `failed` or `unknown` receipt raises `JournalBarrierError`. A confirmed receipt with different content or record IDs is treated as `journal.write_receipt_mismatch`. The owner supplies separate evidence of the action's result and reconciles any uncertainty after registration of the intent. Hosts opt in to the gate for the actions that require it.

## 4. Producer/collector coverage and bounded history

`SequenceRange(first, last)` and `merge_ranges`, `subtract_ranges`, `intersect_ranges`, `find_gaps` and `count_ranges` operate on **intervals**. Missing sequences never require a set of all numbers between 1 and the highest observed ID. `OperationHistory` exposes `missing_sequence_ranges`, `missing_sequence_count` and a bounded `sample_missing_sequences()`. `inspect_execution_lifecycle` is the **shared** bounded structural validator for both the in-memory history and file reader: unique local `sequence`, one `started` at 1, one terminal `finished` at the last producer sequence, consistent invocation/operation identities, and agreement between optional envelope and payload identifiers. Numeric gap coverage alone cannot certify a structurally invalid execution.

`CaptureCoverage` identifies an invocation, collector scope, observed sequence ranges, the ranges whose **actual types the collector saw** before intentionally filtering, known loss, unknown loss, qualified producer counter, terminal observation, generation and quality of evidence. `assess_coverage` returns a qualified `CoverageAssessment`:

- `complete`: only relative to a stated capture scope, with a finite producer range, collector-observed evidence, matching lifecycle start and finish, proved policy exclusions, and zero unexplained gaps or losses.
- `incomplete`: established lifecycle contradiction, known loss, mismatched producer/collector counters, unexplained sequence gaps, conflicting identities or truncated input. A missing start/finish *without* producer coverage evidence is indeterminate unless another definite structural contradiction exists.
- `indeterminate`: no competent collection evidence or unknown producer tail without positive contradiction.

**Forbidden shortcuts:** `progress_filtered=True` suppressing arbitrary gaps; `capture_complete=True` asserted by an arbitrary caller; `set(range(1,max_sequence+1))`; treating `OperationResult.observability.degraded=False` as proof of a complete event history. `operation_state_from_result(result)` reports the result known with `event_coverage='not_collected'` regardless of event sink status.

`select_records` is lazy, including diagnostic lookup inside frozen `MappingProxyType`; `group_records` explicitly materializes within budgets; `inspect_causes` uses bounded iterative traversal and reports cycles, truncated graphs, conflicting IDs and missing aliases. Missing foreign parents are qualified separately from an invocation's own lifecycle.

A closed `SnapshotJournalSource` and `FileJournalSource` supply
`JournalPage` values through the same positioned read contract. The host
registers the source authority and pins a head for the read. A cursor
contains a scope, stream, partition, epoch and last accounted position.
Pages report their own storage, capture and domain coverage. A dormant
source requires outside scheduling evidence to qualify missed checks.

`RecordDataSchema` validates closed, recursively typed event data by
version. The enclosing `JournalRecord` remains schema v1. A canonical
result summary is linked to the actual matching terminal execution event.
Its data schema v2 and record identity are distinct from archived v1
summaries. History uses a single consistent result assertion per invocation
for aggregation and flags conflicting assertions.

Notifications consumes the positioned journal through an explicit source
binding. [Notification architecture and consumer evidence](notifications.md)

## 5. Versioned domain projections and qualified external effects

- Source checks and publications are chronologically observable. Multiple distinct confirmed releases are a **history**, not an automatic conflict. The current release is `None` without a domain-supplied resolver that selects among the confirmed candidates. Distinct byte identities sharing one release ID are **ambiguous** by default (`revision_relation='indeterminate'`, `observed_byte_versions` counts them); a separate competent `revision_resolver` may explicitly classify the relation as `same`, `supersedes`, or `competing`. A byte difference alone does not prove a semantic conflict.
- Dataset comparisons are keyed by `dataset + baseline + candidate + comparison scope + semantic method`. Different historical pairs may have different states. Conflicting assertions about the **same** pair/scope/method are a conflict. Incomparable pairs without a domain resolver produce an indeterminate latest state.
- Artifact production does not imply stored confirmation. Multiple byte identities without a domain version key can be ambiguous, not necessarily conflicting. A coherent version/identity key allows qualified conflict detection.
- `fact_from_stored_bytes` retains the owner's `status` (`stored`/`already_present`/`failed`/`unknown`) and provides normalized `effect_state` (`confirmed`/`failed`/`unknown`). When a real `effect_id` exists, a qualified `ObjectRef('effect', ..., 'receipt')` links that fact to `EffectReceipt`. A different unconfirmed attempt does not automatically erase a previous confirmed logical effect.
- Projections are **read-only**: no source fetching, comparison replay, delivery or external effect execution occurs when reducing records.

## 6. Immutable segments and a sealed generation manifest

Individual batches can always be written without a manifest: they have qualified byte receipts but **not** a claim of completeness for an entire event generation.

A `JournalManifest` is an independent immutable object containing `writer_id`, `generation_id`, `scope_id`, `SegmentDescriptor` entries (file identity, record count, record IDs digest, write status), `CaptureCoverage` evidence for each included invocation, a qualified **`GenerationCaptureAssessment`** and origin/attestation references when supplied. The manifest ID is deterministic from its canonical content.

To claim complete storage *within the locally declared scope*:

1. Collect qualified producer/collector coverage through a real capture boundary.
2. Write each immutable segment and retain its confirmed `JournalWriteReceipt`.
3. Build a **v2** manifest with those receipt descriptors, the actual in-memory `records` and collector evidence bound to the same `generation_id`. `build_manifest` computes its own aggregate; it does not accept a caller-declared per-invocation `CoverageAssessment` as a generation proof. `seal_state='sealed'` requires confirmed segments and complete collector-observed coverage.
4. Publish the manifest immutably, verify its own bytes and get a confirmed manifest receipt.
5. `FileJournalReader(store, namespace=writer.namespace).read_report(manifest_receipt=...)` rereads the manifest, checks exact expected segments, each segment's byte identity and record IDs digest, deduplicates matching records, excludes conflicting IDs, and recalculates **every** invocation's lifecycle and coverage. A single indexed pass detects invocation IDs missing on either side, and the full deterministic generation assessment (counts, statuses, loss totals, digest and reasons) must equal the manifest's declaration. Both `storage_coverage` and `capture_coverage` must be `complete` for the report's `.complete` to be true.

### 6.1 Verified multi-invocation generation (explicit close and handoff)

```python
from datetime import datetime, timezone
from stratbox.core.observability import (
    OriginClaim, RecordMemorySink, CapturePolicy, FileJournalWriter,
    SegmentDescriptor, build_manifest, FileJournalReader,
)

origin = OriginClaim("collector_1", "collector", "generation_1")
collector = RecordMemorySink(CapturePolicy(progress=False), origin=origin)
# Run two or more ordinary operations with ExecutionContext(sink=collector).
# Their OperationResult.observability values belong to the respective producers.
# coverages = tuple(collector.coverage_for(result.invocation_id, producer=result.observability)
#                   for result in completed_results)
# snapshot = collector.finalize_generation()  # closes this collector to new events
# writer = FileJournalWriter(store, "events", writer_id="writer_1")
# receipt = writer.write_batch(snapshot.records)
# manifest = build_manifest(writer_id="writer_1", generation_id="generation_1",
#                           scope_id=coverages[0].scope_id,
#                           segments=(SegmentDescriptor.from_receipt(receipt),),
#                           records=snapshot.records, capture_evidence=coverages,
#                           sealed_at_utc=datetime.now(timezone.utc))
# manifest_receipt = writer.write_manifest(manifest)
# report = FileJournalReader(store, namespace=writer.namespace).read_report(
#     manifest_receipt=manifest_receipt)
```

`CaptureCoverage` belongs to one invocation. Sequence `7` of invocation A and sequence `7` of invocation B are unrelated; the aggregate contains counts and a digest of per-invocation results, **never a merged numeric sequence**. Each recovered execution invocation needs a matching evidence item; an item with no recovered execution or an execution without evidence blocks `complete`. A `generation_id` mismatch is invalid. Missing generation identity remains explicitly indeterminate and cannot seal a generation. A collection of domain-only facts without execution evidence can still be retained but does not prove capture completeness.

Manifest schema **v2** replaces the former single-invocation assessment with `GenerationCaptureAssessment`. Stored journal *record* schema remains **v1**. Old manifest v1 bytes are rejected with `journal.unsupported_manifest_schema` rather than silently acquiring v2 completeness; no automatic data migration occurs.

### 6.2 Bounded observer metadata and receipt lifecycle

`ObserverLimits(max_tracked_invocations=10000, max_total_sequence_ranges=100000,
max_ranges_per_invocation=5000)` bounds the collector's tracking metadata independently of
`CapturePolicy.max_records/max_bytes`. On capacity overflow the collector rejects new
execution-event capture with `journal.coverage_metadata_limit`, keeps previously observed
bounded evidence, and reports `metadata_overflow_events`/`degraded` through its
`ObserverHealthSnapshot`. It never silently evicts old evidence and upgrades the scope
back to `complete`. `RecordMemorySink.finalize_generation()` closes capture and returns
an immutable bounded `ObserverGenerationSnapshot`; the next generation uses a new sink.
`FileEventSink` accepts the same explicit `origin`/`limits`, and its finalization closes
its buffered journal. A snapshot is volatile until storage is independently confirmed.

`BufferedFileJournal(max_retained_receipts=4096)` retains at most that many **latest**
receipts by segment ID. `snapshot_receipts()` passes a bounded immutable tuple to its
caller. After the caller has independently recorded a **confirmed** segment identity,
`acknowledge_receipts(segment_ids)` releases those entries. Unknown and failed receipts
cannot be silently acknowledged; `reconcile_pending()` updates the same receipt slot.
When the catalogue reaches capacity, a new flush raises
`journal.receipt_capacity_exceeded` **before** any new write, retaining the pending
record buffer. `close_status` continues to distinguish confirmed versus unresolved
publication. No automatic daemon, timer, worker, or background rotation is introduced.

The manifest is neither an external authority nor a cryptographic anchor. A compromised writer/root may forge a self-consistent replacement. This library does **not** build a remote collector, signatures, IAM, SIEM, scheduler, daemon or universal retention policy.

## 7. Formats, exports and resource bounds

JSON/JSONL schema v1 remains the atomic record format; persisted generation manifest schema is v2. Nested `Decimal` and large integers are encoded with explicit tags and recovered exactly; ambiguous single-field reserved tag mappings are rejected at construction. Decoders reject malformed encodings, duplicate JSON keys, unknown schemas and oversized inputs; bad segments produce diagnostic issues and never contribute a spurious valid prefix. Persisted schema v1 stays v1; no silent upgrade to stronger provenance guarantees.

CSV projection requires explicitly named columns and rejects unexpected fields. `export_projection_csv(..., spreadsheet_safe=True)` is the default. Text beginning with `=`, `+`, `-` or `@`, including after hiding whitespace/control characters, is prefixed as text; numeric negative values remain numeric. A machine-oriented CSV profile must be consciously requested for consumers that **never** interpret fields as spreadsheet formulas. CSV/HTML/AI consumers must treat imported log content as untrusted data and enforce authorization independently.

Default budgets, adjustable at call boundaries: observer metadata 10,000 invocations / 100,000 total intervals / 5,000 intervals per invocation, retained receipts 4,096; journal record 2 MiB; segment 8 MiB; in-memory capture 10,000 records/16 MiB; buffered journal 256 records/1 MiB; reader 10,000 segments with separate total record/byte limits; causal traversal 10,000 nodes; bounded number of sequence intervals and manifest segments. Budget overruns are reported, never silently treated as a complete history.

## 8. Failure table

| Failure | Correct observed state | Incorrect inference |
|---|---|---|
| Optional sink fails | Business operation continues; observer reports loss | All emitted messages were stored |
| Collector intentionally removes progress | Exclusion intervals backed by actually seen progress | Every gap is harmless progress |
| Producer omits finish | `incomplete` lifecycle | Operation definitely failed |
| Buffer crashes before flush | Pending / missing seal / indeterminate | Buffer was durable |
| Commit acknowledged by no one | `unknown`, explicit reconcile on *same* bytes | Write definitely failed / effect should be retried |
| Segment missing or corrupt | Issue; other segments readable; generation incomplete | Missing record never existed |
| Source publishes historical revision | Multiple releases, no inferred order | Last checked release is current |
| Effect owner reports `unknown` | Owner reconciliation required | Effect completed because its intent was journaled |
| User-controlled content exported | Named allowlist + spreadsheet-safe text | CSV, HTML or AI can execute it |
| Manifest and all local hashes replaced | Local checks may be fooled | Authenticity is proved |

## 9. Local testing and deliberate API changes

```sh
python -m pytest -q tests/unit/observability
python -m pytest -q tests/integration/test_observability_pipeline.py
python -m pytest -q tests/integration/test_observability_storage.py
python -m pytest -q tests/performance/test_observability_bounds.py
python -B -m pytest -q
```

No GitHub Actions job is required for this library. Verification must be performed locally; a test file in the repository does not prove it has run on the complete installed package. The old monolithic `tests/unit/test_observability.py` is replaced with deeper contract/regression, integration and bounded-performance tests. Deliberate breaking changes: removed `PersistencePolicy.reliability`, `capture_complete`, `progress_filtered`, and individual-number `missing_sequences`; `FileJournalReader` requires `JournalNamespace` for scoped reads; standalone `reconcile_write` requires `namespace`; result history uses qualified coverage and effect statuses instead of implicit claims.

The library deliberately excludes platform-specific topology, desktop application history, deployment permissions, external monitoring services and employer-private implementation details. Any additional provenance attestation or access-control decision belongs to an explicitly competent host/runtime boundary.
