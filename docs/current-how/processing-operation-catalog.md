# Processing contracts and independent operation discovery

Stratbox exposes processing semantics through the same `OperationDefinition`
objects used by Python execution. Canonical `OPERATION_*.yaml` records supply
these objects through `core.registry`; source and route declarations have
separate canonical resources. The catalog describes source acquisition,
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
7. Extending an owner — publish canonical metadata and its implementation references.

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

An operation resource holds method identity, request/result type references,
capabilities, effects, resource limits, runtime dependencies and optional
`OperationSemantics`. Lightweight Python metadata modules expose projections of
that same resource for direct handlers and public APIs. They retain the typed
request/result classes needed by the implementation; they do not maintain a
second contract description.

`shared.data.operations` owns stage and port invariants. `core.registry` owns
loading, catalog assembly and discovery projections. `core.execution` consumes
those definitions for binding, runtime admission and outcomes.

`OperationRef` projects the declaration's definition and handler references. For an admitted
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
    owner_id="cbr",
    query="cbr.offices.",
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

### CBR source and family descriptions

CBR has one registered operation owner, `cbr`. Functional segments under
`stratbox.domains.cbr.operations` contribute references to that root. Source
identifiers such as `cbr.reporting_forms.f802` and
`cbr.service_network.bank_offices` are publication identities, so they are not
valid substitutes for `owner_id="cbr"` in generic owner coverage.

The domain supplies a more specific read-only interface:

```python
from stratbox.domains.cbr.operations.catalog import (
    DescribeSourceRequest, DescribeFamilyRequest,
    describe_source, describe_family,
)

source_result = describe_source(DescribeSourceRequest(
    "cbr.reporting_forms.f802", format="rar",
))
assert source_result.outcome == "succeeded", source_result.diagnostics
source = source_result.value
for operation in source.operations:
    print(operation.key, operation.method_version, operation.parameters)
for stage in source.stages:
    print(stage.stage.value, stage.state, stage.qualifications)

family_result = describe_family(DescribeFamilyRequest("cbr.reporting_forms"))
assert family_result.outcome == "succeeded", family_result.diagnostics
for stage in family_result.value.stages:
    print(stage.stage.value, stage.conditional_sources, stage.missing_sources)
```

The registered operation IDs are `cbr.describe_source@1` and
`cbr.describe_family@1`. `DescribeSourceRequest` accepts `series_id` and optional
`format`, `table_id` and `edition` selectors. Unknown sources, formats, tables
and editions fail admission instead of inheriting another source's capabilities.

| Source-card field | Meaning |
| --- | --- |
| `source`, `table_profile`, `tables` | Logical publication, reviewed table variants, physical patterns, schemas, dimensions, period basis and unit policy |
| `profiles` | Extraction, source projection, financial model, integration and product profiles with editions and applicable operation keys |
| `operations` | Exact registered versions, method versions, ports, parameters, composition flags and source-specific qualifications |
| `stages` | Applicability for this source and selection, including conditional interpretation and missing work |
| `handoffs` | Compatible direct ports, explicit collection assembly and crossings to delegated neutral operations |
| `delegated_operations` | Actual neutral storage/archive contracts requiring caller-selected infrastructure |
| `supported_formats`, `original_only_formats` | Formats with a reviewed source extractor versus formats admitted only for original preservation |

These cards resolve operation metadata from the executable registry. They are
bindings to existing definitions rather than a second executable catalog.
`describe_family` preserves each source's description and separately lists
supported, conditional, missing and delegated sources for every stage. It also
exposes multi-source method dependency contracts where the family declares them.

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
path denotes the whole object. Metadata inspection never invokes handlers.
The explicit `project_output` and `bind_request` helpers in
`stratbox.core.execution.handoff` apply declared paths to checked outputs and
caller-supplied parameters. They do not select a business route on the caller's
behalf.

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
coverage = catalog.coverage("cbr")
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
source-specific readmission after reading. Snapshot constructors produce
portable logical values; their declared stages reflect the encoded boundary
or a representation-rendering step. Encoding itself performs no persistence.
Ingestion delegates to `dataset.write_snapshot`, whose receiving adapter
performs the actual write. Snapshot reads and domain restore operations provide
the explicit continuation boundary.

Missing readable conversion, semantic integration or external publication stages
remain visible where the owner has no implementation. A shared ingestion adapter
does not imply a reviewed cross-source semantic database or remote publication.
Coverage entries never create callable tools or substitute empty success for
absent functionality.

Runtime availability is separate: an implemented acquisition can still require
an HTTP provider in a particular environment. Likewise, an unused stage does
not become inapplicable merely because one consumer omits it.

### CBR source coverage remains narrower than aggregate domain coverage

The root CBR registration aggregates publication lifecycle, source extraction,
statistical integration, financial models, office counts, escrow and corporate
lending methods. `coverage("cbr")` therefore describes the union of declared
implementations. A consumer planning work for one source uses its source card
and input qualifications as well.

