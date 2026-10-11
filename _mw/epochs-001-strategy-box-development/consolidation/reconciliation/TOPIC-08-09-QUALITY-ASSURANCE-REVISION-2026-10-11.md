# Topic 08 versus Topic 09 — quality-provision revision and conformance frontier

**Working reconciliation:** Source original `SB-SRC-0055` (Whole-System Topic 09, blob `00e38a158a4538052930e677cce3e9aff449b026`) and subsequently available `SB-SRC-0047` (independent Trust/Safety/System Qualities Topic 08, blob `636c854e25bde15d380e757aa6e4762cf587b3b8`). Both are dated 2026-10-09 research, not formally admitted Product WHAT or a release conformance result.

## 1. What changed in the known research universe

The Topic 09 source [§12](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md#L896-L1006) states explicitly that its system-qualities block is **provisional** because Topic 08 did not belong to its own then-available source set; it records open Item **D41** as missing dedicated quality input. This statement is correct *for its historical research cutoff*. Treating D41 as a current missing document would be stale: the pinned main includes dedicated [Topic 08](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md).

**Disposition of D41 source gap:** `INPUT_RECOVERED_AND_READ`. **Disposition of whole-product security and acceptance:** `RESEARCH_CONSOLIDATED / PRODUCT_POLICY_UNADMITTED / IMPLEMENTATION_UNCERTIFIED`. Availability of a stronger research paper is not evidence that its proposed policy now runs in the installed product.

## 2. Cross-source qualitative reconciliation

| Topic 09 provisional claim | Topic 08 direct contribution | Result |
| --- | --- | --- |
| Epistemic, authority/effect and operational trust are different | Formalizes five separate truth axes: execution, physical effect, domain qualification, Work acceptance, environment/health | **REFINED**, no state collapse |
| Missing/unavailable FileStore must not become valid empty result | Pinpoints current LocalFileStore `listdir` absent/non-directory → `[]` and qualifies that not all errors are suppressed | **DIRECT CODE CONFIRMED**, scoped; see Current HOW |
| Unsafe copy/delete fallback and artifact publication need explicit effect proof | Adds destructive source protection, staged bytes→catalog publication and conditional backend atomicity checks | **REFINED TARGET CANDIDATES**, no generic distributed transaction claim |
| Retry/cancel/unknown effect need strict lifecycles | Splits effect receipts, idempotency scope, resource/worker leases, schedule occurrence, revalidation and fencing | **REFINED**; source negative fixtures explicit |
| Shared-node errors should be safely shown to affected participants | Adds audience/ACL filtered notification and event cursor; credentials/raw trace excluded | **REFINED**; closed-team versus public-Web profiles distinct |
| Version and deployment assurances must be explicit | Adds version-vector, clean wheel/package provenance and real backup/restore/fault verification | **REFINED**; no actual test run |
| Performance/accessibility are operational qualities | Adds resource classes, cancellation safe points, keyboard/contrast/reduced motion, tested localization semantics | **REFINED**; thresholds and platform tests remain OPEN |
| Preliminary security suite spans 15 cases | Dedicated Topic 08 provides **50 source-exact T/E/D/S/O invariant and negative-test pairs** plus **26 Decision/Gap records** | **EXPANDED EVIDENCE**, none passed or formally admitted |

The full 50 source-exact candidate rows are now carried in maintained [Science of System Qualities](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/science/trust-and-assurance/system-quality-assurance-threats-and-failure-gates.md) and addressable via `units/TOPIC08-EXACT-QUALITIES-50-0047.jsonl`. This matrix is an **explicit original-source inventory**, not a new mandatory product quality constitution without Product Authority.

## 3. A direct falsification: LocalFileStore

Frozen source [`LocalFileStore.listdir` L66–L70](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L66-L70) returns the same `[]` for absent path, wrong path kind and genuinely empty directory. Earlier quality studies correctly warn of false absence. But the same implementation's `stat` and directory iteration can raise: the stronger claim “every backend exception is silently suppressed” would be **false**. See [current pinned FileStore HOW](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/local-filestore-missingness-and-publication-limits.md). This is a specific observed state, not proof of actual alternate backend failure or release behavior.

The user's primary annotated intent permits manually moved/deleted generated files to be marked unavailable in chat. That valid minimal UX does not entitle a source calculation to read missing workspace inputs as an empty official publication. **Distinguish intended-use and effect risk.**

## 4. Collision with user-access profiles

The now-read ten-topic primary annotation describes two different future contexts: a small known shared team and public website access with a desire for simple setup. These are different threat models. A nickname-only local view can be suitable for a trusted small team, but a public Internet mutation surface needs authenticated principals and authority-side permission checks. The later Topic 08 is right to treat that stronger requirement as **conditional on enabling Web/remote exposure**. Product authority must choose profile and minimal mechanism rather than silently ignoring developer cost constraints or deploying a porous interface.

## 5. Independent verification and decision frontier

**Already checked:** both source studies primary-read, 50 exact source-row IDs and negative cases destination-matched, direct LocalFileStore implementation read, research state distinction preserved. **Not checked:** actual FileStore fault injection, real backend integration, Web auth/ACL session tests, clean AppDock runtime install, 26 decisions, SLO/RPO/RTO measurement, source-level complete material conservation or independent cold reader.

Relevant next tests: missing vs empty/wrong-type directory; hostile disabled-button API attempt; effect after ACK loss; two writers with one conflict resource; broadcast redaction of peer error; restore DB with missing Artifact bytes; source in-place revision; idempotency replay; clean install with provider/version drift. Each requires a declared profile, a real test fixture and a named owner.

**Disposition:** supersede *only* the “Topic 08 is missing from the source universe” claim; retain Topic 09's general system map and its historical provisional bridge, now refined by qualified Topic 08 evidence. Do not declare a chosen database, all-negative tests passed, or a final host/service architecture.
