# Technical execution core

The core executes prepared commands and owns shared capacity, value lifetime,
technical providers, effects and execution facts. Source meaning arrives through
bound [domain specifications](../domains/).

- [Execution](execution/) coordinates work, consumers, acceptance, cancellation and effect state.
- [Commands](commands/) implement standard technical actions.
- [Formats](formats/) and [network](network/) turn explicit materials and requests into physical evidence.
- [Storage](storage/) supplies retained data and file primitives; [runtime](runtime/) resolves provider roles and optional dependencies.
- [Observability](observability/) records factual lifecycle events; [notifications](notifications/) retains delivery intent state.

Callable definitions and preparation belong to [capabilities](../capabilities/);
portable values belong to [shared](../shared/). Applications own deployment,
schedules, channels and user interfaces.

See [core boundaries](../../../docs/architecture/core-operation-boundaries.md)
and [admission](../../../docs/current-how/core-execution-and-admission.md).
