# Author a standard command

Declare a `CommandDefinition` with semantic input and output ports, a `MethodRef` or required domain specification, resource demands, providers, effects and a reuse policy. A method accepts `(inputs, settings, context)` and returns named values or an explicit completion.

Use direct immutable settings. Expose acquisition, decoding, interpretation, validation, calculation, rendering and effects as separate visible actions. Checks and required effects must belong to the prepared graph closure.

Compose the command using `OperationDefinition`, `ScenarioDefinition` or `CascadeDefinition` and the common graph vocabulary. All execution goes through `ExecutionService`.

For a graph which depends on supplied entrances or a target's declared formats,
set the definition's optional `recipe` to a pure `MethodRef`. Its method receives
`(definition, values, parameters, record, catalog)` and returns the same definition
kind and identity with its concrete `GraphBody`. The compiler invokes that
declared strategy; extending a catalog requires no central identifier switch.
Provider access and physical work belong to execution methods.

References in command parameters participate in graph closure and topological
ordering just like input references. Resource controls require exact integers;
booleans, strings and fractional values cannot silently alter map or repeat
bounds. Authored and prepared control collections are detached from caller-owned
mutable collections.
