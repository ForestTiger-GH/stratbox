# Original-first 0558 challenge — authorization-aware Run snapshots and scoped event feed

**When / role:** 2026-10-12, `PRODUCER_SOURCE_FIRST_CANDIDATE_GAP_REPAIR`. Not an independent whole-source semantic review, installed host security test, actual cursor cryptography, product authorization or deployed Web/Android endpoint.

**Original:** `SB-SRC-0558`, frozen `stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97`, blob `68e433f98e9f660c1c5738ef8a41e077ac738a95`, `_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/05_Strategy_Box_Полномочия_безопасность_и_многопользовательская_работа.md` (1,206 physical lines). **Maintained Science already contains the full conceptual principles:** `docs/science/trust-and-assurance/identity-authorization-and-effect-boundaries.md` and `docs/science/collaboration/authorized-streams-read-cursors-and-private-work.md`; source-shape SEC-01..30 and earlier 15 shared-node cases remain separately maintained. New work corrects a **divergence in executable candidate Host LCD**, not missing scientific treatment.

## A. Direct source and code contradiction

| Frozen original source | Scientific meaning (dated Research, not deployed claim) | Defect in prior Host LCD |
| --- | --- | --- |
| Security 0558 §9.2 L438–L455 | Authoritative restricted record must be projected **after object ACL and field sensitivity qualification**; Windows `ScenarioRunCase.short_params_text` and `OperationalEvent.body/meta` can carry raw parameter text | `ScopedReads.observe` ran one `can_read_run` then returned **unfiltered `LedgerPort.read_after` tuples** to client; typed `safe_text` alone cannot certify safety |
| §9.3 L455–L469 | ACL applies before exposing event IDs; old clients and ACL changes require redaction/resync | Direct ledger return had no per-event scope revision or genuine server-owned projection contract |
| §9.3 L467–L471 | Node-global monotonic sequence may disclose private activity; use scope-specific opaque cursor + revocation/generation | Previous `observe(after:int)` and `Observation.sequence:int` were transport-facing; `RunSnapshot.last_sequence:int` also threatened an indirect disclosure |
| §9.4 L471–L488 | Personal read receipt differs from shared event/history and from notification acknowledgment | New feed cursor is a projection position **not** user read/ack permission or notification receipt; still a separate owner |
| §19–20 L1050–L1075 | Safe schemas must fail closed when new sensitive fields appear | A declared `Observation.safe_text` string cannot by itself prevent a future payload from containing path/token/traceback |

The earlier `read_run` used `if not policy.can_read_run(actor, run_ref)`; a buggy policy port returning `1` or `"false"` was truthy and would grant read. An exception passed through with arbitrary internal error detail. In `observe`, old numeric `after` and `Observation.sequence` also allowed a private event-count inference if backed by a node-level ledger sequence. Merely renaming an internal sequence as opaque does not fix that.

## B. Bounded candidate corrections

The public-neutral [Host LCD](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/lcd/hosting/host-authority-and-client-contract-construction.md) now:
1. Grants Run read **only** if the policy returns literal Boolean `True`; reports policy service uncertainty as a safe denied exception, never an implied grant or `RUN_UNAVAILABLE`.
2. Qualifies the returned `RunSnapshot` instance, exact run identity, revision type/range, phase/outcome enums and `stale` Boolean. Its client DTO no longer includes an arbitrary `last_sequence` from the unfiltered ledger.
3. Changes `observe(after:int)` to `observe(after_cursor:str|None)`, returning a typed `ObservationPage` with explicit `feed_generation`, opaque `next_cursor`, qualified `event_ref`, `resync_required` and bounded, schema-limited public observation roles. Internal ledger `read_after` remains an **internal** storage operation only.
4. Requires a separately trusted `AuthorizedFeedPort.read_authorized(actor, run_ref, cursor)` that owns per-event object ACL, per-field sensitivity, safe text/enum schema, session+generation-specific authenticated cursor and invalidation. The wrapper validates structural consistency (foreign Run/page/record, wrong cursor type, page with resync+events, non-tuple event collection), but **actual data classification and cursor unforgeability remain port obligations**, not guaranteed by dataclass types.
5. Uses explicit `RESYNC_REQUIRED`/denial/unavailable interpretations rather than empty-success on a broken feed or storage change.

This updates a *candidate* interface without compatibility aliases: no released remote protocol exists to preserve. ClientTransport and HostApplicationPort now use the typed, scope-aware page rather than raw integer/sequence tuples.

## C. Artificial behavior evidence and 8 new target vectors

The existing Work-only `tools/test_lcd_candidate_behavior.py` adds **one new Host packet probe** `probe_authorized_host_feed`, executing the exact Markdown-defined `ScopedReads`, `RunSnapshot`, `Observation` and `ObservationPage` AST, with synthetic ledger, policy and safe feed. It checks true grant; denies `False`, `"false"`, `1`, `None`; fails closed on policy outage; rejects raw/incompatible cursor, foreign Run and malformed safe pages; exposes no raw ledger event reads; returns explicit resync; and refuses malformed aggregate snapshots. The temporary fake `SafeFeed` manually enforces safe output — **the test does not prove** actual field redaction or a real actor-bound signed/opaque token.

The separate [Host LDD](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/ldd/hosting/host-client-attachment-boundary.md) gained eight prospective, **UNEXECUTED** vectors **HC-52..59**: untyped grant, sensitive event fields, hidden node-seq, revocation, stolen/expired cursor, malformed/failed authorized feed, untrusted `safe_text`, and atomic snapshot-to-stream lifecycle. `verify_host_ldd_case_ids.py` checks those IDs for missing/duplicate definitions, **not their behavioral pass**.

The first candidate-only patch intentionally failed CI because the previous fake harness still used the old constructor/type; this was corrected by updating **literal documented code** rather than removing the test. The later intermediate code change also required matching the `RunSnapshot` fixture. Treat these intermediary red runs as caught counterexamples, not the final checkpoint. The exact next green CI must be verified by source SHA before claiming successful updated probe count.

## D. Blockers and conservation status

**Actual authority and security proof remain OPEN:** authenticated principal/session, field classification and safe text language, signed/opaque cursor issuer/validation/revocation, live streaming and concurrent ACL changes, event retention/compaction/snapshot-consistency, privacy timing side channels, OS/network transport and deployment, real permission store/policy revision, independent threat assessment and Web/Windows split-host conformance.

**Source and release grades remain unchanged:** `SB-SRC-0558` is still `material_unit_state=unaccounted` under independent whole-original accounting. `GLOBAL LOSSLESS_PASS=BLOCKED`; Host LCD is still `LCD_BLOCKED`. No confidential/private provider details or concrete organizational endpoints entered public code or documentation.
