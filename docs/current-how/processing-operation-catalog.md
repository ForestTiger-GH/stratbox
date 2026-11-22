# Processing contracts and independent operation discovery

Stratbox exposes processing semantics through the same `OperationDefinition`
objects used by Python execution. The catalog describes source acquisition,
interpretation, calculations and products without importing their handlers.
This article documents the implemented library interfaces. Domain coverage
entries distinguish callable implementations from missing or unassessed work.

Applications can inspect these contracts, select retained inputs and call
individual operations. Scheduling, durable jobs, protocol servers, physical
directory naming and artifact retention remain application responsibilities.

Contents:

1. Data roles and schemas — distinguish processing meaning from file format.
2. Definitions and schemas — inspect contracts without loading handlers.
3. Bounded discovery — page and filter application-facing descriptions.
4. Qualified connections — inspect semantic links and their conditions.
5. Domain coverage — distinguish independent operations, delegation and gaps.
6. Execution boundaries — preserve evidence and incomplete outcomes.
7. Extending an owner — keep metadata with its typed operation definition.

## 1. Data roles and editioned schemas

| Code | `DataRole` | Meaning |
| --- | --- | --- |
| R01 | `ORIGINALS` / `originals` | Source-native material, including an archive published by the source. Original members retain this role inside a separately generated container. |
| R02 | `READABLE` / `readable` | A reading-oriented publication representation. |
| R03 | `EXTRACTS` / `extracts` | Source-local structured data or its retained representation. |
| R04 | `INTEGRATED` / `integrated` | Data aligned under a shared semantic integration model. |
| R05 | `PRODUCTS` / `products` | Constructed views and rendered analytical outputs. |

`DataContract(schema_id, version, role)` names an explicit semantic schema.
Equal roles or file extensions do not establish compatibility. Industry debt
and issuance streams use distinct schema identities. A CSV containing a retained
source-local extract has the `extracts` role; an archive of exact source files
retains the `originals` role. Control values such as source indexes, cleanup
plans and comparisons use `role=None`.

Schema versions, method versions, byte identities and destination revisions
have separate meanings. The schema describes the admitted value; the method
describes its production; byte and computation evidence identify actual inputs
and results. Metadata never changes an existing receipt or computation identity.

Roles impose no directory structure. A consumer may use `scrolls` and `flakes`,
technical directory names, an in-memory value or an external store. Merely
declaring `readable` or `integrated` does not provide a converter or integrator;
actual callable coverage is inspected separately.

## 2. Definitions, executable handlers and machine schemas

An owner keeps typed definitions in a lightweight `definitions.py` module and
imports those same objects into `operations.py` or `api.py`. Neutral original
operations use `original_definitions.py` and `version_definitions.py`.
The definition holds request/result classes, method identity, capability and
effect declarations, resource limits and optional `OperationSemantics`.

`OperationRef` separately identifies the definition and handler. For an admitted
read-only machine operation it also identifies a `ReadOnlyWireContract` and a
`ReadOnlyWireCodec`. The codec binds the immutable schema contract to the
invocation/projection functions. Schema getters return detached dictionaries;
editing a returned schema never changes the registered contract.

| Code | Catalog call | What it loads |
| --- | --- | --- |
| L01 | `list_refs()` | Registered references. |
| L02 | `get(id, version)` / `definitions` | Typed definitions. |
| L03 | `describe()` / `page(...)` | Definitions and explicitly registered machine schema contracts. |
| L04 | `wire_schemas(id, version, catalog=...)` | Definition and machine schema contract. |
| L05 | `resolve(id, version)` | Definition, executable handler and admitted codec. |

An unavailable handler therefore does not prevent inspection of an otherwise
loadable definition. Executable resolution still reports an explicit registry
error. Built-in description, paging, routing, coverage and schema inspection
work without loading registered handlers or optional dataframe, HTTP, Excel
and solver engines. Definitions supplied by an extension must preserve the
same import boundary.

## 3. Bounded discovery for application adapters

```python
from stratbox.domains.registry import operation_catalog

catalog = operation_catalog()
page = catalog.page(
    owner_id="cbr.service_network.bank_offices",
    stage="extract",
    role="extracts",
    offset=0,
    limit=20,
)
for item in page.entries:
    print(item["operation_id"], item["processing"])
```

`page()` returns `CatalogPage(entries, offset, total, next_offset)`. It accepts
an owner, processing stage, data role, case-insensitive ID/summary query and
`machine_only=True` filter. The default page contains at most 50 entries; the
maximum requested page size is 200. Ordering follows operation ID and contract
version. Offset pagination describes an immutable catalog instance; an adapter
should retain that instance while walking its pages.

Descriptions include ownership, Python types, semantic input/output ports,
schema editions, accepted outcomes, qualifications, coverage requirements,
selection parameters, capabilities, effects, limits and machine admission.
`describe()` remains the complete Python inspection view. Applications that
project descriptions into a model context should use `page()`.

`machine_read_only=True` identifies an expressly admitted codec. A Python
handler declaration alone grants no machine interface. Network, writes and
publication still require the host's actual provider and authorization boundary.
The core supplies no MCP server or application task manager.

## 4. Semantic connections retain their conditions

