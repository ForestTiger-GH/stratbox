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
    -> handler execution / expected-error classification
    -> output accounting / computation evidence where applicable
    -> seal invocation facts
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

A successful `operation.finished` collection matches the result's operation,
invocation, versions and outcome. This event is *an observation*: its presence
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
all used-input entries. The invocation is sealed before resolution;
`stage`, `progress`, `use`, `record` and `effect` cannot be called
after finalization through the supported API. The frozen envelope does not
deep-freeze arbitrary domain values such as mutable DataFrames.

## Diagnostics, result and resource accounting

Primary work diagnostics are kept in original order. Additional system
diagnostics are appended for unresolved effects (`effect.outcome_unknown`,
one qualified entry per independent known effect) or contradictory receipts
(`effect.receipt_conflict`). A known failed effect from a successful
handler adds `effect.failed`. Equivalent diagnostics may be deduplicated;
distinct evidence references must survive.

A domain-level `unknown` retains its own diagnosis without a fabricated
effect-reconciliation instruction. External uncertainty and receipt
conflicts carry `reconcile` with the concrete effect ID and known owner.
Budget, HTTP and provider failures usually carry `after_condition`.
Internals are reduced to `internal.error` with a separate incident ID;
exception strings, raw paths, credentials and payloads are never projected
as public diagnostic values.

Output bytes for an in-memory `Representation` are accounted at the
operation boundary when no physical publication effect has already been
charged. Storage publication charges its bytes at the owning commit
boundary. Computation identity may be recorded for a representation
**regardless of whether an effect also occurred**; it describes calculated
content and must not be interpreted as proof of durable publication.

Budget/deadline checking is cooperative. The runner does not claim to
interrupt unbounded native calls, recover mid-commit process failures,
or provide transaction-wide atomicity across multiple resources.

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
