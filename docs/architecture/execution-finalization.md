# Operation execution finalization and effect integrity

## Scope and ownership

`stratbox.core.execution.run` is the single runner for one typed Python
operation. It owns invocation-local outcome resolution and the terminal
operation observation. It does not schedule jobs, authenticate identities,
write an external effect ledger, or claim crash/power-loss recovery.

`core.runtime` selects the provider; resource owners (`core.storage`,
`core.network`, notification consumer, etc.) execute and qualify physical
effects; `core.observability` captures optional evidence and qualifies
collection coverage. A trusted application host owns admission of durable
Work/Run/Attempt lifecycles and real permission enforcement.

## Canonical execution path

```text
Invocation + optional started event
    -> type and provider admission
    -> signature preflight for effectful operations
    -> handler execution / expected-error classification
    -> trusted result postconditions
    -> output accounting / computation evidence where applicable
    -> deadline-only post-handler check (independent of late cancellation)
    -> runner-owned seal of invocation facts
    -> resolve work outcome against effect receipts
    -> validate immutable OperationResult envelope
    -> attempt exactly one best-effort operation.finished event
    -> attach final telemetry counters and return result
```

A failed `OperationResult` constructor must not follow an emitted false
`operation.finished(succeeded)` event. The internal result validator runs
first. If an ordinary error occurs while constructing the validated result,
the runner produces a classified fallback with preserved receipts and without
repeating the handler or external effects.

`ExecutionContext.result_admissions` carries trusted typed `ResultAdmission`
policies from the binding. Each policy returns bounded diagnostics for a
prepared or final value. The runner applies final-value policies before
constructing `OperationResult` and before emitting its terminal event. A rejected
value becomes unavailable and the normal result carries the rejection reason.
Confirmed receipts remain confirmed; an unresolved effect still forces
`unknown` and reconciliation. A late source mismatch never implies rollback.
The final policy receives the actual work outcome. Source obligations select
the usable complete or partial output branch, so a valid office-selection
candidate never requires a complete-release attribute that it does not carry.

`Invocation.admit_prepared(value)` runs the same policy in its `precommit`
phase. Dataset publication calls it on the prepared snapshot before asking the
writer to persist any component. This prevents a detectable bad snapshot from
causing storage writes. Other effectful handlers can use the same explicit
boundary when prepared data exists. A policy comes from trusted Python code;
registry data cannot install executable callbacks.

A successful `operation.finished` collection matches the result's operation,
invocation, method identity and outcome. This event is *an observation*: its presence
does not independently certify a stored file, external authorization or
physical durability. A sink may accept an event and then fail to acknowledge
it. The runner records degraded telemetry, **never retries that emission**,
and never changes business truth because an optional sink failed.

## Work outcome vs. physical effects

The handler returns an ordinary typed value (`succeeded`), a qualified
`Completion(value, "partial"|"failed"|"unknown", diagnostics...)`, or
raises a classified `OperationFailure` / other exception. The handler
alone determines whether a partial value is materially useful.
`OperationDefinition.partial_allowed` is a necessary condition for
`partial`; having one confirmed effect is not sufficient.

| Handler completion | All effects confirmed / none | Any failed (none unknown) | Any unknown/conflict |
| --- | --- | --- | --- |
| succeeded | succeeded | failed | unknown |
| explicit permitted partial | partial | partial | unknown |
| failed | failed | failed | unknown |
| accepted cancellation | cancelled | cancelled | unknown |
| unknown | unknown | unknown | unknown |

A failed external effect with an ordinary successful handler result produces
a **structured failed result**, optionally retaining the typed candidate
value. An invalid return type or forbidden partial result is classified as
a contract failure before the same effect-precedence rule is applied.

`failed` does not mean that the invocation made no external changes.
Previously confirmed effects remain in `OperationResult.effects`; `cancelled`
also preserves them. A `cancelled` outcome means the cooperative token
was encountered at a safe point, not simply set before an otherwise
completed handler returned.

`unknown` is a *qualification*, not a retry instruction. It may result
from an ambiguous domain calculation without an external action; such a
case does not automatically get `retry_disposition="reconcile"`.

## Effect receipt registry: one invocation, one accounting authority

An effect is registered via `Invocation.effect(EffectReceipt(...))`. Its
`kind` must be explicitly declared in
`OperationDefinition.possible_effects`. HTTP capability by itself
describes network access; acquisition has its own source receipts and does
not fabricate a `network.receive` effect.

