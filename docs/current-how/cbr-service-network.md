# Bank of Russia service-network releases

The two source families retain their own parsers and qualifications. Their
portable boundary is a complete `DatasetSnapshot`: it includes the literal
representation, typed observations and the evidence needed to continue
comparison after storage. The office CSV remains a useful representation of the
published table; its cells alone carry less information than the complete
release.

## Families and registered operations

| Publication family | Registry source | Source extraction | Portable encoding | Portable reading |
|---|---|---|---|---|
| Offices by bank and published region | `cbr.service_network.bank_offices` | `cbr.offices.parse` | `cbr.offices.snapshot` | `cbr.offices.restore` |
| Territorial office network | `cbr.service_network.territorial_offices` | `cbr.offices_reg.parse` | `cbr.offices_reg.snapshot` | `cbr.offices_reg.restore` |

The parsers admit explicit offline `material.payload`, `source.payload` or their
own original contract and perform source-specific validation. Acquisition from
CBR remains available independently. Exact originals can pass through
`source.save_original` / `source.read_original` or the material operations.

Snapshot encoding is a `render` operation. Durable preservation and ingestion
belong to the selected dataset adapter. The route is:

1. Parse or capture one source release.
2. Encode the full release with the family's `snapshot_release` operation.
3. Write the `DatasetSnapshot` through `dataset.write_snapshot`.
4. Read its pinned reference through `dataset.read_snapshot` in a later process.
5. Restore with the family's `restore_release` operation and continue comparison.

The storage reference owns physical placement. The dataset identity depends on
the logical contents, schema, coverage and input lineage. The full source bytes
remain a separately preservable original; the release snapshot retains their
identities and acquisition evidence.

## What survives the boundary

Each release snapshot has a typed metadata component and a typed observation
component. It retains:

- The exact CSV bytes, representation profile, encoding and row count.
- The original dataset version and its manifest, including method, parameters,
  resource identifiers and source input identities.
- Subject namespace and identifier; published region and section labels;
  metric, unit, scale, measurement kind and definition version when present.
- Observation period and value with its explicit scalar type, value status,
  source-row evidence and original cell token. Blank, dash and numeric zero keep
  their different meanings.
- The qualification's provenance, analytical coverage, scope and excluded
  fields; fact identity and comparison method.
- Original acquisition receipt and source input lineage. Reading retained data
  records a separate `retained_snapshot` input in the new invocation and keeps
  the release's original evidence unchanged.

Decoding checks component membership and schemas, rebuilds the dataset-version
and fact identities, validates source-specific evidence, and checks the complete
snapshot identity. A selected subset of components cannot become a complete
restored release. The codecs use explicit scalar and metadata grammars and do
not deserialize arbitrary Python objects.

## Bank offices: observation date and capture date

`ParseOfficesRequest(payload, captured_on, official_as_of=None)` has two different
date meanings. `captured_on` identifies the capture. A supplied `official_as_of`
identifies the known state of the data. Observations use `PeriodRef("as_of", ... )`
when that date is known. Otherwise they use an explicitly capture-based period.
The complete snapshot retains both fields and the resulting observation periods.

For example, an official state of 1 November captured on 22 November remains an
observation for 1 November after storage and reading. `ParsedRelease.as_of`
remains the capture date for this family; `source_details` distinguishes the two
date roles. The read-only machine adapter accepts `official_as_of` and projects
both `captured_on` and `official_as_of`.

The CSV reader is version 2 and uses the explicit request:

```python
from datetime import date
from stratbox.domains.cbr.service_network import bank_offices as offices
from stratbox.shared.evidence import SourcePayload

replay = offices.read_representation(offices.ReadOfficesRequest(
    SourcePayload(csv_bytes, "text/csv"),
    captured_on=date(2026, 11, 22),
    official_as_of=date(2026, 11, 1),
))
```

If the caller only knows the capture date, the default CSV read has
`period_basis="unknown"`, a literal-only qualification and no analytical batch.
This prevents a missing observation date from becoming the capture date. A
caller with explicit evidence that the CSV describes a capture-based snapshot
can supply `period_basis="capture"`. Conflicting `period_basis` and
`official_as_of` values fail admission. Use the full dataset snapshot when the
original qualification and provenance are required as well as the cell values.

## Territorial offices: source selection and formula evidence

The complete territorial release preserves the selected sheet, header rows,
first and last data rows, territory column, physical column order, date basis,
unresolved fields and scope. It also retains formula text, formula attributes,
missing-cache markers and error-value markers by source row and column.

The published territory is stored in `cbr.published_territory`. A source label
survives even when a common geographic directory cannot resolve it. Existing
source-name inspection can be performed separately. Unknown columns and units
remain in the literal representation. The analytical batch includes only the
fields qualified by the extraction rules. A selected fragment retains
`scope="selected_fragment"` and partial analytical coverage.

Multiple candidate blocks produce `OfficesRegCandidates` with a partial outcome.
Its snapshot retains **all** candidates, the source identity, the requested
date and selection parameters, source inputs and acquisition receipt when
available. Reading this snapshot returns the same candidate set with the same
partial outcome. It never chooses a block on the caller's behalf. The typed
`candidates` output can be bound to the snapshot operation and remains distinct
from the `release` output.

The version-2 CSV reader accepts
`ReadOfficesRegRequest(payload, as_of, source_details=None)`. Without source
metadata it reads literal cells, including a short fragment, with
`scope="unqualified_csv"` and no analytical batch. Explicit metadata must contain
the complete selection and formula evidence. The reader validates this metadata
against the CSV and excludes unresolved formula columns before restoring
observations. It rejects evidence that would silently requalify a missing
formula cache. The snapshot codec is the default route for lossless release
preservation.

## Example: preserve and continue

The same steps apply to either family. This example uses bank offices and a
caller-owned file store; another dataset adapter receives the same logical
snapshot.

```python
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.domains.cbr.service_network import bank_offices as offices
from stratbox.shared.data.releases import CompareReleaseRequest

encoded = offices.snapshot_release(offices.SnapshotOfficesRequest(
    release=parsed_release,
    dataset_id="cbr.bank-office-history",
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

# A later process creates its own adapter and reads the same pinned reference.
loaded = datasets.read_snapshot(
    datasets.ReadSnapshotRequest(written.value.reference), store=store,
)
assert loaded.outcome == "succeeded", loaded.diagnostics
restored = offices.restore_release(loaded.value)
assert restored.outcome == "succeeded", restored.diagnostics
comparison = offices.compare(CompareReleaseRequest(
    candidate=restored.value, baseline=previous_release,
))
```

The restored release has the same fact identity, source selection, qualifications
and observation periods as the value before preservation. Comparison therefore
retains the distinction between changed facts, changed structure, changed
coverage and changed representation. The original parser is not called during
restoration.
