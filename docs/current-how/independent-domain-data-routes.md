# Independent domain data routes and portable replay

This guide describes the executable processing architecture in Stratbox 0.20.0.
Publisher domains own source identity and economic meaning. Shared contracts
preserve evidence, and neutral operations handle extraction, storage, bounded
inspection and machine invocation. Each transformation can be called separately;
composition operations explicitly declare the stages they run.

The five artifact roles are originals, readable source representations, extracts,
integrated data and products. A route can start from an admitted retained value
and stop at any useful role. Saving is an independent decision for each value
and destination.

## Contents

1. Functional ownership — boundaries between source rules and transformations.
2. Physical evidence — workbook and document extraction guarantees.
3. Context and coverage — source identity, scope and update decisions.
4. Independent persistence — snapshots, artifacts and replay.
5. Observations and products — interpretation, calculations and presentation.
6. Unified discovery — publisher cards and actual operation bindings.
7. Machine access — typed references and bounded inspection.
8. Verification limits — runtime dependencies and the scope of local evidence.

## 1. Functional ownership

Each publisher has one root operation registration and root source registries.
Substantive families sit inside functional owners. Public operation entry points
stay in `operations`; lower owners can be used without application orchestration.

| Owner | Responsibility | Permitted lower domain dependencies |
|---|---|---|
| `publications` | Series, issues, access, discovery, selection and acquisition | Publications |
| `documents` | Source-local ordered document blocks and profiles | Publications and documents |
| `tables` | Physical evidence and source-local table flakes | Publications, documents and tables |
| `integration` | Explicit meanings, periods, units, identities and editions | Source owners and integration |
| `analytics` | Declared calculations and comparability conditions | Source owners, integration and analytics |
| `products` | Prepared views, rendering and artifact packaging | All lower semantic owners |
| `operations` | Typed requests, execution, metadata and compositions | The publisher's functional owners and neutral core |

The static dependency gate applies these directions to every publisher.
Cross-publisher imports are rejected. Shared contracts import no executable
core or publisher implementation. See [functional architecture](../architecture/domain-functional-semantics.md).

Publisher-specific routes have their own guides:

- [CBR publications and families](cbr-data-pipeline.md).
- [FNS full-source extraction and explicit projections](fns-data-pipeline.md).
- [Rosstat families and KEP2](rosstat-data-route.md).
- [Minfin tables, documents and products](minfin-data-route.md).
- [Frank RG workbooks and supplied profiles](frank-rg-data-route.md).

## 2. Physical evidence

### 2.1 Workbooks

`WorkbookExtract` retains series, issue and asset identity; original byte
identity; format and profile; all decoder-visible sheets and cells; lineage;
coverage; and qualifications. Cells retain coordinates, scalar types, numeric
tokens, formula expressions and caches, number formats, indentation and formula
attributes where the decoder supports them. Merged ranges and declared geometry
remain visible. Source worksheet names retain trailing spaces.

| Format | Retained evidence | Explicit boundary |
|---|---|---|
| XLSX / XLSM | OOXML tokens, exact decimal values, formula expressions and caches, merges and formats | No formula evaluation, external-link resolution or active-content execution |
| XLS | Exact decoded binary values, cached values, formats and merges | Original numeric text and formula expressions are unavailable from the decoder |
| XLSB | Decoder-visible values with a binary evidence marker | Formats, merges and expressions are unavailable; date serials remain uninterpreted |

An absent formula cache and an explicitly cached empty string remain different
states. Date decoding retains the serial token and number format. Binary
numbers carry `decoded_binary`; generated decimal text is not claimed as an
original source lexeme.

The reader uses sparse records. Inflated dimensions do not allocate a rectangular
grid; explicit dense conversion has a separate size guard. Workbook snapshots
partition by sheet, at most 20,000 rows and a conservative 8 MiB encoding bound
per cell partition. Selected components can be read independently.

Neutral operations are `workbook.extract`, `workbook.readable`,
`workbook.compare`, `workbook.snapshot` and `workbook.replay`. Economic meaning
remains in the publisher domain. Implementation owners are
[workbook contracts](../../src/stratbox/shared/data/workbooks.py) and
[format extraction](../../src/stratbox/core/formats/spreadsheets/extracts.py).

### 2.2 Documents

`DocumentExtract` retains ordered blocks, original identity and publication
context. PDF extraction attempts each admitted page and records failed pages or
empty text layers explicitly. It performs no OCR or inferred table recognition.
A caller's page ceiling is checked before text extraction. DOCX preserves
main-body paragraph/table order; headers, footers, drawings and layout remain
outside the declared profile and available in the original bytes.

`document.extract`, `document.readable`, `document.snapshot` and
`document.replay` are independent. Reviewed source-local profiles admit document
values as economic observations. Legacy DOC remains original-only where no
decoder is declared.

## 3. Context and coverage

`SourceAssetIdentity` separates series, issue and asset from an exact acquired
byte version. Filenames and upload dates do not automatically establish an
observation period. Publisher issue models, publication dates, observation
intervals and vintage choices remain explicit.

`SnapshotCoverage` has a summary status and structured `CoverageDimension`
axes. Each axis can record requested, materialized, validated, interpreted,
output and missing members. Axes can describe sheets, archive members, source
fields, geography levels or indicators. Empty lists make no completeness
assertion. Missing output members prevent a complete coverage claim.

`processing.plan_update` compares explicit desired targets with retained
processing records. Decisions separate source-content changes, schema/method
changes, reference-edition changes and missing destination copies. An unchanged
result can be copied to another destination without recalculation. A new
reference edition can require recalculation while source bytes stay unchanged.
Unlisted sources remain outside the plan; planning performs no effects or deletion.

