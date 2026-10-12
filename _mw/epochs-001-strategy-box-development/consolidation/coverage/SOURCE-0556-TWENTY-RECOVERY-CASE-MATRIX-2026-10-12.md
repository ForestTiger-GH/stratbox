# Original Topic 03 — full twenty-row recovery matrix, source-first Science routing

**Date:** 2026-10-12. **Grade:** `PRODUCER_SCOPED_ORIGINAL_TO_SCIENCE_CASE_RECONCILIATION`; no independent original-first review or actual host-storage release evidence.

**Primary original:** `SB-SRC-0556`, frozen `stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97`, blob `f919df034a2e15ae8947d51aaec9cd564fe462ad`, `_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md` (785 physical lines). Its original §13 L575–L600 enumerates 20 independent fault triggers, present failure risk, future response and minimal test. Its §§4–6 distinguish four durability grades, managed storage capabilities and three different commit boundaries. Its §16 separately asks 16 Product/Platform owner decisions.

## Existing correct Science before this pass

The maintained owners `docs/science/state-and-recovery/authority-durability-and-recovery.md` and `shared-state-backup-generation-and-retention.md` already contained separate original-specific SREC source packets (12 meaning units), 16 original Q03 unresolved decisions, 15 state trade-offs and numerous qualified backup/recovery distinctions. The existing Work verifier `tools/verify_state_0556_recovery_routes.py` checks those exact packets. It **does not independently preserve all twenty §13 matrix rows** by unique adverse-case identity; broad preservation of JSON corruption, CAS, disconnect and backup concepts did not establish a one-row-per-original fault-map.

## Material precision added

The producer has now added `## Original Topic 03 — twenty distinct recovery failure proposals` to the existing `docs/science/state-and-recovery/authority-durability-and-recovery.md`. Exact source 1–20 map to individually numbered `R03-01..R03-20`, each with the original adverse trigger and qualified target evidence. Differences intentionally preserved:

- JSON torn state R03-01 versus split Case/Artifact transaction R03-02 versus missing external artifact bytes in otherwise successful DB backup R03-15;
- unsupported Data mount R03-12 versus **unsupported SQLite/SMB/NFS authority topology** R03-17;
- Web/Windows lifecycle R03-07/R03-13 versus stale writer after a restore R03-14;
- workspace Thread title CAS R03-06 versus per-principal read receipts R03-18;
- corrupt middle journal frame R03-19 versus incomplete trailing record and verified migration cutover R03-20;
- official/AppDock activation contract mismatch R03-16 before state effects, not proof an external platform can provide a state DB.

The new source-pinned `tools/verify_recovery_0556_twenty_faults.py` reads the original 785-line Git blob by exact hash, counts the 20 original numbered §13 cases, asserts 20 unique Science `R03` rows, and checks each row contains a distinct adverse condition and expected evidence. The existing 12 SREC units and 16 original questions are **preserved, not replaced or re-counted as new independent sources**.

## Epistemic ceiling / next consumer

All 20 are original **candidate acceptance tests**; no green structural route verifier can certify native atomic file creation, SQLite WAL on a specific filesystem, authenticated owner/session, actual multiuser chat edit, filesystem generation fence, full backup coverage or Power-fail recovery. For that, a selected target owner must implement actual semantics and exercise typed injected faults plus native storage/admission/restore windows. A genuinely different competent reviewer must separately establish original source→Science completeness, destination→source soundness and publication-only sufficiency.

**Authoritative census unchanged:** `SB-SRC-0556` remains `full_read / unaccounted`, as do all frozen 566 sources under independent complete material disposition. No Product Decision, private implementation details or unverified deployment claims entered the public Knowledge.
