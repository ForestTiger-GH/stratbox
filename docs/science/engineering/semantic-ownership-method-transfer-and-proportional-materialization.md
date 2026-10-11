# Semantic ownership, method transfer and proportional materialization

**Scientific question:** how can a bank/macro analytical product use broad engineering methodology without mistaking methodology categories for runtime packages, turning every useful distinction into a database entity, or allowing a calculator or UI to become the authority for decisions and knowledge? **Status:** source-qualified study of alternatives rather than an accepted semantic schema, new package topology or commitment to use a particular methodology at runtime. Primary original research: [target epistemic architecture](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md) and [semantic product decomposition](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md). Their 2026-10-07 references to the then-current MADAR Stage 3 wave and six specialist repositories are **dated input observations**, not certification of present external repository completeness or of new binding rules.

## 1. A product spans several methods without becoming any one of them

A typical analyst asks the system to identify two banks, retrieve official reports, resolve IFRS/RAS perimeter and period, compare indicators, explain a change, export a table and perhaps recommend a decision. This single product experience draws on object identity, Work, evidence, measurements, transformations, evaluation, communication and possibly strategy. No one method can own the entire process.

The main architectural distinction is between **semantic responsibility** and **physical implementation**. A source-retrieval Python package may implement part of an information/observation method; a Windows view may depict current Work state; a scheduled worker may implement part of execution. None thereby becomes the authority that owns all Research knowledge, all decisions or an engineering constitution. Conversely, a shared semantic responsibility may be realized by source code, a managed service, files, a DB and rendered UI projections.

The source research explicitly rejects copying a methodology directory taxonomy into the product:
```text
EOM-like object identity != an eom/ Python package requirement
Work semantics       != a Qt Case card
Knowledge semantics  != the latest spreadsheet
Method templates     != arbitrary scripts
Design               != a design/ microservice
Activity             != everything a scheduled operation does
```

The right ordering for a material new type is: problem and consumer → independent object identity/lifecycle? → semantic owner → relation and failure semantics → evidence/assurance need → only then storage representation and API.

## 2. Four simultaneous orders must not be collapsed

| Order | Basic question | Failure from treating another order as its proxy |
| --- | --- | --- |
| Domain/object | What subjects, datasets, models and resources exist, with what identity and state? | A filename or memory address becomes bank/group identity |
| Work/obligation | What was commissioned, attempted, owed, accepted, left unresolved, handed over or reopened? | A completed Job closes a material analytical obligation |
| Knowledge/evidence | What can be claimed, on what grounds, under what uncertainty and for which reliance? | A successful parser “proves” an economic claim |
| Authority/decision | Who is permitted to decide, publish, commit or change a protected object? | A model recommendation or participant presence becomes approval |

They interact through typed relations, not by inheriting all of one other's fields. Object status, Work status, Job/Attempt outcome, acceptance, currentness and Node health have different clocks and owners. A single success Boolean creates precisely the misleading collapse that a disciplined analytical system should prevent.

A robust sample state is: Job execution finished; external effect outcome unknown; Excel staged; analytic result qualified but not accepted; new source vintage detected; user approval pending. This is not one `FAILED` or `SUCCESS`.

## 3. Material identity matters more than vocabulary

A product may use “Scenario” for a user-friendly catalog entry, “Case” for a visible execution card, “Work” for an accountable obligation, “Run” for one accepted plan execution and “Job” for a schedulable unit. The names are optional. Their **semantic invariants and lifecycle differences** are not optional when users require durable work, evidence and effects.

Similarly, a claimed bank entity needs to distinguish licensed institution, issuer, brand, banking group and consolidated financial group when a ratio or exposure depends on the reporting perimeter. A time-series row may reference original observation, normalization, estimate, reconstruction or forecast; the semantic family and source vintage matter more than Excel cell type.

