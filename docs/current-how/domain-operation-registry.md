# Canonical processing contracts and registry admission

Stratbox declares operation contracts in `stratbox.operations` and source
identities, content groups, profiles and template bindings in
`stratbox.domains.registry`. Their catalogs admit declarations and derive exact
connections. `core.execution` runs operations and compiled graphs, preserving
each operation's qualified outcome and effects. Domain packages retain
publisher layouts, economic interpretation and scientific admission.

Logical operation and registry IDs are unversioned. Content-addressed method
fingerprints identify computational meaning and its executable dependencies.
Publication revisions, data schemas and reference editions describe the actual
materials consumed by that method.

Contents:

1. Canonical facts — identify each declaration and its substantive owner.
2. Catalog admission — separate metadata, typed links and executable delivery.
3. Computation signatures — classify every request coordinate and method.
4. Source coordinates — preserve source, group, issue and material relationships.
5. Source-bound finalization — enforce output obligations inside the runner.
6. Requirements and readiness — connect named roles to actual typed inputs.
7. Exact routes and planning — explain possibilities without performing effects.
8. Domain responsibilities — retain publisher-specific admission.
9. Delivery and extension — verify the same implementation and declarations.

## 1. Canonical facts have one owner

| Code | Record or contract | Responsibility |
| --- | --- | --- |
| G01 | `SOURCE` | Logical series, publication facts and content groups. |
| G02 | Nested `SourceGroup` | Addressable dataset, contracts, grain, profiles, format and period model within one source. |
| G03 | `PROFILE` | Applicability and references to actual domain interpretation/admission rules. |
| G04 | `OPERATION` | Ports, exhaustive request roles, method dependencies, effects and runtime policy. |
| G05 | Source route binding | Template selection and source-specific qualifications, embedded in the source record. |
| G06 | `GROUP` | Additive reuse of an identical set of transformations. |
| G07 | `OWNER` | Owner identity, coverage declarations and exact value-context adapters. |
| G08 | `SourceInstance` | A particular issue/material selection, supplied during a call. |
| G09 | `SourceUse` | Qualified relationship between a consumed value and its source coordinates. |

Operation declarations live under `operations/specifications`; sources and
profiles live under `domains/registry`. `OWNER.yaml` establishes operation
ownership. Source records reference reusable route templates and keep their
specific overrides. Moving a declaration within its admitted owner preserves
its logical identity. Both catalogs use the same neutral resource inventory
mechanism used by delivery checks.

A source's `family_id` is taxonomy, its content `group_id` addresses data, and a
processing `GROUP` shares transformations. A publisher table code is retained as
`source_table_code`; it does not automatically create another logical source or
dataset. Full physical layouts and economic rules remain with their domain
implementations. Profile declarations reference that owner rather than copying
all its coordinates into YAML.

## 2. Catalog admission has explicit proof levels

```python
from stratbox.operations import operation_catalog

catalog = operation_catalog()
page = catalog.page(owner_id="cbr", limit=20)
metadata = catalog.metadata("cbr.sors.prepare_inputs")
report = catalog.admit(level="metadata")
```

| Code | Level | What is checked |
| --- | --- | --- |
| A01 | `metadata` | Declaration shapes, ownership, source/group/profile/route links, role requirements and duplicate identities. |
| A02 | `typed` | Python types, exhaustive request fields, port paths, collection/default facts, profile/context adapters, parameter types and method dependencies. |
| A03 | `executable` | Typed admission plus handler and admitted codec signatures. Work is not invoked. |
| A04 | Distribution inspection | Actual implementation bytes, registry resources, reference assets and archive identity. |
| A05 | Semantic fixtures | Scientific behavior on reviewed domain values; reported separately from catalog admission. |

Metadata pages, source descriptions, requirement discovery and route planning
avoid importing handlers and optional scientific engines. `get(id)` performs
selected typed admission. `resolve(id)` additionally resolves the handler.
`metadata(id)` returns the computational declarations without loading request
classes; the inert type placeholders serve inspection only.

Admission reports distinguish exact source-resource identity, normalized
semantic registry identity and installed implementation/distribution identity.
A successful metadata report does not claim that scientific fixtures ran.
Validated immutable catalogs cache their admission gate; explicit refresh is
available for a deliberately changed development tree.

## 3. Computational signatures classify every request coordinate

