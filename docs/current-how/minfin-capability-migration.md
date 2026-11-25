# Fiscal data through canonical capabilities

The fiscal domain supplies exact command graphs for publisher discovery,
acquisition, physical cells, source interpretation, integration, calculations,
portable snapshots and products. Every graph executes through the common
session. Supplied cells, flakes, observations, documents and views support
independent continuation without reacquiring a publisher asset.

Table interpretation admits registered column layouts. Document interpretation
requires a source-qualified reviewed field profile; ordered extracted blocks
alone establish physical evidence. Deterministic tests establish contracts and
selected layouts, while certification of additional published editions remains
an independent evidence requirement.

Contents:

1. Source routes — table and document interpretation responsibilities.
2. Retained fiscal meaning — periods, monetary units and source evidence.
3. Legacy DOC conversion — explicit provider admission and identities.
4. Independent continuation — exact calls and source recipes.

## 1. Source routes

| Route | Source scope | Semantic admission |
| --- | --- | --- |
| Budget tables | Federal, consolidated and regional budgets; monthly, quarterly and annual series | Registered period-column layout, source-specific frequency and cumulative/annual basis |
| NWF table | Fund movement and management series | Per-row units and bases; RUB stock rows have reviewed integration/headline mappings |
| NWF documents | Fund volume, preferred shares and VEB deposits | Ordered paragraphs/table grids followed by an explicit reviewed document field profile |

`minfin.extract` retains full selected physical cells, formulas, available cached
values, lexical tokens, merged ranges, publication context and qualifications.
`minfin.build_flake` applies a selected layout method. `minfin.integrate` admits
reviewed row bindings independently of storage ingestion. Source rows outside a
selected economic projection remain in the physical extract and flake.

`minfin.discover` interprets a supplied publisher index and performs no network
substitution. `minfin.acquire` receives one identified publisher asset. The
`minfin.capture` scenario exposes separate acquisition, payload, publication
context and physical extraction boundaries. `source.extract` and
`source.product` recipes select the applicable exact route for all thirteen
registered series.

## 2. Retained fiscal meaning

Fiscal observation periods remain independent of publication/modified dates and
publisher document labels. Monthly and quarterly YTD amounts retain intervals
starting on January 1; annual flows retain their annual interval. Stock values
retain an explicit observation date. Document fields supply their own admitted
period rather than deriving one from acquisition time.

NWF rows retain explicit currency, scale and basis. An unclassified mixed-unit
row receives no automatic RUB interpretation. Zero, dash, missing and blank
retain distinct statuses. Ratios and indices require explicit semantic periods.
Budget and fund headline calculations validate their source/basis/unit
contracts and preserve previous-year comparison qualifications.

Flake, observation, summary, document and view snapshots support semantic
round-trip. Document snapshots retain ordered blocks, all input identities and
publication context. Source comparison, economic comparison and update planning
remain separate calls. Saving and publishing use explicit shared effect
operations and confirmed receipts.

`minfin.validate` reports physical table structure and formula-cache gaps.
`minfin.validate_document` checks publisher context and ordered document
structure, reporting extracted content and failed blocks separately from
economic correctness. Physical source extracts replay through
`minfin.read_representation` or `minfin.read_document`.

`minfin.ingest_observations` and `minfin.ingest_document` create exact semantic
snapshots before invoking the common immutable-version dataset writer. Their
snapshot outputs remain independently usable when storage fails. The returned
reference supports `query.dataset` followed by the appropriate domain replay.

## 3. Legacy DOC conversion

`minfin.legacy_document` has two visible operations: conversion and decoding.
Conversion requires a caller-supplied `document_converter` provider implementing
`DocumentConverter`. The provider declares its identity and revision and returns
bounded DOCX bytes with the same source identifier. The library validates the
package and main document XML independently.

The DOC remains the publisher original. The converted DOCX has a separate byte
identity. Decoded document lineage retains both identities and the converter
identity/revision; snapshots retain that evidence. A missing provider is an
admission failure. The provider contract permits a supported host conversion
engine without bundling an environment-specific executable into the library.

`DocumentInterpretationProfile` binds a source, format, revision, required text
anchors and exact table-cell selections to explicit metrics, currencies,
subjects, periods and perimeters. Unsupported geometry or anchors reject the
profile. PDF page text has no admitted table geometry for this method; a PDF
table provider requires its own qualified layout interpretation.

## 4. Independent continuation

```python
from stratbox.sdk import StrategyBox

with StrategyBox() as box:
    interpreted = box.invoke(
        "minfin.build_flake",
        inputs={"extract": retained_source_cells},
        group_id="minfin.fedbud.annex3.monthly.processing",
    ).output("value")
    batch = box.invoke(
        "minfin.integrate",
        inputs={"flake": interpreted},
        parameters={"dataset_id": "fiscal.budget", "release_id": "edition-42"},
    ).output("value")
    snapshot = box.invoke(
        "minfin.observation_snapshot", inputs={"batch": batch}
    ).output("value")
```

`minfin.table_product` accepts retained source cells and exposes observations,
summary, view and representation as independently accepted outputs.
`minfin.document_product` accepts a retained publisher document and an explicit
reviewed field profile. Supplied intermediate outputs prune preceding work
through the common planner. Profile fingerprints participate in the prepared
computation identity; a reviewed layout change requires a new profile revision.

`minfin.document_ratio` interprets separate reviewed numerator/denominator field
profiles and calls the common ratio operation. Its explicit analytical pair
declares metric definitions, units, scales, period policy, input release policy
and origin compatibility. Ratio arithmetic therefore remains a separate
calculation contract rather than an implied document parser transformation.
