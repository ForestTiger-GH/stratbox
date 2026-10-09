# Current ↔ Target correspondence — bounded candidate matrix

**Result ID:** `SB-DELTA-2026-10-09-CANDIDATE-1`.  
**Status:** CONDITIONAL, not an admitted global Current–Target delta or Roadmap-ready migration basis. The applicable comparison Work was intentionally **narrowed** because global Current HOW and Target WHAT/HOW are materially incomplete.  
**Current evidence:** core `8459dc58922b7e8df853cf1d9e8131fa9e132580`, Windows `959e9c4ce1441124af5111c1e025041714e04d3b`, external platform selected contracts `a4d87c643e620e54e04083d4d0b8d867513e7065`.  
**Knowledge input:** Current HOW modules from `0c5cd7695f68ca21464896292a38e537007a1ace`; candidate WHAT `TW-SB-2026-10-09-CANDIDATE-1`, candidate HOW `TH-SB-2026-10-09-CANDIDATE-1`, candidate architecture `PA-SB-2026-10-09-CANDIDATE-1`.  
**Consumer:** later Product Decision and change-impact analysis, not production migration execution.

| Stable concern | Direct CURRENT witness | Proposed target / status | Correspondence type and category | Transition obligation and gap |
| --- | --- | --- | --- | --- |
| Headless analytical core | `src/stratbox/base/runtime.py`, `macrobanks`; `docs/current-how/core-runtime-network.md` | Independent core / BOUNDARY_ACCEPTED | PRESERVED / Product-meaning boundary | Keep imports and domain behavior independent of frontend |
| Provider composition | `base/runtime.py`; process-level provider cache, generic interfaces | Versioned capability binding / CANDIDATE | MODIFIED / realization | Account current runtime default/fallback and test new binding without assuming environment behavior |
| HTTP source download | `base/net/http.py`, retries and `DownloadResult` | Source snapshot with provenance and differentiated failures / CANDIDATE | ADDED around PRESERVED helper / Product and realization | Preserve raw fetched bytes/URL provenance; policy for source revisions unresolved |
| Windows activation | `appdock/manifest.json` + `adapters/appdock/entry.py` | Same external managed boundary / BOUNDARY_ACCEPTED | PRESERVED / interface | Exact manifest/platform version conformance must be verified separately |
| Scenario execution | `application/scenarios/runner.py` sequential steps with fail-fast | `Run/Job/Attempt` and shared execution authority / CANDIDATE | SPLIT and POSSIBLY RE-OWNED / semantic and realization | Resolve case/Run identity migration and compatibility before shared profile, Q-01/Q-04 |
| Desktop runtime composition | `runtime/bootstrap.py` imports Qt coordinator | portable application orchestration / CANDIDATE | MODIFIED allocation | Isolate presentation toolkit; preserve concrete Windows functionality and proper owner |
| Runtime recent history | `application/history/persistence.py`, five JSON projections; silent empty after corrupt input | durable truth separate from projections / CANDIDATE | SPLIT / operational | Define exact data-retention/repair guarantees and orphan handling, Q-02 |
| Background status | `application/background/store.py` in-memory state | scheduler/worker with persistent occurrences / CANDIDATE | ADDED execution to PRESENTATION-ONLY CURRENT state | Do not claim current scheduler; decide scopes/trigger semantics, Q-04 |
| Artifacts | Windows runner emits file paths and records | manifest/verified publish and identity / CANDIDATE | MODIFIED + potentially RE-OWNED / operational | Protect existing bytes/references when migrating to catalog; Q-05 |
| Managed remote | Manifest specifies local foreground Windows | shared host/remote optional / CONDITIONAL | NEW VARIANT, not current absence defect | Bind published external contract Q-06 and secure managed profile |
| Android | current Qt windows only | companion/full mobile / CONDITIONAL | NEW VARIANT / Product scope undecided | No migration obligation before Product Decision Q-07 |
| Manifest smoke test | `tests/smoke/test_repository_contract.py` expects 3.0 `package_identity`, manifest has 4.0 `package_requirement` | release conformance property / CANDIDATE | CURRENT DEFECT, not a Product feature addition | Reconcile test with actual contract in separate implementation Commission |
| User authorization | current local runner/paths within sampled scope | authority-side per-effect checks / CANDIDATE | EVIDENCE GAP, not proven ABSENCE globally | Reconstruct complete current auth path and receive policy Q-03 |

## Cross-boundary constraints

- Source→result evidence identity must remain distinguishable through migration; a newer publication cannot silently overwrite an earlier proven observation.
- Persistence migrations are *data continuity decisions*, even when old API compatibility is intentionally absent.
- UI state and Job authority cannot be switched piecemeal for one shared write scope without fenced ownership and validation; however separate read-only interfaces can evolve independently.
- External host/provisioning and remote contract changes cannot be declared current solely from a conceptual AppDock description.

## Bidirectional bounded test

**Forward current→target:** all material entries from the selected two Current HOW modules appear above or remain outside the declared narrow comparison. There is no claim to full Current HOW inventory. **Reverse target→current:** each selected future property is labelled candidate/conditional and mapped to witness or declared as a new variant/evidence gap. `UNKNOWN CURRENT` has not been relabelled `REMOVED`.

**Readiness:** `ROADMAP_NOT_READY` for global migration because accepted complete WHAT/HOW, all-state/current mapping, authority, technical conformance and product risk policies are unresolved. This table is a review input for scoped discussions only.

**Reopen:** any selected source revision, accepted product decision, target design revision, new component/current-state evidence, changed external platform contract or corpus-level reconciliation.
