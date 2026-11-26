# Rosstat source processing

The single immutable [domain catalog](../../src/stratbox/domains/rosstat/domain.py)
contains four publication channels and three continuing table series.
Publication discovery and numerical interpretation have different evidence
boundaries.

| Table series | Supported scientific scope |
| --- | --- |
| `rosstat.short_term_indicators` | One coherent KEP2 set with eleven indicators and annual, quarterly and monthly source periods |
| `rosstat.population_municipalities` | Population stock layouts for 2022, 2023 and 2024, including source-native geography |
| `rosstat.socioeconomic_regions.industrial_production` | Industrial indices in reviewed June/August 2026 regional archive layouts |

The national report remains a publication channel. Its real numerical tables
require reviewed geometry and semantic mappings before individual table series
can be declared. Other regional archive tables require the same census and
source review. A generic text decoder establishes physical evidence only.

## Standard lifecycle

The shared acquisition operation prepares an official request, fetches exact
material and identifies its outer format. Workbook processing uses:

`command.workbook.decode` → `command.table.extract` →
`command.table.interpret` → `command.observations.validate`.

Each boundary has typed named inputs and outputs. The standard operation
`operation.series.extract_workbook` accepts a material, an already decoded
`physical` workbook, or selected `tables`. Supplying a later accepted entrance
cuts the preceding work from the prepared plan.

```python
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

original = Material(workbook_bytes, source_id="rosstat.short_term_indicators",
                    metadata={"issue_id": "2026-08", "asset_id": "main_workbook"})
with StrategyBox() as box:
    result = box.invoke(
        "operation.series.extract_workbook",
        inputs={"material": original},
        target=SeriesTarget("rosstat.short_term_indicators"),
    )
    assert result.outcome == "succeeded", result.diagnostics
    dataset = result.output("dataset")
```

Extraction and interpretation methods consume existing evidence. They perform
no hidden network request or workbook decoding. The physical identity must
match its exact source material.

Regional archives use the standard archive inspection/member extraction
commands first. Select the actual industrial workbook member explicitly, retain
the container identity and member name, then pass the resulting material to
workbook decoding with the logical table target.

## KEP2 semantics

The eleven indicators are investment, wages, construction, freight turnover,
retail trade, food retail, nonfood retail, catering, wholesale trade, paid
services and agriculture. The shared dictionary in
`common/kep2.py` owns their names and units. Some source sections publish
different measure sets; agriculture's admitted scope is the year-on-year index.

The parser preserves annual/quarterly/monthly periods, printed units and
scales, exact decimal values, raw tokens, notes, source cells and last-source-row
selection decisions. A displayed next-month date is kept separate from its
economic interval. Source indices remain reported indices. The independent
`rosstat.index_growth` calculation specializes `command.calculate.index`
with the declared percent-index-minus-100 method.

## Geography and regional indices

Population is a count stock at the printed 1 January date. The title, table
heading and requested issue must agree. Total, urban and rural measures remain
distinct. The 2022/2023 identities are dated source rows; 2024 supplies TERSON-MO
codes. Repeated source codes retain their independent source perimeters and
row identities. A canonical municipal crosswalk requires separate evidence.

Regional industrial observations retain monthly year-on-year, year-to-date
year-on-year and previous-month bases. Monthly and accumulated intervals remain
different observations. Published notes, including the source's weight-base
change, remain attached.

## Retention, products and observability

Rows carry source identity, economic period, values/statuses, exact source
coordinates, units, scale, dimensions and evidence references.
`command.value.encode` / `command.value.decode` retain shared values without
rerunning source parsing. `command.dataset.ingest` receives a dataset object.

The product target `rosstat.kep2.monthly.xlsx` supplies
`command.view.prepare` and `command.product.render`. It creates a retained
monthly selection and XLSX with source evidence. Generic CSV/JSON products use
the core renderer. Storage and final publication are separate commands.

Every invocation uses the common execution service and journal. Notifications
consume accepted-output/effect facts through separate prepare/deliver/reconcile
commands. An unknown delivery remains in `RunResult.effects`; it does not
invalidate an already accepted source dataset or authorize blind resend.

See [publication evidence](rosstat-publications.md) and
[catalog responsibilities](rosstat-capability-migration.md).