CBR source-stage states are `supported`, `conditional`, `missing` and `delegated`.
They qualify business scope rather than replace the generic owner-level states
above. In particular, semantic integration, calculation and view construction
are conditional on admitted source/table editions and explicit interpretation.
A `supported` renderer can still be a source-flake exporter rather than a
financial-workbook renderer.

| CBR scope | Actual independent coverage | Scope that remains qualified |
| --- | --- | --- |
| The 44 registered workbook-flake series | `cbr.tables.extract`, `validate`, `compare`, `readable`, `flake_snapshot`, `read_flake_snapshot`; `cbr.statistics.align`, `calculate_change`, `calculate_share`, `build_view`, `render_view` and dataset/view replay operations | Complete source-cell extraction precedes economic interpretation. Source variants, units, periods, mappings and formula caches determine admitted analytical coverage. |
| Six modeled reporting forms | Source projection; semantic alignment; `prepare_model_inputs`; `calculate`; prepared views; result and observation replay; workbook rendering | One reviewed form per model input, complete source channels, exact metric/unit/scale, subject and period bindings, formula axes and explicit subject selection |
| Forms `134` and `803` | All-member DBF extraction, readable source records, source comparison, typed flake replay and CSV collections | Reviewed projection, semantic alignment, financial calculation and financial views are missing; source export rendering remains available |
| Office-network publications | Qualified source release/history, explicit identity alignment, count changes, prepared views and CSV/XLSX rendering | Known official state date is separate from capture date; unresolved geography, selected fragments and formula-cache exclusions remain explicit |
| Escrow/project-finance publication | Reviewed regional workbook source, integrated data, prepared views, separate rendering and replay | Historical HTML has an original-preservation scope; metric definitions and source periods must remain qualified |
| Corporate industry/SORS routes | Independent debt/issuance source flakes, integration, APK, views and rendering; SORS prepared bundles, restoration and retained products | Stock/flow meanings differ; SORS declares complete required inputs and an optional validation history independently of the displayed subset |

The workbook series have callable processing routes beyond original acquisition.
Their full physical cell coverage is a different claim from complete semantic
interpretation. A shared `ObservationBatch` or dataset codec also establishes
portable structure, not automatic cross-source metric or geography equivalence.

### A retained reporting-form batch can enter the financial model independently

For the six reviewed forms, the source card exposes these exact contracts:

| Producer output | Consumer input | Meaning |
| --- | --- | --- |
| `cbr.forms.align@1` → `batch` | `cbr.forms.observations_snapshot@1` → `batch` | Encode aligned data before the neutral dataset write/read boundary |
| `cbr.forms.restore_observations@1` → `batch` | `cbr.forms.prepare_model_inputs@1` → `batch` | Resume from retained semantic observations |
| `cbr.forms.prepare_model_inputs@1` → `inputs` | `cbr.forms.calculate@1` → `inputs` | Admit reviewed model variables before evaluating the selected model |
| `cbr.forms.calculate@1` → `data` | `cbr.forms.build_views@2` → `data` | Prepare presentation tables from calculated data |
| `cbr.forms.build_views@2` → `views` | `cbr.forms.render_workbook@2` → `views` | Render independently of source reading or calculation |

`cbr.forms.build_data@2` is an explicitly declared composition of
source-projection alignment, model-input preparation and the same calculator.
It does not provide the sole entry into calculation. Form `102` requires an
explicit interval in either route, and bank and banking-group namespaces remain
distinct.

A source-card handoff with `assembly="direct"` means the output and input port
shapes match. Its consumer's parameters and semantic conditions still apply;
the generic catalog can therefore classify the same connection as
`conditional`. `assembly="explicit_collection"` additionally requires the
caller to assemble selected outputs into a tuple, resolve competing revisions
and preserve coverage. Source-local projections cannot silently become an
integrated collection merely by sharing the same file extension.

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

Keep lightweight request/result classes and handlers with their actual domain
or neutral-core owner. Publish the full contract and implementation references
in an atomic operation resource. Add meaningful schema identities, named ports,
selection parameters and an accurate summary. Mark convenience compositions
explicitly; advertise a partial output only when the definition admits it.

Bind applicable source routes through profile resources and preserve their
formats, fixed parameters and stage transitions. Reuse the assembled catalog
for application discovery. An optional wire contract remains separate from its
codec. Declare genuine coverage gaps and exact neutral-operation delegations
in owner metadata.

The same approach applies to future publisher domains and their functional
segments. Choose the registration boundary deliberately: a nested implementation
package does not require its own registered owner. Automatic discovery and
packaging validation impose no fixed owner or operation count.

See [functional domain boundaries](../architecture/domain-functional-semantics.md)
and the maintained [CBR processing route](cbr-data-pipeline.md) for source-specific
ownership and the independent continuation contracts.
