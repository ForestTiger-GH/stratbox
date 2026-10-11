# Semantic promotion firewalls and bounded reliance in analytical work

**Scientific problem.** A statistical workflow can preserve source bytes and still produce a misleading analysis when it silently upgrades what a datum *means*: publication to world truth, normalization to independent evidence, model output to observation, agreement to verification, visualization to permission or recommendation to decision. This article sets out the classes of illicit promotion, the role of explicit bridges and negative tests for bank and macroeconomic analysis. **Status:** evidence-qualified architecture research; no universal epistemic database or new product promise is approved. The current [analytics core](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox) supplies real examples of partial implementation, not an exhaustive implementation of this model.

## 1. A source is authoritative only for a bounded claim

The fact that an official bank regulator published a value supports the proposition *“the authority published this value under the recorded definition and vintage.”* It does not, without further grounds, entail comparability across perimeters, causal attribution, current relevance, forecast reliability or action permission. This is not skepticism for its own sake: it is semantic precision about the proposition and the authority that supports it.

```text
Publication identity and bytes
   → source-specific observation (reported; period, perimeter, unit, method)
   → normalized representation (defined transformation)
   → qualified analytic claim (grounds, warrant, assumptions and alternative interpretations)
   → evaluation for a stated intended use
   → reliance by an identified consumer
   → recommendation
   → authorized decision / commitment / effect
```

This graph is **not a mandatory linear ETL workflow**. A study may end in an unresolved set of hypotheses; a data collection may preserve source bytes without inference; a forecast may be issued with conditional relevance but no decision; a recommendation may be rejected. The firewall means each edge requires an explicit reason and cannot be inferred from an earlier step's successful process status.

## 2. The minimum semantic distinctions

| Pair often collapsed | Material distinction | What would falsify a truthful result |
| --- | --- | --- |
| Source versus observed world | Publication authority proves the published statement, not all properties of reality | A user can retrieve “official” without knowing publication vintage and limitation |
| Data versus Observation | A parsed cell needs subject, measure, unit, time and perimeter to be meaningful | A value is used as a fact solely because the parser returned a number |
| Canonical versus true | Canonical denotes an internal normalized representation for a declared construct | A revised normalization overwrites the preserved original source assertion |
| Transformation versus evidence | Arithmetic or modeling manipulates inputs; proof strength requires a justified inferential bridge | Summing independently rounded figures is presented as an exact official total |
| Model result versus measured fact | A solver's choice reflects model constraints and assumptions | Reconstructed/selected values look indistinguishable from actually published values |
| Decomposition versus cause | An accounting contribution is not a causal mechanism | A waterfall chart alone is narrated as an explanation of why the outcome happened |
| Scenario versus Forecast | Conditional world asks *what if*; forecast assesses a future outcome under a specific information state | `IF H THEN C` is rendered as a probability or asserted prediction |
| Forecast versus target/plan | Prediction does not itself commit resources or set objectives | Target-vintage replaces forecast-origin metadata in history |
| Evaluation versus acceptance | A check has bounded criterion and evidence; acceptance invokes an authorized actor for a use | Green schema validation silently publishes or approves a business decision |
| Result versus Artifact | Semantic answer persists across report/Excel/table formats; file is a representation | Changing a title/style changes inferred claim strength |
| Log versus Work state | A log line is a process observation, not authoritative closure | Exit code 0 causes Work accepted without effect verification |
| Recommendation versus Decision | Analysis informs a choice; accountable authority resolves it | An AI summary asserts a policy has been adopted |

These distinctions are not a mandate to create one table or class per concept. They may be held inside a typed Result, linked lineage record, Work manifest or specialist model. A new durable identity is justified by independent citation, lifecycle, evaluation or approval needs—not by ontological symmetry.

## 3. Banking and macroeconomic dimensions that alter meaning

**Bank/perimeter.** A licensed bank, banking group, financial group, issuer, brand and consolidated holding are not interchangeable identifiers. IFRS, Russian statutory accounts, prudential reporting and statistical reporting have different perimeter and recognition bases. Two columns labeled “assets” or “profit” do not become comparable from their text alone.

**Measure definition.** A value can vary by nominal/real basis, reporting date versus flow interval, quarterly cumulative versus standalone quarter, gross versus net basis, currency conversion, geographic membership, classifier/industry mapping, aggregation and rounding. A cross-series bridge has a **declared transformation, assumptions, domain of applicability and limits**, not a blanket `comparable=true`.

