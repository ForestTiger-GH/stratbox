# Executable scenarios, shared resources and the SDK

The `StrategyBox` facade exposes the canonical operation and source catalogs,
compiles scenarios and cascades, and submits their tasks to one execution
session. Existing operation results retain their outcomes, provenance and
effect receipts. A graph result adds named outputs, task states and the outcome
of the requested composition.

The implementation provides local thread execution and process-local state.
Durable workflow recovery, a process backend and application interfaces have
separate owners. A waiting timeout leaves a running operation and its resource
reservation active until the operation actually completes.

Contents:

1. Public entry point — discover capabilities and execute the same plan in a
   script, notebook or application host.
2. Definitions and admission — identify task instances, bind ports and validate
   templates before execution.
3. Shared execution — coordinate concurrency, cancellation and bounded maps.
4. Shared network work — preserve access, freshness and source-use boundaries.
5. Observation and notifications — connect qualified run outcomes to the
   existing journal and delivery runtime.

## 1. One public entry point

```python
from stratbox.sdk import StrategyBox, ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore

settings = ExecutionSettings(max_workers=4, active_runs=2, per_origin=2)
with StrategyBox(settings=settings,
                 providers={"filestore": LocalFileStore("data")}) as box:
    page = box.operations.page(limit=20)
    result = box.invoke("material.read_location", parameters={
        "locator": "original.csv", "media_type": "text/csv",
    })
    if result.outcome == "succeeded":
        payload = result.output("source")
```

`invoke`, `run` and `submit` use the same compiler and session. `invoke` expands
a supplied composition where the operation has an expansion rule. Otherwise
it creates a single operation task. `submit` returns a handle with `result`,
`snapshot`, `events` and `cancel`; `run` waits for that result. Catalog discovery
starts no worker threads and imports no optional table or HTTP libraries.

`box.workflow(operation_id, inputs=..., parameters=...)` returns that scenario
without executing it, so it can be embedded with `ScenarioStep`. A capability
classified as a graph cannot be inserted as an opaque `OperationStep`; the
compiler reports `composition.scenario_required`. This keeps every constituent
task in the shared plan. Integral numerical and streaming transaction boundaries
remain ordinary operation tasks.

Applications pass an `ExecutionContext` for explicit capability bindings,
cancellation, admission and evidence policies. The `providers` convenience
argument accepts a role-to-provider mapping or the standard `Providers` bundle.
It rejects conflicts with already bound roles. Callers retain ownership of
adapters supplied explicitly. Closing the facade closes its execution session
and resources created by that session.

`box.sources` exposes source selection, source descriptions, explicit binding
and `workflow(series_id, ...)`. Supplied domain workflows accept original
payloads or source-specific acquisition parameters. An explicit local input
selects local processing; a missing local input is an error.

## 2. Definitions, ports and source specialization

| Code | Model | Responsibility |
| --- | --- | --- |
| C01 | `OperationStep` | One named call with inputs, parameters, resource requirements and retry policy. |
| C02 | `ScenarioDefinition` | A reusable graph with named inputs and outputs. |
| C03 | `ScenarioStep` / `CascadeDefinition` | Scoped composition using the same task and execution model. |
| C04 | `PlanOutputRef` / `InputRef` | A named upstream output or supplied workflow argument. |
| C05 | `MapStep` / `CollectStep` | Bounded per-item subgraphs and explicit typed collection. |
| C06 | `Condition` | Selection by terminal state or a declared output field. |
| C07 | `ExecutionPlan` | Concrete task identities, dependencies, scopes and method fingerprints. |
| C08 | `TemplateDefinition` / `TemplateSlot` | Typed substitution of an operation or a declared subgraph. |

The compiler resolves operation definitions and source bindings, validates
required inputs and port contracts, rejects cycles and pins method identities.
Multiple calls of the same operation remain distinct tasks. Explicit sharing
requires equal computational inputs and policy and excludes effectful calls.
Selected outputs retain their dependency closure; effects that belong to that
output must be declared in its dependencies.

Nested scenarios flatten into scopes. A scenario has no worker of its own.
Map bodies are compiled templates; runtime expansion preserves that admitted
body and the item key. The plan codec supports a closed set of portable values
and rejects unsupported live objects. Loading a plan does not bypass admission.