| Code | Request role | Computational identity |
| --- | --- | --- |
| F01 | `input` | Exact consumed content, contract, context, order and multiplicity. |
| F02 | `parameter` | Actual semantic options, including applied defaults. |
| F03 | `method` | Method/profile choices that change interpretation. |
| F04 | `dependency` | Used semantic dependencies and their identities. |
| F05 | `effect` | Destination and effect controls belong to effect qualification. |
| F06 | `runtime` | Provider/runtime objects remain outside the mathematical signature. |
| F07 | `observability` | Correlation and telemetry controls remain outside it. |

Canonical typed admission requires every initializable request coordinate to be
classified. Mixed configurations split nested semantic and technical fields.
The same projection applies to named inputs and handler-supplied parameters, so
an effect destination cannot re-enter the mathematical key through a root port.

`MethodDescriptor` combines the computational contract, reachable substantive
executable symbols and explicitly declared resource bytes. Normalized source
AST removes comments, documentation and unrelated functions. A formula/helper
or admitted profile-resource change changes the fingerprint. Package release
numbers and editorial changes do not stand in for method identity.

The runner records the method fingerprint with the exact argument signature.
Producer history remains provenance. An independently supplied reference only
becomes a computational dependency when actually consumed through `use` or
`depend`. Typed immutable identities can be reused within their admitted
lifetime; mutable frames are rehashed. Scientific scalar distinctions, decimal
literals, indices, dtypes, missing values and collection multiplicity remain
significant.

`core.execution.reuse.assess_reuse()` additionally requires a qualified outcome,
matching computation, actual readable material and admission by the receiving
owner. A stored hash or locator alone never establishes eligibility.
Partial results are eligible only through a declared partial-result output port
whose actual material and required qualifications pass the same receiving checks.

## 4. Source coordinates preserve relationships

`SourceCoordinate` associates source, family, content group, issue, asset,
material identity and layout/profile editions. `SourceUse` adds its input role,
qualification and evidence reference. `ValueContext.uses` is authoritative;
source/issue set projections are conveniences for browsing.

Context adapters declare exact typed paths and metadata table contracts,
including schema edition and role. Unknown fields, schema links or incompatible
editions are rejected at the applicable admission level. A transport label or
filename is not promoted into a logical publisher identity.

`prepare_input(value, contract, source_context=...)` can retain an explicitly
qualified context supplied by the consuming owner. Positive claims already
present in the value must agree. Snapshot and replay preserve the same linked
coordinates. Supporting sources retain their named roles.

## 5. Source-bound expectations participate in finalization

```python
source = catalog.bind_source(
    "cbr.corporate_lending.debt_0105a",
    format="xlsx",
    group_id="regional_debt",
)
```

Source selection and descriptions use the same applicability assessment for
format, group, profile and edition. Identity selectors are declared, including
scalar and collection selectors; they are not guessed from parameter names.

| Code | Output policy | Obligation |
| --- | --- | --- |
| O01 | `primary_source_required` | Retain the bound primary source. |
| O02 | `source_collection` | Retain the declared source collection and supporting roles. |
| O03 | `source_optional` | Absence is permitted; positive claims are checked. |
| O04 | `source_inapplicable` | Technical/control output has no publisher-source obligation. |

A trusted `ResultAdmission` policy is attached before execution. The runner
checks the candidate before its terminal result/event. Rejection returns a
normal qualified `OperationResult`. Confirmed effects remain visible; an
unresolved effect retains `unknown` and reconciliation information.
Output policies apply to the actual outcome admitted by each port: a partial
candidate is checked through its partial-result ports rather than a success-only
projection that does not exist. `source_context_path` explicitly selects the
enclosing typed carrier when a projected dataframe relies on its source context.

Where a commit has a prepared candidate, `Invocation.admit_prepared()` checks it
before the external write. Dataset publication uses this boundary. A final
postcondition remains necessary when an effect can only be qualified afterward.
Effectful execution also performs signature/resource preflight before work.
These checks preserve the existing runner and do not promise rollback of an
already confirmed external action.

## 6. Requirements connect named roles to actual values

```python
requirements = catalog.requirements("cbr.sors.prepare_inputs")
readiness = catalog.readiness("cbr.sors.prepare_inputs", available={})
assert readiness.required_count == 10
assert readiness.state == "blocked"
```

Requirements resolve source IDs and optional content groups to real contracts,
profiles, grain and declared compatibility conditions. Metadata claims cannot
manufacture group membership from a consumer's requested role. Before binding,
actual typed coordinates and consumed identities are checked.

