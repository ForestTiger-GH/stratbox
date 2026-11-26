# Independent typed data stages

The standard route is a graph of available actions. Values flow through explicit
ports; the file extension or the position of a function in a script does not
establish the data's processing role.

Physical evidence, source interpretation, integration, calculation, presentation
and external retention remain separate responsibilities. Existing suitable
values permit entry at the corresponding stage.

## Contents

1. Material — requests, acquisition and physical decoding.
2. Meaning — typed source and integrated observations.
3. Numbers — individual histories, tables and coupled models.
4. Products — prepared views, encoded bytes and explicit effects.

## 1. Material and physical evidence

| Input | Action | Result |
| --- | --- | --- |
| Locator and issue query | `command.request.prepare` | RequestSpec. |
| RequestSpec | `command.material.fetch` | Material and acquisition evidence. |
| File location | `command.material.list` or `material.read` | Bounded inventory or exact Material. |
| Material | Archive/workbook/document/JSON/CSV/DBF action | Bounded physical evidence. |
| Historical document | `command.document.convert` | Converted material with original/conversion evidence. |
| Physical evidence | `command.publication.transcribe` | Readable publication and explicit coverage. |

Acquired bytes and source attribution are distinct. Several logical series can
use one physical asset. Compatible decoding can therefore be shared independently
of the selected interpretation. A conversion retains the identity of both its
input and output.

## 2. Source meaning and integration

`command.table.extract` selects physical tables. `command.table.interpret`
produces source-local observations. `command.observations.validate` assesses
rules and coverage. `command.observations.align` applies admitted identifiers,
units and semantic mappings to produce integrated data.

Grain, period kind, stock/flow/index meaning, units, scale, perimeter, raw tokens
and value status accompany the values. A published dash, withheld value and exact
zero remain different. National/district aggregates are not implicitly summed
with their constituents.

## 3. Numerical actions

A typed dataset query can feed `command.timeseries.prepare` directly. A single
history is identified by numerical coordinates and does not require a separate
publisher-Series registry entry. Whole-table application partitions compatible
histories at a declared grain and reports each unit's outcome under bounded
execution.

Coupled models receive complete model inputs. SORS can operate on one reporting
date while relating many regions and industries. A narrow output projection
preserves the full necessary constraint system.

`calculate.change` compares periods of one compatible measure. `calculate.formula`
evaluates explicitly related inputs, including different measures on one date.
Ratios, accumulated-flow conversion and index transformations retain their
separate semantic requirements.

Seasonal-adjustment estimation requires a compatible provider and explicit
treatment. Independent estimates for all table rows establish unit coverage,
not additive coherence. Indirect aggregation or reconciliation needs its own
admitted component/constraint policy.

## 4. Products and effects

`view.prepare` selects analytical content; `product.render` encodes it. An
accepted dataset feeds `dataset.ingest` directly. Encoded material feeds
`artifact.commit`. Encoded bytes are not a dataset-ingestion input.

A release checks actual member lineage and immutable retention before publishing
its manifest/current pointer. A confirmed write, uncertain write and accepted
in-memory value have different outcomes. Notifications consume retained journal
facts rather than being called inside the source methods.
