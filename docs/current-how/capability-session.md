# Calling commands, operations, scenarios and cascades

`StrategyBox` resolves canonical definitions, prepares a command plan and
submits it to one bounded session. The same client accepts direct IDs, typed
requests and temporary typed definitions.

```python
from stratbox.sdk import StrategyBox
from stratbox.composition.requests import InvocationRequest

with StrategyBox() as box:
    request = InvocationRequest("material.read", inputs={"material": b"source data"})
    result = box.run(request)
    assert result.outcome == "succeeded"
    payload = result.output("value")

# The returned result owns its retained values until close().
assert payload.data == b"source data"
result.close()
```

## Inspecting the prepared route

`box.prepare(id, inputs=..., parameters=...)` returns an `ExecutionPlan`.
`plan.explain()` reports the root kind, selected bindings, semantic scopes,
physical command work and logical uses. `plan.to_dict()` provides a versioned
projection for supported portable inputs. Nonportable values require a host
reference or a supported typed snapshot rather than arbitrary object loading.

Use `outputs=(...)` to request named outputs. Required checks and effects remain
in the closure. `supplied_outputs` cuts upstream work at a qualified named
output while preserving independent obligations. Use an actual projected or
prepared value with its contract and qualification when passing results
between invocations.

`box.invoke("extract.observations", inputs={"material": payload},
parameters={"profile": profile})` uses the standard row interpretation method.
Profiles describe sheet selection, source axes, periods, units and cell
coordinates. `method_id`, `profile_id` and `group_id` select registered
specializations explicitly. Missing or ambiguous bindings fail preparation.

## Local definitions and goal requests

An `OperationDefinition` contains a `GraphBody` of command calls. Scenarios
contain operations or reusable scenarios; cascades coordinate scenarios.
Passing a local definition to `box.prepare` or `box.invoke` admits it through
the same catalog rules. Its identity is then addressable in that client.
Replacing a live definition under the same ID is rejected; use a distinct ID
for a different definition.

For a group of local definitions and profiles, create a `CatalogContribution`
and use `catalog_snapshot().overlay(contribution)` as the `capabilities=`
constructor argument. A `RecipeDefinition` binds a goal to a capability.
`GoalRequest` and `box.prepare_goal` use that registered recipe and the same
exact preparation path.

The [offline example](../../examples/capability_session.py) uses standard-library
data and a temporary operation. The [ownership description](../architecture/capability-execution.md)
explains dependency rules and the migration boundary for existing domains.

## Provider and result lifetime

Supply provider instances through `StrategyBox(providers={...})`.
`http.acquire` requires `http`; `store.commit` requires `output_filestore`.
Acquisition is explicit. Extraction from supplied material opens no source
connection. Save is an explicit effect with a destination and revision policy.

Submit independent plans with `box.submit(plan)` to share one resource ledger.
Call `handle.snapshot()`, `handle.output(name)` or `handle.result(timeout)`.
`result.scopes` preserves independent scenario and operation outcomes.
Accepted output release can precede unrelated unfinished scopes. A failed
operation's rejected value remains unavailable.

Close retained results explicitly when finished. A read lease preserves an
already acquired reader across result closure; its bytes remain charged until
the reader releases them. Temporary spill is process-local. Durable restart
recovery belongs to a host implementing the recovery ports.
