# Proportional assurance, engineering knowledge and product admission

**Domain:** how an analytical product preserves distinct engineering-object, work and knowledge truths, applies a broader engineering method at the appropriate scope, and turns research into evidence-grounded implementation decisions. **Status:** bounded methodological Science, not an independent conformance certificate, Product Decision, current executable requirement or new MADAR standard. **Exact comparative baseline:** `stratbox@95b9ab36990e0ab1dea59d473f6de2fa005c2c25`, `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`, MADAR `spec/@7029b47676659161d9f54b4def8f0c1aa979b614`.

## 1. Truth before method compliance scores

The published Strategy Box research compared a real analytical Python library, a local Qt-based application, and a separate managed deployment platform with the then-effective MADAR engineering specification. Its central finding is **partial alignment of architecture and epistemic discipline, but unverified whole-product execution/decision integrity**. This is a qualified comparative assessment, not proof of passing a standardized assurance framework.

The exact MADAR source used was [`spec/manifest.yaml`](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/manifest.yaml), `version: 1.0.0-dev`, with Editor's Draft status; the contemporary Stage 3 A1–A8/B1–B9 materials were **non-normative Development Inputs**, not an already adopted successor. Product research references to a future three-part EOM/EWM/EKM methodology therefore cannot be treated as requirements automatically binding Strategy Box.

Useful evidence categories, without false aggregation:
- **Confirmed scoped alignment:** an exact behavior implements a particular applicable principle in the examined code/boundary.
- **Partial:** some relevant machinery exists, but necessary scope, transition or proof is absent.
- **Observed conflict:** a current applicable behavior contradicts a stated contract or recovery property.
- **Gap:** a mechanism needed for a selected goal is missing; a future optional feature may be *not applicable* instead.
- **Insufficient evidence:** a claim could be true or false but lacks the necessary test or direct contract proof.
- **Not applicable now:** a multi-host/agent/mobile invariant applies only if that profile actually ships.

These classes are **not percentages**. Forty-four classified comparative observations from the source study (described in §6) do not mean 44 independent full MADAR compliance tests. A matrix entry derived from the same source code as another is not independent empirical confirmation.

## 2. EOM — the product, its investigated external subjects, and its owners

Strategy Box as an engineering object is the **product that turns external financial and macroeconomic publications into interpretable analytics and user-visible work**. Its current implementation has at least two distinct source owners: [domain core](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox) and [Windows application](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). The managed external platform supplies installation/activation/Node/Session capabilities under its own contracts, rather than being a Strategy Box analytical subsystem.

Banking organizations, the Russian financial system, official data publishers and statistical observations are **subjects of analysis**. Modeling them does not grant the product power to change their institutional state or certify the external world as absolutely correct. Distinct truths must be attributed explicitly:

| Truth | Representative statement | Who may substantiate it |
| --- | --- | --- |
| **Source/publisher** | These bytes were retrieved through a particular route at a particular time | Publisher evidence plus actual acquisition receipt |
| **Domain meaning** | This statistic has a unit, period, reporting perimeter and formula | Domain code and method/source expert |
| **Release/package** | A specific core and Windows binary/dependency graph was installed | Versioned distribution/install records |
| **Environment/runtime** | Node and process were ready or degraded | Deployment/platform owner |
| **Application execution/effect** | This Run was admitted and a file operation succeeded or remained uncertain | Application authority, worker/backend receipts |
| **Evidence/claim** | A mathematical conclusion is justified under these assumptions | Domain proof/check with a qualified claim |
| **Authority/acceptance** | An authorized user permitted an action or accepted a result | Policy owner and appropriately verified actor |

The decomposition is by **semantic identity, mutable owner and change boundary**, not simply a map of repositories. A single computer may house all scopes physically; separate monitors and independent verification can legitimately coexist with one canonical writer for a particular shared mutation. “One owner” should not be exaggerated to one database or one decision maker for everything.

