# Observability revision — 2026-11-15

## Scope

Core-only semantic and storage corrections of `stratbox.observability`; no other repository, application lifecycle, scheduler, GitHub Actions execution or private deployment details.

## Corrected defects

- Frozen `MappingProxyType` diagnostics/effects are consumed as `Mapping` in selection, history and projections.
- Lost `operation.stage` is no longer hidden by progress filtering; observed progress exclusions are individually accounted for.
- Sequence gaps use bounded intervals, not `set(range(...))`.
- `StoredBytesReceipt` carries original storage status and normalized effect state, linked by a real effect ID when available.
- Sequential releases and incomparable comparisons do not fabricate a version conflict or domain ordering.
- File reconciliation reads once, then validates digest, schema and record IDs over those exact same bytes.
- Persistence policy is batching-only; a required audit barrier can be invoked explicitly before a selected effect.
- Named CSV projections escape formula-like untrusted text by default.
- Producer result outcome is distinct from event coverage and separate from filesystem confirmation.

## New qualification and recovery contracts

`SequenceRange`, `CaptureCoverage`, `CoverageAssessment`, `OriginClaim`, `OriginAttestation`, `JournalNamespace`, `SegmentDescriptor`, `JournalManifest`, `ObserverHealthSnapshot`, `CaptureDisposition` and local `FieldSchemaRegistry` provide portable, bounded evidence and presentation controls. A sealed generation requires collector evidence, confirmed segment receipts and a confirmed manifest; the reader independently recomputes the declared collection scope from recovered execution records. This proves only self-consistency and qualified local coverage, not external authenticity or power-loss durability.

## Deliberate Python API changes

- Removed `PersistencePolicy.reliability`, `capture_complete=True`, `progress_filtered=True` and the unbounded `OperationHistory.missing_sequences`.
- Added `OperationHistory.missing_sequence_ranges`/`missing_sequence_count`, `coverage=CaptureCoverage`, and bounded sequence sampling.
- `FileJournalReader` accepts `namespace=JournalNamespace`; `reconcile_write` requires a matching explicit namespace or use `FileJournalWriter.reconcile`.
- `record_from_result` differentiates source event timing from a new observation, with explicit canonical final summaries when a matching finish event exists.
- `OperationState.result_known` and `OperationState.event_coverage` distinguish business outcome from capture completeness.
- Legacy `JournalRecord` JSON envelope remains schema version 1 with strict version checks. Persisted v1 content is **not** assigned new provenance or completeness claims.

## Testing and limits

Regression cases include frozen payloads, changed/missing source releases, same-scope conflict, read-once reconciliation, unknown commits, concurrent immutable writes, buffer recovery, missing/corrupt manifest segments, provenance claims, large gaps, enormous causal chains, safe CSV and no-observer execution. Core integrations test an existing original-save operation and computation receipts without network access. Storage tests are offline and use explicit temporary stores.

Implementation limitations: no independent integrity anchor; no root compromise defense; no exactly-once external effects, power-loss guarantee, platform access-control layer, remote collector or built-in retention agent. The live repository's full test result must be reported separately from local isolated tests.
