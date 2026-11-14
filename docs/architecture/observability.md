# Universal observability and journal history

`stratbox.observability` is an optional, reusable component for representing,
querying, persisting and reconstructing facts about library operations. The
existing `execution.run` remains the only operation runner. All business
operations work without an observer or a storage backend.

## Meaning and ownership

- `ExecutionEvent`: lifecycle of an invocation (`started`, `stage`, `progress`,
  `finished`). `ExecutionContext.sink` is best effort: failures increment the
  runner's `observability.dropped` counter without failing the operation.
- `DomainFact`: domain-qualified observation with a stable *semantic* `fact_id`
  and a separate `observation_id` for each occurrence. Its creator owns the
  meaning and the comparability conditions. `make_fact_id` hashes only the
  explicit identity components supplied by the domain.
- `EffectReceipt` and other evidence receipts: reports from the corresponding
  operation or capability. Recording a receipt does not substitute for it.
- `JournalRecord`: storage-independent, versioned semantic envelope. References
  identify resources independently from locators or storage paths. Payloads
  contain bounded portable metadata, not raw tables, secret values or tracebacks.

An `operation.finished` event can be missing while the operation has actually
finished; an unsuccessful attempt can discover a real new publication. These
facts must not be confused. The library never infers causality from timestamps
or picks the newest source release purely from invocation order.

## Observing in memory

```python
from stratbox.execution import ExecutionContext
from stratbox.observability import RecordMemorySink, CapturePolicy

observer = RecordMemorySink(CapturePolicy(progress=False, max_records=10000))
# result = some_stratbox_operation(..., context=ExecutionContext(sink=observer))
# observer.capture_result(result)  # optional result summary
records = observer.records
capture_losses = observer.dropped
```

Capture limits can drop records independently of the execution runner's sink
loss count. The in-memory sink is safe for concurrent `emit` calls. A composite
sink isolates errors between recipients and exposes its own dropped count.

## Pure records, history and projections

```python
from stratbox.observability import (
    RecordFilter, select_records, build_operation_history,
    project_operation_state, encode_records, decode_records,
)

selected = tuple(select_records(records, RecordFilter(kinds=frozenset({"operation.finished"}))))
# history = build_operation_history(records, result.invocation_id, capture_complete=True)
encoded = encode_records(selected, format="jsonl")
restored = decode_records(encoded, format="jsonl")
```

`capture_complete=True` is an explicit claim by the caller that all relevant
events for the selected interval were captured. Without that evidence,
operation-history completeness is `indeterminate` even when the visible start
and finish records are present. Presence of unexplained sequence gaps,
conflicts or capture loss produces `incomplete`. If progress events were
intentionally excluded by `CapturePolicy(progress=False)`, pass
`progress_filtered=True` during reconstruction: missing sequence numbers are
still surfaced, but deliberate progress suppression does not constitute
capture loss.

`project_source_state` and `project_dataset_state` retain competing confirmed
versions as a set with a conflict flag. The library does not silently select
one without a domain-defined publication order. `operation_state_from_result`
provides a direct projection without writing any journal.

## Storage and durability

`FileJournalWriter` creates one **immutable file per segment** under a root and
writer identifier supplied by the caller. Multiple writers do not append to a
shared file. The writer requires `stage_write(...).commit("immutable", None)` or
`create_if_absent`. A regular overwrite-only `write_bytes` capability cannot
satisfy the contract.

```python
from stratbox.base.filestore.local import LocalFileStore
from stratbox.observability import FileJournalWriter, FileJournalReader, reconcile_write

store = LocalFileStore("/tmp/stratbox-logs")
writer = FileJournalWriter(store, "journal", writer_id="sample_run")
# receipt = writer.write_batch(records)
# if receipt.state == "unknown": receipt = reconcile_write(store, receipt)
# recovered = FileJournalReader(store).read_report((receipt.locator,))
```

