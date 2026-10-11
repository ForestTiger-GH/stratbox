# Observed failure, unknown effects and authoritative state preservation

**Scope:** distinguishing a valid empty observation, a missing observation, read failure, an uncertain external effect and a confirmed outcome. **Status:** bounded scientific explanation supported by a specific Strategy Box implementation witness, not a future JobManager specification.

## Observational states are not interchangeable

An empty result means an operation **successfully inspected the declared scope** and found zero items. A storage failure means the operation **did not obtain reliable knowledge** of that scope. These facts require different evidence and different user responses: `EMPTY_SUCCESS` cannot be silently substituted for `READ_FAILED`.

In the frozen Windows app, `HistoryPersistenceService._load_list()` returns `[]` on certain JSON read/decode exceptions and on a payload of an unexpected type, while `load_into()` repopulates five history projections using those returned lists. See the [direct persistence implementation](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py). A corrupted JSON history source and a genuinely empty history can thus become the **same in-memory projection**. This is a direct **static observability/missingness gap**, not empirical proof that a particular deployed user already lost historical files, or proof of every possible race condition.

## A remote effect and a locally observed response

If an external effect can occur before the caller receives acknowledgment, a disconnected caller can observe the same timeout across multiple mutually distinct worlds:

| Actual possible world | Caller observation | Implication for retry |
| --- | --- | --- |
| Effect has **not** occurred | timeout | Retrying may be needed to accomplish the original intent. |
| Effect **committed**, reply was lost | timeout | Blind retry may duplicate the effect. |
| Effect **partially applied** | timeout | Full replay may worsen inconsistency or duplicate partial mutations. |

This is a **logical deduction under the stated asynchronous failure premise**, not evidence of one named provider's historical outage. `timeout` by itself proves neither `effect_failed` nor `effect_succeeded`. Stable idempotency keys, server-side deduplication, an effect receipt and independent reconciliation address different failure boundaries; none can be inferred solely from a retry configuration.

## Two defensible recovery options with different costs

**Fail-closed handling of damaged authoritative state** preserves the distinction between absent and corrupt data and denies risky mutations until recovery. It can, however, block simple read-only use.

**Diagnostic-only/degraded read mode** may permit safe inspection while making corrupted state visibly explicit and preventing new writes to the affected authoritative scope. Whether this is acceptable depends on what the state means: a disposable recent-history UI projection and the **sole durable record of Work** require different durability and recovery guarantees.

The same logical mistake appears in banking source data when `UNKNOWN` becomes numeric zero, or in a client when an absent progress event is represented as a confirmed terminal success. Material severity depends on rights, consequences, declared preservation promises and whether an independent source of truth exists.

## Current code witnesses and the limits of proof

**Observed source behavior:** the Windows JSON history loader collapses some errors to empty projections; the core domain HTTP downloader returns a typed `DownloadResult(ok=False, error)` after unsuccessful attempts and thereby preserves more information than an unqualified empty byte body. Its valid success path remains conditioned on configured transport/status/size checks. See [core download code](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py).

**Not established:** real-world failures of the delivered version, an operational global Event authority, universally safe retry for arbitrary external effects, a completed principal/grant policy, or end-to-end recovery. Static source control flow cannot substitute for fault injection, installed-version checks and storage restoration drills.

**Reopen on:** a change in state persistence/error contracts, an actual transactional state owner, confirmed operational incident records, and deployment-specific risk and durability commitments.

**Product implications remain separate:** rejecting silent fallbacks, introducing effect receipts and choosing recovery profiles are candidate Target WHAT/HOW choices. This article **does not approve** or implement them.
