# CBR industries — monthly corporate loan issuance (01_04_A)

The `stratbox.macrobanks.cbr_industries.issuance_0104` package is the second
series adapter in the industry-statistics domain. It reads the Bank of Russia
`01_04_A_New_loans_corp_YYYYMMDD.xlsx` monthly workbooks as corporate loan
**flows**, independently of the `01_05_A_Debt_corp` **stock** series.

## Public operations

| Operation | Request | Output |
| --- | --- | --- |
| `discover` | `DiscoverIssuanceRequest` | Dated official source links |
| `acquire` | `IssuanceSourceLink` | Verified original `AcquiredSource` |
| `parse` | `ParseIssuanceRequest` | One semantic `ParsedIssuanceFile` |
| `build_stream` | `BuildIssuanceStreamRequest` | Canonical regional-industry history |
| `calculate_apk` | `CalculateIssuanceApkRequest` | Shared APK calculation and augmented stream |
| `build_pivots` | `PivotIssuanceRequest` | Generic two-dimensional pivots |
| `render_industry` | `IssuanceWorkbookRequest` | In-memory XLSX representation |

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
  checked against the current validated SORS publication layout. Alias
  handling is reused with the portfolio series. A structural change fails
  closed and requires an explicit adapter update.
- Currency component differences greater than 1 million RUB are reported as
  **warnings** (independently rounded official numbers); values remain exact
  to the source. Negative observations are errors, blanks remain missing.

## Offline example

```python
from pathlib import Path
from stratbox.data import SourcePayload
from stratbox.macrobanks.cbr_industries import issuance_0104 as loans

path = Path("01_04_A_New_loans_corp_20260801.xlsx")
request = loans.ParseIssuanceRequest(SourcePayload(path.read_bytes()), path.name)
stream_run = loans.build_stream(loans.BuildIssuanceStreamRequest((request,)))
if stream_run.outcome != "succeeded":
    raise RuntimeError(stream_run.diagnostics)
for industry in ("apk", "total"):
    workbook_run = loans.render_industry(loans.IssuanceWorkbookRequest(stream_run.value, industry))
    if workbook_run.outcome != "succeeded":
        raise RuntimeError(workbook_run.diagnostics)
    Path(f"{industry}.xlsx").write_bytes(workbook_run.value.representation.data)
```

Consumers that need historical reports discover the published dates, acquire
or reuse verified monthly sources and build a stream from the full selected
set. Do not derive URLs by guessing release dates.
