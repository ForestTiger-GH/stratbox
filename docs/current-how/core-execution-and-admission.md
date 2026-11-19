# Execution, admission and recovery

Stratbox exposes versioned Python operations and an optional read-only
JSON interface. Domain modules own release selection, labels, interpretation
and calculations. General-purpose HTTP, file, archive and format commands
live in `stratbox.core.storage`, `stratbox.core.network`, and `stratbox.core.formats`. Callers choose periods, repetition and destinations.

The runner resolves every operation's outcome against all registered external
effect receipts before validating the result and emitting the optional terminal
event. An explicit domain partial result remains partial after known failed
effects; an unresolved effect or contradictory receipt yields `unknown`.
See [Execution finalization and effect integrity](../architecture/execution-finalization.md)
for the canonical matrix, effect identities, diagnostic precedence and limits.

## Discover and bind

Use `stratbox.domains.registry.operation_catalog().describe()` to obtain operation IDs,
request and result types, versions, capability roles, effect descriptions
and limits. The domain registry discovers local declarations from built-in packages.
Import `wire_schemas` and `invoke_read_only` from
`stratbox.core.execution.machine` and pass `catalog=operation_catalog()`
explicitly. The generic executor has no direct imports of concrete domains.

| Read-only JSON operation | References resolved by the caller | Returned data |
| --- | --- | --- |
| `cbr.offices.parse` v1 | Source bytes, optional expected SHA-256 | Date, row count and result digests |
| `cbr.offices.compare` v2 | Candidate and optional baseline | Change state, reason, count, evidence layers and coverage |
| `frg.plan_cleanup` v1 | Scoped directory reference | Plan digest and action count |

`invoke_read_only(raw, catalog=..., materials=...)` accepts UTF-8 JSON bytes. The envelope contains
`operation_id`, `contract_version` and `input`. An application-supplied
`MaterialResolver` resolves each opaque reference under its current read
permissions. The codecs reject extra fields, duplicate keys, excess
nesting, incorrect types and unknown operations before material access.
The result projection contains bounded diagnostics and excludes input
material, paths and URLs. Python operations remain available by direct
import, including the operations that write or send.

The default local context is for trusted Python with the selected adapters.
When a call omits its HTTP or storage adapter and the role has no explicit
binding, it can use a default provider installed in the environment. The
runtime looks for one factory under the `default` entry point in the
`stratbox.runtime` group or under `stratbox_*/_stratbox_runtime.py` beside
the core package. A sibling factory exposes `create_providers()`. The
factory returns a `Providers` bundle, which the runtime caches for the
process. Ambiguous or invalid configurations raise a provider error.

A managed `ExecutionContext` requires one matching `ProviderBinding` for
each capability used, with the expected version and guarantees. Use
`select_provider` or an explicit `probe_provider` to test binding and readiness.
A binding describes the selected trusted adapter. The accepting provider
enforces the actual scope and effect conditions.

`ExecutionBudget` can cap time, input, wire, decoded and output bytes, HTTP
requests, visited objects, cells, temporary bytes and archive nesting.
The strictest value across the operation, application ceiling and request
applies. Supported nested readers and writers share a meter. Long in-process
decoder calls, provider calls and OS lookups may complete at their next
checkpoint. A consumer with a hard deadline or resource requirement uses
an independently constrained adapter.

Cancellation is cooperative **at handler checkpoints**; it is not a promise
of immediate preemption. A request arriving after a handler completes does
not reclassify established success. Effect receipts from earlier work remain
visible even when a later checkpoint accepts cancellation.

Execution events use envelope version 3 and include correlation IDs, stage
timing, classified outcomes and incident IDs. A separate optional technical
sink receives the incident ID, exception type and a bounded list of function
names and line numbers. The result reports each sink's drop count. An acceptance policy requiring durable audit enforces it
at the receiving provider before commit.

## Acquire, qualify and inspect

`RequestsTransport` checks endpoints, each redirect, transfer encoding and
response limits. `PeerBoundTransport` also admits numeric destination addresses
before connecting and verifies the established peer and TLS hostname. Managed
acquisition requires a transport that enforces the destination and accounts
for HTTP budgets. Operations with read-only POST semantics can opt in to
POST retries. A conditional 304 needs a matching strong validator, request
and final target. Managed reuse also requires owner verification. A caller
can request a full response after `http.full_representation_required`.