**Time.** Period described, publication time, retrieval time, reference classifier effective date, forecast origin and decision time are separate. A time-series revision may preserve valid historical publication truth while invalidating a past comparison that pretended to use information unavailable at its origin.

**Missingness.** `UNKNOWN`, unavailable, not observed, not reported, suppressed, ambiguous, inconsistent, zero and not applicable imply different mathematics and user actions. Converting all to an empty cell, `False` or `0` silently introduces facts not justified by source.

These are first-order financial analytics errors, not just metadata niceties. A useful output is a **qualified comparison**: “A and B comparable for purpose U under explicit adjustment J, except regions/time periods P, with uncertainty L”. A legitimate alternative is to return **not comparable** or **insufficient evidence**.

## 4. Provenance, validity and reproducibility are independent tests

A reproducibility manifest can pin exact source hashes, registry and parser versions, model revision, parameters, execution environment when material, results and artifacts. This answers *what was computed from what*. It does not by itself prove the definition was appropriate, the source accurate, the inference valid or the resulting action authorized. An exact, reproducible mistake is still a mistake.

The most mature direct [SORS reconstruction domain](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration) illustrates proportional evidence: source publications contain rounded values, while latent components satisfy exact additivity. Its source-preserving inference and evidence tiers avoid silently promoting a chosen weak reconstruction to an official fact. It would be a category error to demand its full mathematical ledger of every CSV import. The relevant general principle is **do not strengthen an observation's support through transformation or representation**.

An evidence source can support one claim, conflict with another and be irrelevant to a third. Counting several generated reports of one input as multiple independent corroborations is a lineage error. In a current knowledge system, support needs independent evidence where a conclusion calls for independence; multiple summaries or repeated AI statements do not meet that requirement.

## 5. Hypotheses, conditional worlds and responsible uncertainty

Useful legitimate outputs include plausible hypothesis sets, directional investigation of a hypothesis, counterfactual consequences, robustness checks and explicit unresolved uncertainty. A system may be commissioned to construct the strongest available argument in favor of H; such a **search posture** is different from adopting H. A conditional analysis `IF H THEN C` does not assert `H` or a numerical probability of H.

Sometimes a decision can be made responsibly before the uncertainty resolves: if action A is reversible, stays within protected constraints and performs tolerably across plausible H1/H2/H3, an accountable actor can select A under explicit triggers for review. That **robust choice** does not certify any one hypothesis true.

A model might legitimately output:
```text
supported reported observation: O
unresolved hypotheses: H1, H2
conditional result: if H1, consequence C
decision-support result: A is robust under constraints K
not established: unique cause of O
reopen on: newly published series V or changed policy constraint
```
Turning this into “the cause was H1, therefore do A” would be an unsupported two-step promotion.

## 6. Knowledge currentness without historical erasure

Historical correctness is about what was claimed, known and done **then**. Current reliance is about whether that historical result remains applicable **now** for a particular use. Fresh data or an updated classifier should not overwrite earlier Forecasts or pretend the old report never existed. A better transition is:

```text
new SourceSnapshot / registry revision
   → compare which dependency meaning changed
   → identify dependent Result versions
   → determine unchanged / possibly stale / needs revalidation / superseded
   → propose bounded successor Work where justified
   → retain exact historical Result and its original information vintage
```

“Newer” alone does not imply more accurate, currently applicable, independently grounded or authoritative for every purpose. Some changes are cosmetic and require no analytical recalculation; others change classification, institutional perimeter or measurement semantics and invalidate a downstream comparison. Source-change watchers should understand this distinction before publishing replacement outputs.

A knowledge graph *view* can help traverse support, derivation and currentness, but graph storage itself does not validate semantics. Relational tables, typed objects and manifests can represent the same qualified relations. The meaningful question is which inference relations are valid: `derived-from`, `supports`, `contradicts`, `uses-vintage`, `applies-to`, `accepted-for`, `supersedes` and `decided-by` are **not** interchangeable or generally transitive.

## 7. Work, communication and attention preserve semantic force

A Work record can carry objective, source/parameter bindings, concrete Run/Attempt evidence, actual external effects, interim results, evaluations, residual questions and acceptance state. No single `DONE` status can reliably express “execution ended, effect unknown, report created, result not yet accepted”. A message in a conversation may propose or announce a decision, but its delivery does not alone establish the authorized decision object, comprehension, or downstream commitment.

