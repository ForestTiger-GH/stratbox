# Stratbox 0.12 core operations

The Python package exposes independent acquisition, parsing, comparison,
calculation and representation operations. Each domain owns its source
identity and analytical rules. HTTP, file and directory commands, and
format primitives are reusable across domains.

| Domain | Public operations | Subject and result |
| --- | --- | --- |
| `execution.originals` | `receive_original`, `save_original`, `receive_to_store`, `read_original`, `reconcile_original` | Original bytes, acquisition and storage receipts, versioned material references and conditional verification. |
| `macrobanks.cbr_offices` | `acquire`, `parse`, `capture`, `read_representation`, `compare` | Exact HTML and a literal bank-by-territory CSV. Capture date uses the supplied zone. An asserted official as-of date has its own field. |
| `macrobanks.cbr_offices_reg` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Monthly territorial XLSX and wide CSV. Formula lineage preserves the formula and attributes alongside cached values. |
| `organizations.fns_sme` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Regional register JSON, typed counts and literal CSV. Comparison tracks changes by the published region code and qualifies drops in coverage. |
| `organizations.fns_1yur` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Part I from BIFF, OOXML, ZIP or a supplied RAR reader. The dated field map retains identity-equivalent columns, records omissions and keeps original geographic perimeters. |
| `macrobanks.cbr_file_collector` | `discover`, `collect_raw`, `collect_to_store`, `prepare_archive`, `archive_to_store` | Explicit selection from 41 official files, original bytes and acquisition receipts. A partial result lists attempted, completed, failed and remaining IDs. |
| `macrobanks.cbr_industries` | `discover`, `acquire`, `parse`, `build_stream`, `calculate_apk`, `build_pivots`, `render_pivots`, `render_industry`, `render_industries` | Monthly 01_05_A_Debt_corp **stock** and 01_04_A_New_loans_corp **flow** via `issuance_0104`. `IndustrySelection` validates all source cells while materializing only needed published industry codes; `apk` expands to its five source ingredients. Batch rendering verifies one mutable input snapshot and generates multiple individually identified XLSX representations. |
| `macrobanks.cbr_forms` | `select_sources`, `acquire`, `parse_form`, `build_form_data`, `build_form_views`, `render_workbook` | 101, 102, 123, 135, 802 and 805. Selected DBF member and packaged model have independent byte evidence. Formula outputs require all referenced source values. |
| `macrobanks.escrow` | `discover`, `acquire`, `parse`, `build_history`, `build_views`, `render_workbook` | Caller-selected releases, region and indicator history, and workbook bytes. |
| `macrobanks.cbr_sors_restoration` | `read_source_files`, `load_sources`, `restore`, `run_crosswalk`, `build_pivot`, `render_workbook` | Exact workbook and classifier inputs, tiered inference, strict feasibility and projections. The result carries bounds, proof and publication statuses. |
| `macrobanks.frg` | `scan`, `plan_cleanup`, `apply_cleanup`, `prepare_archive`, `prepare_archive_to_store` | Read-only catalog and plan, scoped conditional copy/move/removal, per-action receipts; in-memory ZIP for small selections or disk-streamed, SHA-verified ZIP for large selections and mounted directories. |
| `notifications` | `prepare`, `deliver`, `qualify`, `reconcile` | Stable intent from qualified facts and confirmation or reconciliation with the receiving channel. |

## Execution and observations

Operations return `OperationResult` with the definition and versions,
invocation ID, outcome, diagnostics, inputs, effects and observability.
A failed feasibility check can carry a diagnostic result. A partial result
requires explicit support from the operation. An uncertain effect keeps its
unknown status until the effect owner supplies a confirmation.

`ExecutionContext` accepts a clock, a cooperative cancellation token, a
resource budget, provider bindings, an event sink and correlation IDs. Events serialize bounded fields
for start, stage, progress and finish. Optional sink failure increments
the dropped counter. Cancellation is checked before effects and between
declared stages. Long external calls observe cancellation at the next
available checkpoint.

