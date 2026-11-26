# Minfin command bindings

Use the [maintained fiscal route](minfin-data-route.md) for source IDs, scientific
coverage, retained-value entrances and executable examples.

The immutable [`DOMAIN`](../../src/stratbox/domains/minfin/domain.py) provides
thirteen explicit `SeriesSpec` records. Each binds these standard commands:

| Command | Narrow domain responsibility |
| --- | --- |
| `command.request.prepare` | Official index/attachment URL and request facts |
| `command.publication.scan` | Publisher cards, document identity and per-attachment dates |
| `command.issue.select` | Source/issue selection and unresolved ambiguity |
| `command.source.assess` | Qualified source evidence comparison |
| `command.table.extract` | Reviewed workbook geometry or actual document table blocks |
| `command.table.interpret` | Exact row/field values and fiscal meaning |
| `command.observations.validate` | Units, scales, grain, balance and period checks |
| `command.observations.align` | Explicit integrated identities retaining source evidence |

`operation.series.extract_workbook` and `operation.series.extract_document` are
common recipes. DOC requires the visible conversion command before physical
decoding. The three document series require actual reviewed field settings;
physical decoding alone does not complete their economic interpretation.

Numerical targets use independent standard change, deaccumulation, ratio and
same-date formula commands. Product targets prepare existing values before
rendering them. HTTP, decoders, resource bounds, persistence, journals and
notification delivery belong to the core.

There are no domain operation builders, compatibility routes, profile registries
or method/schema release counters. Shared dictionaries and rules live in
`common/`; each record refers to those ordinary immutable values directly.
