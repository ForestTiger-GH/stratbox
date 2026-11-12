# Stratbox 0.9 core operations

The Python package exposes independent acquisition, parsing, comparison,
calculation and representation operations. Each domain owns its source
identity and analytical rules. HTTP, file and directory commands, and
format primitives are reusable across domains.

| Domain | Public operations | Subject and result |
| --- | --- | --- |
| `macrobanks.cbr_offices` | `acquire`, `parse`, `capture`, `read_representation`, `compare` | Exact HTML and a literal bank-by-territory CSV. Capture date uses the supplied zone. An asserted official as-of date has its own field. |
| `macrobanks.cbr_offices_reg` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Monthly territorial XLSX and wide CSV. Formula lineage preserves the formula and attributes alongside cached values. |
| `organizations.fns_sme` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Regional register JSON, typed counts and literal CSV. Comparison tracks changes by the published region code and qualifies drops in coverage. |
| `organizations.fns_1yur` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Part I from BIFF, OOXML, ZIP or a supplied RAR reader. The dated field map retains identity-equivalent columns, records omissions and keeps original geographic perimeters. |
| `macrobanks.cbr_file_collector` | `discover`, `collect_raw`, `prepare_archive` | Explicit selection from 41 official files, original bytes and acquisition receipts. A partial result lists attempted, completed, failed and remaining IDs. |
| `macrobanks.cbr_industries` | `discover`, `acquire`, `parse`, `build_stream`, `calculate_apk`, `build_pivots`, `render_pivots`, `render_industry` | Monthly 01_05_A_Debt_corp data, versioned geography, derived APK and in-memory Excel views. |
| `macrobanks.cbr_forms` | `select_sources`, `acquire`, `parse_form`, `build_form_data`, `build_form_views`, `render_workbook` | 101, 102, 123, 135, 802 and 805. Selected DBF member and packaged model have independent byte evidence. Formula outputs require all referenced source values. |
| `macrobanks.escrow` | `discover`, `acquire`, `parse`, `build_history`, `build_views`, `render_workbook` | Caller-selected releases, region and indicator history, and workbook bytes. |
| `macrobanks.cbr_sors_restoration` | `read_source_files`, `load_sources`, `restore`, `crosswalk`, `build_pivot`, `render_workbook` | Exact workbook and classifier inputs, tiered inference, strict feasibility and projections. The result carries bounds, proof and publication statuses. |
| `macrobanks.frg` | `scan`, `plan_cleanup`, `apply_cleanup`, `prepare_archive` | Read-only catalog and plan, scoped conditional copy/move/removal, per-action receipts and an independently prepared ZIP. |
| `notifications` | `prepare`, `deliver`, `qualify` | Stable intent from qualified facts, route authorization and one attempted delivery with a qualified acknowledgement. |

## Execution and observations

Operations return `OperationResult` with the definition and versions,
invocation ID, outcome, diagnostics, inputs, effects and observability.
A failed feasibility check can carry a diagnostic result. A partial result
requires explicit support from the operation. An uncertain effect keeps its
unknown status until the effect owner supplies a confirmation.

`ExecutionContext` accepts a clock, a cooperative cancellation token, an
event sink and caller-owned correlation IDs. Events serialize bounded fields
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
The payload has a separate digest. An unknown acknowledgement requires
reconciliation or verified channel idempotency before repeating the same
key and payload. The consumer owns any durable outbox and publication
record.

## Verified input coverage

Offline golden comparisons cover two daily HTML layouts, regional SME
JSON, territorial XLSX cached formulas and the five 1-YUR mapping epochs.
The 1-YUR samples exercise BIFF and OOXML with separately identified archive
members. Existing historical CSV files can be validated as CSV evidence.
Access to original historical books, a system RAR extractor, and live
publication and delivery integrations is qualified per environment.

[Installation and examples](../how/install-and-run-core.md)
