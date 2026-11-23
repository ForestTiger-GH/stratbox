# CBR publications about credit-institution office networks

The service-network domain processes publications about credit-institution
offices. Its two source families have independent parsers and qualifications:
counts by bank and published region, and counts by published territory. Source
history, semantic alignment, count changes, prepared views and output rendering
have separate callable boundaries and storage-independent values.

A complete source `DatasetSnapshot` preserves the literal representation,
observations and source-specific evidence. A separate observation snapshot
preserves aligned semantic data. A prepared product is another typed snapshot
that can be rendered after reopening a dataset store. These three boundaries
serve different purposes and keep their own identities.

## 1. Functional owners and source identities

| Owner | Responsibility |
| --- | --- |
| `cbr.publications.catalog` and `profiles` | Logical source identities and reviewed official acquisition routes |
| `cbr.tables.service_network` | Source parsers, literal representations, source observations, readable source material and selected histories |
| `cbr.integration.service_network` | Explicit subject, geography and metric mappings |
| `cbr.analytics.service_network` | Changes in comparable reported office counts and unmatched-cell coverage |
| `cbr.products.service_network` | Prepared typed views and CSV/XLSX rendering |
| `cbr.operations.service_network` | Public requests, execution handlers, operation metadata and retained observation boundaries |

Paths are relative to `stratbox.domains`. The registry source identifiers remain
logical publication identities:

| Publication | Source ID | Source operation namespace | Main source contract |
| --- | --- | --- | --- |
| Offices by bank and published region | `cbr.service_network.bank_offices` | `cbr.offices` | Current HTML capture with separately supplied official state date |
| Office counts by published territory | `cbr.service_network.territorial_offices` | `cbr.offices_reg` | Dated XLSX publication with explicit source selection and formula evidence |

The parsers admit explicit offline payloads and validate source structure.
Acquisition from CBR is independent. Exact original bytes can be preserved by
`source.save_original` / `source.read_original` or neutral material operations.
The domain does not choose a file-system root, network destination or database.

## 2. Callable processing route

The two source facades are
`stratbox.domains.cbr.operations.service_network.bank_offices` and
`stratbox.domains.cbr.operations.service_network.territorial_offices`.
Shared lifecycle functions are exported by
`stratbox.domains.cbr.operations.service_network`.

| Boundary | Registered operations | Result |
| --- | --- | --- |
| Source discovery | `cbr.offices_reg.discover` | Reviewed dated territorial publication links |
| Acquisition | `cbr.offices.acquire`, `cbr.offices_reg.acquire` | Exact source bytes and acquisition receipt |
| Source extraction | Both families' `parse`; `capture` composes acquisition and parsing | `ParsedRelease`, or a qualified territorial candidate set |
| Literal replay | Both families' `read_representation` | Validated CSV, with observations only when date/selection evidence supports qualification |
| Source comparison | Both families' `compare` | Layered comparison, period and coverage qualification |
| Source persistence | Both families' `snapshot`, `restore` | Complete source-release encoding and replay |
| Readable source | `cbr.service_network.make_readable` | Native HTML, or all decoded worksheet cell tokens and formula evidence |
| Selected source history | `cbr.service_network.build_history`, `restore_history` | Independently replayable selected captures or source issues |
| Semantic alignment | `cbr.service_network.align` | Qualified `ObservationBatch` with explicit mapping editions |
| Semantic persistence | `cbr.service_network.observations_snapshot`, `restore_observations` | Exact portable aligned or derived observations |
| Calculation | `cbr.service_network.calculate_changes` | Count differences on comparable cells and unmatched coverage |
| Presentation preparation | `cbr.service_network.build_view` | Typed, reusable office-count view |
| Rendering | `cbr.service_network.render` | CSV or XLSX from the prepared view |

Snapshot encoding does not imply storage. `dataset.write_snapshot` and
`dataset.read_snapshot` provide durable ingestion and restoration through the
selected adapter. The storage reference determines placement; dataset identity
depends on logical contents, schemas, coverage and input evidence.

## 3. Bank offices: capture date and official state date

`ParseOfficesRequest(payload, captured_on, official_as_of=None)` carries two
different date meanings. `captured_on` identifies the capture. An evidenced
`official_as_of` identifies the state described by the publication. Observations
use `PeriodRef("as_of", ...)` when the official date is supplied. Otherwise the
source parse records an explicitly capture-based period.

