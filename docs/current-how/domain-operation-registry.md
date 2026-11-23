# Canonical source and operation registry

Stratbox keeps source identities, operation contracts and processing-profile
bindings in `stratbox.registry`. `core.registry` loads and validates those
records; `core.execution` binds actual values and invokes the registered handler.
Publisher-specific recognition, reviewed layouts and algorithms remain Python
implementations in `stratbox.domains`.

Catalog inspection describes available contracts and their conditions. Execution
still requires admitted inputs, selected providers, resource budgets and any
applicable effect authorization.

Contents:

1. Registry responsibilities — separate sources, routes and callable contracts.
2. Catalog discovery — inspect identities and schemas while handlers stay lazy.
3. Named calls — bind supplied values and execute one operation.
4. Source binding — apply source formats, route stages and fixed parameters.
5. Extending an owner — publish declarations and retain domain implementation ownership.
6. Machine access — preserve explicit protocol admission and host authority.

## 1. Sources, routes and operations have separate contracts

| Code | Declaration or owner | Responsibility |
| --- | --- | --- |
| G01 | `registry/<owner>/sources/SOURCE_*.yaml` | One logical publication series, its formats, publication attributes and profile references. |
| G02 | `registry/<owner>/operations/OPERATION_*.yaml` | One versioned operation: request/result types, method, named ports, stages, parameters, capabilities, effects, limits, runtime dependencies and implementation references. |
| G03 | `registry/<owner>/profiles/PROFILE_*.yaml` | Shared publication metadata and source-route bindings, including applicable operations, profile editions and allowed stage transitions. |
| G04 | `registry/<owner>/OWNER.yaml` | Operation ownership and explicit missing, inapplicable or delegated stage declarations. |
| G05 | `core.registry` | Resource loading, schema and ownership validation, immutable catalog assembly and discovery projections. |
| G06 | `core.execution` | Source binding, actual input/output adaptation, lineage propagation, runtime admission and invocation outcomes. |
| G07 | `shared.data.operations` | Storage-independent processing stages, named port contracts, schema compatibility and coverage identities. |
| G08 | `domains.<publisher>` | Typed source profiles, validators, publication recognition and economic algorithms. |

The resource files use the JSON subset of YAML, so discovery requires no YAML
engine. Source records contain no handler selection logic. Route bindings name
existing logical operation contracts; each operation independently defines its
request and result. Technical encoding, replay and maintenance remain distinct
from economic processing stages.

Routes reference separate profile metadata records. Identical metadata has one
record; source-specific scope or format qualifications have distinct resource
identities while retaining the logical profile ID and method edition.

Python definition symbols are projections of canonical operation metadata.
Their lightweight request/result classes remain in their owning implementation
packages. Changing a handler path therefore does not change the logical
operation identity; changing a public schema or method requires its own version.

## 2. Discover and resolve catalogs

```python
from stratbox.core.registry import domain_catalog, operation_catalog

business = domain_catalog()
catalog = operation_catalog()
references = catalog.list_refs()
descriptions = catalog.describe()
definition = catalog.get("frg.plan_cleanup", 1)
```

Discovery finds resource owners deterministically and has no fixed publisher or
operation count. Each logical operation ID has one owner across its contract
versions. Duplicate contracts, invalid resource schemas, inconsistent identities
and references outside the admitted owner fail explicitly. Domain reference
validation uses the nearest declared owner, with Python package segment boundaries.

`catalog.get()` resolves a typed definition; `catalog.resolve()` additionally
loads its executable handler and any explicitly registered machine codec.
Metadata listing leaves handlers and optional spreadsheet, document or solver
engines unloaded. Creating a catalog performs no acquisition, capture or storage.

`domain_registration_inventory()` in `stratbox.domains.registry` exposes the
same validated domain snapshot as owner/operation/version rows. Distribution
checks compare canonical resources and registered contracts across source,
wheel and sdist. Resource metadata and executable implementation have one
validation route.

## 3. Bind named inputs and invoke an independent call

