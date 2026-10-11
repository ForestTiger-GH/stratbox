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
