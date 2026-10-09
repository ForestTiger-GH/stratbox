# Execution control, parameter profiles and cancellation — source-unit extraction

**Original Research:** `SB-SRC-0026`, complete source L1–L2113, pinned blob `0cf37ddf3b0b44495a30ec1d31117fc9dfc70671` at `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`. **New provisional units:** 37, each with exact source span, semantic role and authority/disposition in `units/BASE-STUDY-0026.jsonl`. All source identities and original blobs remain stable. Only this source's census `read_state` moves to `full_read`; `material_unit_state=unaccounted` pending proof.

## Reconciled current facts versus future design

- Current Windows defines atomic and composed scenarios; the latter map a short scenario-level parameter set to domain-operation inputs. Case records include actor, state, steps, inputs and outputs, but this **does not prove** durable multi-client job truth.
- Its Qt-based coordinator permits one active scenario in the examined baseline. Merely having `cancelled` in a status vocabulary does not establish a working end-to-end cancellation token, interruption-safe core operation or correct handling of committed external effects.
- Current user form values persist by scenario; no demonstrated comprehensive per-field policy separates secret, remembered, shared, context-derived and effective launch-snapshot values. Parameter-profile richness is target Research.
- Local presence and JSON history do not establish live multiuser authorizations, remote subscription or transactional cross-user control.
- Portable semantics are plausible, but actual application bootstrap retains a concrete Qt coordinator dependency.

## Concepts requiring preservation

**Command versus computation:** a canonical domain Operation produces subject-level results; a control command submits, cancels or modifies work. **Scenario versus Case versus Attempt:** definition, user work item, and concrete execution/retry require different identities and recovery rules. **Parameters:** a mutable remembered profile differs from the effective, version-bound parameters for a specific run; cascade steps inherit via explicit mappings, not a blind union of internal settings.

**Cancellation and irreversible effects:** a cancellation request is not terminal cancellation, stop is not rollback, timeouts can leave side effects unknown, and a completed terminal outcome must not be overwritten by a racing late cancel. Queued cancellation, cooperative safe-point cancellation, after-step stop and forcibly terminated subprocesses have different guarantees. A generic Pause should remain outside initial scope absent real checkpointable operations.

**Shared work and permitted consumers:** a future shared execution authority would evaluate actor/scope, authorization, revision and resource conflict. Personal preferences and shared presets are different data classes. A permitted cognitive consumer is another limited caller, not a privileged owner or arbitrary Python execution authority.

## Alternatives, limits, and owner routing

- A full JobManager, universal command API, typed cancellation protocol, per-user preset profiles, shared node case ledger, Android/client projections and exact endpoint signatures are **Research candidates**, not admitted WHAT/HOW.
- An external managed environment's task cancellation, remote capabilities and lifecycle contracts require direct versioned upstream evidence and cannot be imputed to Strategy Box by analogy.
- Tests proposed for cancellation races, parameter migrations, secret-safe fields, multiuser races and permission denial were **not run**.
- The earlier proposed development sequence is historical reasoning, not a current approved Roadmap.

**Consumer routes:** preserved as a source→meaning Work ledger; qualified current mechanisms go to `docs/current-how/` when direct code supports them, source/uncertainty concepts to `docs/science/` only after evidence/assurance, and proposed promises to the Target WHAT/Decision owner. This does **not** certify global meaning conservation or Research Amputation.

**Next authorized source:** remaining base-study Research, with commands/scenarios/cascades and single-node state/authorization as a cohesive concern group, before broad 00–09 synthesis reconciliation.
