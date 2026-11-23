# Universal material flow and operation handoff

Scope: implemented core contracts and independent publisher routes. Original formats include PDF, workbooks, archives, HTML and arbitrary
admitted byte representations. Logical dataset adapters have a separate typed
table interface.

An operation consumes a qualified value and produces another qualified value.
The caller chooses where bytes come from, where results are retained and which
adapter provides access. A domain owns recognition, interpretation and financial
meaning. Source registry records identify logical series and processing profiles;
an acquisition profile can supply a convenient default public route.

Contents:

1. Independent identities and responsibilities — what remains stable across stores.
2. Reading and retaining materials — exact bytes and complete semantic descriptors.
3. Binding operation results — named inline/result adapters, source routes, admission and lineage.
4. Selecting adapters — explicit source and destination bindings.
5. Logical datasets — the common boundary for file and database representations.
6. Shared archives — exact members and separately identified generated containers.
7. HTTP routes — logical publisher policy and qualified transport evidence.
8. Domain lifecycles — Minfin, Frank RG and CBR behavior.
9. Integration boundaries — supplied routes, external owners and operational limits.

## 1. Independent identities and responsibilities

| Contract | Meaning | Physical location included? |
| --- | --- | --- |
| `DataContract` | Semantic schema, edition and processing role | No |
| `SourceAssetIdentity` | Logical series, issue and asset | No |
| `ByteIdentity` | SHA-256 and length of exact bytes | No |
| `Representation` | Encoding profile, version, media type, bytes and encoding | No |
| `MaterialArtifact` | Representation, semantic contract, source context and lineage | No |
| `MaterialReference` | Exact bytes at one store location and observed revision | Yes |
| `ArtifactReference` | Pinned representation and complete descriptor | Yes |
| `DatasetSnapshot` | Typed table components under an immutable logical manifest | No |
| `CollectionManifest` | Ordered materials, semantic roles, exact identities and per-item outcomes | No |
| `SnapshotReference` | Provider, scope, dataset, version and expected logical identity | Provider and scope |
| `ResultReference` | Consumer-owned handle to an operation result | Opaque consumer authority |

`originals`, `readable`, `extracts`, `integrated` and `products` are processing
roles. Every role can use the material layer. Roles alone establish neither
schema compatibility nor physical format. A PDF original can be retained before
any parser or external AI conversion is available. A later readable document has
its own representation identity and records the original PDF as an input.

An issue identifier identifies a publication issue; observation periods inside
a workbook remain domain data. Existing source payload IDs are retained as
explicit producer context. `MaterialArtifact.series_id` and its optional
`source_asset` make the series/issue/asset distinction explicit without deriving
it from filenames, URLs or observation dates.

## 2. Reading and retaining materials

| Operation | Input | Output |
| --- | --- | --- |
| `source.receive_original` | Admitted HTTP request and accepted media types | Exact bytes and HTTP receipt |
| `source.receive_to_store` | HTTP source and independent destination | Verified streaming storage result |
| `material.read_location` | Explicit store locator, optional expected hash/revision | Neutral exact payload and pinned reference |
| `source.read_original` | Pinned material reference | Verified original payload |
| `source.save_original` | Original payload and destination | Exact byte-preserving storage result |
| `material.transfer` | Pinned material and independent destination | Streaming copy; source remains present |
| `material.save_artifact` | Complete encoded artifact and destination | Pinned representation and descriptor |
| `material.read_artifact` | Artifact reference | Restored contract, representation and lineage |
| `material.transfer_artifact` | Artifact reference and destination | Same artifact identity at a new location |

The first read can establish a previously unknown hash. Replay checks the
retained hash and, when supplied, the observed revision. A revision change
during a read fails that read. An explicit missing file, unavailable adapter or
incorrect identity terminates the operation; acquisition never switches to a
default Internet route.

An arbitrary file read returns `material.payload` with no original role. The
receiving source operation admits its format and explicit source context before
treating it as an original. Existing complete artifact descriptors retain their
own roles during replay; storage itself never changes a product into an original.

`ArtifactDestination("flakes/budget.json")` retains raw representation bytes at
that locator and a canonical descriptor at
`flakes/budget.json.stratbox.json`. A caller can supply a separate descriptor
locator. The descriptor contains the `DataContract`, representation profile,
encoding, exact byte identity, qualified source identity, input receipts and
complete computation parents. Original bytes remain unchanged when retained as
an artifact.

