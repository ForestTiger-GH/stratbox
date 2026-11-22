# Portable corporate lending data, calculations and views

The 0105a debt and 0104a issuance families provide independent source parsing,
integration of retained flakes, APK calculation, preparation of views and workbook
rendering. Each analytical result has a complete typed snapshot codec. A caller
can save a result through the shared dataset adapter, stop execution, read it
through another adapter and continue the same domain route.

The implemented route preserves the current parsers' semantic tables, their
source coordinates and original byte identities. The parsing profiles remain
bounded to the admitted workbook layouts; snapshot transport does not expand
historical layout support or claim publisher-wide completeness.

Contents:

1. Economic identity — distinguish stocks, flows and their observation periods.
2. Independent operations — choose an entry point and retain a complete result.
3. Source flake integration — control selected releases, conflicts and geography.
4. Dataset storage — continue after a separate read operation.
5. Views and calculations — preserve the analytical boundaries before rendering.
6. SORS input reuse — reuse the complete regional debt flake.
7. Verification and limits — understand what replay validates.

## 1. Economic identity

| Code | Family | Quantity | Observation period | Publication unit |
| --- | --- | --- | --- | --- |
| D105 | `cbr.industries.0105a` | Debt and overdue debt stocks | `report_date`, as of that date | Million rubles |
| I104 | `cbr.industries.0104a` | New loan flow | `reference_period`, the calendar month preceding the release date | Million rubles |

The issuance release date and observation month are both retained. For example,
the release `2019-02-01` describes the month `2019-01`. Snapshot admission checks
this relationship in the metadata and every materialized row. Saving or reading
the value never substitutes a storage timestamp for either economic date.

Both families retain published currency scopes and source labels. Geography
uses the explicit `cbr-industry-geography-2026-06-01` reference edition, embedded
region descriptions and the declared normalization method. An unsupported
reference edition requires a domain decision before a new integration.

## 2. Independent operations

| Code | Operation | Input | Result |
| --- | --- | --- | --- |
| P1 | `parse` | Supplied workbook bytes | Source-local parsed flake |
| P2 | `integrate_flakes` | Qualified parsed flakes | Integrated history with declared release selection |
| P3 | `calculate_apk` | Qualified observations | APK calculation and enriched observations |
| P4 | `build_pivots` | Selected observations and pivot specification | Prepared tables |
| P5 | `render_pivots` | Prepared tables and rendering parameters | Workbook representation |

Each family also exposes `build_flake_snapshot` / `read_flake_snapshot`,
`build_stream_snapshot` / `read_stream_snapshot`, `build_calculation_snapshot` /
`read_calculation_snapshot`, and `build_view_snapshot` / `read_view_snapshot`.
The build functions take `IndustrySnapshotRequest(value, dataset_id, version_id)`;
read functions take `ReadIndustrySnapshotRequest(snapshot)`.

`build_stream` remains an explicit parse-and-integrate composition over supplied
originals. Its `parsed_files` retain the same independently sealed source flakes
as standalone `parse`; each can be saved, read and reintegrated separately.
Geographic normalization applies to the aggregate, while each retained flake
keeps its source-local rows and extraction receipt. `render_industry` and `render_industries` remain convenience
compositions that can calculate APK and prepare views. Their catalog declarations
identify those stages. Independent `render_pivots` consumes prepared values and
performs no source parsing or financial calculation.

## 3. Source flake integration

`IntegrateIndustryFlakesRequest` and `IntegrateIssuanceFlakesRequest` take a tuple
of already parsed flakes. Each flake can come directly from `parse` or from its
snapshot reader. Integration does not need workbook bytes or spreadsheet IO.

Every supplied flake is checked against its computation receipt and domain
context. Its release date, source SHA-256, row count, full-source validation
scope and industry selection must remain coherent. Flakes with different
materialized industry selections are rejected. Error-level source diagnostics
also block integration.

The release policy is explicit: one selected version per release date. Repeated
dates fail with `request.duplicate_release`; integration never silently selects
a different revision or averages duplicates. The caller resolves revision
selection before integration.

`expected_report_dates` optionally declares a larger selected issue set. Missing
members produce a partial result with an explicit stop reason. The latest
accepted release and latest expected release remain separate. Calculations that
require a complete stream reject that partial result. Omitting the argument
declares only the supplied issue selection, with no claim about all publisher
history.

