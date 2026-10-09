# Background work, automation and chat semantics — Research extraction

**Source:** `SB-SRC-0018`, entire L1–L1041, blob `5ed80eeb3065b60f89d0706bfa49bbfd272fc066` at pinned `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`. 21 provisional material units, `units/BASE-STUDY-0018.jsonl`. Stable source ID/blob/commit retained, `read_state=full_read`; exhaustive conservation unverified.

## Reconciled model with current-state limits

The Research distinguishes **Scenario** (definition), **Case** (user goal), **Job** (managed execution), **Attempt** (specific try), **Automation** (persistent rule), **Trigger/Occurrence** (reason/time for invocation), and **ChatThread** (place to discuss/contextualize work). A background launch is not a different business algorithm, and an enabled automation is not equivalent to a currently executing Job.

The current `stratbox-windows` contains an in-memory `BackgroundProcessStore` and visible enabled statuses, but no demonstrated persisted job scheduler. The existing Qt scenario coordinator may keep GUI responsive during work, yet this does not establish work surviving a closed GUI. No independent `ChatThread`/multi-thread durable model is proved by the current application source.

The study proposes one application execution authority, separate chat and all-jobs projections, dynamic active-chat group rather than destructive reordering, resource-dependent parallelism, idempotent submission, worker leases/fencing, recovery, audience-sensitive read views, and profile-specific behavior across clients. **These are Target WHAT/HOW candidates, not approved commitments, APIs or new package/repository obligations.**

### Time, uncertainty and safety

- Calendar rules need timezone identity, civil/UTC occurrence semantics, daylight-saving behavior and explicit missed-run policy; a display-only `schedule_label` cannot guarantee scheduling.
- Cancelling queued work differs from requesting cancellation of running work; an already-performed external effect cannot be assumed rolled back by a status toggle.
- A worker whose lease expired may still run, so fencing/effect reconciliation cannot be replaced by checking the old lease's expiry time.
- Actual progress must not show a fabricated percentage without a denominator or commit proof.
- Worker/node failure and lost connections can require `OUTCOME_UNKNOWN`, not automatically `FAILED`.
- Multiuser automation needs explicit authorization and per-user read/notice scope; no agent or delegated consumer gains rights from a mere actor label.

### Alternatives and independent evidence

Scheduler adapters may use existing libraries, but scheduler state is not sufficient Product Job authority. A separate 'background-only' executor or per-occurrence chat would duplicate history and blur ownership. SQLite is one possible local transactional implementation, not a network-shared DB promise. Source references largely reuse previous Windows/observability Research, so they do not count as additional independent confirmation.

**Assurance:** complete source read, typed provisional unit register and source-role distinction. No direct end-to-end test, scheduled occurrence, UI crash recovery or multiuser security run. Next: bounded `SB-SRC-0026` execution/control research and unresolved error/effect semantics.
