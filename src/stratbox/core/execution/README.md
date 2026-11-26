# Execution lifecycle

`ExecutionService` owns one bounded coordinator for prepared plans. It schedules
physical work across runs while preserving each caller's logical acceptance,
source context, cancellation and result ownership.

`ExecutionSettings` supplies capacity and budget limits. `RunHandle` supports
waiting, status and cancellation; `RunResult` exposes accepted outputs,
diagnostics and effect receipts. Closing a result releases its library-owned
values. Effect receipts and uncertain confirmations have a separate lifecycle;
configure [durable effect state](effect_state.py) for recovery across service restarts.

Command methods receive a `CommandContext` for declared providers, checkpoints,
budget spending and authorized effects. Methods execute an already bound action;
they do not rebuild the graph or select publisher specifications.

The [journal](../observability/journal/) records lifecycle facts.
[Capabilities preparation](../../capabilities/preparation/) owns the graph and
its contracts. See [admission and resources](../../../../docs/current-how/core-execution-and-admission.md)
and [result lifetime](../../../../docs/current-how/capability-session.md).