Both objects use immutable creation. Each physical write has its own effect
receipt; the artifact reference is returned only after both are confirmed. A
confirmed data write followed by an unavailable descriptor does not constitute
a published complete artifact. `unknown` remains distinct from failure and
requires reconciliation or an explicit immutable retry. A descriptor collision
does not overwrite a previously retained version.

Portable references use `ArtifactReference.to_bytes()` and
`ArtifactReference.from_bytes()`. They preserve exact locators and provider scope,
so a consumer retains them inside its own access boundary. They are integrity
expectations, not signatures or independent origin attestations.

`material.transfer` streams exact bytes. Artifact replay and artifact transfer
currently materialize bounded representations in memory. Their default limits
are 64 MiB for replay, 8 MiB for a descriptor and 512 MiB for aggregate operation
byte resources. Caller budgets can lower these limits. Representation codecs
can impose additional domain limits.

## 3. Binding operation results

`project_output(result, output_name)` projects only a declared dataclass path
from an actually admitted outcome. `bind_request()` checks schema/version/role,
required qualifications, coverage, mandatory inputs and parameters, then builds
the consumer's declared request type. It never imports a callable from input
data, evaluates a Python expression or performs an implicit semantic conversion.

```python
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.operations.source.original_definitions import SAVE, OriginalDestination
from stratbox.core.operations.source.originals import save_original

# prepared is a successful frg.prepare_file OperationResult.
bound = bind_request(
    SAVE,
    {"source": project_output(prepared, "payload")},
    parameters={"destination": OriginalDestination(prepared.value.filename)},
)
saved = bound.invoke(save_original, store=destination_store)
```

`BoundRequest.invoke()` preserves input receipts and computation parents through
`ExecutionContext`. Producer receipts are explicitly marked as provenance and
remain in result evidence. Upstream effects stay attached to their producer.

The runner captures exact named inputs, collection order and multiplicity, and
actual semantic parameter values including defaults. These determine the
computation together with the operation, content-addressed method fingerprint
and actually consumed semantic dependencies. Inherited producer history is separate from this signature.
Equal values supplied directly or restored from retention therefore retain the
same computation key. `Invocation.use` and `Invocation.depend` establish actual dependencies; merely
supplying an unused receipt adds provenance. Consumed dependency editions remain
significant even when their bytes match another input.

`core.execution.values` supplies common value descriptors, exact identities,
snapshot adapters, input receipts and byte/cell accounting. Domains provide
interpretation and admission rules for their own types. Source context has its
own explicit adapters, so transport labels cannot become logical source claims.

For an encoded result, `artifact_from_output(result, name, series_id=...)`
constructs its complete artifact. After replay, `project_artifact(result)`
exposes the retained representation under the descriptor's semantic contract
and with its original computation. The next domain decoder performs the actual
interpretation. Storage does not add publisher-origin or coverage claims.

Successful and explicitly admitted partial results can be connected. Failed,
cancelled or unknown results are rejected. A confirmed storage qualification
requires matching actual effect evidence, or matching read evidence for a
read-only operation; merely seeing input bytes cannot confirm a write.

For a retained operation result, `ResultResolver` belongs to the consuming
application. `reference_output()` and `resolve_output()` check the owner,
operation, invocation, output and expected identity. The core supplies this
handoff contract, while the consumer owns durable jobs, access control, result
storage and admitted result codecs.


### Supplied values and named collections

`prepare_input(value, contract=...)` creates a `PreparedInput` for an explicitly
supplied typed value. It carries exact input receipts, optional computation
lineage and caller-owned qualifications. A `SourcePayload` has the built-in
`source.payload` contract and its original-byte receipt. A `MaterialArtifact`
default preserves the complete artifact wrapper under `material.artifact`;
`artifact_input(artifact)` explicitly exposes its representation under the
artifact's semantic contract. Domain decoding remains a separate operation.
Prepared input adapters cannot assert `storage.confirmed`.

`collect_inputs(items, contract=..., element_contract=...)` assembles a named
tuple of admitted projected or prepared values. Every member must have the
exact element contract. The collection preserves input receipts and member
computation parents, intersects qualifications/coverage, and retains a partial
outcome when any member is partial. Collection assembly supplies no storage
confirmation or implicit semantic integration. Revision and coverage selection
remain explicit caller decisions.

