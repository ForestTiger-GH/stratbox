# Canonical source and operation registry

Stratbox stores source identities, operations, profiles, routes and meaningful
publication families in `stratbox.registry`. `core.registry` validates those
records and builds immutable catalogs. `core.execution` binds actual values and
executes one selected operation. Publisher recognition and economic algorithms
remain with their domain implementations.

Operation and registry record identities are unversioned. A logical ID resolves
to one current declaration. Payload schemas, publication revisions, dataset
versions and reference editions describe data and retain their separate roles.

Contents:

1. Declaration ownership — organize records by responsibility.
2. Catalog discovery — compile definitions and resolve handlers lazily.
3. Named calls — bind exact typed inputs and semantic parameters.
4. Source binding — retain source context through processing and replay.
5. Requirements and readiness — explain the inputs a call needs.
6. Extension and delivery — preserve one discovery rule across distributions.

## 1. Declaration ownership follows explicit owners

| Code | Location within an owner | Responsibility |
| --- | --- | --- |
| G01 | `sources/**/SOURCE_*.yaml` | One logical series, publication attributes and profile references. |
| G02 | `operations/**/OPERATION_*.yaml` | One operation, its method, request/result types, ports, parameters and runtime policy. |
| G03 | `profiles/**/PROFILE_*.yaml` | Canonical processing properties and qualified source-specific applications. |
| G04 | `routes/**/ROUTE_*.yaml` | Source applicability, fixed parameters, formats and processing coverage. |
| G05 | `families/**/FAMILY_*.yaml` | Shared publication facts with independent substantive meaning. |
| G06 | `groups/**/GROUP_*.yaml` | Explicit shared transformations, stages and topology referenced by source routes. |
| G07 | `OWNER.yaml` | Owner identity, coverage exceptions and explicit value-context adapters. |

Core owners live under `registry/core/`; publisher owners live under
`registry/domains/`. Deeper directories group substantive areas such as
corporate lending, publication acquisition or extraction. `OWNER.yaml` establishes
ownership. Grouping folders and declaration filenames carry no additional
identity. Moving a record within the admitted owner structure preserves its ID.

Files use the JSON subset of YAML. The declaration format has explicit required
and optional fields with defaults, independent of Python dataclass field lists.
Unknown fields, duplicate identities and unresolved references fail validation.
Profile cards derive from canonical properties; an application to a particular
source retains its additional scope and format qualifications. CBR family IDs
are derived from canonical sources directly.

Routes may include shared transformation groups from their own owner. Group
contents are additive and explicit: nested includes, overrides and conflicting
operation bindings are rejected. Source-specific profiles, applicability and
qualifications stay on the source route. Shared groups have unversioned IDs.

## 2. Definitions compile directly from declarations

```python
from stratbox.core.registry import operation_catalog

catalog = operation_catalog()
references = catalog.list_refs()
definition = catalog.get("frg.plan_cleanup")
descriptions = catalog.page(owner_id="cbr", limit=20)
```

`catalog.get()` compiles the canonical declaration into `OperationDefinition`.
Python definition constants are convenient projections of the same record.
`catalog.resolve()` additionally loads the handler and an expressly admitted
machine codec. No `definition_ref` or round trip through a Python constant is
required. Each operation has an unversioned `method_id` identifying its method.

Metadata discovery leaves handlers and optional data engines unloaded. Catalog
creation performs no acquisition, capture or storage. A typed extension can
supply an explicit definition with its handler reference through `OperationRef`.
The catalog checks that the definition and operation identity agree.

## 3. Named calls retain exact inputs and parameters

```python
from stratbox.core.execution.handoff import prepare_input

# payload is an admitted SourcePayload.
call = catalog.bind(
    "workbook.extract",
    inputs={"source": prepare_input(payload)},
    parameters={"series_id": "example.series", "issue_id": "2026-08"},
)
result = call.invoke()
```

Binding validates named ports, accepted schemas, outcomes, qualifications and
coverage, then creates the typed request. `call.invoke(context=..., **options)`
uses the same runner as the direct Python API. Binding alone has no effects.
`project_output(result, name)` transfers an in-memory output;
`resolve_output(reference, resolver)` restores an explicitly retained output.

The runner records exact consumed named arguments and applied semantic parameter
values, including defaults. Collection order and multiplicity remain part of
this signature. Source lineage and independent semantic dependencies remain
separate evidence. Equal values supplied directly or restored from a snapshot
have equal semantic signatures; invocation history and storage placement add no
artificial differences. Different values sharing the same original retain
different computation identities.

## 4. Source-bound calls preserve explicit value context

```python
source = catalog.bind_source("rosstat.short_term_indicators", format="xlsx")
call = source.bind(
    "rosstat.tables.extract_workbook",
    inputs={"payload": prepare_input(payload)},
    parameters={"issue_id": "2026-08", "asset_id": "main"},
)
```

Source binding applies fixed parameters and the explicitly declared identity
parameter. Value-context adapters declare how source, group, issue and edition
are represented by a typed value or saved metadata. Inputs and returned values
are checked against the source binding. Auxiliary source roles require their own
explicit allowance.

Source-scoped retained inputs require a verifiable source context in their
snapshot metadata or artifact descriptor. Unqualified snapshots use the generic
catalog directly; a dataset name or transport label supplies no source claim.
Selected snapshot components retain the metadata needed for source binding.
Auxiliary sources are admitted per named input role, while the actual output
preserves the bound primary source alongside any declared supporting sources.

Exact port compatibility governs a producer-to-consumer handoff. Economic
stages classify operations and describe coverage; their coarse route graph
cannot reject an otherwise compatible typed handoff. Independently supplied
values and restored values undergo the same input checks. The optional
`from_stage` qualifies an explicit stage selection. Selecting a source format
still limits operations to their reviewed format scope.

## 5. Requirements explain readiness

`catalog.source_catalog().describe(series_id, operations=catalog)` exposes
qualified source coverage, profiles and bound operations. Operation requirements
identify named roles, allowed sources, groups, cardinality, compatible schemas
and source compatibility conditions. Readiness explains missing or incompatible
roles and permits inspection before execution. SORS publishes its mandatory
source roles and optional history through this common representation; scientific
validation remains with SORS.

```python
requirements = catalog.requirements("cbr.sors.prepare_inputs")
readiness = catalog.readiness("cbr.sors.prepare_inputs", available={})
assert readiness.required_count == 10
assert readiness.state == "blocked"
```

Readiness and route inspection create no schedules, durable tasks or provider
authority. Applications continue to own orchestration and storage decisions.

## 6. Discovery and delivery share one inventory

Owners and all record kinds are discovered recursively by the same resource
traversal. Runtime discovery, static validation, wheel and sdist inspection use
that inventory. Unowned declarations and unexpected record locations are errors.
`domain_registration_inventory()` exposes owner/operation pairs.

New owners publish their implementation types and canonical declarations under
the appropriate architectural root. Machine admission requires an explicit wire
contract and codec; a Python operation alone grants no network, write or
publication authority. See [processing discovery](processing-operation-catalog.md),
[value handoff](universal-data-flow.md) and
[independent publisher routes](independent-domain-data-routes.md).
