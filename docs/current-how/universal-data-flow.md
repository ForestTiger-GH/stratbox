# Universal material flow and operation handoff

Scope: implemented core contracts and the Minfin and Frank RG pilots in Stratbox
0.17.0. Original formats include PDF, workbooks, archives, HTML and arbitrary
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
3. Binding operation results — typed projection, admission and lineage.
4. Selecting adapters — explicit source and destination bindings.
5. Logical datasets — the common boundary for file and database representations.
6. Shared archives — exact members and separately identified generated containers.
7. HTTP routes — logical publisher policy and qualified transport evidence.
8. Pilot lifecycles — Minfin and Frank RG behavior.
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
| `material.read_location` | Explicit store locator, optional expected hash/revision | Exact payload and pinned reference |
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

`BoundRequest.invoke()` preserves input computation parents through
`ExecutionContext`. The consumer still identifies the typed input it actually
uses. Route changes therefore do not change a business computation key, while
changed typed values, source evidence or methods do.

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

See [logical dataset snapshots](logical-dataset-snapshots.md) for executable
examples, type semantics, publication guarantees and bounded storage behavior.
The implementation provides a usable file representation of a logical database;
a desktop SQL engine remains an adapter implementation owned by that consumer.

## 6. Shared archives

`material.archive` accepts explicitly named members containing supplied payloads
or pinned references from independently selected stores. It preserves exact
member bytes, validates member names and collisions, rejects source/destination
aliases, and commits the generated archive through the receiving store.

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

## 8. Pilot lifecycles

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
Table parsing, flakes and financial calculations are outside this domain's
implemented scope. Other domains retain their existing operation surfaces;
this release's complete portable lifecycles cover Minfin and Frank RG.

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