`adapt_input(value, output_name=..., resolver=...)` accepts a projected/prepared
input directly, projects an operation result only with a named output, and
resolves a retained result only through the supplied resolver. Raw domain values
require `prepare_input()` and their explicit contract. Binding never guesses a
schema from a filename or evaluates a serialized Python object.

### Catalog calls and source-route admission

```python
from stratbox.operations import operation_catalog
from stratbox.core.execution.handoff import prepare_input

catalog = operation_catalog()
# payload is a supplied SourcePayload.
call = catalog.bind(
    "workbook.extract",
    inputs={"source": prepare_input(payload)},
    parameters={"series_id": "example.series", "issue_id": "2026-08"},
)
result = call.invoke()
```

`catalog.bind_source(series_id, format=...)` selects a logical source and its
canonical route. Its `bind(operation_id, ..., inputs=..., parameters=...)`
checks operation applicability, formats, fixed source parameters and exact
named input contracts. Exact producer/output and consumer/input contracts govern
handoff. Stages describe a derived overview. When an operation supports only a subset of the
source's formats, a format selection is required.

A retained extract can enter its independent next operation directly. A source
route does not impose acquisition or intermediate saving as prerequisites.
Technical encoding, replay and maintenance stay separate from economic stages.
The resulting `OperationCall.invoke()` resolves the existing handler and retains
the same execution, budget, provider and finalization rules as its direct API.

## 4. Selecting adapters

The execution context can contain multiple bindings for a capability. Each
binding carries a provider ID, optional scope, readiness and guarantees. Reading
and writing have independently selected roles.

```python
from stratbox.core.execution import ExecutionContext
from stratbox.core.runtime.capabilities import (
    CapabilityRequirement, ProviderBinding, ProviderSelection,
)
from stratbox.core.operations.materials.definitions import ReadLocationRequest
from stratbox.core.operations.materials.operations import read_location

context = ExecutionContext(bindings=(
    ProviderBinding("files", CapabilityRequirement("filestore"), "ready", incoming, "incoming"),
    ProviderBinding("files", CapabilityRequirement("filestore"), "ready", retained, "retained"),
    ProviderBinding("files", CapabilityRequirement("output_filestore"), "ready", retained, "retained"),
))
loaded = read_location(
    ReadLocationRequest("delivery/report.pdf", "application/pdf", "publisher.report"),
    selection=ProviderSelection("files", "incoming"), context=context,
)
```

Selection occurs before mandatory capability admission. A binding can supply
the provider object directly; a caller can also pass the object explicitly,
provided it agrees with the selected binding. An explicit absent, ambiguous or
unready choice never falls back to a local default. Physical locator parsing,
mounting and path aliases belong to the selected adapter.

Portable material operations require a stable `store_id` and a canonical
`storage_scope(locator)`. Namespace selection and canonical object identity are
different: provider/scope selects an adapter, while the store verifies that a
reference still points to the expected object. Separately retained descriptors
can use the `descriptor_filestore` capability.

## 5. Logical datasets

The logical dataset layer separates schemas and table values from file or
database layout. `DatasetCatalog`, `DatasetReader` and `DatasetVersionWriter`
are narrow ports; a backend advertises additional query or update capabilities
separately.

`MemoryDatasetStore` and `FileDatasetStore` implement the same immutable snapshot
contract. A file representation stores exact typed components and publishes its
manifest last. `DatasetAssembly` pins components in other snapshots/providers;
selected reading resolves only requested members and performs no automatic
row concatenation.

Domain snapshot constructors encode in-memory representations. The independent
`dataset.write_snapshot` operation performs ingestion and preservation. Repeated
logical components with identical table identities share one physical object
while retaining every component name in the manifest.

See [logical dataset snapshots](logical-dataset-snapshots.md) for executable
examples, type semantics, publication guarantees and bounded storage behavior.
The implementation provides a usable file representation of a logical database;
a desktop SQL engine remains an adapter implementation owned by that consumer.

## 6. Shared archives

`material.archive` accepts explicitly named members containing supplied payloads
or pinned references from independently selected stores. It preserves exact
member bytes, validates member names and collisions, rejects source/destination
aliases, and commits the generated archive through the receiving store.

Every generated archive includes a shared `CollectionManifest`. A supplied
manifest must agree with the exact member names, hashes, sizes and media types.
Member roles and source-asset identities remain independent of the generated
container. Per-item dispositions and source coverage remain explicit; successful
selection completion does not assert complete publication history.