The observed [Windows `runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) imports a Qt-specific scenario coordinator, weakening the proposed headless seam. It is a direct, dated implementation observation, not evidence of an already working host. Details in [semantic ownership](../architecture/semantic-ownership-and-contract-boundaries.md) and [portability](../surfaces/semantic-portability-and-client-authority.md).

## 3. EWM — accountable work is not a worker's final boolean

At the studied baseline, Windows has **three operation specs**, automatically produced atomic scenarios and a composed sequential scenario; background/assignment and actor concepts exist in varying degrees, but a durable multiuser JobManager, true cooperative cancellation and host service are not confirmed. These are real partial achievements with gaps, rather than “no application.”

A robust *managed* activity separates commissioned intent/criteria → Work → selected domain capability/Scenario → immutable Run plan → the actual Job/Attempt → effect and result receipts → assessment → acceptance/rejection → closure/residual obligations. A direct Python notebook may reasonably use `Request→Result` without any Work service. Physical entities should be introduced only when separate identity, lifecycle, author, control, rights or consumer justifies them.

High-value semantic prohibitions:
- Scenario definition is not a particular Run; the same scenario can run twice with different evidence.
- A Case card is not automatically independent long-lived Work authority.
- Requested cancellation does not prove the process stopped or an external write was prevented.
- Worker completion does not prove bytes committed; published bytes do not prove economic validity; user acceptance is yet another assertion.
- Timeout after potential file/network effect implies `UNKNOWN` until reconciliation, not “no effect.”
- A valid Work may conclude “hypothesis unsupported,” “insufficient evidence” or “safely blocked” where those outcomes meet the original acceptance criteria.
- Background, manual, machine and future agent launches are initiators/execution modes, not competing sources of job truth.

**Durable accounting / disposable computation / safe effects** is a restrained research preference. It preserves accepted Work and meaningful effects while allowing an interrupted foreground worker to be stopped and later investigated or rerun; a full Temporal-style automatic replay engine is not required by a simple desktop use case. For complex effects, direct evidence and risk-sensitive acceptance remain essential. See [Work/closure Science](../work/evidence-based-work-lifecycle-and-closure.md).

## 4. EKM — source representation, statistical knowledge and strength of reliance

One core strength is the specialized SORS reconstruction evidence model. Its treatment of **published rounded quantity vs latent feasible interval, exact bounds, assumptions, proof/solver rounds, conflicts and tiers** demonstrates that a value can be computed while the strength of its claim remains limited. At the pinned [SORS evidence model](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration/evidence.py), statuses `STRICT_OFFICIAL`, `SOURCE_PRESERVING`, `ROUNDING_OPTIMAL`, `ROUNDING_PREFERRED`, `ROUNDING_SELECTED` have materially different epistemic meaning. Publishing `ROUNDING_SELECTED` to XLSX does not promote it into an official fact. See [statistical evidence and rounding](../data-and-knowledge/publication-rounding-and-claim-strength.md).

A reusable lighter lineage for simpler domains is:
```text
External publication
  → actual acquisition time + byte identity / source snapshot
  → parsed observation (units, time, scope, blank versus zero)
  → registry/method vintage and transform
  → qualified result (coverage, missing, assumptions, failures)
  → materialized artifact with provenance
  → authorized expert reliance / acceptance with stated limits
```
For a raw file collector, a timestamp, source/locator, checksum where applicable, validation and resulting file are valuable. Importing SORS solver/proof structures into every parser would be an unjustified maintenance burden.

These distinctions protect against hidden errors: authentic published data can later be revised; canonical representation does not prove external truth; equal numbers from different bank/group perimeters are not automatically comparable; checksum proves byte identity rather than policy sufficiency; a green test does not authorize a business decision; no finding does not prove no defect without a scoped search method and adequate coverage.

An important late human-intent refinement **limits earlier global Source Catalog proposals**: actual time of fetch for used inputs is central, byte digest helps detect revision at the same URL, `method_ref` can be a light link when the method exists, and indiscriminate registration/monitoring of every statistical series is excessive. This is **scoping and proportionality**, not an invitation to discard evidence of consequential calculations. See [source vintages/replay](../data-and-knowledge/source-observation-vintages-and-replay.md).

## 5. Engineering Knowledge and Product admission are different artifacts

The maintenance system must distinguish:
1. original Research and historical notes (sources of hypotheses, rejected approaches and dated evidence);
2. thematic Science (qualified explanations with direct grounds, negative cases and reopening rules);
3. Current HOW (what a pinned implementation currently does, evidence-limited);
4. Target WHAT (accepted requirements versus unapproved options);
5. Target HOW, Architecture and LDD (implementation candidates and precise conditions);
6. Product Decisions (a competent authority's actual choice, alternatives and impacts);
7. executable tests and deployment evidence (specific property of a specific build/profile).

Saving all research files and compiling a topic summary does **not** demonstrate lossless knowledge preservation. For every source claim, an independently checkable destination and qualification are necessary, and Science must support a reader who lacks the old research folder. Reverse mapping from Science claims to real code/publications must also be tested. As of the source comparison, source census coverage was already acknowledged as incomplete; the same remains true until independent source-level disposition is verified.

The desired workflow is *source identification → bounded analysis → semantic reconciliation → candidate and contradiction preservation → Product/Decision-owner admission if required → implement/test in accepted scope → refreshed Science and downstream docs*. Copying a research figure, candidate API, MADAR rule ID or Stage3 ontology into public product specifications cannot skip any of these distinct operations. The no-backward-compatibility preference permits retiring obsolete code paths but **does not justify deleting valuable user history without verified one-time migration or an explicit scope decision**.

**Avoid method replication.** MADAR governs its own engineering method; Strategy Box applies appropriate decisions and checks without embedding an all-purpose MADAR Rules database, global scoring/waiver engine or EOM/EWM/EKM namespace into ordinary product runtime classes. The methodological role is to challenge the product's actual evidence and governance, not become a mandatory toolkit dependency.

## 6. What the source's 44-row alignment matrix really says

The source compares four evidence clusters. Reproducing the 44 verdicts as a single “compliance percent” would destroy their epistemic meaning. Their analytical dispositions by area are:

| Area and source row IDs | Bounded direct/current strengths | Conflicts / gaps / nonapplicable cases |
| --- | --- | --- |
| **Engineering object, ownership, requirements and architecture (01–10)** | Core/application/external responsibilities are explicitly separated; several IDs and historical/Research statuses are recorded; repository ownership clear | Headless application, full current Truth geometry and complete Knowledge admission lacking; Qt bootstrap coupling; Scope-specific acceptance incomplete; prior future extension claims require real consumers |
| **Statistical meaning, lineage, evidence and source freshness (11–20)** | Canonical IndicatorId, explicit missing/zero distinctions in domains, SORS mathematical proof tiers, packaged source resources, Research safety limits | Incomplete cross-domain source snapshot→Run→artifact lineage; mtime isn't publisher revision; old “current” data may be stale; no-finding/negative evidence needs coverage; many numeric comparisons lack measured comparability |
| **Work, effects, permissions and multiuser collaboration (21–32)** | Local Case/Scenario/Step and FRG plan/apply, typed exceptions, visible background/presence scaffolds | Silent history corruption is a **direct recovery conflict**; cancelled state is not verified stop; loss of ACK lacks UNKNOWN; general effect-aware retry untested; AI actor labels not grants; remote host requirements currently not applicable; an enabled background toggle would mislead if rendered as active service |
| **Release, quality, operation, human attention and evolution (33–44)** | Installed profile boundaries, local degraded mode, multiple domain tests, selected diagnostic paths and explicit partial docs | **Exact version drift** core `0.8.0` vs Windows/manifests `0.2.1`; end-to-end clean install CI unknown; SORS tests not cross-surface recovery; insufficient end-user and target-device benchmarking; Web/Android/AI conformance not applicable to unshipped profiles; methodological cost unmeasured |

The original's labels map to: confirmed scoped correspondence, partial correspondence, directly contradicted applicable behavior, gap in selected contract, insufficient evidence, and presently not applicable. **“Not applicable” is not a defect**. In the source baseline, selected Windows errors could appear in this table as direct architectural contradictions only when a real current claim of correctness exists; future host absence alone is not current failure. The grouping above preserves 44 source row identities while collapsing repeated causal mechanisms into coherent scientific domains.

Representative original anchors: [MADAR constitution](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/core/01-constitution-method-semantics.md), [state/data/execution](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/core/05-state-data-time-execution.md), [verification/assurance](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/core/10-verification-validation-testing-assurance.md), [applicability/conformance](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/core/14-applicability-profiles-conformance-adoption.md). Links identify the historical comparison baseline and do not certify this article against the latest evolving MADAR main.

## 7. Key competing proposals and disciplined resolution

| Tension | Defensible finding | Decision still needed |
| --- | --- | --- |
| Full ontology now vs few useful roles | Semantic roles are distinct; physical classes/servers should be justified by separate lifecycle, actor or consumer | Minimal capability/Work contracts |
| Everything through host vs direct Python | Host authority is valuable for shared execution, not prerequisite for notebook parsing | Managed profiles and release scope |
| SQLite-first vs atomic file/journal first | Verified guarantees and single writer matter more than named storage technology | Actual storage profile, RPO/RTO, provider readiness |
| A green operation vs committed effect | Result, effect, file generation, acceptance each need their own grounds | Output and review criteria |
| Deep SORS evidence vs global full data governance | Risk-graded evidence and used-input provenance preserve quality at bounded cost | Domain risk classes and retention |
| Everybody sees chats vs confidential logs | Safe collaboration can coexist with object-level grants and restricted evidence | Actual team visibility policy |
| AI as actor vs AI as authority | Machine consumers need explicit delegation/permission, not implied admin status | Authorized machine capability list |
| Independent component checks vs system integrity | Narrow unit tests do not prove source→Run→published artifact across failure windows | An actual negative end-to-end vertical test |
| No backward API compatibility vs data migration | Old behavior can be retired; valuable data needs migration/read-back or explicit user-informed disposition | Migration scope and destructive cleanup |
| Apply MADAR vs copy its entirety | Engineering decisions remain Strategy Box's, methodology remains its owner's | Approved local conformance and tailoring policy |

The strongest counterexample is compositional: domain SORS tests can be correct while Windows corrupt history on crash; Windows manifest smoke can pass while a statistical source revision changes meaning; platform health can be green while the analyst rejects a result. Neither independent green status produces a global validated Work.

## 8. Risk, applicability and human feasibility

The comparison identifies five distinct application profiles:

| Profile | Applicable critical concerns | Premature obligations |
| --- | --- | --- |
| **Direct Python/Colab** | Typed domain semantics, source/byte provenance, errors, caller-controlled FileStore | Shared Work DB, GUI ACL, remote JobManager |
| **Local managed Windows** | Package resolution, activation, truthful Case/Run, effect safety, artifact publication, local recovery and diagnostics | Distributed consensus/HA fleet and elaborate IAM |
| **Future shared node/Web/Android** | One application authority, real principal, ACL, concurrency, session state, host storage, honest stale/unknown effects | A second independent workflow engine without demonstrated need |
| **Future permissioned machine/AI** | Governed discovery, delegated authority, prompt/source trust boundary, bounded effects and review | Open shell permissions or unconstrained agent graph |
| **High-impact mathematical model (SORS)** | Method-specific uncertainty, bounds, proof IDs, source vintage and stronger checks | Forcing the same solver apparatus on a raw CSV downloader |

Assurance effort should follow **consequence, uncertainty, blast radius, reversibility, freshness, fault recovery difficulty, user attention and external duty**, not repository name or how many rules appear in a checklist. Independent checks may be highly valuable for a destructive file action but heavy formal artifacts can obstruct a low-risk read-only calculation. In the absence of measured target hardware capacity, no numeric resource/SLO guarantees are established.

## 9. Verification traces: present status is PROPOSED, not PASSED

The source proposes twelve highly discriminating traces: same URL with new bytes; rounded statistical measurement without false precision; interrupted file publication; corrupt local JSON history; timeout after an effect; cancel during commit; exact core/Windows/manifest version conflict; revoked grant at delete boundary; background enabled without scheduler; incomparable economic perimeters; client disconnect during hosted Job; and a small local execution that correctly works without a global broker/ontology.

A verified pilot should contrast two classes: a **direct source→domain→artifact** run and a **fault-injected partial/unknown effect** run. At a minimum, preserve exact receipts for `observed_at`, meaningful source byte/version, domain validation, state admission, publication, displayed status and user acceptance. Tests should record actually observed outputs, scope and environment rather than tick boxes because an expected event appears in a design diagram.

The source's recommended sequence (not authorized roadmap): align package/manifest/test versions, fix false success/artifact publication, make local history corruption visible, avoid background toggle implying a worker, then instrument a single collector or escrow end-to-end slice. Only introduce remote host, AI bridges, global source catalog, full event sourcing or graph stores after a genuine consumer and evidence justify their complexity.

**Gaps pending:** actual installed Windows/host trials; full source-vintage verification across domains; multiuser and agent authorization; Windows crash/power loss; alternative file/SQLite recovery and benchmarking; user acceptance workflows; independent MADAR applicability/adoption and contemporary source freshness checks.

## 10. Open engineering decisions and reopening conditions

Still unresolved are exact Work vs one-off Run identity, durable state promises and RPO/RTO, classes of irreversible file operations, foreground vs background lifetime, first Web/Android release obligations, real target workloads, who authorizes economic reliance and acceptance, effective AI delegation, local adoption of MADAR spec clauses and economic utility of methodology tooling. A new review is triggered by an approved product profile, actual changed core/Windows/platform source, a damaging lost-data incident, measured resource constraints, a newly accepted MADAR normative revision, or a falsifying end-to-end test.

**Research-to-Science assurance limit:** this topic is readable without MADAR Stage 3 research history for its bounded distinctions, but the complete Strategy Box corpus cannot yet be declared lossless. The 44-row comparator is a *dated expert crosswalk*, not a set of independent production certifications.

## Original Windows source study 0020: evidence strength, release identity and repository hygiene

**Provenance:** [original pinned Windows study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`, cross-checked against the unchanged public Windows source revision `959e9c4ce1441124af5111c1e025041714e04d3b`. Dated implementation descriptions, research recommendations, static source conflicts and real executed tests retain different evidence force. These addresses are historical Research meaning, not automatic Product Decisions.

| Address and role | Original material meaning | Defeater / countercase | Exact lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/TEST-01` · `HISTORICAL_TEST_GAP` | The original listed ten Windows test files and warned that core runner, history and GUI behavior had little executable test coverage. | Current knowledge CI now tests nine original source behavior cases, but Windows repo's own native release suite is still unverified. | [L1124–1151](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1124-L1151) |
| `SB-SRC-0020/CONTRACT-01` · `DIRECT_STATIC_CONFLICT` | The original found checked-in Manifest 4.0 and package_requirement conflicting with smoke expectations Manifest 3.0 and package_identity; independent activation/context revisions complicate interpretation. | A contradictory assertion is not an actually executed complete Windows pytest failure or a deployed integration result. | [L1152–1190](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1152-L1190) |
| `SB-SRC-0020/HYGIENE-01` · `DIRECT_GIT_TREE_CORROBORATED` | The original identified generated runtime-state and bytecode tracked in Git as repository source-quality issues. | Presence of tracked development files does not permit examination or reproduction of their contents. | [L1196–1225](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1196-L1225) |
| `SB-SRC-0020/HISTORY-01` · `BOUND_HISTORY_WARNING` | Two SORS-named commit messages did not correspond to source changes implementing a Windows SORS feature in the pinned Git tree. | Commit messages are not feature evidence; a missing Windows source path does not prove nonexistence outside the examined repository. | [L1227–1240](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1227-L1240) |
| `SB-SRC-0020/VERSION-01` · `EXECUTED_CURRENT_SOURCE_WITNESS` | Original research warned that VersionInfo obtains provenance from local Git and may return unknown in a materialized non-checkout installation. | Real version helper returns unknown in a Git-free temporary directory; this is not installed package provenance. | [L1368–1372](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1368-L1372) |

**Qualified conclusion:** commit subjects, file inventory, Manifest declaration, smoke assertions and installed-process evidence are distinct. A missing Git metadata directory gives a truthfully unknown local revision, not a verified release fingerprint. Existing model shapes and automated source characterization do not prove a native Windows or hosted release.

**Scope boundary:** this nine-row producer slice does not exhaust 1,741 physical original lines. The file's whole-source state is `unaccounted`; no independent Science conservation or Research Amputation has been performed.

## Original Windows Study 0020: proposed client, artifact and collaboration maturity (source packet B)

**Source:** [frozen 2026-10-06 Windows study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), exact blob `225128f2599f0792422c0b31cb3cbe1437991ced`; a dated future-option/release-maturity study, **not** binding architecture, accepted permission semantics or an executed host. Each row retains a competing disconfirming case.

| Address · epistemic role | Original material proposal or observation | Counterexample / limit | Original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/FUT-09` · `DATED_IMPLEMENTATION_MATURITY_MATRIX` | The study separated realized local desktop operations, local JSON preferences and AppDock activation from only-scaffold Background, presence, AI, cancellation, remote and Android features. | Its matrix is historical, not a delivery certificate at a future commit; exact direct code and native tests govern any current implementation claim. | [L1642–L1668](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1642-L1668) |

**Evidence status:** a future AI actor label, mobile sketch, host execution backend or artifact field list cannot establish the relevant implementation or rights. This packet is a **producer source transfer**; independent review, complete source accounting and host/client release tests remain open. All frozen source dispositions are still `unaccounted`.

## Original automation Research 0041 — dated roadmap, logical architecture and example machine endpoints

**Frozen source:** [primary automation/AI study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. These are historical engineering alternatives with explicitly limited authority. A phase number, API-like name or deployment box in the original document is not evidence of an actual provider, Product Decision, accepted schedule or real effect.

| Material address and epistemic role | Source-defined proposition | Defeater, cost, competing choice | Primary lines |
| --- | --- | --- | --- |
| `SB-SRC-0041/ROAD-09` · `HISTORICAL_PRIORITY_RELATIVE_RANKING` | The P0–P3 table grouped core contracts and durable execution before scheduler/router, full agents/remote mobile, then multi-agent/complex DSL. | Priority labels were author recommendations, not risk-economics proof or an authorized current product-release sequence; host necessity was subsequently accepted. | [L2118–L2150](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2118-L2150) |

**Conservation limit:** this is a producer source-first packet; independent reverse review, empirical release tests and whole-original material accounting remain open. The current accepted Strategy Box host requirement supersedes only conflicting historical ownership/timing assumptions, not the original's record as a real alternative.
