# Frank RG: delivered files and table interpretation

The domain handles caller-delivered workbooks. A filesystem inventory or supplied
bytes is the acquisition boundary. Automatic retrieval from a Frank RG website
is outside the declared source method.

The single catalog is [domain.py](../../src/stratbox/domains/frank_rg/domain.py).
Its immutable maps contain fourteen continuing series, one shared delivered-file
publication channel, shared naming rules, and explicit scientific obligations.
Series records directly bind standard command IDs to a method, typed settings and
applicability. Operations and scenarios remain in the shared capabilities layer.

| Boundary | Standard command | Accepted value and result |
| --- | --- | --- |
| Local inventory | `command.material.list` | Caller location → bounded inventory from the selected filestore |
| Source recognition | `command.publication.scan` | Inventory → publication listing and scope assessment |
| Issue selection | `command.issue.select` | Listing + source/issue selection → asset selection |
| Local acquisition | `command.material.read` | Selected asset locator → exact material and read evidence |
| Attribution | `command.material.identify` | Material + source/issue claim → identified material |
| Physical decoding | `command.workbook.decode` | Material → workbook cells and decoder qualifications |
| Table selection | `command.table.extract` | Physical workbook + explicit table rules → selected evidence |
| Interpretation | `command.table.interpret` | Selected evidence + semantic cell rules → source dataset |
| Qualification | `command.observations.validate` | Source dataset → checked dataset and assessment |
| Placement | `command.observations.align` | Source dataset → integrated dataset retaining native semantics |

The selection is complete only within the supplied inventory. It establishes no
publisher-wide completeness. Same-issue competing files remain ambiguous.
A snapshot label, numbered week or Q marker identifies a delivered report;
economic frequency and accumulation come from the table's semantic rules.

## Supplied workbook execution

```python
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

# raw_bytes and reviewed_rules are supplied by the caller.
material = Material(raw_bytes, source_id="frg.express.issuance",
                    metadata={"issue_id": "2026-05-01", "format": "xlsx"})
with StrategyBox() as box:
    result = box.invoke(
        "operation.series.extract_workbook",
        inputs={"material": material},
        target=SeriesTarget("frg.express.issuance"),
        parameters={"table_rules": reviewed_rules},
    )
    assert result.outcome == "succeeded", result.diagnostics
    dataset = result.output("dataset")
```

A supplied `physical` or `tables` entrance cuts the preceding work from the
prepared operation. Decoding remains a visible command. The domain methods
perform neither network access nor storage effects.

## Explicit semantic rules

`methods/tables.py` owns frozen `TableRules`, `CellRule` and `CellAnchor`.
A cell states its sheet/coordinate, metric, subject namespace, unit, scale,
measure kind, economic period, frequency, perimeter and missing-token meanings.
A stock requires an as-of date; a flow requires an interval.

Rules are bound either to an exact original identity, or to an explicitly
reviewed layout with inspected originals, geometry, anchors and review evidence.
The workbook's physical identity must match its original material. Changed
geometry, mismatched source attribution, unavailable coordinates, duplicate
semantic keys, unsupported numeric tokens and absent formula caches reject
interpretation.

All fourteen source identities currently require supplied semantic rules.
The repository contains recognition rules and physical decoding support, but
contains no reviewed built-in Frank RG business cell maps. Synthetic regression
workbooks validate the mechanism; they supply no publisher-layout certification.

## Retention, calculations and products

Accepted rows retain exact values, raw tokens, missing statuses, economic
periods, source coordinates, evidence identities and scope qualifications.
`command.value.encode` / `command.value.decode` retain shared values without
rerunning recognition or decoding. `command.dataset.ingest` receives the actual
dataset; its writer provider owns storage.

Same-period revisions use `command.observations.compare`. Temporal changes,
ratios, formulas and seasonal adjustment use their own standard contracts over
accepted observations or time series. They receive no filenames or HTTP results.
Generic views and CSV/JSON/JSONL products use `command.view.prepare` and
`command.product.render`.

See [catalog responsibilities](frank-capability-migration.md),
[archives](frg-streaming-archive.md), and
[explicit maintenance](frg-cleanup-effects.md).