The integrated result retains the original source-local flakes, including their
original receipts. Geography normalization works on private copies for the
integrated table. A later read therefore retains both the source-local context
and the integration result.

## 4. Dataset storage

A snapshot contains a canonical metadata component plus independently typed
table components. Metadata includes source dates, source names and SHA-256,
selection, diagnostics, reference edition, table descriptors and complete
computation lineage. The shared dataframe codec retains nullable values,
categorical dictionaries, ordered axes, Decimal values and supported scalar
types. It verifies the original table fingerprint after reconstruction.

```python
from stratbox.domains.cbr.corporate_lending.industries import debt_0105a as debt
from stratbox.core.storage.datasets.definitions import (
    WriteSnapshotRequest, ReadSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import write_snapshot, read_snapshot

# parsed is a successful debt.parse(...).value.
encoded = debt.build_flake_snapshot(debt.IndustrySnapshotRequest(
    parsed, "cbr.debt.selected-release", parsed.report_date,
))
assert encoded.outcome == "succeeded", encoded.diagnostics
stored = write_snapshot(WriteSnapshotRequest(encoded.value), store=writer)
assert stored.outcome == "succeeded", stored.diagnostics

# reader may be created in a later process and use another physical adapter.
loaded = read_snapshot(ReadSnapshotRequest(stored.value.reference), store=reader)
assert loaded.outcome == "succeeded", loaded.diagnostics
restored = debt.read_flake_snapshot(debt.ReadIndustrySnapshotRequest(loaded.value))
assert restored.outcome == "succeeded", restored.diagnostics
history = debt.integrate_flakes(debt.IntegrateIndustryFlakesRequest(
    (restored.value,),
))
assert history.outcome == "succeeded", history.diagnostics
```

The writer and reader are caller-selected dataset adapters. Physical paths,
network mounts, application database ownership and remote publication are outside
the domain codec. A generic dataset read restores the typed snapshot; the
domain reader then validates its complete profile before exposing a qualified
domain value. A selected subset of components cannot be read as a full flake.

## 5. Views and calculations

The calculation snapshot retains the APK formula, component codes, calculated
rows, enriched stream and input lineage. The view snapshot retains each table,
its dimensions, fixed filters, sheet keys, order, source coverage and receipt.
These values remain independently reusable after storage.

Debt `render_pivots(RenderPivotRequest(...))` renders generic prepared industry
tables. Issuance `render_pivots(RenderIssuancePivotsRequest(...))` renders the
three published currency sheets. The issuance renderer requires the prepared
industry code/name and observation months; it validates those months against
the report-date columns in the supplied view. Existing source-equivalent
workbook compositions remain available for small one-process workflows.

## 6. SORS input reuse

`regional_traditional_from_flake(parsed, as_of_date, policy)` adapts a retained
0105a flake into the same regional observations and geography tables used by
the SORS calculation. It preserves the original publication SHA-256, source
coordinates and economic date. The source byte length remains available in
the original input receipt preserved by the flake snapshot.

SORS requires the complete regional source grid: all six measure/currency
sheets, all admitted regions and all 26 published industry categories. A
selective analytical flake remains useful for ordinary industry analysis but
fails SORS admission. The explicitly supplied rounding policy controls the
publication intervals; file location and float spelling do not select it.

## 7. Verification and limits

The offline regression route covers each family from source flake through file
storage, fresh-adapter reading, integration, another stored history, APK,
another stored calculation, prepared views, another stored view and final
rendering. A separate source-adapter check compares the SORS output from XLSX
with the output from a restored full 0105a flake.

Replay rejects mismatched family contracts, missing components, changed table
identities, incoherent periods and altered source context. Snapshot coverage
describes the selected material; it is independent of publisher inventory
coverage. The dataframe codec uses a bounded supported scalar/dtype vocabulary
and a five-million-cell limit per frame. Arbitrary Python objects and executable
descriptors are outside the format.

The preserved flake values follow the admitted workbook parser's numerical
contract, including its nullable floating point observation column. Exact XLSX
bytes remain a separately retained original; the snapshot does not claim to
recreate the publisher's workbook binary or the lexical spelling of its XML.
