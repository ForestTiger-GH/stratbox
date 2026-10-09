# Computation reuse, retry and externally visible effects

**Status:** bounded scientific and engineering explanation. **Evidence:** directly inspected implementation at pinned Git revisions and explicit logical models. This topic is not an accepted planner design, authorization rule, cache policy, or idempotency guarantee.

## Four superficially similar duplication problems

| Problem | Question | Minimum distinct evidence |
| --- | --- | --- |
| Within-plan deduplication | Can two currently requested computations share one output? | Semantic equivalence of versioned inputs and consuming expectations |
| Cache reuse | Can a stored result from an earlier run be reused? | Same relevant inputs **plus** accepted freshness, scope, provenance and invalidation |
| Transport retry | Can a failed or unanswered attempt be repeated? | Failure classification, retry budget and possible prior side effects |
| Effect idempotency | Does repeating a request repeat a durable external effect? | Receiving authority's stable-key contract, scope, digest and lifetime |

Equal `command_id` or function names do not establish any of these equivalences.

## Computation and publication can have different identities

Suppose `Compute_v(x, r, a) = y`, where `x` is a snapshot, `r` a registry version, `a` assumptions and `v` the algorithm. Two consumers of the **same meaning** of `y` may use a single computed result, provided their constraints match. But `Publish(y, path_A)` and `Publish(y, path_B)` remain separate externally visible obligations, even if they materialize identical bytes. Permission or retention differences may further prevent treating them as equivalent.

This is a **formal consequence of the declared semantics**, not a benchmark or observed deployed optimizer.

One consumer may accept cached input; another requires a newly validated official publication. A fresh snapshot satisfying both can sometimes be shared. A cached snapshot cannot satisfy the strict request merely because its URL, filename or displayed period equals the newer one. Source authority, content digest, reporting period, transformation version and validity policy are distinct.

## Timeout does not determine whether an external effect occurred

Assume that a receiver can perform an irreversible effect before the caller receives an acknowledgement, and the response can be lost. A local timeout is then consistent with (A) no remote effect and (B) an effect already committed. A blind retry helps in A and may duplicate the effect in B.

A durable local intent, shared in-plan computation or local mutex does not distinguish A from B. Remote idempotency and receipts can mitigate this only if the effect provider recognizes a stable identity within a declared contract window, and reconciliation establishes a conclusive outcome. Without that evidence, `OUTCOME_UNKNOWN` is a more accurate epistemic state than confirmed success or failure.

This model explicitly excludes systems where the remote participant joins an accepted atomic transaction; it does not establish an unconditional impossibility theorem or a released Strategy Box retry policy.

## What the current code actually demonstrates

The [HTTP downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) executes up to `retries+1` requests and returns typed `DownloadResult` status, content and error. It implements retry of this network read path; it is **not** a generic application-wide command deduplicator or guarantee of external write idempotency.

The [FRG cleanup implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py) prepares a plan before optional execution. Its apply phase performs copy, rename, delete and archive actions per row, catches exceptions into status records, and can continue with later rows after a failure. It may remove a target before attempting its replacement. Thus an accepted plan and a successful computation are not proof that **every requested physical effect** completed atomically or that bytes were verified. No measured data-loss incident is claimed.

The [Windows scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) executes ordered steps and honors `fail_fast` on failed operations. In this module no cross-scenario planner, in-plan deduplication, durable remote job authority or effect receipt coordination is demonstrated. Its existing sequential shape is not evidence that more elaborate target semantics are necessary for every use case.

## Competing approaches, limits and negative knowledge

- **Repeat all computation:** straightforward but potentially wasteful; does not prevent overlapping output writes.
- **Deduplicate only demonstrably pure work:** a narrower assurance envelope with separate effectful publication.
- **Versioned, validated cache:** can save work, but costs storage, invalidation and provenance maintenance.
- **Provider-recognized stable effect keys plus receipts:** supports bounded retry safety if external retention/validation guarantees are explicit.
- **Global single-worker lock:** suppresses some races at the expense of parallelism, but cannot settle ambiguous remote effects.

Meaningful negative findings: within-plan dedup is not cache reuse; cache reuse is not authorization; a transport retry is not exactly-once execution; successful local code return is not independent artifact-byte verification; cancellation of a caller does not reverse an already committed effect.

**Unknown:** real production call distribution, source freshness promises, cost/scale thresholds, accepted risk grades, receipt lags, idempotency horizons and actual runtime tests. No tests, network operations or destructive effects were executed for this scientific module.

**Reopen:** new accepted execution policy, revised core/Windows control flow, upstream effect provider contract, artifact integrity evidence or changed source/registry version semantics. The direct code links above and the stated formal premises are sufficient for bounded ordinary study; raw Research is not a necessary intermediary. Product choices remain with their proper owners.
