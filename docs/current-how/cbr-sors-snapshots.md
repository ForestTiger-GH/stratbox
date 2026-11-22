# SORS source dependencies and portable computation

## Implemented scope

`stratbox.domains.cbr.corporate_lending.sors_restoration` reconstructs regional
OKVED2 observations from corporate, SME and SME-IE publications. The source
bundle, strict restoration and crosswalk each have a complete `DatasetSnapshot`
codec. A retained strict result contains the source data needed to build a fresh
crosswalk model. A retained crosswalk contains that strict result and its source
bundle. Solver sessions, Python pickles and live workbook objects are outside the
snapshot format.

This route makes material boundaries independent of a process lifetime:

1. Acquire caller-selected publication bytes, or reuse the complete 0105a flake.
2. Run `load_sources` to extract, align and validate a source bundle.
3. Encode the bundle, write it through neutral dataset storage, read its pinned
   reference, and decode it when computation is required.
4. Run `restore` on that reconstructed bundle with an explicit `SorsRunConfig`.
5. Retain and read the strict result independently. `run_crosswalk` then rebuilds
   its model from retained source data and component bounds.
6. Retain and read the crosswalk independently. `build_pivot` and
   `render_workbook` consume reconstructed domain results.

`load_sources` remains an explicit extraction-and-integration composition for
the eleven input roles below. Individual source flakes for the other ten roles
are not implemented by this change. The existing source adapters and validation
profile still qualify a specific publication structure; portability does not
extend their coverage to arbitrary historical CBR layouts.

## Declared publications

`DEPENDENCIES` is the machine-readable declaration. Logical publication IDs are
resolved through the shared CBR publication registry. Acquisition profiles own
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

## Reusing the 0105a flake

`SorsSourceInputs.regional_traditional` accepts either a `SourcePayload` or a
`ParsedCbr0105ADebtCorpFile` returned by the shared 0105a extractor, including one
reconstructed from a stored flake snapshot. Other source fields currently accept
original payloads.

The flake bridge verifies its computation seal, original identity, report date,
geography reference and full source dimensions. A selected industry subset is
insufficient for SORS and is rejected. The projection preserves original source
coordinates and identity, then applies the explicitly selected publication
rounding policy. It does not reopen the workbook. The source-bundle receipt
retains the flake extraction as a computational parent.

The source manifest uses the original workbook's byte hash and size from the
flake's source receipt. It does not substitute the size or identity of a flake
encoding. Rebuilding an input bundle from a flake therefore preserves its
published-source identity while recording a different computational route.

## Snapshot contents and integrity

All snapshots have a canonical context table, a dataframe descriptor table and
typed components for every domain grid. The neutral dataframe codec preserves
column order, indexes, dtypes, tuple-valued expressions, missing values and
unbounded numerical intervals. Full source and result grids retain publication
tokens, coordinates and interval semantics where supplied by their adapters.

| Snapshot | Retained context |
| --- | --- |
| Bundle | Every source-specific and combined grid; geography and classifier dimensions; categories; bindings; validation; source and dependency manifests; original and reference receipts; report date; rounding step; coverage; adapter version; computation receipt |
| Restoration | Complete bundle plus all strict result, component, constraint, fact, derivation, rounding, optimization, conflict and audit grids; summary; complete run configuration; computation receipt |
| Crosswalk | Complete restoration plus all crosswalk facts, bounds, mappings, relations, scenario, solver and diagnostic grids; scenario configuration; mapping version; run ID; computation receipt |

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

The following sequence assumes `sources` is an admitted `SorsSourceInputs`,
`config` is the requested `SorsRunConfig`, and `dataset_store` is a caller-selected
dataset adapter. Operation outcomes must be checked before consuming `.value`.

```python
from stratbox.domains.cbr.corporate_lending import sors_restoration as sors
from stratbox.core.storage.datasets.definitions import (
    ReadSnapshotRequest, WriteSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot


def checked(result):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.value


bundle = checked(sors.load_sources(sors.LoadSorsRequest(sources, config)))
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
workbook = checked(sors.render_workbook(sors.RenderSorsRequest(crosswalk)))
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
computation with its own receipt. Rendering an existing result does not require
running HiGHS again.

Tests exercise complete grid and evidence round trips, incomplete and mutated
context rejection, and a separate Python process that reads a retained bundle,
runs the real strict solver, encodes and reads its result, reads an independently
retained strict result, runs a real crosswalk, retains that crosswalk, builds a
pivot and renders a workbook. The bounded numerical fixture identifies two
legacy-to-OKVED2 values as 90 and 10. These tests establish computational
continuation; they do not certify all historical publications or the economic
adequacy of every mapping scenario.
