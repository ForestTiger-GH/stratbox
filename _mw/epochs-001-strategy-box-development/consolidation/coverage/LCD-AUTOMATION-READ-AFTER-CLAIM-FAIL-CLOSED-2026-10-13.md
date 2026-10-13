# Conditional automation LCD — read-after-claim uncertainty and fake-port fault probes

**Date:** 2026-10-13. **Scope:** same single authorized Strategy Box Knowledge consolidation and ten existing LCD design candidates. Source of the discovery: direct review of the *published* automation candidate service, not new Research. Incoming exact `stratbox@33de4b27d234dd82b25a9108d7d20069bb056bb3`, [Actions 38263289705](https://github.com/ForestTiger-GH/stratbox/actions/runs/38263289705) **SUCCESS**; that does not validate this new change.

## Material defect discovered in an existing candidate

After `claim_unique(identity, evidence) -> False` (the occurrence already exists), the candidate immediately called `find_run_ref` and `find_confirmed_no_run_reason` outside a protective exception boundary. If either read raised on storage timeout, write contention or corrupt projection, the candidate propagated an exception instead of classifying the **already-claimed, possibly host-accepted** occurrence as unknown. Client/scheduler recovery could then misinterpret the thrown exception and admit duplicate work. This violates the already published Science distinction among accepted, rejected and uncertain effects.

The candidate now catches failures from either replay lookup and returns `UNKNOWN_ADMISSION/OCCURRENCE_LOOKUP_UNCERTAIN` **without a new host admission attempt**. An exception from qualified source-version comparison maps to `EvaluationOutcome.UNKNOWN` rather than promotion to OBSERVED/NO_CHANGE; a structurally invalid return maps to INVALID_EVIDENCE. Actual diagnostic cause/storage state must remain separately available to the operational evidence owner; this fake code does not implement real logging or durable dispatch.

## Added bounded source-fragment execution

Extend the existing Work-only `tools/test_lcd_candidate_behavior.py` with six new fake-port cases, in addition to the previously recorded twelve: duplicate claimed occurrence with failing Run-ref read; duplicate rejected occurrence with failing no-Run-reason read; host Run link persisted then ACK lost; certified no-Run decision persisted then ACK lost; source verifier raises; source verifier returns non-enum value. Negative checks assert **no second host admission** where the occurrence already has a claim or terminal receipt. Existing fake-port limitations and ten-document LCD packet denominator remain unchanged.

These are documentation-code fragments evaluated with synthetic in-memory fakes in Actions, not native concurrency, external storage transaction tests, user authorization, deployment, production observability, or an actual scheduler. Source status, independent review and Product Decisions remain unchanged. New exact-SHA Actions CI must pass before test execution is claimed.

## Decision and closure limits

A real implementation still requires idempotent host admission by immutable occurrence identity, durable dispatch intent or host-side query on uncertain acknowledgments, one-writer/transaction policy, authentication, access scoping, cancellation/retry economics and proof against crash-between-writes on the selected physical backend. This packet is a **bounded producer repair** in one existing LCD owner. No host/application source or Windows repository has been modified; status remains `LCD_CANDIDATE / LCD_BLOCKED`.
