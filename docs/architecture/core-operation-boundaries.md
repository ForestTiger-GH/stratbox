# Technical command boundaries

A standard command has explicit input and output ports, resource demands, provider requirements, effects, reuse policy and acceptance. Its bound method receives typed inputs, narrow settings and `CommandContext`. Interpretation performs no implicit acquisition, storage or notification.

An operation exposes a reusable local transformation. A scenario defines a complete purpose with required checks and effects. A cascade coordinates independent scenarios. All four callable kinds are prepared into one plan representation and use `core.execution.service.ExecutionService`.

Source-neutral standard definitions live in `capabilities`; publisher specializations live in domain command maps. The executor contains no source-specific command dispatch.