Supplied municipal reference editions preserve namespaces, string codes,
validity intervals, administrative parents and statistical perimeters.
Transitions are explicit evidence. Splits, mergers and recodings do not authorize
automatic aggregation or historical perimeter bridging. The packaged aliases
are not presented as a complete official municipal directory.

## 4. Independent persistence

| Value | Retention | Replay |
|---|---|---|
| Untouched acquired file | `source.save_original` with an admitted FileStore | `source.read_original` |
| Complete flake, dataset, calculation or view | Its snapshot encoder, then `dataset.write_snapshot` | `dataset.read_snapshot`, then its decoder |
| Readable text or rendered product with semantic descriptor | Artifact packaging, then `material.save_artifact` | `material.read_artifact` |

Destinations are caller-selected adapters. Local folders, network shares and
publication repositories can be supplied by their owning application. Core does
not hard-code a user's network path or publish a repository change merely
because a rendered file was produced.

`ProcessingFunction` distinguishes processing from `encode`, `replay`,
`maintain` and `inspect`. Snapshot encoding does not claim integration or
business rendering. Restoring a product is replay. Frank RG cleanup is
maintenance. Source cards retain technical operations alongside economic stages.

Dataset snapshots preserve typed scalar values, schemas, original identities,
coverage and parents. A partial component read cannot enter a decoder requiring
the complete value. Artifact descriptors retain their semantic contract and
lineage beside exact representation bytes. A bare display CSV/JSONL is not a
complete prepared-view replay carrier; use its snapshot or artifact descriptor.

Codec operation ports distinguish a live value from its retained snapshot
wrapper. A precise snapshot port connects to the corresponding replay operation;
an additional generic `dataset.snapshot` port connects to neutral storage. The
embedded manifest continues to describe the logical data. Reading a generic
snapshot requires selecting and invoking the appropriate validating codec.

## 5. Observations and products

`ObservationBatch` retains metric identity, unit, scale, quantity kind,
definition edition, period, dimensions, perimeter, value status and cell
evidence. A physical/source flake can preserve fields outside the admitted
semantic projection, ready for a later reviewed profile.

Common comparison matches the entire semantic key. Changed periods, units,
scales, definitions, dimensions or perimeters create distinct keys. Missing
values and text never become zero, and duplicate keys are rejected. Exact
decimal subtraction derives precision from its operands rather than the
ambient Decimal context. Growth, rebasing and other methods need their own
declared semantics.

An `ObservationView` is an explicit selection with provenance and a snapshot
codec. Preparation does not aggregate duplicate observations. CSV, JSON and
JSONL rendering consumes that view; domain products can supply XLSX layouts.
Calculation, preparation, rendering and destination writes remain separable.

KEP2 illustrates the distinction: yearly, quarterly and monthly values stay in
the source flake; the requested monthly selection belongs to the product.
Published indices remain distinct from derived percentage changes. A notebook
date at the start of the next period is a display label; the observation retains
the actual interval. Row selection decisions retain source evidence, including
discarded duplicate candidates.

## 6. Unified discovery

`operation_catalog().source_catalog()` projects publisher adapters to
`SourceCard`, `SourceProfile` and `SourceOperation`. Cards describe family,
issue model, formats, profiles, qualifications and applicable bindings. Each
binding resolves an exact ID/version in the existing executable operation
catalog; there is no second handler registry.

`sources.describe(series_id, operations=catalog)` exposes actual ports,
requirements, effects and method versions with source-scoped conditions.
Unbound stages remain undeclared. A physical reader does not imply a reviewed
economic schema for every layout. Frank RG semantics and unreviewed Rosstat
table/document layouts require explicit profiles bound to source bytes and
declared meanings.

## 7. Machine access

The existing admitted inline read-only codecs remain available. The generic
typed-reference interface lets a host construct or restore a typed request,
retain it in its own scope and invoke `invoke_reference`. The real definition
remains authoritative for request type, version, capabilities and effects.

Effectful calls require an explicit host grant covering declared effects.
Opaque references confer no credentials or destination authority. The bounded
request envelope accepts handles and preview limits rather than executable
expressions or arbitrary class deserialization. Responses retain full typed
result/value handles and provide a bounded preview, diagnostics and effect
states. Bytes and private dataclass fields are omitted from previews.
Result and value capacity is reserved before the handler starts, so a full
reference store rejects admission before any effects. Preview failures return a
bounded omission while the complete result and effect receipts remain retained.
Deployment as a bot, desktop feature or MCP endpoint belongs to the host.

`dataset.query_snapshot` provides typed predicates and column projection over
a pinned component. Scan/output limits are separate. Original row positions
and a next scan offset support deterministic continuation at the same identity.
A preview does not assert publisher-wide completeness.

## 8. Verification limits

Local regressions cover physical fidelity, sparse geometry, binary precision,
ordered document replay, exact arithmetic, semantic barriers, coverage codecs,
source cards and effect grants. Domain checks cover FNS historical layout
epochs, KEP2 period/duplicate policies, Minfin row semantics and Frank RG supplied
profile admission. See [common route regressions](../../tests/unit/base/test_common_processing_routes.py).

Runtime availability depends on optional decoders and selected providers.
RAR can require an external backend; PDF text extraction is not visual table
recognition. Supplied mappings and reference editions carry their own review
scope. Local correctness tests do not certify every future publisher layout,
remote endpoint or deployed storage configuration.
