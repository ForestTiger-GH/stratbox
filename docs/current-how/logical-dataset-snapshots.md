# Logical dataset snapshots

Scope: implemented core contracts, memory and file reference adapters, Minfin
flake integration and the grouped CBR snapshot codecs in Stratbox 0.19.0.

Stratbox represents a logical dataset as an immutable versioned manifest and
explicitly typed table components. Domain code supplies the same value to any
adapter implementing the dataset ports. The adapter owns physical layout,
scope enforcement and commit behavior. Material files such as PDF, XLSX and
rendered documents use the separate material operations.

The implemented dataset boundary supports immutable publication, version
discovery, selected component reads and distributed composition. The supplied
adapters store values in memory or in verified files. An application database
adapter can implement the same contracts; a SQL query engine and the desktop
application's database are outside this implementation.

Contents:

1. Contracts and identities — distinguish schemas, values, manifests and references.
2. One value, two adapters — execute the same publication and read operations.
3. Provider selection and portable references — resolve an explicit environment scope.
4. Selected and distributed reads — preserve coverage and pinned composition.
5. Publication evidence and recovery — handle confirmed, failed and unknown effects.
6. Limits and domain integration — identify supported behavior and extension boundaries.

## 1. Contracts and identities

The contracts live in
[shared/data/snapshots.py](../../src/stratbox/shared/data/snapshots.py).

| Code | Value | Meaning |
| --- | --- | --- |
| DS1 | `ColumnSchema` | Column name, explicit scalar type, nullability and optional unit. |
| DS2 | `TableSchema` | Editioned `DataContract`, ordered columns and optional primary key. |
| DS3 | `TypedTable` | Immutable ordered rows, schema and logical content identity. |
| DS4 | `DatasetManifest` | Dataset and version IDs, component schemas and identities, row counts, coverage, input evidence and parent identities. |
| DS5 | `DatasetSnapshot` | A manifest and all or a selected subset of its table values. |
| DS6 | `SnapshotReference` | Provider, scope, dataset, version and exact logical manifest identity. |
| DS7 | `DatasetAssembly` | A manifest and explicit links to components in pinned parent snapshots. |

`DataContract.role` can describe originals, readable data, extracts, integrated
data, products, or a control value with no processing role. A role classifies
meaning; it does not select an adapter or establish schema compatibility.

Supported scalar types are `BOOLEAN`, `INT64`, `INTEGER`, `FLOAT64`, `DECIMAL`,
`TEXT`, `BINARY`, `DATE`, `TIMESTAMP`, `LOCAL_DATETIME` and `DURATION`.
Null is represented by `None` and requires a nullable column. Types are explicit:
an integer does not silently become a float, and a string does not silently
become a decimal. `FLOAT64` preserves IEEE bits, including signed zero and
special values. Decimal spelling preserves its exponent and trailing zeros.
Aware timestamps represent UTC instants; local datetimes remain timezone-free.
The [table codec](../../src/stratbox/core/storage/datasets/codec.py) restores
these values and checks the declared logical identity.

A table's logical identity includes its ordered schema and values. A dataset
identity includes its version, component declarations, coverage and lineage.
Physical JSON bytes have a separate byte identity. Backend names, storage paths
and the physical availability of input evidence do not change logical identity.
The codec still preserves input availability for inspection.

## 2. One value, two adapters

This example uses only the standard library and Stratbox. It constructs one
typed value, writes it through both adapters, transports the returned reference
as JSON and reads the same value back. Temporary files disappear when the
example finishes.

```python
import json
from decimal import Decimal
from tempfile import TemporaryDirectory

from stratbox.core.storage.datasets import FileDatasetStore, MemoryDatasetStore
from stratbox.core.storage.datasets.codec import reference_from, reference_value
from stratbox.core.storage.datasets.definitions import (
    ReadSnapshotRequest, WriteSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (
    ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage,
    TableSchema, TypedTable,
)

schema = TableSchema(
    DataContract("example.amounts", 1, DataRole.EXTRACTS),
    (
        ColumnSchema("item", ScalarType.TEXT),
        ColumnSchema("amount", ScalarType.DECIMAL, nullable=True, unit="USD"),
    ),
    primary_key=("item",),
)
table = TypedTable(schema, (("a", Decimal("10.50")), ("b", None)))
snapshot = DatasetSnapshot.build(
    "example.amounts", "2026-11", schema.contract,
    (("amounts", table),),
    coverage=SnapshotCoverage("unknown", "Caller supplied this example table."),
)

with TemporaryDirectory() as directory:
    adapters = (
        MemoryDatasetStore(provider_id="memory", scope_id="example"),
        FileDatasetStore(
            LocalFileStore(directory), "datasets",
            provider_id="files", scope_id="example",
        ),
    )
    for adapter in adapters:
        written = write_snapshot(WriteSnapshotRequest(snapshot), store=adapter)
        assert written.outcome == "succeeded", written.diagnostics
        reference = written.value.reference
        assert reference is not None

        wire = json.dumps(reference_value(reference))
        restored_reference = reference_from(json.loads(wire))
        loaded = read_snapshot(
            ReadSnapshotRequest(restored_reference), store=adapter,
        )
        assert loaded.outcome == "succeeded", loaded.diagnostics
        assert loaded.value == snapshot
        assert restored_reference.identity == snapshot.identity
```

`MemoryDatasetStore` is process-local. `FileDatasetStore` persists canonical
component files and version manifests through the supplied `FileStore`.
Changing the underlying file provider can change path handling and physical
access while keeping the dataset value and domain calculations unchanged.