The same applies to presentation. A green status can mean validation passed, Job succeeded, Artifact published, Work accepted or Knowledge current; these are different semantics and should have distinct labels/actions. A chart, sorted list, low-entropy UI, animated progress, push notification or summarized paragraph must not increase a claim's certainty or alter permissions/urgency merely through salience. An adaptive UI is especially risky if it alters what the user sees and then treats behavior under that intervention as independent evidence of the user's earlier inferred preference.

A knowledge inspector should answer: **what is this**, what observation/construct/perimeter/period, from which exact vintage, how derived, what supports or contradicts it, what remains unknown, how current, and what reliance is justified. Progressive disclosure can keep the main UI calm without hiding safety-critical distinctions.

## 8. Evaluation must be fit for purpose

An evaluation is meaningful only with a specified subject/version, criterion, evidence, conditions, known noncoverage, evaluator independence where relevant, date and intended reliance. The outcome “passed validation” must not grant publication authority. Acceptance is an explicitly scoped relation of an actor/authority to an exact Result for purpose U under conditions K. Later staleness may weaken present reliance while leaving the historical acceptance event intact.

Likewise, a Forecast may be procedurally sound and still miss its realized target. Ex-post accuracy is evidence about forecasting performance, not a license to retroactively overwrite the ex-ante information state or call any lucky number a methodologically sound Forecast.

## 9. Falsification tests before implementation choices

| Test | Failure condition |
| --- | --- |
| Reported vs reconstructed | Same unqualified label and chart style make source and inferred values indistinguishable |
| Source and definition trace | Material comparative conclusion lacks exact data snapshot, perimeter, temporal semantics or versioned definition |
| Comparable only with bridge | Two IFRS/RAS or historical/current geographic aggregates compare without a justified relation or disclosed limitation |
| Unknown preservation | An unavailable/conflicted datum becomes zero or false in export/UI |
| No silent admission | A model Output or passed schema check turns into accepted or published Result without a separate authorized transition |
| Historical forecast integrity | Revisions replace the original ex-ante input vintage rather than create a successor |
| Qualifier preservation | A conditional/candidate/counterfactual assertion becomes an unconditional prose sentence or AI answer |
| Claim-grounded evaluation | “Verified” is asserted with no exact criterion, coverage, independence or evidence |
| Decision boundary | Recommendation/agent speech is rendered as an authorized policy decision |
| Source independence | Multiple documents derived from one source are counted as several independent observations |
| Result/artifact separation | A complete analytical Result is marked delivered despite unverified Artifact publication |
| Recovery and external effect | Timeout is interpreted as “nothing happened” and the destructive action retries |
| Currentness impact | Classifier change either invalidates everything or silently invalidates nothing without dependency evidence |
| UI and notification | Visual priority, sorting, success badges or adaptation alter material reliance/authority without justification |

Tests must include negative cases and property-based sequences, not only a happy-path exported workbook. They should be scoped to actual modules and named product acceptance criteria; this article does not claim these tests are already passing.

## 10. Materiality, proportionate implementation and open decisions

A trivial deterministic conversion may need only an input source, formula, unit and result. A cross-bank strategic conclusion can require exact vintages, definitions, a comparison bridge, grounds, uncertainty, independent challenge and a Decision record. **The depth of assurance should scale with consequence and reliance**, not with the number of possible metadata fields.

The research's strongest conceptual conclusion is a shift from `source → DataFrame → Excel` and `operation → scenario → case → file` as universal *meaning* to qualified observational/result/work transitions. But mandating a full “epistemic engine” or new `knowledge/` hierarchy before defining actual consumers would be premature. Domain contracts should be introduced where changed meaning or audit need justifies them.

**Still open:** whether Claim, Hypothesis, Acceptance or Currentness require distinct persisted objects; which activities are first-class in the shipped product; user-level Decision authority; dependence on historical source-corpus methodologies; cross-domain registry ownership; and how rich the first Knowledge inspector should be. None is settled by the scientific distinctions. Reopen on explicit Work demands, economic data failure examples, authorized Product requirements or direct evaluated code.

Related maintained Science: [observation semantics](observation-semantics-comparability-and-claims.md), [source vintages and replay](source-observation-vintages-and-replay.md), [dataset lineage/currentness](dataset-versions-lineage-currentness-and-retention.md), [claim/work closure](../work/evidence-based-work-lifecycle-and-closure.md), [cross-client publication](../artifacts/output-identity-publication-and-availability.md), [proportional assurance](../engineering/proportional-assurance-and-knowledge-admission.md).
