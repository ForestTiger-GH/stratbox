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


## Additional source-first reconciliation: provenance, local execution and external activation (2026-10-12)

| Concern and exact observed owner | Candidate target and authority | Delta and required falsification | Scope |
| --- | --- | --- | --- |
| [Collector byte transport](../../../../docs/current-how/source-download-receipts-registry-choice-and-coverage-limits.md) records HTTP/source outcomes and size but no universal used-input SHA/time | Optional bounded per-input receipt at analytic core, then actually consumed input linkage | ADDED semantic evidence, **not** replacement of transport or global Source Catalog; negative PR-01/05/07/18 in [provenance LDD](../../../../docs/ldd/data/used-source-receipt-boundary.md) | Candidate local Python-core pilot; never claim existing implemented API |
| [OKVED data-only ordinary `read()`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) | Conditional coherent registry bundle when multiple components consumed | MODIFIED optional validation; **not** a missing 3-file invariant of current basic read | Only multi-component consumers that demand revision consistency |
| [Qt one-run coordinator and sequential callbacks](../../../../docs/current-how/windows-application.md) | Qt-free local application coordinator before considering cross-client host | SEPARATED presentation adapter from semantic Run state; [LS-01..LS-14](../../../../docs/ldd/application/local-scenario-orchestration-boundary.md) | Initial in-process portability, no durable host promise |
| [Windows exception messages and history](../../../../docs/current-how/windows-application.md) | Safe shared messages and observable corrupt-cache errors, conditional | CURRENT STATIC RISKS: raw exception messages, false aggregate success and case Artifact paths; specialized verification before product release | Existing Windows, implementation change authority outside Knowledge Work |
| [External RuntimeState hint](../../../../docs/current-how/windows-application.md) | Application-side durable Job authority **only if adopted** | EXISTING external continuity **not** proof of domain Job/effect durability; no implied remote API | Public pinned AppDock contract, only versioned scopes |

**Global readiness unchanged:** these are high-value bounded Current↔Target correspondences. The actual Product Commitment Census, production host scope, retention/access policy, authoritative source unit dispositions and independent verification remain missing; no roadmap or release may be inferred. 


## Accepted new host scope — typed Current ↔ Target delta (2026-10-12)

**Target product baseline changed:** [PD-SB-HOST-2026-10-12-01](../../../../docs/what/strategy-box/host-deployment-commitment.md) supersedes the earlier conditional host-existence field. The following delta is **current-source grounded and target-admitted**, but the full program's Current HOW, exact technology and migration still require further evidence.

| Identity / actual owner | Admitted target meaning | Typed change and transition constraint | Evidence limit |
| --- | --- | --- | --- |
| Qt coordinator, in-process scenario run and recent local JSON views at pinned Windows revision | Application host serves attached clients without projecting Qt local history as authoritative shared Job truth | `RE-OWNED / MODIFIED`: move authoritative shared admission and execution semantics to a host role, retain local UI adapter | No actual host exists in inspected code; no native runtime test |
| Current Windows AppDock managed foreground installation | Windows/AppDock installation may serve as host, while a separate Windows/AppDock installation connects | `ADDED DEPLOYMENT VARIANT`: host-capable vs connecting-client role, with one/two repo package choice explicitly open | Requires exact external platform contract and native two-installation test |
| No demonstrated Web-accessible Strategy Box service at pinned baseline | Host serves browser by site/domain, supported Windows and Android clients | `ADDED PRODUCT PROFILE`: authorized Web endpoint, reliable case/artifact projections | Host and Web runtime implementation absent from inspected baseline |
| Core Python analytics callable independent of Qt | Both host types consume same core operation semantics | `PRESERVED` and re-used; avoid copying domain methods into Windows or HTTP handlers | Core import tests still required for release |
| Client disconnect vs existing local foreground exit | Hosted work truth remains with active host, while local-only work may end with UI | `SPLIT LIFECYCLE`: do not infer cancel or success on remote client exit | Host crash/storage guarantees are separate open Decision |
| Platform node/session/runtime-state hint | Product-owned host Case/Job state and external platform-owned activation coexist | `AUTHORITY SEPARATION`: AppDock cannot become sole owner of domain effect truth | Platform feature availability version-bound |

**Specific next verification:** [HC-01..HC-16](../../../../docs/ldd/hosting/host-client-attachment-boundary.md). **Open**: protocol, host process and package organization, network/identity/authorization profiles, data retention, AppDock manifest, target delivery priority and actual migration ownership. This delta does **not** select two Windows repositories or assert an adopted server framework. Global Roadmap still `NOT_READY`.

## Host adoption: local-data provenance and authority cutover

The admitted host product direction introduces a **cross-authority migration boundary** rather than automatically invalidating local Windows data. Existing locally run Cases and per-event unread flags correspond to historical local evidence; future host Cases and per-principal read positions are distinct owner-scoped state. Retained local XLSX files may be referenced as unavailable until explicitly verified/ingested by an authorized host. An observed Windows path does not become a remote-client open command. This is `SPLIT / RE-OWNED / HISTORICAL-QUALIFICATION`, with user-consent, migration and data-retention Decisions still open. See [host LDD transition HC-17..22](../../../../docs/ldd/hosting/host-client-attachment-boundary.md). No code migration or historic data mutation has been executed.
