# Frank RG report files

This domain identifies delivered Frank RG reports, selects report periods,
assigns standard filenames, and prepares verified file effects and archives.
Workbook originals remain unchanged. Physical workbook evidence, explicitly
bound semantic flakes, integration, history, calculations and prepared products
are independently callable and independently retainable.

## Source and method boundaries

Root `REGISTRY_*.yaml` resources describe four logical report groups and their
series. They contain source IDs, titles, period-label kinds and profile IDs.
Directories, URLs, filenames and Python entry points belong to other owners:

| Owner | Responsibility |
| --- | --- |
| [Publications](../../src/stratbox/domains/frank_rg/publications/) | Registry admission, typed file evidence, recognition, selection, names and cleanup plans |
| [Profiles](../../src/stratbox/domains/frank_rg/publications/profiles.py) | Supplier naming rules, supported formats, period cutoffs and executable methods |
| [Bindings](../../src/stratbox/domains/frank_rg/operations/bindings.py) | Resolve logical sources to compatible registered profiles |
| [Operations](../../src/stratbox/domains/frank_rg/operations/) | Independent operations through the shared runner and explicit file-effect handlers |
| Caller | Runtime directory, storage providers, supplied bytes and output destination |

`families()`, `all_sources()` and `validate_all_profiles()` expose the available
logical sources. The operation catalog discovers one `frank_rg` owner with
the `frg.*` operation namespace. Importing the domain requires no spreadsheet
or dataframe dependency.

The [universal material flow](./universal-data-flow.md)
provides typed handoff, retained references and independent named input/output
providers. `discover`, `scan`, `acquire`, `plan_cleanup`, `apply_cleanup` and
`prepare_archive` accept `selection=ProviderSelection(...)`; the streaming
archive composition also accepts `output_selection`. Binding-only invocation
resolves the selected provider from the execution context.

## Directory input in Colab or a mounted filesystem

```python
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg

inputs = LocalFileStore(root="/content")
catalog = frg.scan(frg.DiscoveryRequest("."), store=inputs)
assert catalog.outcome == "succeeded", catalog.diagnostics

planned = frg.plan_cleanup(frg.PlanCleanupRequest("."), store=inputs)
assert planned.outcome == "succeeded", planned.diagnostics
plan = planned.value
print(plan.actions)

# Apply the exact reviewed plan. The default copies selected originals.
applied = frg.apply_cleanup(
    frg.ApplyCleanupRequest(plan, ".", plan.identity.sha256), store=inputs,
)
assert applied.outcome == "succeeded", applied.diagnostics
```

Use a different `LocalFileStore(root=...)` for a filesystem mount, or pass a
different `FileStore` implementation. Network transport, mounting and access
configuration belong to that provider. Discovery, identification and selection
are also independently callable as `discover`, `inspect` and `select`.

`delete_others=True` explicitly plans renaming and removal of recognized older
reports. Unknown files and reports with invalid period labels remain untouched.
Applying a plan rechecks its directory, profile methods, file versions and exact
digest. Same-period candidates with different bytes block cleanup. Byte-identical
copies can be resolved after verification, making repeated copy runs idempotent.

## Input supplied by a specialized method

An external method can supply bytes and explicit report context without a
directory, filename or file-store provider:

```python
from datetime import date
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.operations.source.original_definitions import OriginalDestination, SaveOriginalRequest
from stratbox.core.operations.source.originals import save_original
from stratbox.domains import frank_rg as frg
from stratbox.shared.evidence import SourcePayload

# raw_bytes is the exact material returned by the caller's acquisition method.
captured = frg.capture(frg.CaptureRequest(
    source_id="frg.express.issuance",
    period=frg.ReportPeriod(date(2026, 5, 1)),
    payload=SourcePayload(raw_bytes),
    format="xlsx",
))
assert captured.outcome == "succeeded", captured.diagnostics
prepared = frg.prepare_file(frg.PrepareFileRequest(captured.value))
assert prepared.outcome == "succeeded", prepared.diagnostics

outputs = LocalFileStore(root="/content/stratbox_outputs/frg")
saved = save_original(
    SaveOriginalRequest(prepared.value.payload,
                        OriginalDestination(prepared.value.filename)),
    store=outputs,
)
assert saved.outcome == "succeeded", saved.diagnostics
```

`acquire` reads an identified filesystem asset with before/read/after version
verification. Both acquisition routes feed the same `prepare_file` operation.
The supplied source and period are caller assertions checked against the
registered profile; this scope does not decode the workbook to confirm them.

## Revision evidence and archive output

`plan_updates` can compare observed metadata with `SourceCheckpoint` values.
Its `metadata_unchanged` result is only a filesystem observation.
`force_refresh=True` requests exact material verification; `assess_material`
compares acquired byte identities. `checkpoint_for` returns a candidate that
the consumer commits after its intended effects complete.

Weekly labels mean a numbered week within a month. A `Q` filename marker is
part of recognition; it does not establish an economic aggregation period.

Frank RG prepares the selected members and their standard names. Shared core
archive functions create and verify ZIP bytes. Use `prepare_archive` for a small
in-memory result and `prepare_archive_to_store` for staged streaming to a caller
selected store. The latter supports large files, immutable retries and conditional
replacement. See the [streaming archive usage](./frg-streaming-archive.md).