Within one invocation, a non-null `effect_id` is indexed by
`(kind, effect_id)`. Repeated qualifications of that same logical effect
retain its first position. Each anonymous receipt (`effect_id=None`)
is independent and appended; anonymous receipts are not eligible for
in-place requalification.

Allowed same-ID qualifications:
- `unknown -> confirmed` after authoritative positive evidence;
- `unknown -> failed` after authoritative negative evidence;
- exact/idempotent `confirmed -> confirmed`, `failed -> failed`;
- consistent `unknown -> unknown` enrichment.

An established `confirmed` or `failed` cannot silently transition to
the other status or back to `unknown`. Incompatible resource reference,
content identity, guarantee or reconciliation owner under one effect ID is
also a conflict; stage `commit -> verify` is allowed.

Conflicts become **sticky** within the invocation: the result projects that
effect as `unknown` with `effect.receipt_conflict`, and a subsequent
duplicate receipt cannot erase the conflict. The original key, stable
reference and available evidence remain, while raw reference strings are
excluded from public diagnostics. A separate competent resource owner or
host may later reconcile the prior effect; the runner does not rewrite
historical outcomes or execute a compensating action.

The return envelope snapshots all effects in first-registration order and
all used-input entries. The runner alone invokes private `Invocation._seal()`
before resolution; a handler invoking the previously exposed `seal()` fails
as a classified internal contract error. Even early private seal misuse does
not drop receipts. `stage`, `progress`, `use`, `record`, `account_output`
and `effect` reject supported mutations after finalization. The frozen
envelope does not deep-freeze arbitrary domain values such as DataFrames.

## Diagnostics, result and resource accounting

Primary work diagnostics are kept in original order. Additional system
diagnostics are appended for unresolved effects (`effect.outcome_unknown`,
one qualified entry per independent known effect) or contradictory receipts
(`effect.receipt_conflict`). A known failed effect from a successful
handler adds `effect.failed`. Normal diagnostics use stable, expected-linear
hash-based deduplication; independent anonymous unknown effect observations
retain multiplicity and must never acquire fabricated effect IDs. Identical
domain diagnostics are deduplicated by value. Fallback finalization applies
the same safe stage/component/reason classification.

A domain-level `unknown` retains its own diagnosis without a fabricated
effect-reconciliation instruction. Addressable external uncertainty and receipt
conflicts carry `reconcile` with the concrete effect ID and known owner.
Independent anonymous unknown receipts retain separate diagnostic entries
with `evidence_ref=None` and `retry_disposition=none`: there is no
fabricated addressable reconciliation identity.
Budget, HTTP and provider failures usually carry `after_condition`.
Internals are reduced to `internal.error` with a separate incident ID;
exception strings, raw paths, credentials and payloads are never projected
as public diagnostic values.

### Output obligations and explicit coverage

`BudgetMeter.account_output(key, identity, covered_by=None, completed=False)`
records one invocation-local logical output obligation. Each key is unique;
repeating a claim is idempotent **only** when `(key, ByteIdentity, covered_by)`
is identical. `BudgetMeter.ensure_returned_output(identity)` checks the
already-declared `returned` claim (including explicit coverage), or registers
an otherwise absent output. This separate check avoids weakening the claim
idempotency rule for the runner's automatic completion path. Distinct destinations
must use distinct keys even for identical payloads. The `ByteIdentity` proves
the bytes/size, **not** the identity of the output obligation.
`covered_by` explicitly links a returned output to a previously accounted
obligation of exactly the same bytes; the runner never infers coverage from
`Invocation.effects`, storage success or a matching SHA alone.

`Invocation.account_output(identity, key="returned", covered_by=...)` allows
a handler to make an explicit claim. The runner accounts a returned
`Representation` (including the supported `.representation` wrapper) using
the `returned` key, irrespective of unrelated effects. Staged storage charges
`publish:<effect_id>` **before** physical commit, and per-industry multi-render
results account each `render:<code>` independently. Physical confirmation
remains exclusively an `EffectReceipt`. Independent low-level
`BudgetMeter.charge("output_bytes")` is still appropriate for a separately
materialized preview; it does not automatically cover the returned output.

