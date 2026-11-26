# Technical action handlers

These methods implement the source-independent mechanisms behind
[standard command contracts](../../capabilities/commands/): material access,
physical decoding, observation processing, numerical treatment, presentation,
retention, publication, maintenance and notification handoff.

The action protocol is `method(inputs, settings, context) -> named outputs`.
Settings describe the selected technical treatment. Provider access, budgets,
cancellation and effects go through the [execution context](../execution/).

Publisher locations, table geometry and economic interpretation belong to
[domains](../../domains/). Resolve an action's implementation through its catalog
method reference. Substantive contracts are documented in
[the typed processing stages](../../../../docs/current-how/standard-data-stages.md).
