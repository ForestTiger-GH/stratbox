# Minfin: fiscal series through standard commands

[`domains/minfin/domain.py`](../../src/stratbox/domains/minfin/domain.py) is the
single static entry point. It explicitly lists thirteen continuing source
series, shared immutable access facts, numerical purposes and products.

## Sources and common facts

| Series | Frequency and source meaning | Representation |
| --- | --- | --- |
| `minfin.fedbud.annex3.monthly`, `.quarterly`, `.annual` | Federal budget; YTD monthly/quarterly and annual flows | XLS/XLSX |
| `minfin.conbud.monthly`, `.quarterly`, `.annual` | Consolidated budget; the corresponding budget perimeter and periods | XLS/XLSX |
| `minfin.subbud.monthly`, `.quarterly`, `.annual` | Regional budget perimeter; the corresponding frequency and basis | XLS/XLSX |
| `minfin.nwf.flows` | NWF movement/management table with row-specific stock or flow semantics | XLS/XLSX |
| `minfin.nwf.volume` | Fund-volume publication | DOCX |
| `minfin.nwf.preferred_shares` | Preferred-share publication | DOCX |
| `minfin.nwf.veb_deposits` | VEB-deposit publication | DOC original, explicit conversion to DOCX |

The exact source IDs are declared in `series/`; shared asset IDs, filename
rules and official indexes live in `common/publications.py` and
`common/access.py`. Common periods, numbers and row dictionaries have one
owner. A table record refers to these facts directly through narrow command
settings. Source specifications do not assemble executable operations.

## Lifecycle

| Stage | Input → output | Owner |
| --- | --- | --- |
| Request | Locator/query → `RequestSpec` | Domain publication rules |
| Publication scan | Supplied HTML `Material` → `PublicationListing` and coverage | Domain card/attachment interpretation |
| Selection | Listing/query → `AssetSelection` | Domain source/issue rules |
| Acquisition | Prepared request → original `Material` | Core and explicit HTTP provider |
| Workbook decode | Material → `WorkbookEvidence` | Core physical decoder |
| Document conversion | DOC material → converted material with original identity | Core and explicit converter provider |
| Document decode | DOCX/PDF material → `DocumentEvidence` | Core physical decoder |
| Table selection | Physical evidence → `TableEvidenceSet` | Domain source geometry |
| Interpretation | Selected tables → `SourceDataset` and assessment | Domain fiscal semantics |
| Validation/alignment | Dataset → qualified source/integrated dataset | Domain rules, without storage |
| Calculation | Admitted observations → `DerivedDataset` | Common numerical command with explicit purpose/settings |
| View/render | Dataset → `View` → `EncodedProduct` | Common product commands |

A supplied index is used as supplied, including malformed or incomplete
content. It does not trigger substitute network requests. Attachment dates
come from their own cards; a page-wide modification date is not assigned to
every attachment. Stable official document identity survives a filename rename.
Contradictory document/file identities remain unresolved. Observed page coverage
is separate from complete historical coverage and confirmed source absence.

## Offline workbook example

```python
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

with StrategyBox() as box:
    result = box.invoke(
        "operation.series.extract_workbook",
        target="minfin.fedbud.annex3.monthly",
        inputs={"material": Material(workbook_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "minfin.fedbud.annex3.monthly")},
    )
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    source_dataset = result.output("dataset")
    aligned = box.invoke(
        "command.observations.align",
        target="minfin.fedbud.annex3.monthly",
        inputs={"dataset": source_dataset},
    )
    integrated_dataset = aligned.output("dataset")
```

Retained workbook/document evidence can enter `command.table.extract` directly;
retained tables can enter interpretation; a database query may supply admitted
observations directly to a numerical command. These entrances have different
input contracts. A request, publication listing or update assessment cannot
stand in for observations.

## Fiscal meaning and numerical purposes

The default reviewed budget scope covers revenue, expenditure and balance.
Fund-table scope covers total and other-asset stocks. Unknown physical rows
remain in the selected evidence and produce omitted-coverage findings; they
receive no automatic economic interpretation. Explicit additional `RowRule`
settings must supply their own metric, basis, currency and scale.

Monthly and quarterly YTD amounts use intervals from January 1 through the
source period end. Annual flows use the calendar-year interval. A stock uses
the actual date from its header; a source date such as November 1 does not
become November 30. Source economic dates, attachment publication dates and
capture timestamps are independent. Row-specific currencies and flow bases
remain independent within a mixed NWF workbook.

Exact numbers use `Decimal`. Reported zero, blank, dash, missing and an
unavailable formula cache remain distinct statuses. Formulas and source cell
coordinates remain evidence; the decoder does not calculate formulas.
Validation checks semantic grain, admitted units/scales and the budget
revenue-minus-expenditure balance where all reviewed operands are available.

| Calculation target | Standard command | Meaning |
| --- | --- | --- |
| `minfin.budget.changes` | `command.calculate.change` | Comparable budget flow windows with the same budget perimeter |
| `minfin.budget.period_flows` | `command.calculate.flow` | Individual period flows from consecutive YTD values with calendar-year reset |
| `minfin.budget.ratios` | `command.calculate.ratio` | Explicit same-period numerator/denominator selection |
| `minfin.nwf.liquid_assets` | `command.calculate.formula` | Same-date `nwf.total - nwf.other_assets`, with matching RUB scale/perimeter |
| `minfin.nwf.changes` | `command.calculate.change` | Net change between qualified fund stocks |

Different accumulation windows are not interchangeable comparisons. A missing
preceding YTD period prevents deaccumulation; it is not replaced with zero.
Numerical work may target one queried series or partition a whole table while
retaining each metric's economic axes.

## Document evidence and remaining scientific work

The three document source records are present and their physical routes are
explicit. Current static `DocumentRules` deliberately contain no unreviewed
field coordinates. Interpretation requires actual reviewed anchors and
`DocumentField` records identifying block/row/column, row label, metric, currency,
scale, stock date and perimeter. Without them it fails with
`minfin.document.reviewed_fields_required`.

DOCX decoding supplies real table geometry. PDF page text alone does not
establish reviewed table coordinates. DOC conversion is a visible preceding
command with an explicit provider, original/converted identities and a bounded
result. A successfully decoded document does not imply economically admitted
values. Additional real editions must be supplied and reviewed before extending
default scientific coverage.

## Retention, execution and notifications

`command.value.encode` and `command.value.decode` preserve complete supported
physical/semantic values, exact evidence and assessments. Dataset ingestion
accepts a logical dataset through `command.dataset.ingest`. Encoded
representations enter `command.artifact.commit`; encoding alone performs no
write. Domains do not choose a filesystem destination or dataset provider.

Every command runs through the same bounded execution service. Execution and
accepted data are journaled before notification delivery. A failed optional
notification does not erase accepted observations. Acquisition, storage,
publication and delivery have separate effect receipts and outcomes.

Source observations carry typed relational `SourceUse` coordinates: source,
family, issue, actual material identity and hashes of the recognized geometry and
reviewed semantic rules. Alignment and numerical work preserve those uses. An
explicit issue input must agree with retained publication context. Geometry
recognition establishes scientific applicability independently of official
transport provenance; a supplied source label alone establishes neither.

Implementation is identified by the repository revision. Content hashes identify
actual evidence. Domain settings, source records and numerical rules carry no
independent release counters. See the [binding reference](minfin-capability-migration.md)
and [common invocation lifecycle](capability-session.md).