```python
from stratbox.core.registry import operation_catalog
from stratbox.core.execution.handoff import prepare_input

catalog = operation_catalog()
# payload is an admitted SourcePayload; its exact input receipt is retained.
call = catalog.bind(
    "workbook.extract", 1,
    inputs={"source": prepare_input(payload)},
    parameters={"series_id": "example.series", "issue_id": "2026-08"},
)
result = call.invoke()
```

`catalog.bind()` checks the actual definition, named inputs and declared
parameters before constructing the typed request. It returns an `OperationCall`;
`call.invoke(context=..., **options)` resolves the catalog handler and uses the
same operation runner as the direct Python API. Binding alone has no effects.

An in-memory result uses `project_output(result, name)` before binding. A retained
result uses `resolve_output(reference, resolver)` with the consumer's explicit
resolver. Supplied typed values use `prepare_input()` with an explicit
`DataContract`, except for the narrow built-in payload/artifact defaults. See
[material flow and value adapters](universal-data-flow.md#3-binding-operation-results).

## 4. Bind a logical source and its processing route

```python
source = catalog.bind_source("rosstat.short_term_indicators", format="xlsx")
card = source.source
route = source.route
call = source.bind(
    "rosstat.tables.extract_workbook",
    inputs={"payload": prepare_input(payload)},
    parameters={"issue_id": "2026-08", "asset_id": "main"},
)
# The source binding supplies and pins series_id.
```

Use a series ID returned by `catalog.source_catalog().sources` for the desired
publication. `SourceBinding.bind()` selects one of that source's exact operation
contracts and returns an independently invocable call. It applies fixed source
parameters, validates caller selections and checks route stages and supplied
producer transitions. The optional `from_stage` makes an independent predecessor
selection explicit. A source format that admits only original preservation does
not gain a reviewed parser merely because another format has one.

A source route describes admissible processing boundaries. It does not schedule
all boundaries or require acquisition before an independently supplied extract.
Named roles still require exact schemas, accepted outcomes, qualifications and
coverage. Route metadata cannot prove that source bytes or an economic mapping
are valid; the operation's input validator retains that responsibility.

`catalog.source_catalog().describe(series_id, operations=catalog)` gives the
shared source/profile/operation view. CBR's `describe_source` and
`describe_family` additionally expose reviewed tables, original-only formats,
source-specific handoffs and multi-source method requirements. See the
[CBR route](cbr-data-pipeline.md) and [independent publisher routes](independent-domain-data-routes.md).

## 5. Extend a publisher or operation owner

Add the publisher's normal Python implementation packages and its canonical
registry owner resources. Define request/result classes and a handler in the
appropriate functional package. Publish its full operation declaration and
reference it from applicable route profiles. Add source records for logical
series and qualify their formats, profile editions and coverage.

Keep physical recognition and economic rules in typed domain profiles. New
sources share neutral operations only through an explicit binding. Source
families, callable namespaces and implementation subpackages do not create new
operation owners by themselves. Owner discovery and inventory validation need
no manually maintained central list.

For optional machine access, declare the immutable protocol contract separately
from its codec. A typed Python operation is not automatically admitted to a
wire protocol. Preserve lazy imports and verify the packaged resources together
with relevant source, semantic and replay behavior.

## 6. Machine dispatch preserves host authority

```python
from stratbox.core.execution.machine import wire_schemas

schema, response_schema = wire_schemas("cbr.offices.parse", 1, catalog=catalog)
```

Restricted read-only wire admission covers `cbr.offices.parse` v1,
`cbr.offices.compare` v2 and `frg.plan_cleanup` v1. Their codecs live with their
owners. This admission grants no network, storage, deletion or publication
authority.

Hosts holding validated typed requests can use `invoke_reference` with a
host-owned `TypedValueResolver`, explicit effect grants and reserved result
capacity. The response contains typed handles and a bounded preview. Durable
results, authorization and admitted codecs remain consumer responsibilities.
See [machine access](independent-domain-data-routes.md#7-machine-access).

[Processing roles, bounded discovery and qualified connections](processing-operation-catalog.md)