## 3. Provider selection and portable references

The [dataset ports](../../src/stratbox/core/storage/datasets/ports.py) separate
catalog, reading and version writing. Registered operations use the capability
roles `dataset_catalog`, `dataset_reader` and `dataset_writer` respectively.

A trusted local call can pass `store=adapter`, as above. An application can
instead supply `ProviderBinding` values through `ExecutionContext` and select
one with `ProviderSelection(provider_id, scope_id)` in the request. A read with
no explicit adapter or selection resolves the provider and scope recorded in
its `SnapshotReference`. An unavailable or ambiguous provider produces an
error; it does not redirect the read to another store.

Managed readers and catalogs require `scope_bound`. Managed writers require
`scope_bound` and `verified_commit`. The binding admits the adapter's declared
capability; the accepting adapter still enforces actual scope and commit
conditions.

The explicit `reference_value()` and `reference_from()` codecs transport
`provider_id`, `scope_id`, `dataset_id`, `version_id` and the manifest identity.
They encode no Python objects, classes, executable expressions or filesystem
paths. The receiving process supplies its own authorized provider bindings.

## 4. Selected and distributed reads

`ReadSnapshotRequest(reference, components=("amounts",))` requests named
components. `components=None` requests all declared components, and an empty
tuple requests only the manifest. Returned tables follow manifest order.
Unknown or duplicate component names fail validation.

The returned `DatasetSnapshot.manifest` always retains the complete pinned
composition. `DatasetSnapshot.complete` indicates whether every component is
materialized in that value. This is distinct from `SnapshotCoverage`, whose
`complete`, `partial` or `unknown` status describes caller-declared source
coverage. Reading every stored table does not prove that the publisher's
historical series is complete. A selected subset cannot be published as though
it were the full original snapshot.

For distributed composition, construct a `DatasetManifest` with the intended
component schemas, identities and row counts. Set `parents` to the exact
parent manifest identities. Each `ComponentLink` maps one output name to one
component in a `SnapshotReference`; `DatasetAssembly` validates that mapping.
Provide a `DatasetProviders` resolver containing the parent readers to the
receiving adapter.

The adapter validates each referenced snapshot and table before publishing the
assembly. Reads resolve only the selected components and validate their pinned
identities again. Tables remain distinct components; concatenation, joins,
period interpretation and calculations belong to explicit domain operations.

## 5. Publication evidence and recovery

The [file adapter](../../src/stratbox/core/storage/datasets/files.py) commits and
verifies content-addressed table files before committing the version manifest.
The manifest makes the version visible to its catalog. A failed attempt can
leave reusable component objects, while no confirmed snapshot reference is
returned for an incomplete publication.

Identical content-addressed components within one snapshot are written once.
Their logical names remain separate manifest entries and selected reads still
address each name independently. This prevents conflicting effect receipts for
an identical physical object during one invocation.

An existing dataset/version with different logical content produces
`dataset.version_conflict`. An identical immutable write can return
`already_present` after verification. There is no automatic mutable `latest`
pointer or overwrite of an older version.

`dataset.write_snapshot` records logical `dataset.write` evidence separately
from physical `storage.write` effects. Its result contains a confirmed
reference only for `stored` or `already_present`. An uncertain commit or lost
acknowledgement yields `unknown`; callers must inspect operation outcome and
effect receipts before using a result as confirmed publication evidence.

A later explicit retry of the same immutable file version can reconcile the
result by reading and validating the completed manifest and components. An
unknown result is never converted to success solely because a write was
attempted. Scope mismatches, changed bytes, missing components and incompatible
schemas fail a read before a typed snapshot is returned.

## 6. Limits and domain integration

Registered dataset operations have 512 MiB ceilings for input, output and
temporary bytes. Caller budgets can impose stricter limits. Nested reads,
writes and distributed component resolution share the operation's budget and
cancellation checks. The file reference adapter defaults to 64 MiB per encoded
object and 10,000 catalog entries; read controls default to five million cells.
These are bounded reference implementations, rather than a storage format for
unlimited single-object tables.

Minfin's `minfin.flake_snapshot` and `minfin.read_flake_snapshot` operations
preserve a complete source-local flake as metadata, column and row components.
The same flake can therefore round-trip through memory or file snapshots while
retaining its domain meaning. CBR adds complete codecs for reporting-form source
records and results, corporate-lending flakes/streams/calculations/views, escrow
flakes/datasets/views, service-network releases and SORS bundles/results. Their
domain decoders require complete component sets and verify source context and
computation lineage. See [CBR routes](cbr-data-pipeline.md).

The explicit dataframe codec preserves ordered axes, nullable values, supported
dtypes, categorical dictionaries and exact scalar values. Mixed scalar objects
use allowlisted tags; arbitrary Python objects and executable descriptors fail
admission. Its default limit is five million cells per frame.

Snapshot constructors advertise `render`, because they prepare a logical value
in memory. `dataset.write_snapshot` advertises `ingest` and `preserve`, while the
matching domain restore operation advertises `read_extract`. Confirmed durable
storage requires the actual dataset write receipt.

Frank RG currently retains its file-oriented
scope and does not acquire a table parser or analytical database through this
infrastructure.

A future database adapter must preserve the same declared schemas, values,
versions, selected-read behavior and commit evidence. SQL execution, row-level
updates, transactions across versions and domain query semantics require
additional explicit ports or capabilities. They are not inferred from the
presence of a `FileStore` or a dataset reader.