Output admission is separate from the business handler and applies to every
typed returned `Representation` or supported `.representation` wrapper,
including `Completion(value, "failed"|"unknown")`. Exceeding the byte limit
suppresses the candidate value, preserves the handler's original diagnostics
and physical effect receipts, and appends `budget.output_bytes`. Original
`unknown` remains unknown; useful `partial` without a deliverable value
becomes failed. Cancelled operations have no deliverable value.

A successfully recorded `ComputationReceipt` is retained even when the
subsequent publication fails or becomes unknown and the final value is absent.
For an already-built returned `Representation`, the runner records its
computation identity **before** checking the output-byte admission, so a
budget rejection cannot erase evidence of computed content.
It is evidence of **calculated content**, not file publication or usability.
No raw content/paths are projected into the result journal.

### Deadlines, cancellation and clocks

Internal checkpoints remain cooperative. After a handler returns, the runner
performs a deadline-only check for every outcome, without checking the
cancellation token again. An otherwise successful run beyond the deadline
is `failed` with `budget.deadline`; an explicitly useful `partial` remains
`partial` with the extra deadline diagnostic. Other failures and cancellation
retain their primary reason; any unknown physical effect still forces
`unknown`. Already confirmed physical effects are never rolled back by a
late deadline or cancellation observation.

Strict `BudgetMeter` timestamps must be finite `int|float` samples and
nondecreasing within one meter. The runner reuses the initial invocation
monotonic tick as the budget origin, so an immediate backward step is also
detected without extending the deadline. Equal ticks are valid; backward ticks,
nonnumeric/nonfinite samples and clock exceptions become
`BudgetClockError(code="budget.clock_unavailable")`, distinct from
`BudgetExceeded(code="budget.deadline")`. Both inherit `BudgetError`, and
archive/batch/domain consumers must propagate and classify them without
renaming an invalid clock into corrupt input. If a strict deadline clock
fails, a successful computation cannot assert timeliness: it becomes
`failed` with `budget.clock_unavailable`, preserving receipts. With no deadline, the
business outcome remains intact. Optional terminal timing failures produce
nullable `duration_ms`/`stage_elapsed_ms` and
`ObservabilitySummary.timing_degraded=True` when a sink actually requests
timing. Stage/progress telemetry reads are best-effort and skipped if no
event sink exists; with a sink, missing throttle time skips optional progress
emission. Required budget checkpoints remain independent. If trusted UTC cannot be
obtained, the event is dropped with coverage degradation rather than a fake
timestamp. These failures never authorize re-emission.

Clock admission depends on the requested policy. Without a deadline and
without an event sink, `run` does not sample monotonic time. With only an
optional sink, an initial monotonic failure sets `timing_degraded` but does
not prevent business execution. With a strict deadline, an unusable initial
monotonic tick produces an ordinary `OperationResult(failed)` with
`budget.clock_unavailable`, no handler call, no effects, and no fictitious
started/finished timestamps. Configuration/type failures are separate from
clock faults.

The runner does not claim hard preemption of native calls, crash recovery
during a commit or transaction-wide atomicity across resources.

### Declared ports and external-runtime dependencies

Every `Invocation.provider` / `Invocation.require_provider` role must first
appear in the operation's `required_capabilities` or
`optional_capabilities`; `OperationDefinition.capability(role)` applies
the same invariant. Local defaults cannot bypass the declaration. Required
ports are eagerly admitted and optional ports are admitted when used.

Some operations receive a separate scoped runtime whose own owner resolves
dependent providers at runtime; forcing these ports into eager runner admission
would be incorrect. `RuntimeDependency(role, phase, owner)` describes such
dependencies separately in the catalog, with `phase=scoped|conditional`.
Notification runtime declarations cover state, authority, journal source and
conditional consumer. Real scope-bound grants still belong to
`core.notifications.runtime.require_binding`, not to catalog metadata.

## Qualified effect identity across execution and observability

`EffectKey(kind, effect_id)` is the identity of an addressable external
effect **within a single invocation**. `EffectReceipt.key` is `None` for an
anonymous observation; those entries remain independent. A public final
`OperationResult` contains at most one receipt per identified key.
The core accumulator merges successive qualified observations of the same
key and retains sticky conflicts.

