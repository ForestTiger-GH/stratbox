# Supplied tasks, pinned membership and coherent releases

The SDK combines neutral and domain metadata into one immutable capability
snapshot. `stratbox.sdk.bootstrap.default_snapshot()` includes all five domain
contributions. `stratbox.capabilities.manifest.catalog_snapshot()` contains the
neutral building blocks for independently composed catalogs. Neither route
loads numerical or workbook backends during metadata discovery.

## 1. Source goals use contributed recipes

`box.sources.workflow(source_id, inputs=..., parameters=..., format=...,
output="extract")` returns an `InvocationRequest`. The generic binder selects a
contributed recipe using source identity and representation. `output="product"`
selects a useful domain product task. Publication contexts, reviewed profiles
and typed source identities are explicit inputs. The binder rejects conflicting
source or issue coordinates.

```python
from stratbox.sdk import StrategyBox
from stratbox.domains.fns.publications.contracts import ReleaseContext

with StrategyBox() as box:
    request = box.sources.workflow(
        "fns.sme", inputs={"payload": payload, "release": release},
        output="product",
    )
    result = box.run(request)
```

`payload` and `release` are actual caller-owned values. Reading a source card
establishes discoverability; its supported format and reviewed interpretation
scope remain separate conditions. A format admitted only for original capture
has no fabricated extraction recipe. Historical DOC interpretation uses an
explicit conversion provider and retains both byte identities.

## 2. Retained products avoid earlier source actions

`scenario.retained_product` prepares a view and renders a representation from
accepted observations. `scenario.save_retained_product` adds a required
conditional save. They accept the same observation contract as direct
`view.table`; no discovery, acquisition or extraction is added.

`cascade.retained_products` reuses the product scenario twice under independent
`primary` and `secondary` occurrences. Inputs and parameters are namespaced,
for example `primary__observations` and `secondary__format`. The prepared plan
identifies the exact input values and both bindings. Geographic coincidence
never creates a cross-domain calculation: ratios require an explicit admitted
analytical pair and alignment requires explicit semantic mappings.

`cascade.coherent_products` saves both members and treats their required outputs
as one accepted group. `publish.release` separately verifies confirmed member
receipts against their actual current bytes and revisions before writing a
release manifest. Its expected members, input-version vector and member-version
vectors identify one coherent release. Publication supports one declared output
store; broader atomic publication belongs to a provider with that guarantee.

## 3. References preserve reusable scenario occurrences

`operation_scenario(snapshot, operation_id, ...)` wraps an exact operation in an
independently useful scenario. `ScenarioMember` and `cascade_definition` compose
scenarios through retained definition references. An incompatible same-ID
replacement is rejected after authoring as well as before preparation.

`scenario_members` freezes the selected catalog membership. Later catalog
additions cannot widen an existing cascade. Each occurrence keeps its own scope,
acceptance and parameters even when two occurrences reuse the same definition
or share equivalent physical work.

Required completion roots retain independent goals when only one output is
requested. They do not delay an already accepted sibling output. Required checks
instead gate the data whose acceptance they guard. Required effects require an
actual confirmed receipt. Optional failures produce a qualified partial result;
uncertain effects remain uncertain even in optional branches.

## 4. Ordered collection uses ordinary scheduled work

`FoldCall` describes a finite selected sequence of state transitions. Each item
becomes a separate scenario occurrence; the accepted state of one item is the
input of the next. Retries apply to the failed member, and aggregate byte limits
remain in the shared state. Empty selections retain an explicit initialized
state. Membership and limits are admitted before execution.

`ParameterRef(name, path="field")` selects an explicitly named public coordinate
of a supplied mapping or typed parameter. Fold retry bindings can select attempt
and delay coordinates without importing a publisher or transport into the
compiler. Runtime-discovered membership uses a separately admitted continuation;
this finite fold does not hide network discovery inside a parser.

## 5. Coverage and scientific admission are independent

`python -B scripts/check_capability_migration.py` checks every original operation,
source, source-stage cell, profile and template against canonical routes. The
report keeps publisher-edition evidence obligations separate from callable
coverage. `--require-publisher-evidence` fails until those obligations are
actually discharged. A deterministic layout fixture proves its stated scope;
it does not certify unavailable licensed reports or unknown publisher editions.

See [standard stages](standard-data-stages.md),
[CBR capabilities](cbr-capability-migration.md),
[FNS capabilities](fns-capability-migration.md),
[Minfin capabilities](minfin-capability-migration.md),
[Frank capabilities](frank-capability-migration.md), and
[Rosstat capabilities](rosstat-capability-migration.md).