An operation's `source_assembly` maps requirement roles to one typed input
object. `catalog.bind(..., inputs=role_values, source_resolver=...,
domain_admitter=...)` uses that bridge when supplied by the operation. Metadata
instances require actual resolution; an identity without a value cannot form a
request. Direct prepared ports remain independently callable.

SORS's ten mandatory publications and optional history map to its existing
source-input bundle. Requested output territory does not reduce the required
constraint scope. Its scientific completeness and uncertainty rules remain
with SORS.

Readiness exposes declaration/applicability, supplied instances, structure,
actual material, economic admission, runtime and effect authorization
separately. Caller claims can satisfy metadata requirements while remaining
conditional. Actual bytes are hashed; consumed typed identity is separate from
provenance of original materials. Domain interpretation and receiving runtime
checks remain independent. Availability assessment grants no new authority.

## 7. Exact connections and bounded plans explain remaining work

```python
page = catalog.connections(
    source_id="cbr.corporate_lending.corp_debt_a",
    producer="cbr.publications.select",
    consumer="cbr.publications.acquire",
    limit=20,
)
explanation = catalog.explain_route(
    "cbr.publications.acquire",
    source_id="cbr.corporate_lending.corp_debt_a",
    max_nodes=1000,
)
```

Connections identify exact producer/output and consumer/input contracts.
Edition mismatch, qualifications, coverage, additional inputs, required
parameters and collection assembly/cardinality have separate reasons. Direct,
collection, conversion, projection, replay, effect and composite links retain
their different meanings. Page size and planning depth/node count are bounded.

Stages classify operations. Their transition overview is derived from actual
port connections; routes no longer store an independently maintained stage-edge
truth. Actual handoff uses projected producer/port evidence and `bind_request`.
The binding API has no ambiguous `from_stage` admission parameter.

Plans describe AND dependencies and unresolved conditions. They do not run
handlers, read providers, establish material availability or grant effects.
An unreachable or truncated search explains missing inputs or its budget.
Applications continue to own scheduling and durable execution plans.

## 8. Publisher semantics retain their domain owners

CBR preserves stock/flow, entity/group and partial-coverage distinctions. Its
reporting-form and office observations retain actual source coordinates. FNS
families own typed operation adapters; a central series/action dispatcher is
unnecessary. Rosstat KEP2 preserves period and selection evidence. Minfin keeps
fiscal basis distinct from shared technical routes. Frank RG's physical
extraction remains separate from conditional economic interpretation requiring
an admitted byte-bound profile.

`core.execution.values` supplies common descriptors, signature, snapshot and
resource bookkeeping. A domain wrapper retains scientific admission and its
own interpretation. Unknown formats and layouts acquire no economic support
merely because a generic reader exists.

`scripts/profile_computation_signatures.py` measures immutable-cache and mutable
frame behavior; `scripts/profile_processing_values.py` measures actual snapshot
codecs and source-context extraction on synthetic technical fixtures. One local
Python 3.12 run with allocation tracing produced these resource observations:

| Code | Fixture | Streaming signature peak | Snapshot encoding peak |
| --- | --- | --- | --- |
| P01 | CBR workbook, 100,000 physical cells | 0.095 MB | 111.42 MB |
| P02 | Rosstat flake, 10,000 source values | 0.088 MB | 18.52 MB |
| P03 | SORS bundle, 20 grids and 180,021 rows | 0.188 MB | 52.14 MB |

These are measured temporary allocations for those fixtures, rather than a
universal memory bound or proof of publisher-layout coverage. Snapshot encoding
still materializes its durable table components. Budget checks and cancellation
checkpoints remain necessary at the consuming boundary; streamed signatures do
not make the surrounding domain algorithm allocation-free.

## 9. Delivery and extension use the same admitted corpus

Wheel/sdist inspection compares every Python/type-marker file, canonical
record and reference asset with the source inventory, and reports an archive
identity. ZIP imports reuse an immutable root instead of rescanning resources.

A new owner declares its sources, meaningful groups, real profile links and
exhaustive operations, then passes metadata, typed and executable admission plus
appropriate scientific fixtures. Inline typed extensions retain explicit
ownership of their supplied definitions. No central publisher list or second
execution framework is required.

See [processing discovery](processing-operation-catalog.md),
[value handoff](universal-data-flow.md) and
[execution finalization](../architecture/execution-finalization.md).
