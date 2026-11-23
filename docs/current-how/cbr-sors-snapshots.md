# SORS source dependencies and portable computation

## Implemented scope

`stratbox.domains.cbr.analytics.corporate_lending.sors` reconstructs regional
OKVED2 observations from corporate, SME and SME-IE publications. The source
bundle, strict restoration and crosswalk each have a complete `DatasetSnapshot`
codec. A retained strict result contains the source data needed to build a fresh
crosswalk model. A retained crosswalk contains that strict result and its source
bundle. Solver sessions, Python pickles and live workbook objects are outside the
snapshot format.

The public operation API is `stratbox.domains.cbr.operations.corporate_lending.sors`.
Source extraction belongs to `tables.corporate_lending`, qualified model input preparation belongs
to `analytics.corporate_lending.sors.inputs`, and prepared products belong to
`products.corporate_lending.sors`.

The independent route is:

1. Acquire and identify selected publication originals through `publications`.
2. Extract complete workbook flakes and independent corporate observations;
   extract the regional 0105a workbook through its specialized source parser.
3. Run `prepare_inputs` on those retained source observations and the complete
   regional flake to align and validate a model input bundle.
4. Retain the bundle through neutral dataset storage and read it in another
   invocation when calculation is required.
5. Run pure `restore` on the qualified bundle with an explicit `SorsRunConfig`.
6. Retain and read the strict result. `run_crosswalk` rebuilds its model from the
   retained source data and strict component bounds.
7. Run `build_views` on a strict or crosswalk result. It prepares every selected
   data, pivot, dimension and audit sheet into a complete `SorsViewPack`.
8. Retain and read that view pack independently; `render_views` encodes only the
   supplied prepared sheets into a workbook.

| Code | Operation | Declared work and admitted input |
| --- | --- | --- |
| P1 | `prepare_inputs` | Integration of sealed corporate source observations and a complete parsed 0105a flake |
| P2 | `prepare_from_flakes` | Explicit extraction/integration composition over workbook flakes and a parsed 0105a flake |
| P3 | `prepare_from_originals` | Explicit extraction/integration composition over supplied publication bytes |
| P4 | `restore` | Calculation from a qualified `SorsSourceBundle` only |
| P5 | `restore_from_originals` | Explicit extraction/integration/calculation composition |
| P6 | `build_views` | Product selection and preparation from a strict or crosswalk result |
| P7 | `render_views` | Workbook encoding from a prepared, sealed `SorsViewPack` |

The model input preparation has INTEGRATE semantics and belongs physically to
the SORS analytical method because it applies that method's classifier, portfolio
and rounding rules. Common industry history alignment remains under integration.
The composition operations expose their stages in the catalog. `restore` never
extracts a workbook implicitly. `prepare_inputs` never interprets unqualified
workbook cells. `render_views` never chooses a model scope, builds a pivot or
runs the solver. These entry points allow a caller to retain the intermediate
result appropriate to its own workflow.

The source observation profiles retain all periods by default, with exact
numbers, missing-value statuses and source references. Their source layout
qualification remains explicit; this route does not claim support for every
historical CBR workbook edition.

## Declared publications

`DEPENDENCIES` is the machine-readable declaration. Logical publication IDs are
resolved through the shared CBR publication catalog. Acquisition profiles own
URLs and file selection. SORS owns the computational purpose of each input.

| Input field | Publication | Requirement | Computational purpose |
| --- | --- | --- | --- |
| `regional_traditional` | `01_05_A` | Required | Regional corporate totals and legacy activity evidence |
| `national_traditional` | `01_02_A` | Required | National corporate total and legacy activity evidence |
| `national_okved2` | `01_02_C` | Required | National corporate OKVED2 observations |
| `federal_district_okved2` | `01_03_C` | Required | Federal district corporate OKVED2 observations |
| `sme_national_totals` | `01_11` | Required | National SME and SME-IE totals |
| `sme_national_okved2` | `01_11_F` | Required | National SME OKVED2 observations |
| `sme_ie_national_okved2` | `01_11_I` | Required | National SME-IE OKVED2 observations |
| `sme_federal_district_okved2` | `01_12_A` | Required | Federal district SME OKVED2 observations |
| `sme_regional_totals` | `01_13_F` | Required | Regional SME totals |
| `sme_ie_regional_totals` | `01_13_I` | Required | Regional SME-IE totals |
| `regional_totals_history` | `01_05_D` | Optional | Regional total validation and history |