Useful relation classes include `uses-vintage`, `derived-from`, `supports-claim`, `contradicts`, `accepted-for`, `supersedes`, `proposed-by`, `authorized-by`, `published-as`, `reported-by` and `revalidated-under`. They are **not generally transitive**. Deriving C from B, which was derived from A, gives lineage but not equivalence of economic meaning. Several citations to the same publication do not create independent evidence.

A source may be authoritative for what it officially **published** while being insufficient to establish a causal mechanism or a current decision. Keeping this distinction explicit is more important than building an expensive graph database.

## 4. The activity portfolio and its limits

The research maps several professional activity methods to product needs:

| Activity | Potential Strategy Box functionality | Crucial limit |
| --- | --- | --- |
| Framing / Inquiry | Refine subject, question, scope, source universe and desired reliance | An inquiry may end honestly with unknown/negative findings |
| Analysis | Compare, normalize/reconcile, decompose, investigate explanations | Common label ≠ comparable construct; decomposition ≠ cause |
| Forecasting | Versioned forecast candidates/vintages, scenario and stress conditions | Forecast ≠ target, scenario, plan or adopted policy |
| Evaluation / Challenge | Evaluate an exact Result/version and actively seek counterevidence | Passed check ≠ acceptance; challenge finding ≠ established defect |
| Communication | Produce faithful text/tables/charts/Excel and verify intended consumer understanding | Delivery ≠ understanding, acceptance or commitment |
| Strategy/Decision support | Link alternatives, objectives, protected interests, uncertainty and recommended options | Recommendation ≠ authorized Decision; realized outcome ≠ ex-ante quality |
| Operation/Learning | Repeat source check, run deterministic transform, maintain currentness and improve capability | A log or one successful execution ≠ admitted product knowledge |

This is a map of useful **semantics** and possible future capabilities, not evidence that current code already implements all the activities. A statistical library need not become a general strategy decision platform merely because methodology describes a Decision object.

## 5. Proportionality: the answer is not maximal metadata

The strongest counterargument to a large epistemic design is its cost. Every extra class, schema, persisted relation, user field and approval prompt adds compatibility, migration, performance, attention and maintenance burden.

A small read-only transformation may need a qualified input source, unit, function revision and output. An SORS reconstruction from rounded official observations may need latent variables, evidence tier, optimizer, conflicts and audit trail. A high-consequence multi-bank recommendation may need versioned perimeter bridges, forecasts, assumptions, independent challenge and a human Decision record. These cases justify different assurance envelopes.

**Materialization test for a Claim/Assumption/Defeater/Decision/Acceptance object:**
- Is it separately cited or updated?
- Does its authority or lifecycle differ from the parent Result?
- Can distinct consumers accept/challenge/reuse it independently?
- Would losing the distinction change a permitted action, interpretation or reliance?
- Must the product recover it after restart, handoff or revision?

If not, the distinction can be represented as typed structured context within a simpler owner. The goal is **sufficient qualified truth at acceptable whole-system cost**, not maximum noun count.

## 6. Engineering mistakes that a method-aligned product must prevent

| Mistake | Why it is attractive | What must be preserved instead |
| --- | --- | --- |
| Universal ontology before real consumer | Promises future-proof reuse | Narrow meaningful domain contracts and explicit open applicability |
| Graph database as proof of reasoning | Relations look rigorous | Typed valid inference bridges and independent evidence |
| One `latest` view | Simple, fast UX | Historical identity versus current applicability and intended-use reliance |
| Research text as current product contract | Rich explanation already exists | Separate admitted WHAT/HOW/owner; study may remain an unresolved hypothesis |
| Generated file as Result | Easy to send and preview | Semantic answer, producer/vintage, verified bytes, publication and approval state |
| Multiple AI reviewers as independent evaluation | Seems like consensus | Causally independent sources/methods plus explicit criteria |
| Background “refresh all” | Operationally simple | Affected dependency impact; revalidate only material changes |
| Technical exceptions as authoritative diagnosis | Traceback appears exact | Qualified observed failure, correlation and root-cause investigation |
| UI adaptation as objective user preference | Response behavior seems measurable | Distinguish expressed preference from intervention-induced behavior |
| Capability as permission | Tool exists and executes | Principal/object/effect authorization plus challengeable receipt |

