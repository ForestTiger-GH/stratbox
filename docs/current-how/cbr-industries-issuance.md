# CBR industries — monthly corporate loan issuance (01_04_A)

The `stratbox.domains.cbr.operations.corporate_lending.issuance` API processes
Bank of Russia `01_04_A_New_loans_corp_YYYYMMDD.xlsx` monthly workbooks as
corporate loan flows. Debt stocks from `01_05_A_Debt_corp` have separate
source semantics. A single root CBR registration exposes both routes.

Publication discovery and release-period rules belong to
`publications.corporate_lending`. Source parsing and common published dimensions
belong to `tables.corporate_lending`. Cross-release normalization belongs to
`integration.corporate_lending`; APK calculations belong to
`analytics.corporate_lending.industry`; prepared views and rendering belong to
`products.corporate_lending`. Shared industry shapes support both stock and flow
without assigning issuance to the debt implementation.

## Public operations

| Operation | Request | Output |
| --- | --- | --- |
| `discover` | `DiscoverIssuanceRequest` | Dated official source links |
| `acquire` | `IssuanceSourceLink` | Verified original `AcquiredSource` |
| `parse` | `ParseIssuanceRequest` | One semantic `ParsedIssuanceFile` |
| `build_stream` | `BuildIssuanceStreamRequest` | Explicit parse/integrate composition over selected originals |
| `integrate_flakes` | `IntegrateIssuanceFlakesRequest` | History built from independently retained source flakes |
| `calculate_apk` | `CalculateIssuanceApkRequest` | Shared APK calculation and augmented stream |
| `build_pivots` | `PivotIssuanceRequest` | Prepared two-dimensional product tables |
| `render_pivots` | `RenderIssuancePivotsRequest` | Workbook encoding from prepared tables |
| `render_industry` | `IssuanceWorkbookRequest` | One independently verified XLSX representation |
| `render_industries` | `RenderIssuanceIndustriesRequest` | Batch of XLSX representations from one verified snapshot |

Flakes, integrated histories, calculations and prepared views each have complete
snapshot/read operations. The [corporate lending route](cbr-corporate-lending.md)
shows how to retain and continue each boundary through neutral dataset storage.

Use `OperationResult.outcome` and diagnostics before consuming `.value`. Only
complete streams can be rendered by `render_industry`; partial collection is
an explicit outcome, never silently treated as complete. Writing to a store,
selecting an output location, caching, downloading for Colab and scheduling
remain consumer responsibilities. `discover` accepts an optional exact HTML
`SourcePayload` for offline replay; `parse` and `build_stream` accept exact
workbook payloads. `acquire` uses the shared restricted HTTP transport.

## Period and identity

The release name `..._20260801.xlsx` refers to loans issued in **July 2026**.
Each observation retains `report_date=2026-08-01` and
`reference_period=2026-07` separately. Release identity, bytes digest and
cell lineage are preserved. The Excel report displays the actual reference
month; the returned `IssuanceWorkbookResult` exposes both time scales.

## Semantic boundaries

- Three currencies: rubles, foreign currency and precious metals, total.
- One measure: `new_loans` (millions of RUB). Issuance has no overdue measure.
- Published `total` is used verbatim; never reconstructed as an industry sum.
- APK uses the same additive **industry formula** as 01_05, per period,
  currency and region. A missing source component blocks the computation.
- The complete ordered 26-industry schema and 96-row geographic schema are
  checked against the current validated SORS publication layout.
  `IndustrySelection(("apk", "total"))` only reduces materialized observations;
  **all original numerical cells** still participate in the full validation.
  APK automatically expands to five published source industries. The published
  total remains a source value, not a sum. Alias
  handling is reused with the portfolio series. A structural change fails
  closed and requires an explicit adapter update.
- Currency component differences greater than 1 million RUB are reported as
  **warnings** (independently rounded official numbers); values remain exact
  to the source. Negative observations are errors, blanks remain missing.

## Offline example

```python
from pathlib import Path
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.operations.corporate_lending import issuance as loans

path = Path("01_04_A_New_loans_corp_20260801.xlsx")
request = loans.ParseIssuanceRequest(SourcePayload(path.read_bytes()), path.name)
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection

stream_run = loans.build_stream(loans.BuildIssuanceStreamRequest(
    (request,), selection=IndustrySelection(("apk", "total")),
))
if stream_run.outcome != "succeeded":
    raise RuntimeError(stream_run.diagnostics)
workbook_run = loans.render_industries(loans.RenderIssuanceIndustriesRequest(
    stream_run.value, ("apk", "total"),
))
if workbook_run.outcome != "succeeded":
    raise RuntimeError(workbook_run.diagnostics)
for book in workbook_run.value.items:
    Path(f"{book.industry_code}.xlsx").write_bytes(book.representation.data)
```

Consumers that need historical reports discover the published dates, acquire
or reuse verified monthly sources and build a stream from the full selected
set. Do not derive URLs by guessing release dates.