Both archive routes include `manifest.json` with the selected original members,
their logical series and issues, byte identities, media types and completed
dispositions. Its logical identity excludes source directories, provider names,
file revisions and cleanup plan locations. The optional `selection_report.json`
remains a separate supplemental member with its own identity. Complete archive
membership describes the selected reports; publisher inventory coverage remains
unspecified. Packaging preserves every selected original's exact bytes.


## Complete table route and semantic profile admission

The fourteen registered sources have technical workbook extraction for XLSX,
XLSM, XLS and XLSB. `extract` consumes an `AcquiredReport`; `extract_snapshot` and
`read_extract` retain/replay all extracted cells, sheet dimensions, available
merged ranges and decoder qualifications. `validate`, `compare` and `readable`
operate on the retained extract independently of the original. OOXML numeric
lexemes remain exact. Binary formats retain exact decoded binary numbers and
explicitly state the decoder's limitations for formulas, formatting and merges.

Every source currently declares `supplied_profile_required` in
`all_profile_availability()`. Real supplier workbook fixtures are not retained
in this repository, so no business layout is claimed from a filename, report
title or `Q` marker. The operational route is complete for a caller supplying an
explicit `SemanticProfile`; discovery of a file alone supplies no economic
semantics.

A profile binds one exact original identity to typed cell bindings. Each binding
states the sheet and coordinate, subject, metric and definition version, unit,
measurement scale, quantity kind, economic period and reporting perimeter.
Decimal separators and missing tokens are explicit. Stock metrics require an
`as_of` period, flows require an interval, and a supplier snapshot label cannot
substitute for either. Reusing the profile on changed original bytes fails
admission. Duplicate cell bindings, duplicate semantic keys, absent formula
caches, errors and ambiguous numeric values also fail admission.

```python
from datetime import date
from decimal import Decimal
from stratbox.domains import frank_rg as frg
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef

physical = frg.extract(frg.ExtractRequest(captured.value))
assert physical.outcome == "succeeded", physical.diagnostics

# The coordinates and semantics below are a caller-owned example, not a
# declaration of an actual Frank RG workbook layout.
profile = frg.SemanticProfile(
    physical.value.series_id, "application.reviewed_layout.v1", 1,
    physical.value.source_identity,
    (frg.CellBinding(
        "Reviewed sheet", 2, 3, SubjectRef("bank", "reviewed-bank-id"),
        MetricRef("reviewed.metric", "RUB", "stock", "1", Decimal("1000000")),
        PeriodRef("as_of", as_of=date(2026, 4, 30)),
        "explicitly_reviewed_reporting_population",
    ),),
)
flake = frg.build_flake(frg.BuildFlakeRequest(physical.value, profile))
```

`build_flake` produces a source-local semantic flake that retains issue/asset
identity, original and extract identities, profile identity/version, exact raw
tokens, units, periods and missing statuses. `flake_snapshot` and `read_flake`
restore that result independently of spreadsheet readers and current profiles.

## Integration, history, calculations and products

| Owner | Responsibility | Main operation IDs |
| --- | --- | --- |
| `publications` | Source recognition, issue labels, original acquisition, naming and maintenance plans | `frg.discover`, `frg.acquire`, `frg.capture` |
| `tables` | Physical workbook evidence and explicit source-local cell interpretation | `frg.extract`, `frg.build_flake`, independent snapshot/replay operations |
| `integration` | Explicit dataset placement, strict alignment and publication history | `frg.integrate`, `frg.align`, `frg.build_history` |
| `analytics` | Qualified comparisons of revisions with matching semantic keys | `frg.calculate` |
| `products` | Prepared observation selections and portable renderings | `frg.prepare_view`, `frg.view_snapshot`, `frg.read_view`, `frg.render_view` |
| `operations` | Admission, runtime accounting, evidence and common source cards | One `frank_rg` owner with `frg.*` IDs |

`integrate` places a semantic flake in a caller-named common `ObservationBatch`.
`align` requires identical metric definitions and rejects ambiguous duplicate
semantic keys. `build_history` preserves every explicitly supplied publication
release as separate history dimensions; it does not overwrite revisions or infer
which vintage is the latest.

`calculate` emits same-period revision deltas only when subject, metric,
definition, units, scale, period, dimensions and perimeter match exactly. Added,
removed, missing, suppressed and semantically incompatible values remain
qualified; missing values never become zero. The result uses the common
observation schema and has the same independent snapshot/replay route as
integrated data. Cross-period growth, market totals, seasonal adjustments and
forecast models require their own explicitly reviewed semantics.

`prepare_view` selects admitted observations without aggregation. Prepared
views have complete snapshot/replay and CSV/JSON/JSONL rendering. Original,
physical-extract, source-flake, integrated, historical, calculated and view
snapshots can each be stored independently through the common dataset adapters.
Rendered representations can be wrapped in a typed material artifact and
retained or copied through the common material operations.

File housekeeping remains available separately. Cleanup planning and application
are classified as maintenance and contribute no data-processing or publishing
capability. Archive preparation preserves selected original bytes with a
verified manifest. Per-series source cards expose physical support and the
explicit condition on semantic processing for all fourteen sources.