Receipt states are `confirmed`, `failed`, `unknown`. `confirmed` means an immutable
file's exact bytes were read back and matched the expected SHA-256. It **does
not guarantee survival of a power outage**: even local staged commits may lack
a directory fsync and the underlying store may have different filesystem
semantics. A lost acknowledgement after a possible commit yields `unknown`;
reconcile by checking the expected bytes and record identifiers. Reattempt an
external effect only according to its own owner-confirmation and idempotency
policy. `read_report(...).complete` stays false by default because a set of readable
files alone does not prove that all planned segments were published. It can be
claimed true only when the caller supplies an exact `expected_paths` manifest,
sets `capture_complete=True`, and no segment is missing or corrupt.

`BufferedFileJournal` provides explicit `append`, `flush` and `close` with
bounded memory. Unflushed data is volatile and its pending records remain
available when publication is unconfirmed. `RequiredJournalGate` invokes an
action only after the corresponding immutable intent record is confirmed;
this is a pre-action barrier, **not** an exactly-once transaction or workflow
engine.

## Formats and compatibility

Version 1 supports deterministic UTF-8 JSON and JSONL. JSONL is the recommended
segmented history format but not part of the semantic identity contract.
Named projections can be exported to CSV with explicit columns. `Decimal`
and integer values beyond JavaScript's exact-integer range use tagged JSON
scalars and round-trip precisely. The parser rejects unknown schema versions,
invalid UTC instants, malformed records and unsupported payload types.

Python API backward compatibility is not a design constraint for the project.
Previously **persisted** journal schema versions are a different matter: version
1 is read strictly; future schema versions require explicit readers/migrations,
never silent coercion.

The core defines no mandatory log directory, source-specific filename,
scheduler, UI, SQL schema, notification transport, retention schedule or
central event bus. Operators of external runtimes choose those independently.

## Failure boundaries

- Best-effort observation failure: continue the business operation and expose
  counts of lost observations.
- Durable storage: surface the `JournalWriteReceipt`; never treat an unverified
  write as confirmed.
- Required pre-action barrier: reject action on `failed` and `unknown`, keeping
  the receipt available for reconciliation.
- Partial/corrupt history: retain good segments, surface the damaged or missing
  segment separately and qualify the state as incomplete/indeterminate.
- Unknown external effect: preserve `unknown` and use the effect owner's
  qualified receipt or reconciliation operation rather than a journal guess.

Local regression tests exercise independent execution, identity, codecs,
selection, bounded buffers, concurrent immutable commits, fault injection,
read-back reconciliation and crash-recovery boundaries. No CI workflow is
required to use or test this module.

## Post-processing existing operations

The explicit `capture_operation_result` adapter adds a compact result record
and, for supported result classes, an independently identified evidence fact.
It currently recognizes acquired source receipts and qualified comparisons;
when present it also understands stored-original receipts. Unknown values
produce a summary without copying the result into the journal. Comparisons
require caller-supplied dataset and baseline/candidate release IDs; an
incompatible or indeterminate comparison stays indeterminate.

```python
from stratbox.observability import capture_operation_result

# result = existing_operation(...)
# report = capture_operation_result(result, observer, dataset_id="series",
#                                   baseline_id="version_a", candidate_id="version_b")
```

`FileEventSink(BufferedFileJournal(writer))` is available as a best-effort
`ExecutionContext.sink`. It writes bounded immutable segments at checkpoints;
call `close()` to publish the final buffer and inspect its write receipts. Its
`emit` path is **not** suitable for a required pre-effect registration, because
`execution.run` intentionally catches ordinary sink failures. Use
`RequiredJournalGate` explicitly before the action in those cases.

## Causal links and segment conflicts

`inspect_causes` follows explicit `cause_record_ids` and execution
`Correlation.cause_event_id`, resolving existing execution event IDs to
portable record IDs. Missing parents are reported rather than synthesized.
Across segments the reader deduplicates identical record IDs; conflicting
content using the same record ID is flagged and excluded from recovered facts.
A malformed segment contributes no apparently confirmed prefix records.