The bundle's `dependency_manifest_grid` records all eleven declarations in their
defined order. Each row carries the input field, publication code, logical
series ID, purpose, requirement, report date, publication rounding step and
adapter method version. Accepted semantic contracts and the report-date/rounding
compatibility rule are explicit. A resolved row also carries the original byte hash,
size, source ID and admission kind (`original` or `flake`). An omitted optional
publication remains an explicit `not_supplied` row.

Snapshot admission verifies this declaration against source receipts and the
published source manifest. Missing mandatory roles, contradictory original
identities, inconsistent dates or rounding policies, and incomplete dependency
tables fail admission. An unknown historical coverage claim does not waive
these requirements. The default coverage remains `unknown`: a complete set of
inputs for one calculation does not prove publisher history completeness.

## Reusing source observations and the 0105a flake

Each nonregional source field admits a `CorporateSourceDataset` produced by
`cbr.corporate_lending.extract_observations`, including its independently read
snapshot. `prepare_inputs` requires that interpreted and sealed value. The
explicit `prepare_from_flakes` composition also admits an all-sheet
`WorkbookFlake` and runs its source-local interpretation before integration.
`prepare_from_originals` also admits original `SourcePayload` values. The
operation-specific admission rule applies even though `SorsSourceInputs`
represents the common collection of dependency roles.

`regional_traditional` uses the complete `ParsedCbr0105ADebtCorpFile` in the
retained-input routes. The regional bridge verifies the extraction seal,
original identity, report date, geography edition and complete dimensions: all
six measure/currency sheets, 96 geographic rows and 26 published activity
categories. Selected industry flakes remain valid for ordinary industry work
but fail this model's complete-input admission.

National and SME source datasets retain multiple reporting dates independently
of SORS. Federal district datasets retain loan flows as reference months as
well as debt and overdue stocks as dates. Model preparation selects the
requested stock date, qualifies activity/geography mappings, checks dimensions
and applies the caller's explicit rounding policy. Blank cells, markers and
uncached formulas remain visible in the source artifact; required unresolved
model values block preparation rather than becoming zeroes.

The original source hash and byte size remain distinct from the identity and
size of an encoded flake. A prepared input bundle retains source receipts and
the independently supplied source-observation computations as parents. Its
source manifest continues to identify the publisher original.

Model input scope remains complete when an outward product requests one region,
one activity, or a small metric set. All ten required publication roles and the
three portfolio scopes participate in the reconstruction contract. An output
filter therefore cannot remove national, district or auxiliary SME constraints.
The optional regional history supports an additional consistency check.

## Snapshot contents and integrity

Bundle and model snapshots have a canonical context table, a dataframe
descriptor table and typed components for every domain grid. Prepared-view
snapshots have a context component and every selected product sheet. The neutral dataframe codec preserves
column order, indexes, dtypes, tuple-valued expressions, missing values and
unbounded numerical intervals. Full source and result grids retain publication
tokens, coordinates and interval semantics where supplied by their adapters.

| Snapshot | Retained context |
| --- | --- |
| Bundle | Every source-specific and combined grid; geography and classifier dimensions; categories; bindings; validation; source and dependency manifests; original and reference receipts; report date; rounding step; coverage; adapter version; computation receipt |
| Restoration | Complete bundle plus all strict result, component, constraint, fact, derivation, rounding, optimization, conflict and audit grids; summary; complete run configuration; computation receipt |
| Crosswalk | Complete restoration plus all crosswalk facts, bounds, mappings, relations, scenario, solver and diagnostic grids; scenario configuration; mapping version; run ID; computation receipt |
| Prepared views | Every selected sheet in order, complete table values and dtypes, sheet names, product profile, source result identity and view computation receipt |

`source_bundle`, `run_config`, `strict_result` and `crosswalk_config` are explicit
typed dependencies. A tabular export containing only the primary output grid
cannot be encoded as a complete replayable result. The codecs reject missing
dependencies instead of filling them from current memory.

The encoded context retains historical computation receipts, their input and
parent receipts, source container/member metadata, qualified classifier and
mapping identities, and the original output seals. Reconstructed grids are
checked against those seals. The storage manifest pins the source inputs as
references; original workbook bytes are retained separately through source
storage when required. Reading a snapshot adds a read-operation receipt while
preserving the historical calculation evidence within the reconstructed value.