`AcquisitionReceipt` describes the response and its exact decoded content.
`UsedInputReceipt` identifies the bytes that the parser used. `ParsedRelease`
carries provenance, analysis qualification, a manifest digest and, when
available, a separate facts digest. The literal representation has its own
digest. An offline source ID is a label whose provenance is `offline_bytes`.
An HTTP observation qualifies to the level reported by the selected provider.
`RoutedTransport` validates the original endpoint and its configured HTTPS
gateway. Routed receipts carry the logical and physical target hashes and
qualify TLS to the gateway host. They require a full response. Managed
acquisition requires separately verified upstream identity.

For a workbook, call `preview_workbook` in `stratbox.core.formats.spreadsheets.workbook_input`.
It accepts a sheet name, one-based row and column and a bounded width and
height. No table schema is required. The reader identifies XLSX, XLSM, XLSB
and XLS by their contents. XML readers return cached values and disable
active parts and external relationship loading. Legacy readers report
decoder values and provide limited formula, formatting and date evidence.
Selecting a cell range is a research operation. Known domain operations
apply their own published-series rules.

Monthly CBR office parsing records the actual sheet, coordinates and date
basis. Its v3 parse and capture can return `OfficesRegCandidates` as a
partial result with the source identity and candidate coordinates. Supply
`sheet` and, when needed, `national_row` to select the block. Set `last_row`
to qualify an explicitly bounded fragment. A missing formula cache stays
blank in the literal CSV and marks the affected indicator as unresolved. The literal
CSV preserves additional columns. A result with `qualified_subset`
identifies usable observations and lists excluded fields. A result with
`literal_only` preserves the table for inspection. Use `spreadsheet_view` in
`stratbox.core.rendering.spreadsheet_view` for an interactive XLSX projection
of literal CSV. This projection uses text cells. The literal CSV retains
its exact bytes and distinct identity.

For a constrained preview, pass a `WorkbookWorker` and its explicit
`workbook_decoder` binding with `isolation_enforced` and
`require_isolation=True`. The result is checked against the source digest,
requested sheet and range, expected shape and output bounds. The adapter
provides process, network, filesystem and runtime constraints. The trusted
direct XLS readers use the `excel-legacy` extra, and the binary XLSB reader
uses `excel-binary`.

## Commit and reconcile

| Effect | Local API and outcome | Managed accepting port |
| --- | --- | --- |
| Original storage | `source.save_original`, `source.receive_to_store`, `source.read_original` and `source.reconcile_original` | The store admits a staged commit and owns the observed revision |
| Byte storage | `write_verified_bytes`, with `immutable`, `replace_expected_revision` or `best_effort_verified` | Destination owner supplies conditional commit and actual evidence |
| FRG mutation | `plan_cleanup` then `apply_cleanup`, with exact directory, plan digest and source revisions | `ScopedMutationStore.commit_mutation` checks the actual intent and current grant |
| FRG ZIP | `prepare_archive_to_store` uses private staging, verifies selected bytes and reads back the destination | `ScopedStagedWrite.commit_admitted` checks the plan, scope, payload, mode and expected revision |
| Notification | `prepare` on a registered journal and `deliver` on a persisted dispatch ID | `NotificationConsumer.accept` and `lookup` verify the grant, route revision, attempt, fence and structured payload |

The streaming FRG request defaults to `immutable`. Matching existing bytes
return `already_present`. An explicit `replace_expected_revision` requires the
current storage revision. Local conditional storage coordinates cooperating
writers. A managed writer must provide the actual guarantees it declares
for its backend. Local best-effort replacement is available in the local
profile.

Keep the effect ID and intended digest after an unknown result. Ask the
storage owner about that exact effect, and verify the destination revision
and bytes before considering another write. For a local immutable ZIP the
existing destination can be read and compared by SHA-256. An identical
immutable retry returns the existing result and retains the effect ID.
For cleanup, inspect the current directory and the affected source and
destination before re-planning. Per-action receipts identify completed,
failed, uncertain and unattempted work.

Managed notifications atomically record the checkpoint and additions to the
queue. An unknown handoff stays pending for reconciliation. The receiving
owner qualifies acceptance and enforces the current grant, route and
payload binding. The consumer also owns evidence for its downstream
effects. [Notification API and usage](notifications.md)

Use `computation_identity`
for immutable computation reuse. At each access the cache owner checks
current scope, audience, revision and revocation.

[Domain API and installation](universal-business-core.md)
