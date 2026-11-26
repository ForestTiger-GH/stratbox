# Admission and resource scheduling

`StrategyBox.prepare()` resolves a capability and optional domain target into a
prepared plan. The selected entrance determines its actual closure: supplied
physical evidence prunes decoding and acquisition. One execution service admits
that plan, schedules its commands and preserves the logical acceptance scopes.

## Admission precedes retention and publication

`active_runs` controls concurrent activation. It is distinct from the admission
limits on waiting work and completed results which still have an open owner.

| Setting | Retained responsibility |
| --- | --- |
| `max_open_runs` | Accepted runs, including completed results awaiting `close()`. |
| `max_pending_runs` | Runs waiting for activation. |
| `max_plan_nodes`, `max_plan_bytes` | One plan, including nested templates and literal inputs. |
| `max_admitted_nodes`, `max_admitted_plan_bytes` | Aggregate plans retained by the service. |
| `max_retained_bytes`, `max_accepted_values` | Actual live/cached values and their acceptance evidence. |
| `capacities`, `max_workers`, `run_limits` | Physical resource claims and cumulative run budgets. |

An exhausted admission limit rejects the call with an `admission.*` code before
`run.admitted` is appended or the plan is retained. Dynamic maps, repeats and
dispatches reserve their expanded work through the same bounded ownership model.
Resource and graph validation also cover work supplied directly as a prepared
plan. Closing consumed results releases their admission ownership.

Plan-byte accounting estimates retained Python controls and supported payload
storage; it is distinct from serialized input/output budgets and a process-wide
operating-system memory limit. Unsupported hidden mutable payloads are rejected
rather than treated as small immutable handles.

## One service lifecycle

`service.state` is `running`, `draining`, `closed` or `failed`. Only `running`
accepts new work. `close(wait=False)` closes admission and starts draining;
the coordinator keeps the worker pool available until accepted work settles.
`close(wait=True)` waits for that drain. `wait_closed(timeout=...)` provides a
separate bounded wait and returns whether cleanup has finished.

A coordinator failure closes admission immediately. Active physical work settles
before its receipts and resource ownership are finalized. A service failure
cannot convert a completed external mutation into a clean cancellation.

`run(..., timeout=...)` sets an execution deadline and returns after the run's
physical work settles. `handle.result(timeout=...)` limits only the caller's wait;
it preserves the handle and does not establish cancellation or failure. A Python
worker executing a backend which ignores checkpoints cannot be forcibly killed.
Its actual work continues to own resources until it returns.

## Observation remains independent

Appending a journal fact is mandatory. An optional observer receives the
committed fact through one bounded dispatcher, outside the coordinator and
worker pool. Slow, failing or reentrant callbacks cannot hold execution's lock.
`observer_queue_capacity` and `observer_queue_bytes` bound queued facts;
`observer_diagnostic_capacity` bounds retained observer diagnostics.

`observer_status()` reports delivery, failure and overflow counters, queued
bytes, activity and replay coordinates. Optional delivery can drop facts under
pressure or during closing; the journal remains the replay source. The service
does not wait for a stuck optional callback or create replacement threads.
Notification delivery reads the journal independently rather than relying on
the observer queue.

Use `submit()` for concurrent work and close each result after consumption.
See [SDK execution](capability-session.md), [journal consumption](notifications.md)
and [effect recovery](effect-recovery-and-stage-events.md).
