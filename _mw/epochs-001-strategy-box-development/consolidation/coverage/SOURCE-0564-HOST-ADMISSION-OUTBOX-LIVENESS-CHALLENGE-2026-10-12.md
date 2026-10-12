# Original-first Topic 12 — admission durability is not dispatch liveness

**Date / grade:** 2026-10-12, `PRODUCER_SCOPED_CODE_CONTRACT_FALSIFICATION`; **not** independent Research source-completeness, accepted host physical design, durable transactional proof or native fault injection. Frozen original: `SB-SRC-0564`, `stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97`, blob `2ceacde7d706a05251d5d1356002768f11038afb`, `_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/Strategy_Box_Topic_12_End_to_End_Work_Execution_Effects_Results_Research_2026-10-10.md` (892 lines). Existing scientific owner: `docs/science/work/evidence-based-work-lifecycle-and-closure.md`; actual host candidate: `docs/lcd/hosting/host-authority-and-client-contract-construction.md`.

## Source-driven distinctions

- The original §8.2 L391–407 separates validation, **durable physical effect intent**, backend response, verification, reconciliation and effect disposition. Durable intent is not the same as a returned scheduling callback.
- Original §8.3 L410–425 requires authoritative lookup or UNKNOWN when effect acknowledgment is lost, with explicit fencing for stale workers.
- Original §9.1 L415–427 distinguishes **Run admitted/executed**, actual external effect, analytic result, published Artifact and accepted Work: a Run row is not proof that any worker has started.
- Original §6 INV-01..18 L304–331 and §13 T01..30 L610–645 already have source-located representations in maintained Scientific Knowledge; those are research and verification intentions, not shipped host functionality.

## Concrete candidate hole and corrected contract

The candidate `HostAdmission.submit()` had already been repaired to classify a ledger ACK loss after possible durable admission as `OUTCOME_UNKNOWN`, preserving the original intention key and allowing `REPLAY(run_ref)`. Its fake test *demonstrated* the remaining liveness problem: `admit_atomically` could create accepted Run R, lose its ACK, and skip `scheduler.schedule(R)`. A replay returned R but did not schedule it. Good idempotency did not guarantee that accepted work was ever executable.

A **proposed** second-stage `DispatchClaim(dispatch_ref, run_ref, worker_ref, fence_epoch)` and `HostDispatchRecovery` now explicitly require a durable outbox row in the SAME atomic transaction as Run admission. A recovery poller claims pending dispatch and requests an idempotent Job reservation by stable `dispatch_ref`. `mark_dispatched` must be conditional on the claim's actual fencing generation; losing a downstream ACK must preserve `DISPATCH_UNKNOWN` until the original dispatch reference is reconciled. Dispatch confirmed is strictly weaker than worker started, effect completed, Artifact committed or Work accepted. Revocation and plan/target changes still require effect-time checks.

The Work probe `test_lcd_candidate_behavior.py::probe_host_dispatch_recovery` compiles and runs the *exact* `HostDispatchRecovery` candidate class from Markdown. It covers no pending, post-commit scheduler ACK loss then same-key deduplicated recovery, ledger outage, malicious/stale worker claim shape, boolean-as-epoch rejection, untyped truthy scheduler ACK, lost outbox acknowledgment after downstream reservation. Its fakes deliberately **assume** outbox atomicity, in-memory reclaimability and downstream dedup; actual SQL+queue+process recovery is NOT proven. This remains **ten** LCD documents with an additional separate behavior probe attached to existing Host packet; no invented new product module.

## Extra native SQL transaction/process-exit feasibility experiment

The subsequent `tools/test_native_sqlite_outbox_crash_characterization.py` tests a **real disposable SQLite database**, rather than the fake `DurableDispatchPort`. It requests WAL mode and `synchronous=FULL` in a Linux GitHub runner; a subprocess commits Run and outbox in one transaction and deliberately exits with `os._exit(17)` before returning to its caller. A fresh connection sees *both* records. A second subprocess exits **before COMMIT** with code 18: a fresh connection sees **neither** row. A conflicting outbox insert rolls back its entire Run transaction. A later process exits after a committed Job reservation; repeating the same `dispatch_ref` retains exactly one `jobs` row. A fake SQL claim-update increments the fencing generation so an older generation cannot mark dispatch done; a collision of the same dispatch key with a different logical Run or same intention with another Run also fails. **Eight distinct tests** passed at [Actions 38231399705](https://github.com/ForestTiger-GH/stratbox/actions/runs/38231399705), exact `stratbox@68fc9502afd9ea679d565ca468b6faec8ffaef14`, **SUCCESS**.

**Interpretation:** SQLite can serve as one illustrative **local transactional mechanism** satisfying part of the abstract outbox/idempotency invariant in this bounded environment. This test intentionally does not run the Strategy Box host, authenticate users, model asynchronous real worker leasing, prove physical file effects, force a true power-loss crash or decide the future DB/broker product architecture. In particular WAL/FULL semantics on one disposable Linux volume do not imply equivalent properties for Windows, network filesystems or remote orchestration. The actual service lifecycle still requires separate native/host integration and independent acceptance.

## Remaining stopping conditions

1. Test actual DB transaction write of Run+pending intent followed by forced process kill after commit but before response.
2. Test eventual scanner pickup and conflict-safe Job reservation after restart, replay and lease takeover using the same `dispatch_ref`.
3. Prove `schedule_once` does not enqueue duplicate Jobs even when it reserves work and loses ACK.
4. Prove actual fencing at worker claim and physical file effect; a stale worker must fail an irreversible mutation.
5. Re-evaluate grants, plan identity, target and source generation at actual effect time.
6. Record operator-visible stranded intent, quarantine and repair semantics when the selected backend lacks transactional outbox support.
7. Conduct a distinct independent Topic-12 source↔Science and Knowledge-only cold-consumer check. `SB-SRC-0564` remains `material_unit_state=unaccounted`.

This note is Work-only original provenance. Published docs carry a self-contained semantic explanation and concrete candidate logic without Work or private implementation links. No code in real analytical core, Windows, external platform or confidential extension was changed.
