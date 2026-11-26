# Author a standard command

Declare a `CommandDefinition` with semantic input and output ports, a `MethodRef` or required domain specification, resource demands, providers, effects and a reuse policy. A method accepts `(inputs, settings, context)` and returns named values or an explicit completion.

Use direct immutable settings. Expose acquisition, decoding, interpretation, validation, calculation, rendering and effects as separate visible actions. Checks and required effects must belong to the prepared graph closure.

Compose the command using `OperationDefinition`, `ScenarioDefinition` or `CascadeDefinition` and the common graph vocabulary. All execution goes through `ExecutionService`.