An official state of 1 November captured on 22 November therefore remains an
observation for 1 November. `ParsedRelease.as_of` is the capture date for this
family; `source_details` separately retains `captured_on` and `official_as_of`.
The machine adapter admits and returns both fields.

Comparison follows those meanings:

- A different known official state date is a new source release.
- A later capture of the same official state can be unchanged or revised;
  the capture date alone does not establish a new issue.
- When both official dates are unknown, identical representations with the
  same method across different capture dates are unchanged at the named capture
  layer. Changed captured content is reported as a revision at that layer.
- Changing between known and unknown official-date qualification is
  indeterminate. Method, observation-period, indicator-scope and coverage
  differences remain explicit comparison qualifications.

The version-2 CSV reader requires explicit date semantics:

```python
from datetime import date
from stratbox.domains.cbr.operations.service_network import bank_offices as offices
from stratbox.shared.evidence import SourcePayload

replay = offices.read_representation(offices.ReadOfficesRequest(
    SourcePayload(csv_bytes, "text/csv"),
    captured_on=date(2026, 11, 22),
    official_as_of=date(2026, 11, 1),
))
```

If only a capture date is supplied to this CSV reader, its default
`period_basis="unknown"` creates a literal-only qualification and no analytical
batch. A caller with evidence that the CSV describes a captured state can supply
`period_basis="capture"`. Conflicting period basis and official date fail
admission. Use the full source snapshot to preserve the original qualification
and provenance together with the cells.

## 4. Territorial publications: selection and formula evidence

The complete territorial release retains the selected sheet, header rows,
first/last data rows, territory column, physical column order, date basis,
unresolved fields and scope. Formula evidence retains formula text, attributes,
missing-cache markers and error-value markers by physical source coordinates.
Publisher caches are read as supplied; formulas are not executed.

Published territory names use the source namespace `cbr.published_territory`.
A label remains available when a common geographic reference cannot resolve it.
Unknown columns and units stay in the literal representation. The source
observation batch includes only fields qualified as counts by the extraction
rules. An explicitly selected fragment keeps `scope="selected_fragment"` and
its partial analytical qualification.

Multiple candidate blocks produce `OfficesRegCandidates` with a partial outcome.
The source snapshot preserves all candidates, original source identity,
requested date, selection parameters, source inputs and acquisition evidence.
Restoration returns the same candidate set and partial outcome. Candidate
selection remains explicit; the candidate output is distinct from a qualified
release output.

`ReadOfficesRegRequest(payload, as_of, source_details=None)` reads the CSV
representation. Without source metadata it retains literal cells, including a
short fragment, with `scope="unqualified_csv"` and no analytical batch. Supplying
metadata requires complete selection and formula evidence. The reader validates
it against the CSV and excludes unresolved formula columns before restoring
observations. It rejects metadata that would silently requalify a missing cache.

`make_readable(ReadableOfficesRequest(payload, "territorial_offices"))` traverses
all decoded worksheets rather than only the selected analytical block. Its
reading representation includes nonempty cells with physical row/column
coordinates and formula evidence. The corresponding `"bank_offices"` route
validates and returns the exact native HTML bytes.

## 5. What survives source persistence and source history

A source snapshot retains the exact CSV bytes, representation profile and row
count; dataset-version manifest and method; subject and metric properties;
period, explicit scalar type, value status, raw token and source-row evidence;
qualification, excluded fields and scope; fact identity; original acquisition
receipt and input lineage. It also retains the source-specific date, selection
and formula details described above.

Decoding checks complete component membership and exact schemas, reconstructs
dataset-version and fact identities, validates source evidence and checks the
complete snapshot identity. A subset of components cannot be restored as a
complete release. Reading retained data records a separate input for the current
invocation while preserving the release's original evidence.

```python
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.domains.cbr.operations.service_network import bank_offices as offices

encoded = offices.snapshot_release(offices.SnapshotOfficesRequest(
    release=parsed_release,
    dataset_id="cbr.bank-office-source",
    version_id="2026-11-22-capture-1",
))
assert encoded.outcome == "succeeded", encoded.diagnostics
store = FileDatasetStore(
    LocalFileStore("/caller/selected/location"), "datasets",
    provider_id="files", scope_id="research",
)
written = datasets.write_snapshot(
    datasets.WriteSnapshotRequest(encoded.value), store=store,
)
assert written.outcome == "succeeded", written.diagnostics

# A later process opens its own adapter and reads the same pinned reference.
loaded = datasets.read_snapshot(
    datasets.ReadSnapshotRequest(written.value.reference), store=store,
)
assert loaded.outcome == "succeeded", loaded.diagnostics
restored = offices.restore_release(loaded.value)
assert restored.outcome == "succeeded", restored.diagnostics
```

