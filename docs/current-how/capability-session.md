# Direct calls, prepared plans and result lifetime

`stratbox.sdk.StrategyBox` provides one entry for commands, operations, scenarios
and cascades. Discovery reads standard metadata; preparation selects exact
methods/settings and required work; the execution service owns a multicall
session and its resources.

This page describes the common call path. Source and numerical methods still
apply their explicit format, semantic and provider requirements.

## Contents

1. Discovery — inspect standard definitions and continuing source records.
2. Invocation — prepare, run and submit through the same service.
3. Results — named accepted values and independent outcomes.
4. Providers — explicit infrastructure and caller ownership.

## 1. Discovery

```python
from stratbox.sdk import StrategyBox

with StrategyBox() as box:
    page = box.discover(kind="command", limit=20)
    definition = box.describe("command.table.interpret")
    source = box.sources.source("fns.sme")
```

The page contains an offset, total and optional next offset. Source records are
continuing table declarations, not downloaded issues or individual numerical
histories. `box.sources.list(domain_id="fns")` returns the selected source records.

## 2. Preparation and execution

`box.prepare(capability_id, inputs=..., parameters=..., target=..., outputs=...)`
returns a prepared plan. `box.run(plan)` executes it. `box.invoke(...)` performs
the same preparation and run. `box.submit(...)` returns a handle with result,
status and cancellation controls. A caller-authored root definition can be
prepared against a catalog containing its dependencies.

`run()` and `invoke()` interpret `timeout` as an execution deadline and wait for
physical settlement. For an independently bounded caller wait, use
`box.submit(...).result(timeout=...)` and retain the handle. Asynchronous
`box.close(wait=False)` starts draining; a subsequent `box.close(wait=True)`
waits for the same service to finish.

The target can identify a source series, calculation model or product. Input
values are supplied explicitly. Unsupported layouts and source contradictions
are diagnosed; a parser does not silently substitute other material.

## 3. Accepted outputs and lifetime

`RunResult.outcome` describes the task result. `outputs` contains named accepted
values, `scopes` preserves logical composition outcomes, and diagnostics retain
failure or incomplete-work findings. `result.output(name)` reads a selected
output; a single output can be read using the default name.

The caller closes retained results after use and closes the client to release
its service resources. Accepted values and required effects have separate
outcomes. An optional delivery failure does not invalidate the accepted data.
Shared producer cancellation follows the remaining logical demand.

## 4. Infrastructure providers

Providers are supplied explicitly through `StrategyBox(providers={...})`.
The HTTP, file, dataset, document-conversion and seasonal-adjustment roles have
different contracts. An unused backend is not required by another independent
route. A numerical history already obtained from a database needs no publisher
HTTP access or workbook decoder.

The library owns the common meaning and controls. A platform host owns actual
schedules, protocol-server transport and its durable application lifecycle.