Snapshot version IDs are derived from data, context, coverage and input
identities unless a caller supplies an explicit version. Neutral immutable
dataset storage owns version conflicts and publication of complete snapshots.
A selected subset of components remains useful for inspection, but domain
decoding requires every component of the declared snapshot.

## API example

The following sequence assumes `sources` contains interpreted source
observations and the complete regional 0105a flake in a `SorsSourceInputs`,
`config` is the requested `SorsRunConfig`, and `dataset_store` is a caller-selected
dataset adapter. Operation outcomes must be checked before consuming `.value`.

```python
from stratbox.domains.cbr.operations.corporate_lending import sors
from stratbox.core.storage.datasets.definitions import (
    ReadSnapshotRequest, WriteSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot


def checked(result):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.value


bundle = checked(sors.prepare_inputs(sors.PrepareSorsRequest(sources, config)))
encoded = checked(sors.build_bundle_snapshot(sors.SorsBundleSnapshotRequest(bundle)))
reference = checked(write_snapshot(
    WriteSnapshotRequest(encoded), store=dataset_store,
)).reference

# A later invocation may begin here with the pinned reference alone.
material = checked(read_snapshot(ReadSnapshotRequest(reference), store=dataset_store))
restored_bundle = checked(sors.read_bundle_snapshot(sors.ReadSorsSnapshotRequest(material)))
strict = checked(sors.restore(sors.RestoreSorsRequest(restored_bundle, config)))

encoded_result = checked(sors.build_restoration_snapshot(
    sors.SorsRestorationSnapshotRequest(strict),
))
result_reference = checked(write_snapshot(
    WriteSnapshotRequest(encoded_result), store=dataset_store,
)).reference
material = checked(read_snapshot(ReadSnapshotRequest(result_reference), store=dataset_store))
replayed_strict = checked(sors.read_restoration_snapshot(sors.ReadSorsSnapshotRequest(material)))
crosswalk = checked(sors.run_crosswalk(sors.CrosswalkSorsRequest(
    replayed_strict, sors.SorsCrosswalkConfig(mode="feasibility"),
)))
views = checked(sors.build_views(sors.BuildSorsViewsRequest(crosswalk)))
encoded_views = checked(sors.build_view_snapshot(sors.SorsViewSnapshotRequest(views)))
view_reference = checked(write_snapshot(
    WriteSnapshotRequest(encoded_views), store=dataset_store,
)).reference

# Rendering can begin in another process with only this prepared-view snapshot.
material = checked(read_snapshot(ReadSnapshotRequest(view_reference), store=dataset_store))
replayed_views = checked(sors.read_view_snapshot(sors.ReadSorsSnapshotRequest(material)))
workbook = checked(sors.render_views(sors.RenderSorsRequest(replayed_views)))
```

The crosswalk has the analogous `build_crosswalk_snapshot` and
`read_crosswalk_snapshot` pair. Its workbook representation can be sent to
neutral material storage or an application-owned publishing destination.
Dataset durability and external publication remain separate operations.

## Computational qualification and verification

Decoding performs no solver execution. A new strict restoration rebuilds its
quantity graph, interval closure and linear problem. A new crosswalk rebuilds
its mapping problem and solver session from retained source and strict
component data. Constraint expressions exported from a solved strict model use
immutable tuples, so they remain ordinary data across storage and process
boundaries.

Recomputation requires a compatible Strategy Box rule implementation, the
qualified classifier and requested mapping edition, and the official HiGHS
backend. Solver identity and runtime diagnostics remain in the result. A
snapshot retains data and evidence rather than an executable environment;
repeating a solve under a different implementation or backend version is a new
computation with its own receipt. Rendering a prepared view pack requires its data and renderer; source
workbooks, source-bundle reconstruction and a solver session are unnecessary.

Tests exercise complete grid and evidence round trips, incomplete and mutated
context rejection, and a separate Python process that reads a retained bundle,
runs the real strict solver, encodes and reads its result, reads an independently
retained strict result, runs a real crosswalk, retains that crosswalk, builds a
pivot, retains and reads a complete prepared-view pack, and renders its workbook. The bounded numerical fixture identifies two
legacy-to-OKVED2 values as 90 and 10. These tests establish computational
continuation; they do not certify all historical publications or the economic
adequacy of every mapping scenario.