Dataset versions for the four date-keyed releases hash a canonical manifest
with the release, method, significant parameters, exact input digests and
representation digest. Offline replay uses the same method. CSV replay
carries CSV input evidence. `first_seen` requires an explicitly confirmed
absent baseline. An unavailable or incompatible baseline gives a successful
comparison with an `indeterminate` decision.

Computations carry their direct input receipts and parent manifests in
`OperationResult.computation`. Pass the typed result of `build_stream` to
`calculate_apk` to preserve provenance. A standalone DataFrame has its own
identity. Consumers can inspect the manifest and keep the parent receipts
with saved results. Comparison reports original, structure, facts, method
and representation separately, with the number of shared observations.

## Transport and effects

`HttpRequest` declares an HTTPS endpoint policy, GET or POST body, deadline,
response limit and redirect behavior. The default adapter checks each
redirect, streams the body under wire and decoded-size limits and returns
HTTP statuses separately from transport errors. It requests identity content
encoding and handles bounded gzip and deflate replies. Deadlines apply to
the exchange budget and read checkpoints. The system resolver and socket
calls have their own timing behavior.

`write_verified_bytes` checks the supplied digest, delegates the selected
commit mode and verifies the destination by reading it back. Immutable
local writes use a same-directory staged file and a no-clobber hard link.
Conditional replacement requires the store's authoritative revision
capability. A local read-back receipt describes the observed file bytes.
Git, database and durable channel receipts come from those destinations.

FRG rebuilds the approved plan under a directory guard before applying
effects. The standard local guard coordinates participants using that
directory's guard. Use a directory managed by cooperating writers for
cleanup. Local moves link the verified inode to the new name before
removing the old name. A failure between those steps can leave both names
and returns an unknown effect. A new plan starts from the inspected state.

A delivery key includes the publication transition, route and destination.
The payload has a separate digest. In the managed profile a channel checks
the route revision and qualifies acceptance for the bound recipient. Use
`reconcile` to obtain the receiving owner's determination after an unknown
outcome. The consumer owns any durable outbox and publication record.

## Verified input coverage

Offline golden comparisons cover two daily HTML layouts, regional SME
JSON, territorial XLSX cached formulas and the five 1-YUR mapping epochs.
The 1-YUR samples exercise BIFF and OOXML with separately identified archive
members. Existing historical CSV files can be validated as CSV evidence.
Access to original historical books, a system RAR extractor, and live
publication and delivery integrations is qualified per environment.

[Installation and examples](../how/install-and-run-core.md)

[Execution, admission and recovery](core-execution-and-admission.md)

## Selective industry history and batch rendering

For a full industry history, use `IndustrySelection()`. For APK and the published
TOTAL, supply `IndustrySelection(("apk", "total"))` to `build_stream`.
All 26 source industry headers, all 96 geography positions, all relevant sheets,
and **all original numerical cells** are still validated. Only selected published
observations are materialized. The observed validation scope is `full`, while
`selection.industry_codes` and computation parameters describe the narrower output.
A standalone `parse` also accepts a selection.

`render_industries(RenderIndustriesRequest(stream, ("apk", "total")))` for debt and
`issuance_0104.render_industries(RenderIssuanceIndustriesRequest(...))` for issuance
perform one admitted-input copy and identity check per batch, then produce separate
`Representation` objects for each workbook. Existing `render_industry`
is an independent operation and checks its mutable input at that boundary.
Unexpected/mutated source tables, missing APK components, and incomplete history
fail with typed diagnostics; no implicit partial workbook is returned.

For reproducible local timings without network I/O, run
`python benchmarks/cbr_industries_history.py --debt-dir PATH --issuance-dir PATH`.
The report includes source hashes, operation versions, timings, RSS and result hashes.