`build_source_history(OfficeHistoryRequest(releases, dataset_id, version_id))`
packs selected complete releases from one source family. It rejects competing
revisions with the same source capture/issue key. Two bank captures of the same
known official state remain distinct history entries when their capture dates
differ. `restore_history` checks every inner snapshot identity and the rebuilt
history identity. Historical publisher-wide completeness remains unknown.

## 6. Explicit identity alignment and semantic continuation

`align_offices(AlignOfficesRequest(...))` requires a qualified source observation
batch. Literal-only CSV and unresolved candidate sets do not qualify as its
input. A qualified territorial subset remains a subset after alignment.

| Mapping | Explicit contract | Preserved evidence |
| --- | --- | --- |
| Subject | `OfficeSubjectMapping(source: SubjectRef, target: SubjectRef, edition)` | Original namespace/identifier and selected mapping edition |
| Geography | `OfficeRegionMapping(source_label, region_id, edition)` | Published region/territory label, canonical geography ID and edition |
| Metric | `OfficeMetricMapping(source_id, target: MetricRef, edition)` | Count meaning, unit/scale and mapping edition |

Geographic mapping does not guess from a source label. Unresolved geography is
marked explicitly; `require_geography=True` fails when the source label cannot
be mapped. Metric mappings must preserve units and scale and retain count
meaning. The operation rejects dimension collisions and duplicate observations.
The exact source observation identity and mapping material are recorded as
inputs to the aligned batch.

```python
from stratbox.domains.cbr.operations import service_network as network

aligned = network.align_offices(network.AlignOfficesRequest(
    restored.value, "cbr.office-observations", "aligned-v1",
    regions=reviewed_region_mappings,
    require_geography=True,
))
assert aligned.outcome == "succeeded", aligned.diagnostics
portable = network.snapshot_observations(
    network.SnapshotOfficeObservationsRequest(
        aligned.value, "cbr.office-integrated", "aligned-v1",
    ),
)
assert portable.outcome == "succeeded", portable.diagnostics
```

`restore_observations` reads the same logical batch after the neutral dataset
boundary. The shared codec preserves subject namespace, metric definition,
unit/scale, all period fields, dimensions, perimeter, integer/Decimal/text type,
status, raw token, evidence, ordering and lineage. It imposes no additional
publisher-coverage claim and permits stored dataset identifiers to differ from
logical batch identifiers.

## 7. Count changes and independently rendered products

`calculate_changes(OfficeChangesRequest(baseline, candidate, dataset_id,
version_id))` compares aligned observation batches. It requires one period per
semantic cell in each batch and matches subject, complete metric definition,
dimensions and perimeter. The period kind must be compatible. Repeated keys or
disjoint semantic scope fail admission.

Only comparable numeric values with `reported` status produce a derived count
difference. Other matched cells produce an explicitly missing change. The result
reports `matched_cells`, `baseline_only` and `candidate_only`; an absent cell is
not silently interpreted as zero. Each result retains both source evidence
references and pins the exact baseline and candidate observation snapshots.
A count change alone does not identify an individual office opening or closure.

`build_view(OfficeViewRequest(batch, dataset_id, version_id, subjects=(),
metrics=()))` prepares a typed product. It includes subject identity, metric,
unit/scale, period, dimensions, perimeter, numeric value, status and evidence.
The selected batch identity is pinned in its inputs. The view's coverage is
complete for the admitted selected rows, with source-wide coverage inherited
from the supplied batch.

```python
view = network.build_view(network.OfficeViewRequest(
    calculated_changes.batch, "cbr.office-change-view", "view-v1",
))
assert view.outcome == "succeeded", view.diagnostics

# The same view can first pass through dataset.write_snapshot/read_snapshot.
workbook = network.render(network.RenderOfficeViewRequest(view.value, "xlsx"))
csv = network.render(network.RenderOfficeViewRequest(view.value, "csv"))
assert workbook.outcome == csv.outcome == "succeeded"
```

The renderer accepts the exact prepared-view schema and complete component set.
It does not reparse the original source or rerun the count calculation. The
XLSX writer treats cell text literally. Generic artifact operations can publish
either representation to the caller-selected file store, including a network
location. Storage placement and optional publication policy remain separate
from source, analytical and presentation semantics.