Relative nested names are supported. The writer rejects traversal, ambiguous
Unicode/case names and file-parent collisions. `ArchiveWriteLimits` separates
member, input-byte and supplemental-byte limits; the default member ceiling is
10,000, including supplemental files. `material.serialize_collection` and
`material.read_collection` provide canonical portable manifest replay.

The ZIP has its own byte identity. Each returned member receipt records its
source identity, container identity and archive member name. It does not replace
an originally published ZIP/RAR with a reconstructed archive. A publisher's
archive can itself remain an opaque original.

Frank RG retains domain-specific selection and canonical naming. Its existing
archive compositions use the same neutral archive primitives; prepared files
can also be passed directly to the registered `material.archive` operation.

## 7. HTTP routes

An `HttpsRoute` maps admitted publisher hosts to one explicit HTTPS gateway and
path prefix. Its `policy_identity` hashes the full route configuration. Managed
execution admits a route only when the selected HTTP binding includes that
route's exact `admission_guarantee`, alongside destination and budget guarantees.
A changed route requires a corresponding admitted capability.

The response must match both the logical request and physical gateway target,
and the gateway transport must report peer-bound assurance. A routed receipt
keeps `origin_assurance="provider_reported"`, records transport assurance and
route policy separately, and preserves hashes of both targets. Route admission
does not promote a gateway connection into direct publisher peer evidence.
Conditional HTTP 304 reuse remains disabled for routed requests.

## 8. Domain lifecycles

### 8.1. Minfin

The v3 logical registries contain profile references. Typed acquisition profiles
own default official publication pages. Supplied HTML or `DiscoverRequest.page_url`
can override acquisition explicitly. Offline table extraction accepts a
`SourcePayload` from HTTP, disk, a retained object or a preceding operation.

The source-local flake has two durable routes:

1. `minfin.serialize_flake` creates complete JSON; generic artifact operations
   retain/replay it; `minfin.read_flake` restores every field.
2. `minfin.flake_snapshot` produces metadata, columns and rows as three typed
   components; generic dataset operations retain/replay them;
   `minfin.read_flake_snapshot` restores the same flake.

Both preserve original identity, source coordinates, original headers,
periodicity, value basis, method, units and exact null/empty/value distinctions.
Mixed NWF units remain mixed. CSV remains a presentation export. Existing
headline calculations consume the same restored domain object from either route.

### 8.2. Frank RG

Directory discovery/recognition and supplied-byte capture both produce an
admitted report. `frg.prepare_file` creates a canonical name without decoding or
rewriting workbook bytes. Generic save, replay, transfer and archive operations
can then choose independent destinations. Discovery, acquisition and guarded
housekeeping accept named selections.

Cleanup retains explicit plan/revalidation/conditional-effect boundaries.
Both Frank RG ZIP routes now embed the common material manifest. An optional
selection report is an explicitly identified supplemental member. The generated
container is a product; its unchanged report members remain originals.
Table parsing, flakes and financial calculations remain outside this domain's
implemented scope.

### 8.3. CBR

A common registry separates 57 logical source series from acquisition defaults
and canonical processing profiles. The mixed-input collector accepts supplied
bytes, references from individually selected stores and explicit HTTP sources.
It preserves exact original identity and an ordered per-item outcome ledger.

Reporting forms, corporate debt/issuance, regional escrow, service-network
releases and SORS calculations have explicit snapshot codecs. They reconstruct
the complete domain value required by the next operation. Reporting-form CSV
collections also preserve schema, physical record flags and original members.
The domain guide explains source-only variants and remaining parser boundaries:
[CBR processing routes](cbr-data-pipeline.md).

## 9. Integration boundaries

An existing checked-out or mounted corpus is a file provider. A pinned public
corpus object can be acquired through the HTTP operation with its explicit URL
and source context, then retained and identity-checked. Publication into a
remote corpus, repository commit policy and application database ownership
belong to adapters or consuming applications. The core never treats a local
write as confirmation of a remote publication.

External parser or AI operations can supply a `Representation` with an explicit
contract and input receipts. The core persists it uniformly but does not infer
semantic correctness from media type, path or storage. A source parser,
cross-source integration or financial calculation remains a separately declared
operation.

The complete offline example is
[universal storage flow](../../examples/universal_storage_flow.py).
The core remains independent of desktop/mobile scheduling and user interfaces.