Operation declarations live under `operations/specifications`. Source records,
profiles and reusable route templates live under `domains/registry`. Source
records select a template and carry source-specific overrides. Output schemas
are resolved from their canonical operation definitions wherever the source
group explicitly references an operation output.

## 3. Shared execution and qualified completion

The coordinator admits tasks against one resource ledger before submitting
them to the common worker pool. Active-run, pending-run, worker, network,
origin, parser and notification limits are session settings. Independent runs
share those limits; nested scenarios consume no additional top-level run slot.
Resource expenditure remains cumulative, while occupied capacity is released
after the corresponding physical work finishes.

Map windows bound admitted item subgraphs through completion of each local
chain. A nested structural map consumes no worker while waiting for children.
Collections preserve item keys and outcomes; empty discovery and incomplete
collections have explicit policies. Mutable inputs are isolated at handoff.

The retained-material quota measures payload bytes and scientific buffers.
Completed intermediate results can be spilled after their last consumer;
their receipts remain resident and `RunResult.results` resolves their exact
values lazily. These private temporary files remain available while their
result leases live, including after session closure. They are process-local
implementation storage. Values without a spill codec continue to occupy their
quota; they are never silently discarded or counted as released.

Cancellation stops new admission and signals running handlers cooperatively.
Confirmed effects remain in operation results. A failed required dependency
blocks its consumers, independent branches continue under the default policy,
and unknown effects remain unknown in the graph outcome. `fail_fast` stops new
work after a required failure. Explicit retries are limited to admitted failure
codes and effect-free failed attempts; the scheduler releases the worker during
the delay. Transport attempts use the coordinated retry budget.

`RunResult.results` retains qualified operation results. `outputs` retains the
selected output envelopes; `output(name)` returns their values. Task snapshots
distinguish dependency waiting, resource waiting, retry, running, skipped,
blocked and terminal outcomes. A timeout passed to `result` limits waiting;
it does not prove that a thread stopped or an external write failed.

## 4. Connection lifetime and shared materials

Session network resources reuse owned transport pools. Request identity includes
method, exact URL, relevant headers and body, provider/access scope, access
generation and an explicit observation or immutable-content identity.
Independent fresh observations of a mutable URL remain independent.

The shared-work registry separates the producer from consumers. Detaching one
consumer preserves work required by another. Access preparation is coordinated
per generation; response completion, failed streaming and redirects release
their resources through the transport's lifecycle. Caller-owned transports are
left open at session shutdown.

Physical content and logical use are distinct. `SharedMaterial` identifies one
retrieval; `SourceUse` records each qualified source/group relationship.
Supplied CBR multi-source workflows expose the common index in the plan, then
perform source-specific discovery and processing. Sharing bytes does not merge
distinct economic source coordinates or independently requested storage effects.

## 5. Observation, history and notifications

Orchestration events extend the existing observability records and codecs.
Correlation carries the session, plan, run, task, attempt, scope, item and shared
work identities. Task invocation events retain their original evidence.
Snapshots and event cursors support reconnecting clients; capture health reports
eviction, observer failures and pending terminal publication.

Diagnostic retention and observer delivery are bounded. Slow observers run
outside the coordinator. Terminal run evidence has separately reserved capacity
and a publication obligation; retrying its publication preserves the same event
identity. Capacity exhaustion is explicit and cannot silently discard a
notification-triggering terminal transition.

The session journal exposes a positioned source for the existing notification
runtime. `run.completed` and `run.failed` topics project qualified terminal
facts. Reprocessing a transition in one subscription reuses its semantic
dispatch identity. A new run has a distinct identity. Economic publication
topics retain their baseline, backfill and revision rules.

Notification preparation, consumer acceptance and downstream delivery retain
their separate outcomes. Run completion never claims delivery or reading.
Configured preparation and delivery operations can be submitted to the same
session with its notification quota. The session sends no external message
without a supplied consumer and an explicit delivery request. Notification
failures preserve the result of a successfully completed calculation.

Related implementation contracts: [operation admission](domain-operation-registry.md),
[typed handoff](universal-data-flow.md), [notifications](notifications.md).