These are candidates for architecture/assurance regression tests, not a statement that the current app has failed every one.

## 7. Recovery, currentness and knowledge admission

Durable recovery requires the accountable position, not the previous executor's full transcript: commissioned question, known input vintages, last confirmed effects, work/plan revision, available Artifacts, open problems, valid decisions, approvals and next permitted actions. A fresh actor should be able to continue without trusting stale chat summaries or repeating uncertain destructive operations.

Knowledge maintenance must distinguish *historically established* from *safe to rely on now*. On changed source/registry/model, find dependent Results, determine whether their meaning changed, then mark possible staleness, request revalidation or create successor Work as appropriate. Overwriting the only old Excel destroys the ex-ante information state and can create false retrospective precision.

A new research conclusion does not become current Knowledge simply because it is neatly written; reconcile independent origins, opposing grounds, actual evidence, lifecycle and remaining unknowns, then have an accountable current owner adopt or bound it. Equally, a generated optimization script is not automatically an admitted capability without versioned tests/effect review. These are distinct learning/admission paths.

## 8. Practical domain tests

1. Compare bank and group under a shared short label: require a perimeter bridge or return qualified noncomparability.
2. Reprocess a 2024 forecast using information released in 2026: preserve the original ex-ante vintage and label hindsight recomputation.
3. Normalize a series with an updated classification: preserve original published values and record changed mappings.
4. Explain a decomposed ratio's change: distinguish accounting contribution from causal hypothesis.
5. Complete a Research Work with no admissible finding: allow qualified closure with explicit residual questions.
6. Issue a report with visually pleasing styling: make conditional claims, source vintage and uncertainty recoverable regardless of display modality.
7. Simulate a timed-out destructive action: mark external effect unknown and refuse blind repetition.
8. Publish after a compiler/source version change: revalidate dependent qualifications before current reliance.
9. Run without AI: deterministic domain operations continue through the same meaning/effect contracts.
10. Ask a user to accept a result for one named purpose: ensure later use for a different purpose rechecks criteria/authority instead of treating acceptance as universal.

## 9. Status and decision frontier

**Observed baseline:** a standalone Python analytical core, a Qt-bound Windows prototype with local Case/Event/Artifact projections and separate managed deployment interface. **Supported research:** subject/work/knowledge/authority distinctions are needed for accurate future analytical Work, and many are valuable even in a minimal product. **Unaccepted proposals:** any universal Claim graph, independent knowledge engine, new physical repository, obligatory Work object for every button press, full Decision/Strategy lifecycle and exact machine ontology. Appropriate action is a source-grounded Product Decision plus real conformance cases—not silently asserting those subsystems now exist.

Related maintained Science: [epistemic firewalls](../data-and-knowledge/semantic-promotion-firewalls-and-bounded-reliance.md), [observations and comparability](../data-and-knowledge/observation-semantics-comparability-and-claims.md), [Work closure](../work/evidence-based-work-lifecycle-and-closure.md), [composition identity](../capabilities/composition-identity-and-user-machine-projections.md), [ownership](../architecture/semantic-ownership-and-contract-boundaries.md), and [proportional assurance](proportional-assurance-and-knowledge-admission.md).

## 10. Exact source-preserved invariants and rejected transitional doctrines

