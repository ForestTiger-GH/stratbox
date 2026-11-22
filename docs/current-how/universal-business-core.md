# Stratbox core operations

The Python package exposes independent acquisition, parsing, comparison,
calculation and representation operations. Each domain owns its source
identity and analytical rules. HTTP, file and directory commands, and
format primitives are reusable across domains.

The table lists representative public operations. The machine catalog supplies
the complete versioned surface. The [CBR route guide](cbr-data-pipeline.md)
describes the full persistence and replay boundaries added in 0.18.0.

| Domain | Selected public operations | Subject and result |
| --- | --- | --- |
| `domains.rosstat.publications` | `discover`, `acquire`, `acquire_to_store` | Four fixed official Rosstat landing pages and provenance-qualified issue/assets; bounded PDF/XLSX/ZIP/RAR original acquisition without economic parsing; unresolved links are never overwritten automatically. |
| `core.operations.source` | `receive_original`, `save_original`, `receive_to_store`, `read_original`, `reconcile_original`, `compare_original_versions` | Original bytes, acquisition and storage receipts, versioned material references and conditional verification. |
| `core.operations.materials` | `read_location`, `save_artifact`, `read_artifact`, `transfer_artifact`, `archive_materials`, `serialize_collection`, `read_collection` | Neutral bytes, full semantic descriptors and manifest-bearing exact-member archives. |
| `core.storage.datasets` | `write_snapshot`, `read_snapshot`, `list_versions` | Immutable logical typed datasets, selected reads and pinned cross-provider assemblies. |
| `domains.cbr.publications` | `list_sources`, `discover`, `identify` | 57 logical series in 11 families; separate acquisition and exact processing profiles, explicit original admission and qualified inventory. |
| `domains.cbr.service_network.bank_offices` | `acquire`, `parse`, `capture`, `read_representation`, `compare` | Exact HTML and a literal bank-by-territory CSV. Capture date uses the supplied zone. An asserted official as-of date has its own field. |
| `domains.cbr.service_network.territorial_offices` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Monthly territorial XLSX and wide CSV. Formula lineage preserves the formula and attributes alongside cached values. |
| `domains.fns.sme_register` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Regional register JSON, typed counts and literal CSV. Comparison tracks changes by the published region code and qualifies drops in coverage. |
| `domains.fns.legal_entities_1yur` | `discover`, `acquire`, `parse`, `capture`, `read_representation`, `compare` | Part I from BIFF, OOXML, ZIP or a supplied RAR reader. The dated field map retains identity-equivalent columns, records omissions and keeps original geographic perimeters. |
| `domains.cbr.file_collection` | `discover`, `collect_raw`, `collect_to_store`, `collect_materials`, `prepare_archive`, `archive_to_store` | The 41-file convenience selection plus mixed supplied/reference/HTTP collection; exact originals and ordered dispositions; ZIPs include a common material manifest. |
| `domains.cbr.corporate_lending.industries.debt_0105a` | `discover`, `acquire`, `parse`, `build_stream`, `calculate_apk`, `build_pivots`, `render_pivots`, `render_industry`, `render_industries` | Monthly 01_05_A_Debt_corp **stock** series. Full original validation, selective materialization, official industry/geography checks and provenance-preserving XLSX exports. |
| `domains.cbr.corporate_lending.industries.issuance_0104` | `discover`, `acquire`, `parse`, `build_stream`, `calculate_apk`, `build_pivots`, `render_industry`, `render_industries` | Monthly 01_04_A_New_loans_corp **flow** series, independent operation owner. Reuses the published industry, region, APK and workbook semantics of the official 01_05_A reference profile where applicable. |
| `domains.cbr.reporting_forms` | `discover_sources`, `acquire`, `extract_forms`, `normalize_form`, `integrate_forms`, `render_flakes`, `build_form_data`, `build_form_views`, `render_workbook` | All-member DBF extraction with independent schema/lexeme/flag evidence; eight registered source families and six financial model families; complete snapshot and CSV-collection replay. |
| `domains.cbr.escrow` | `discover`, `acquire`, `parse`, `integrate_flakes`, `build_history`, `build_views`, `render_workbook` | Source cell tokens and statuses, selected integrated history, prepared views and independent replay at every boundary. |
| `domains.cbr.corporate_lending.sors_restoration` | `read_source_files`, `load_sources`, `restore`, `run_crosswalk`, `build_pivot`, `render_workbook` | Exact workbook and classifier inputs, tiered inference, strict feasibility and projections. The result carries bounds, proof and publication statuses. |
| `domains.frank_rg` | `discover`, `inspect`, `select`, `scan`, `acquire`, `capture`, `prepare_file`, `plan_updates`, `assess_material`, `plan_cleanup`, `apply_cleanup`, `prepare_archive`, `prepare_archive_to_store` | Logical report registries and typed profiles; caller-supplied directory/store or original bytes; standard naming, revision-qualified copy/rename/removal, and verified archives using shared core ZIP methods. |
| `core.notifications` | `prepare`, `deliver`, `qualify`, `reconcile` | Stable intent from qualified facts and confirmation or reconciliation with the receiving channel. |

Every operation owner publishes its operations in `_registration.py`. Grouping
packages have no operation manifest. The central
`stratbox.domains.registry.operation_catalog()` collects these declarations
and core-owned operations. See the [registry interface](domain-operation-registry.md).

## Shared semantic contracts and packaged references

Stable import owners are `stratbox.shared.identity`, `stratbox.shared.evidence`,
`stratbox.shared.data.*`, `stratbox.shared.reference.*`, and
`stratbox.shared.time.periods`. The bank registry requires a complete
explicit edition manifest, with four separately pinned assets. Rosstat OKVED2
is read from its own three-asset edition. The territory name resolver is a
read-only, conservative association of published labels and reviewed identities;
it is not a crosswalk for a domain's statistical aggregates. Supplied matching rules are validated and content-fingerprinted; source- and perimeter-restricted aliases require explicit matching context.

See [shared contracts](shared-semantic-contracts.md),
[reference editions](reference-snapshots-and-update.md), and
[geography name resolution](geography-name-resolution.md).

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

For service-network releases, a complete snapshot restores the original typed
observations, qualification, acquisition and version evidence. A literal CSV
remains a narrower representation: bank-office CSV reads require a separate
capture date, and an official reference date remains unknown unless supplied
explicitly. See [service-network replay](cbr-service-network.md).

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


## SORS reproducibility

The source loading operation records the exact OKVED2 classifier material
and the edition snapshot as input evidence. SORS strict-model identity
includes the fully qualified classifier use and numerical/model parameters.
The execution identity separately includes solver/optimization settings.
Manually supplied `SorsSourceBundle` instances must carry sealed computation
evidence, and invalid or absent reference evidence fails explicitly.