```python
links = catalog.compatible_next("cbr.offices.acquire", 2)
for link in links:
    print(link.output, link.consumer, link.input, link.state)
    print(link.missing_qualifications, link.missing_coverage)
    print(link.additional_inputs, link.parameters)
```

Each `InputPort` and `OutputPort` identifies a logical port, its schema and
an attribute path relative to the typed request or returned value. An empty
path denotes the whole object. Paths describe binding locations; the library
does not evaluate them or construct subsequent requests automatically.

Connections require an exact schema ID, edition and role match, or an explicitly
listed input alternative. Output and accepted-input outcome sets must overlap.
The result lists missing qualifications, required coverage, other required
inputs and declared parameters. Parameters include selection settings and
defaulted options; their Python request contracts establish which are required.

`compatible` means the declared port metadata matches without extra declared
conditions. `conditional` retains those conditions. Both require actual value,
source, evidence, Python binding and runtime admission before invocation.
Neither state proves byte integrity, freshness, applicability to a particular
question, complete coverage, destination access or successful execution.

Source acquisitions expose their source-specific material contract and a
generic payload projection. Their own parser can match the former; neutral
original storage can consume the latter. Unrelated publisher indexes and
source schemas never match merely because their values contain bytes.

`assess_input(port, contract, outcome=..., qualifications=..., coverage=...)`
checks supplied metadata without effects. It reports schema, outcome,
qualification and coverage mismatches independently. By default an input
accepts only `succeeded`; `partial` requires explicit admission. `failed`,
`cancelled` and `unknown` remain rejected. Supplied labels remain claims from
their owner; this check performs no content verification.

## 5. Domain coverage and bound delegation

```python
coverage = catalog.coverage("cbr.service_network.bank_offices")
for item in coverage:
    print(item.stage.value, item.state, item.operations, item.reason)
```

Coverage spans discovery, update inspection, acquisition, original preservation,
readable conversion, extraction, retained-extract reading, release comparison,
integration, ingestion, calculation, view construction, rendering, publication
and validation. The families describe responsibilities rather than a fixed
number of functions or a mandatory execution order.

| Code | State | Meaning |
| --- | --- | --- |
| C01 | `implemented` | A declared independent local operation covers the stage. |
| C02 | `delegated` | Explicit operation identities and a required domain binding identify a shared implementation. |
| C03 | `composite_only` | A convenience composition includes the stage; an independent operation remains absent. |
| C04 | `missing` | The owner explicitly records an applicable implementation gap. |
| C05 | `inapplicable` | The owner explicitly records a semantic reason for exclusion. |
| C06 | `unassessed` | Applicability or coverage has not been declared. |

`OperationRegistration.stages` holds explicit missing/inapplicable declarations
and delegated bindings. Local implementation coverage comes from the actual
operation definitions. Contradictory coverage, unavailable delegated contracts,
stage mismatches and delegation to a composite fail explicitly. Use the merged
`operation_catalog()` when an owner delegates to neutral core operations.

Selected statistical owners delegate original save/read calls to neutral source
operations. Their binding retains source-issue association and requires
source-specific readmission after reading. Complete domain snapshot constructors
advertise `render`; ingestion delegates to `dataset.write_snapshot`, whose
receiving adapter performs the actual persistent write. Snapshot reads and
domain restore operations provide the explicit continuation boundary.

Missing readable conversion, semantic integration or external publication stages
remain visible where the owner has no implementation. A shared ingestion adapter
does not imply a reviewed cross-source semantic database or remote publication.
Coverage entries never create callable tools or substitute empty success for
absent functionality.

Runtime availability is separate: an implemented acquisition can still require
an HTTP provider in a particular environment. Likewise, an unused stage does
not become inapplicable merely because one consumer omits it.

## 6. Execution evidence and independent local calls

A caller can preserve original bytes, read them later, invoke a parser with
supplied local material, compare compatible releases and render existing views.
Each call retains its established `OperationResult` and `ExecutionContext`
semantics. Acquisition, readable conversion and intermediate saving are selected
according to the actual input contract.

Processing metadata does not replace the execution finalizer. Cancellation,
resource accounting, input lineage, `partial` values, uncertain effects and
reconciliation remain governed by the runner and provider contracts. An output
port advertises only its declared outcomes; source-specific qualification fields
inside the value remain material even when the invocation itself succeeded.

Read-only wire schemas preserve the same outcome vocabulary and nullable
diagnostic stage/component fields. The schema contract and codec must agree,
and a read-only admission cannot advertise an operation with declared effects.
Notifications remain a separate optional consumer of qualified facts.

## 7. Extend an operation owner

Keep the definition, semantics and lightweight request/result types with their
actual owner. Add meaningful schema identities, logical ports, selection
parameters and an accurate summary to its `OperationSemantics`. Mark a
convenience composition explicitly; advertise a partial output only when the
operation definition admits partial results.

Register the definition separately from the handler. If machine calls are
supported, register the immutable machine contract separately from the codec.
Reuse those admitted definitions for application discovery rather than
maintaining an independent application-only catalog. Declare genuinely missing
or inapplicable stages and exact shared bindings where they are known.

The same approach applies to future publishers and deeply nested owners.
Automatic domain discovery and packaging validation impose no fixed owner or
operation count.