The original [method-to-product decomposition source #43 and #53](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2000-L2021) includes **20** target-doctrine rejections and **40** candidate invariants. These lists record research reasoning in exact source wording below; they do **not** bind Product Authority, automatically make all described objects mandatory or imply that every condition is already enforced by the code. In particular, terms such as `PROTOS`, `MachineScheme`, `Work` and `ArtifactStyleSet` were working semantic vocabulary, not necessarily approved public type names or physical packages. Even concise “X is not Y” claims need applicability and materiality checks in each actual Workflow.

### 20 proposals the original recommends leaving behind

| Source item | Exact wording in original research | Frozen line |
| --- | --- | --- |
| `SB-SRC-0029/HISTORICAL_REJECT-01` | Hardcoded OperationRegistry inside client. | [L2002](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2002) |
| `SB-SRC-0029/HISTORICAL_REJECT-02` | Auto-wrap every operation into user Scenario. | [L2003](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2003) |
| `SB-SRC-0029/HISTORICAL_REJECT-03` | `ScenarioRunCase` as only durable unit. | [L2004](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2004) |
| `SB-SRC-0029/HISTORICAL_REJECT-04` | One active scenario/global busy state. | [L2005](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2005) |
| `SB-SRC-0029/HISTORICAL_REJECT-05` | Background as independent execution subsystem. | [L2006](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2006) |
| `SB-SRC-0029/HISTORICAL_REJECT-06` | Local JSON as shared truth. | [L2007](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2007) |
| `SB-SRC-0029/HISTORICAL_REJECT-07` | Shared `unread: bool`. | [L2008](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2008) |
| `SB-SRC-0029/HISTORICAL_REJECT-08` | Path-oriented Artifact identity. | [L2009](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2009) |
| `SB-SRC-0029/HISTORICAL_REJECT-09` | Silent failure/fallback. | [L2010](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2010) |
| `SB-SRC-0029/HISTORICAL_REJECT-10` | UI prefs mixed with runtime binding. | [L2011](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2011) |
| `SB-SRC-0029/HISTORICAL_REJECT-11` | Qt orchestration in shared runtime. | [L2012](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2012) |
| `SB-SRC-0029/HISTORICAL_REJECT-12` | Current package/API compatibility as architectural constraint. | [L2013](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2013) |
| `SB-SRC-0029/HISTORICAL_REJECT-13` | DataFrame as universal external ABI. | [L2014](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2014) |
| `SB-SRC-0029/HISTORICAL_REJECT-14` | “Latest” resolution during execution without pinning exact snapshot. | [L2015](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2015) |
| `SB-SRC-0029/HISTORICAL_REJECT-15` | Raw destructive filesystem primitives exposed to AI. | [L2016](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2016) |
| `SB-SRC-0029/HISTORICAL_REJECT-16` | UI/frontend computing permissions. | [L2017](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2017) |
| `SB-SRC-0029/HISTORICAL_REJECT-17` | Status color as sole status meaning. | [L2018](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2018) |
| `SB-SRC-0029/HISTORICAL_REJECT-18` | Plugin install implying activation. | [L2019](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2019) |
| `SB-SRC-0029/HISTORICAL_REJECT-19` | One health flag standing for many unrelated claims. | [L2020](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2020) |
| `SB-SRC-0029/HISTORICAL_REJECT-20` | Logs/history treated as canonical semantic state. | [L2021](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2021) |

### 40 proposed target invariants

| Source item | Exact wording in original research | Frozen line |
| --- | --- | --- |
| `SB-SRC-0029/CANDIDATE_INVARIANT-01` | One semantic fact has one owner. | [L2326](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2326) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-02` | Projection never silently becomes owner. | [L2327](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2327) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-03` | Work survives UI/process lifetime when materially durable. | [L2328](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2328) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-04` | Run is not Work. | [L2329](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2329) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-05` | Operation is not Work. | [L2330](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2330) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-06` | Scheme is not automatically bounded Work. | [L2331](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2331) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-07` | Result is not Artifact. | [L2332](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2332) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-08` | Artifact identity is not path. | [L2333](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2333) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-09` | Source identity is not URL. | [L2334](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2334) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-10` | Registry identity is not filename. | [L2335](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2335) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-11` | Capability is not Authority. | [L2336](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2336) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-12` | Installed plugin is not active plugin. | [L2337](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2337) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-13` | Active plugin is not ready plugin. | [L2338](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2338) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-14` | Ready capability is not applicable capability. | [L2339](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2339) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-15` | Request accepted is not effect achieved. | [L2340](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2340) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-16` | Execution success is not acceptance. | [L2341](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2341) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-17` | Acceptance is not external outcome. | [L2342](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2342) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-18` | Recommendation is not Decision. | [L2343](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2343) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-19` | Decision is not execution. | [L2344](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2344) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-20` | Chat is not Work state. | [L2345](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2345) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-21` | Message is not commitment without Authority/context. | [L2346](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2346) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-22` | Presence is not ownership. | [L2347](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2347) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-23` | Background is not a parallel execution architecture. | [L2348](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2348) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-24` | AI is not a bypass path. | [L2349](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2349) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-25` | Log is evidence, not truth. | [L2350](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2350) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-26` | Exception is technical evidence, not public problem identity. | [L2351](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2351) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-27` | Clean test is not universal assurance. | [L2352](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2352) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-28` | Multiple reviewers do not prove independence. | [L2353](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2353) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-29` | Freshness is reliance-relative. | [L2354](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2354) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-30` | UNKNOWN is legitimate. | [L2355](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2355) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-31` | User-facing simplicity may not erase material control semantics. | [L2356](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2356) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-32` | Client rendering may not alter product meaning. | [L2357](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2357) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-33` | Artifact style may not alter epistemic meaning. | [L2358](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2358) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-34` | Plugin may not implicitly alter public domain semantics. | [L2359](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2359) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-35` | AppDock platform concerns stay outside domain core. | [L2360](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2360) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-36` | `stratbox` remains usable without Strategy Box application runtime. | [L2361](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2361) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-37` | Strategy Box remains usable without PROTOS. | [L2362](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2362) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-38` | PROTOS effects pass through admitted capabilities and Authority. | [L2363](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2363) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-39` | Generated capability requires admission before trusted fast path. | [L2364](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2364) |
| `SB-SRC-0029/CANDIDATE_INVARIANT-40` | Recovery restores governing meaning, not merely last screen. | [L2365](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L2365) |

### Challenges and conflicts that prevent premature doctrine

**Boundary vocabulary is not code topology.** “One semantic fact has one owner” is an ownership discipline; it does not prove that a subject, measurement, event, result and every projection need individual database tables or repositories. Conversely, “Work survives process lifetime” applies only when the product has admitted durable Work; a one-shot deterministic calculation can validly return a value without a job database.

**Different original studies propose different product navigation.** An operational workbench emphasizes Work / Explorer / Scenarios / Runs; an epistemic navigation stresses Data / Knowledge / Decisions / Artifacts, while a cognitive-first study emphasizes Chat/Threads. These can be different projections of the same semantic objects. No UI selection follows automatically from the forty invariants; see the separate [producer reconciliation](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/consolidation/reconciliation/OPERATIONAL-VS-EPISTEMIC-NAVIGATION-2026-10-11.md).

**Source is a candidate, not an Authority.** The original #43 rejects backward-compatibility preservation as a *future target design constraint*. It does not prove that a current deployed package may ignore ordinary correctness, safe upgrade behavior or versioned Artifacts. Likewise “no hard AI dependency” is a robustness objective, not proof that the existing GUI already has a replaceable cognitive consumer.

**Independent testing remains open.** Anti-patterns need observable counterexamples: two concurrent writer races, stale registry “latest” drift, an output path reassigned to a different Artifact, a UI-inferred permission disagreement, an unsafely retried external effect, or a green health indicator masking a failed required capability. Negative results, explicit `UNKNOWN`, runtime snapshots and recovery tests—not a checklist score—would determine future assurance.

**Preservation limit:** these **60** source lines now have exact material text in maintained Science, with source links and two priority groups; the other material claims, counterarguments and examples in the 2,985-line source are not thereby fully conserved or independently certified.
