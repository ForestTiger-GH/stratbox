# Observability, results, logs and runtime diagnostics — bounded Research extraction

**Original:** `SB-SRC-0030`, full source L1–L2372, pinned blob `c4ec86841e2a92299adbefeb6a6a387b7106f587`. 38 provisional material units registered in `units/BASE-STUDY-0030.jsonl` with line ranges and scientific/target disposition. Master source remains `material_unit_state=unaccounted`; only verified full-read status changes.

## Directly observed current behavior

- `stratbox-windows/application/operations/execution/runner.py` blob `a01bf8d2aa63c3812e7620f42bd1367431782bd8` has an exception-to-text path, an operation-specific FileHandler and no explicit cooperative cancellation token in that module. Raw exception text can therefore reach a result/projection path unless filtered by subsequent boundaries.
- `runtime/logging.py` blob `f1bec8ee2c2b20a31daef5d1f3c44a871da31ff3` uses a FileHandler, with no verified rotation policy in the inspected module.
- `application/history/persistence.py` blob `95a48a89cc9c11e8a3adeedd7cb925d613c8692c` writes independent JSON projections; error-to-empty behavior can hide corruption from consumer-visible state.
- `application/background/store.py` blob `d431b461a39857ed032957f852a1c2e7ca3c7705` is an in-memory model of enabled/active statuses, **not** evidence of a scheduler or durable worker.

## Material distinctions and limits

A domain result, execution lifecycle, retry attempt, technical log, physical incident, problem occurrence, shared condition and user notification are distinct. Uncertain effects after timeout or process crash cannot be collapsed into a confirmed failure; the source suggests separate `UNKNOWN` and reconciliation semantics. Technical exception text and unrestricted case parameters may contain sensitive data, so an audience-safe error boundary must be designed before any multiuser sharing.

An affected shared resource may justify a scoped, deduplicated notice to other authorized users; an individual's invalid parameters do not. Observability subsystem failures (unavailable log sink, uncertain problem registration, blocked mandatory audit) require independent state rather than fabricated references or a false success flag.

**Target admission remains open:** Case/Job/OperationRun/Attempt identity chain, frontend-neutral job manager, logging retention and rotation, transactional history, external problem bridge, safe agent/delegated actions, remote execution, Android projections, cancellation and numeric SLOs are **research proposals**, even where earlier external platform studies describe potential contracts. External versioned interfaces must be checked with their owner before any claim of real-time support.

**Alternatives and negative results:** logs cannot replace durable job state; a new independent incident-management or central Log Manager is not a prerequisite; duplicate broadcasting increases privacy risk; a UI-level cancel control cannot undo an external effect; read-only diagnostics and authorized repair must remain distinct.

**Assurance:** complete reading and typed source-unit extraction established. Tests, remote execution, signal recording, incident handling and independent public-safety review **not performed**. Next original source: background processes and scheduling `SB-SRC-0018` or execution/control study `SB-SRC-0026`.