Portable journal references use
`core.observability.records.effect_refs.effect_ref_id(EffectKey)`, a
SHA-256 of canonical kind/ID with a versioned domain separator.
`record_from_result` and `fact_from_stored_bytes` use identical
`ObjectRef(namespace="effect", object_id=...)`. A journal record also
retains `invocation_id` (and, when available, attempt correlation):
identical raw effect IDs in unrelated attempts are **not** presumed to
identify the same physical action or authority.

Use `effect_state_from_result(result, key=EffectKey(...))` for full local
truth and `project_effect_state(records, key, invocation_id=...)` for
portable evidence. The projected `EffectState` carries the selected key,
observed states, `needs_reconciliation: bool|None`,
`evidence_coverage: complete|partial|not_observed|indeterminate`, and
observed attempts. An observed `unknown` always requires reconciliation,
even if a different attempt reports confirmed. Contradictory byte identities
for one qualified key within the same attempt are also treated as a receipt
conflict requiring reconciliation, even if both observations say confirmed;
absent evidence in a
truncated prefix results in `None` (indeterminate), not a false success.
`confirmed` across multiple unrelated invocations never closes another
attempt without resource-owner evidence.

## Bounded result-summary projection

`record_from_result` retains the full `OperationResult` under the caller's
authority but emits an intentionally bounded, privacy-minimal journal
projection. Its `diagnostics`, `inputs`, `effects` and references are
prefix-limited (initially 128 of each, reduced further if journal node or
byte limits require). `details_coverage` is `complete` only when all three
safe projection lists fit; otherwise it is `summarized`.
`details_counts` reports totals and effect states, with a bounded breakdown
of effect kinds; `details_included` reports displayed prefix lengths.
`details_digest` uses the versioned
`details_digest_profile="stratbox.result-details.v3"` and is an order-sensitive
SHA-256 of all complete **safe projections**. Its inclusion policy covers
`Diagnostic.reconciliation_owner`, `UsedInputReceipt.media_type` and
`availability`, and all previously exposed effect qualifiers. Raw input
source locators are reduced to `source_id_digest`; archive member paths
and physical effect references are omitted.
`privacy_qualification="safe_fields_only_private_locators_omitted"`
explicitly limits its meaning. This digest is not a digest of raw private
paths, material bytes, or the provider-owned receipt itself. This digest cannot authenticate a provider
or prove a missing chunk exists. The journal never infers effect absence
from truncated detail; no durable effect ledger is created.

The standalone observation and actual-finish-linked result summary retain
their qualified identities; the finish-linked result summary uses
`data_version=3` (independent of `ExecutionEvent.version=3` and
`JournalRecord.schema_version=1`). A query must check per-stream
`details_included.effects` against `details_counts.effects` before
inferring absence from a missing effect. For diagnostic code queries,
`select_records_qualified` reports omitted-code candidates, while
`summarize_operations` has separate `diagnostic_coverage`,
`diagnostics_total`, and `diagnostics_observed` counters. A visible
prefix is an observed lower bound, never a complete code histogram. Full
receipts remain accessible to the caller through the returned result.
Independent bounded detail persistence, if required by a host, belongs to
its authorized storage/retention policy.

## Consumer integration and test conformance

Existing staged storage and notification handoff intentionally register
`unknown` before a physical commit/accept and later refine the same
effect ID to `confirmed`/`failed`. The registry preserves that protocol.

FRG cleanup and batch source collection explicitly qualify meaningful
partial results. They are not to be auto-promoted to success or globally
demoted because some independent attempted action has failed.
Observability's `record_from_result(result, finished_event=event)`
remains the canonical agreement check. The machine JSON adapter
projects `outcome` rather than inferring success from `value`.

The test suite is organized around 5 work outcomes × 4 effect conditions
(none, confirmed, failed, unknown), plus same-ID state transitions,
anonymous effects, sticky conflicts, late cancellation, sink failures,
invalid typed returns and real storage/FRG multi-effect scenarios.
Tests in the repository are local Python tests; no GitHub Actions are
required or configured as part of this change.

## Explicit limitations

Ordinary exceptions inside a correctly constructed invocation are
classified. Hard-killed processes, `BaseException` subclasses, corrupt
interpreter memory, uncooperative external adapters, forged provider
confirmations and power failures require trusted host/provider mechanisms
outside this library. Exactly-once effects, persistent effect-intent logs,
cross-resource transactions and host authorization are separate projects.
