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
| `max_retained_bytes` | Managed live/cached values and reserved private working inputs. |
| `max_accepted_values` | Number of retained acceptance records. |
| `capacities`, `max_workers`, `run_limits` | Physical resource claims and cumulative run budgets. |

An exhausted admission limit rejects the call with an `admission.*` code before
`run.admitted` is appended or the plan is retained. Dynamic maps, repeats and
dispatches reserve their expanded work through the same bounded ownership model.
Resource and graph validation also cover work supplied directly as a prepared
plan. Closing consumed results releases their admission ownership.

The pure graph gate visits every nested map, dispatch alternative and repeat
template before admission. Actual value references, command parameters, guards
and whole-member obligations contribute dependency edges. Local namespaces stay
separate; a nested template's captured parent references are rebound during its
bounded expansion. The complete expanded slice is checked before publication.
An invalid request rejects that submission and leaves the service usable.

An optional `admission_guard(plan)` runs after validation and outside the
coordinator lock. Its exception rejects that submission before `run.admitted`.
The persistent local profile uses this boundary for its storage admission
thresholds; already admitted work can still settle.

Plan-byte accounting estimates retained Python controls and supported payload
storage; it is distinct from serialized input/output budgets and a process-wide
operating-system memory limit. Unsupported hidden mutable payloads are rejected
rather than treated as small immutable handles.

## Output use and member completion

A readable value has a producing outcome, a logical disposition and a purpose.
Successful data outputs can be accepted; unsuccessful outputs are reported only
when their port explicitly permits the producing outcome. Diagnostic collection
reports can be accepted for their diagnostic purpose. Payload identity alone
cannot promote a reported value into an analytical result.

Forwarding through an operation, map, dispatch or iteration preserves the output
origin. A collection evaluates both the selected output and the member's own
required checks, effects and completion obligations. Making a member optional in
its parent changes whether that parent must include it; its internal obligations
remain intact. Independently accepted early outputs retain their own usability
when a separate later completion obligation fails.

| Policy | Completion promise |
| --- | --- |
| `all_selected` | Every required selected member satisfies its declared completion. |
| `eligible_subset` | Eligible members can satisfy the requested subset and minimum; excluded members retain their actual outcomes. |
| `diagnostic` | `CollectCall` can aggregate permitted reports for inspection; their failed or unknown producer outcomes remain in member reports. |

Journal output facts expose `output_disposition`, `producer_outcome`,
`output_role` and `origin_uses`. Data projections admit accepted data uses.
Diagnostic reports and unknown effects retain their separate meaning.

## Sealed values and private working storage

Admission detaches supported mutable literals. The owned-value registry records
the private payload's exact identity, normalized processing identity, estimated
resident size and reachable staged resources. Workers receive private input,
resolved parameter, settings and target storage. Returned mutable payloads are sealed before logical
acceptance; each result reader receives its own copy.

Full scientific copying, identity construction, command output validation and
acceptance metadata preparation run outside the coordinator lock. Scheduling,
pins, cache attachment, result attachment and status inspection use descriptors
and incremental ownership accounting. A full scan remains appropriate at a new
untrusted boundary. Arbitrary caller-provided digest attributes establish no
trusted identity.

A typed field exposed as a later graph input acquires its descriptor on that
same bounded worker pool while its source value remains owned. Physical work
keys use actual resolved parameter values and cached settings/target identities.
An unresolved `ValueRef` identifies a dependency; its spelling cannot stand in
for the referenced value. When an exact identity is unavailable, execution
declines reuse instead of hashing an opaque payload on the coordinator.

Private working inputs reserve managed capacity before dispatch and release it
after the physical method settles. Result, cache, input and provisional producer
owners release independently. A result's closure cannot release a resource still
pinned by another admitted use. These managed bounds do not constrain arbitrary
backend allocations or promise a hard process RSS ceiling. Unsupported native
mutable containers and mutable dataframe axis labels fail explicitly.

The reproducible extraction and concurrent-command probe is
`scripts/probe_owned_values.py`. Its measured scope and release qualification are
described in [core operating qualification](core-0-27-qualification.md).

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

Each physical generation has its own active demand set. Completed results retain
values but contribute no deadline or cancellation demand. A generation becomes
permanently unavailable for joining after its final demand detaches; a later
request may start a new generation while the previous worker is still settling.
Claims and provisional resources stay with the actual outstanding worker.
Provider timeouts use the remaining active demand for that exact generation.

`admission_pause(timeout=...)` temporarily rejects new submissions and drains
already admitted work to a stable local cut. It preserves open results and
durable unknown effect evidence. Exiting the context resumes admission; a pause
timeout releases the barrier without forcibly stopping workers. Recovery export
uses this service-owned barrier.

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
