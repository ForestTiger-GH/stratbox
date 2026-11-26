# Stratbox package

Start with the [SDK](sdk/) to discover, prepare and invoke statistical workflows.
The package separates five responsibilities:

- [Capabilities](capabilities/) define the standard action language and prepare executable graphs.
- [Core](core/) executes those graphs and owns technical providers, resources, retention and effects.
- [Domains](domains/) supply publisher knowledge and scientific methods through static command specifications.
- [Shared values](shared/) carry data, identity, evidence and reference contents across those boundaries.
- [SDK](sdk/) provides one caller-facing lifecycle for discovery, prepared plans, asynchronous calls and results.

See [the processing stages](../../docs/current-how/standard-data-stages.md)
for data flow and [execution ownership](../../docs/architecture/capability-execution.md)
for the boundary between declarations and runtime behavior.
