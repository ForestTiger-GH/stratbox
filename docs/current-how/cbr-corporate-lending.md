# Corporate lending: source tables, integration, calculations and products

The corporate lending domain separates source interpretation, integrated histories,
analytical models and prepared products. The 0105a debt and 0104a issuance families
provide independent source parsing,
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
7. Independent national and SME observations — retain all source periods and precise values.
8. Functional owners — locate source, model, product and execution responsibilities.
9. Verification and limits — understand what replay validates.

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
from stratbox.domains.cbr.operations.corporate_lending import debt
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

## 7. Independent national and SME observations

`cbr.tables.extract` reads an identified original into a `WorkbookFlake`. The
neutral workbook reader retains every source sheet, exact numeric lexemes,
scalar kinds, formulas and cached values, number formats, merged ranges and
coordinates. This source artifact can be persisted before a particular
interpretation or analytical model is chosen.

`cbr.corporate_lending.extract_observations` interprets that flake with an
explicit corporate publication profile. It consumes retained cells and performs
no workbook IO, shared geography matching, rounding inference or solver work.
All recognized periods are retained by default. A caller can select a tuple of
periods; the resulting coverage then records the narrower selection.

| Code | Series keys | Source observation semantics |
| --- | --- | --- |
| H1 | `corp_new_loans_a`, `corp_new_loans_c`, `sme_by_activity` | Monthly loan flows; Russian month labels become `YYYY-MM` reference periods |
| H2 | `corp_debt_a`, `corp_debt_c` | National traditional-category and OKVED2 stocks, with debt/overdue and currency dimensions |
| H3 | `sme_debt` | National SME and SME-IE totals, preserving the two published portfolio rows |
| H4 | `sme_debt_activity`, `sme_ie_debt_activity` | National SME and SME-IE OKVED2 stock histories |
| H5 | `sme_debt_subj_f`, `sme_debt_subj_i`, `corp_debt_subj` | Geographic stock histories with source geography labels |
| D1 | `fd_okved2`, `sme_fd_okved2` | Federal district/activity tables with separate loan-flow, debt and overdue sheets |

These thirteen keys have the `cbr.corporate_lending.` series prefix.
The family's `structure_by_benchmark_interest_rate_type` and
`sme_borrowers_info` tables use the shared statistics route; they are outside
this source-specific interpreter and the SORS dependency set. Flow
observations use `period_basis=reference_month`; stock observations use
`period_basis=as_of`. The federal district publication contains both kinds:
a June 1 issue can contain May flows and June 1 stocks. Its source dataset
retains both periods and all three measures. SORS subsequently selects stock
observations for its requested date.

The observation table retains the published row label, its normalized key,
period label, source coordinates, measure, currency and portfolio scope.
`value` is an exact integer or Decimal. `raw_token`, `cell_kind`, `formula`,
`number_format` and an explicit status distinguish numeric values, numeric text,
blank cells, published markers and formulas without a cached value. A missing
source number remains missing. Source-local interpretation adds no SORS
intervals or accepted-fact flags.

```python
from stratbox.domains.cbr.operations.corporate_lending.source_definitions import (
    ExtractCorporateObservationsRequest, CorporateObservationSnapshotRequest,
    ReadCorporateObservationSnapshotRequest,
)
from stratbox.domains.cbr.operations.corporate_lending.source_operations import (
    extract, build_snapshot, read_snapshot,
)

# source_flake is a successful cbr.tables.extract value or its snapshot replay.
observations = extract(ExtractCorporateObservationsRequest(source_flake))
assert observations.outcome == "succeeded", observations.diagnostics
encoded = build_snapshot(CorporateObservationSnapshotRequest(observations.value))
assert encoded.outcome == "succeeded", encoded.diagnostics
replayed = read_snapshot(ReadCorporateObservationSnapshotRequest(encoded.value))
assert replayed.outcome == "succeeded", replayed.diagnostics
```

The independent snapshot stores every admitted observation, column dtype,
period selection, diagnostic, coverage statement and original reference. It
can pass through the same neutral dataset storage route as industry flakes.
Unknown source layouts produce explicit diagnostics or fail admission; a
complete workbook flake still preserves the original cells for later work.

## 8. Functional owners

| Code | Owner below `stratbox.domains.cbr` | Responsibility |
| --- | --- | --- |
| O1 | `publications` | Source catalog, acquisition profiles, HTML discovery, release editions and publication identity |
| O2 | `tables.corporate_lending` | Source contracts, profiles, layout/alias interpretation, independent observations and flake codecs |
| O3 | `integration.corporate_lending` | Cross-release industry histories and shared geography alignment |
| O4 | `analytics.corporate_lending.industry` | APK formula, component requirements and calculated results |
| O5 | `analytics.corporate_lending.sors` | Qualified model input preparation, reconstruction, quantity graph, constraints, rounding policies, optimization and crosswalk |
| O6 | `products.corporate_lending` | View contracts, prepared tables, workbook rendering and product snapshots |
| O7 | `operations.corporate_lending` | Request definitions, runner admission, budgets, evidence and flat operation references |

`publications.corporate_lending` owns the discovered publication asset types,
HTML link discovery and filename/date/reference-period rules. Source workbook
parsers consume those edition rules without owning acquisition.

The shared `industry` packages own the common published dimensions, geography,
source-column selection, APK computation and pivot behavior used by debt and
issuance. Debt-specific sheet semantics remain under `tables...debt`; issuance
sheet semantics remain under `tables...issuance`. Source-published geography
layout and aliases belong to `tables...industry.geography`; cross-release
normalization belongs to `integration...industry.geography`.

SORS source adapters consume the independent observations. The method-specific `analytics.corporate_lending.sors.inputs` owner selects
the model date, aligns published labels with admitted classifier/geography
editions, adds declared rounding intervals and validates the complete input
system. Only that projection converts precise source numbers to the floating
point arithmetic used by the model. The original precise value and source
references remain separately available.

[The SORS continuation route](cbr-sors-snapshots.md) describes its complete
input requirements, pure calculation boundary, prepared views and replay.

## 9. Verification and limits

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

The specialized 0105a/0104a semantic flakes follow their admitted workbook
parser's numerical contract, including a nullable floating point observation
column. The independent all-sheet workbook flake and national/SME source
observation route retain precise source numbers and numeric lexemes. Exact XLSX
bytes remain a separately retained original; the snapshot does not claim to
recreate the publisher's workbook binary or the lexical spelling of its XML.
