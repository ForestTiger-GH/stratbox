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

## 11. Original epistemic stress tests and status-preservation firewalls

This appendix retains source material from the frozen [epistemic architecture original, #87 and #88](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3461-L3646), blob `00d738012f9dc85d80f89105c9ad71521097e221`. The **twenty proposed acceptance tests** and **thirty-eight distinction statements** are Research claims; none is a completed test or an accepted Product rule. Their applicability and verification depth should be proportional to the actual task, risk and material reliance.

### Twenty proposed tests: exact source questions and failure triggers

#### 01. Reported vs restored — `SB-SRC-0019/TEST-01`

Original [L3463–L3468](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3463-L3468).

Может ли пользователь отличить официально опубликованное значение от восстановленного?

Если нет — fail.

#### 02. Source trace — `SB-SRC-0019/TEST-02`

Original [L3469–L3472](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3469-L3472).

Можно ли от material result перейти к source snapshot/vintage?

#### 03. Definition trace — `SB-SRC-0019/TEST-03`

Original [L3473–L3476](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3473-L3476).

Можно ли понять, что именно означает показатель?

#### 04. Comparison bridge — `SB-SRC-0019/TEST-04`

Original [L3477–L3480](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3477-L3480).

Если сравниваются две series с разными perimeter/definitions, есть ли bridge или limitation?

#### 05. Historical integrity — `SB-SRC-0019/TEST-05`

Original [L3481–L3484](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3481-L3484).

Новый source не переписывает старый Forecast/Analysis silently?

#### 06. Currentness — `SB-SRC-0019/TEST-06`

Original [L3485–L3488](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3485-L3488).

Система понимает, что Result historically valid, но needs revalidation?

#### 07. UNKNOWN — `SB-SRC-0019/TEST-07`

Original [L3489–L3492](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3489-L3492).

Не исчезает ли UNKNOWN через normalization/export/UI?

#### 08. Claim-strength preservation — `SB-SRC-0019/TEST-08`

Original [L3493–L3498](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3493-L3498).

Может ли summary/report превратить conditional claim в factual claim?

Если да — fail.

#### 09. Decision separation — `SB-SRC-0019/TEST-09`

Original [L3499–L3504](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3499-L3504).

Recommendation может быть отображена как Decision без Authority transition?

Если да — fail.

#### 10. Acceptance separation — `SB-SRC-0019/TEST-10`

Original [L3505–L3510](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3505-L3510).

Successful computation автоматически становится accepted Result?

Если да — fail.

#### 11. Retry/effect — `SB-SRC-0019/TEST-11`

Original [L3511–L3520](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3511-L3520).

Если remote operation timed out, умеет ли Work выразить:

```text
effect unknown
```

а не просто `failed`?

#### 12. Dependency impact — `SB-SRC-0019/TEST-12`

Original [L3521–L3524](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3521-L3524).

При изменении registry/source можно определить зависимые Results без тотального refresh?

#### 13. Artifact lineage — `SB-SRC-0019/TEST-13`

Original [L3525–L3528](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3525-L3528).

Можно ли из Excel понять, какой semantic Result он represents?

#### 14. AI authority — `SB-SRC-0019/TEST-14`

Original [L3529–L3534](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3529-L3534).

Может ли AI сам повысить статус своего вывода до accepted/decision?

Если да — fail.

#### 15. Shared lineage — `SB-SRC-0019/TEST-15`

Original [L3535–L3540](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3535-L3540).

Несколько derivative reports считаются независимыми evidence только из-за количества?

Если да — fail.

#### 16. Forecast vintage — `SB-SRC-0019/TEST-16`

Original [L3541–L3546](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3541-L3546).

Historical Forecast может быть overwritten?

Если да — fail.

#### 17. UI semantics — `SB-SRC-0019/TEST-17`

Original [L3547–L3552](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3547-L3552).

Цвет/позиция/notification способны скрыто изменить action availability или priority meaning?

Если да — fail.

#### 18. Recovery — `SB-SRC-0019/TEST-18`

Original [L3553–L3556](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3553-L3556).

После restart/actor replacement можно безопасно продолжить Work без чтения полного transcript?

#### 19. Public boundary — `SB-SRC-0019/TEST-19`

Original [L3557–L3560](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3557-L3560).

Публичные core/surface contracts полностью нейтральны к конкретному закрытому окружению?

#### 20. Research amputation — `SB-SRC-0019/TEST-20`

Original [L3561–L3566](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3561-L3566).

После формирования Current Knowledge можно понять текущий result без обязательного чтения всей historical Research, сохранив forensic route назад?

---

### Thirty-eight epistemic non-implications

The “≠” statements are **boundaries on inference**, not claims that the terms are universally unrelated: e.g., an Observation may support a qualified Claim under an explicit warrant, and a Decision may authorize an Action. A bridge is required to strengthen identity, causal meaning, time, evidence, approval or reliance.

| Exact-source ID | Distinction in original wording | Frozen line |
| --- | --- | --- |
| `SB-SRC-0019/FIREWALL-01` | Source ≠ world truth | [L3572](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3572) |
| `SB-SRC-0019/FIREWALL-02` | Published value ≠ canonical internal value | [L3574](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3574) |
| `SB-SRC-0019/FIREWALL-03` | Canonical ≠ true | [L3576](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3576) |
| `SB-SRC-0019/FIREWALL-04` | Observation ≠ explanation | [L3578](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3578) |
| `SB-SRC-0019/FIREWALL-05` | Data ≠ evidence for every claim | [L3580](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3580) |
| `SB-SRC-0019/FIREWALL-06` | Evidence ≠ Authority | [L3582](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3582) |
| `SB-SRC-0019/FIREWALL-07` | Model ≠ target | [L3584](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3584) |
| `SB-SRC-0019/FIREWALL-08` | Model output ≠ fact | [L3586](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3586) |
| `SB-SRC-0019/FIREWALL-09` | Decomposition ≠ cause | [L3588](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3588) |
| `SB-SRC-0019/FIREWALL-10` | Correlation ≠ intervention effect | [L3590](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3590) |
| `SB-SRC-0019/FIREWALL-11` | Scenario ≠ Forecast | [L3592](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3592) |
| `SB-SRC-0019/FIREWALL-12` | Forecast ≠ Target | [L3594](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3594) |
| `SB-SRC-0019/FIREWALL-13` | Forecast ≠ Decision | [L3596](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3596) |
| `SB-SRC-0019/FIREWALL-14` | Probability ≠ confidence | [L3598](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3598) |
| `SB-SRC-0019/FIREWALL-15` | Unknown ≠ zero | [L3600](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3600) |
| `SB-SRC-0019/FIREWALL-16` | No finding ≠ absence | [L3602](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3602) |
| `SB-SRC-0019/FIREWALL-17` | Many documents ≠ independent evidence | [L3604](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3604) |
| `SB-SRC-0019/FIREWALL-18` | Result ≠ Artifact | [L3606](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3606) |
| `SB-SRC-0019/FIREWALL-19` | Artifact ≠ Knowledge | [L3608](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3608) |
| `SB-SRC-0019/FIREWALL-20` | Log ≠ Work State | [L3610](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3610) |
| `SB-SRC-0019/FIREWALL-21` | Execution success ≠ Work success | [L3612](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3612) |
| `SB-SRC-0019/FIREWALL-22` | Evaluation ≠ Acceptance | [L3614](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3614) |
| `SB-SRC-0019/FIREWALL-23` | Acceptance ≠ world truth | [L3616](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3616) |
| `SB-SRC-0019/FIREWALL-24` | Recommendation ≠ Decision | [L3618](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3618) |
| `SB-SRC-0019/FIREWALL-25` | Decision ≠ Commitment | [L3620](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3620) |
| `SB-SRC-0019/FIREWALL-26` | Commitment ≠ Execution | [L3622](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3622) |
| `SB-SRC-0019/FIREWALL-27` | Execution ≠ intended effect | [L3624](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3624) |
| `SB-SRC-0019/FIREWALL-28` | Outcome ≠ ex-ante decision quality | [L3626](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3626) |
| `SB-SRC-0019/FIREWALL-29` | Message sent ≠ understood | [L3628](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3628) |
| `SB-SRC-0019/FIREWALL-30` | Understood ≠ accepted | [L3630](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3630) |
| `SB-SRC-0019/FIREWALL-31` | Accepted ≠ committed | [L3632](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3632) |
| `SB-SRC-0019/FIREWALL-32` | Capability ≠ Authority | [L3634](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3634) |
| `SB-SRC-0019/FIREWALL-33` | Presence ≠ responsibility | [L3636](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3636) |
| `SB-SRC-0019/FIREWALL-34` | Workspace ≠ semantic owner | [L3638](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3638) |
| `SB-SRC-0019/FIREWALL-35` | UI ≠ truth owner | [L3640](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3640) |
| `SB-SRC-0019/FIREWALL-36` | Latest ≠ current for every use | [L3642](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3642) |
| `SB-SRC-0019/FIREWALL-37` | Historical ≠ invalid | [L3644](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3644) |
| `SB-SRC-0019/FIREWALL-38` | Current ≠ permanent | [L3646](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L3646) |

### Adversarial interpretation and cost limits

- Two reports citing the same official source form two carriers but often only one independent observation lineage; counting citations does not establish independent evidence.
- Retaining the issued old Forecast or Analysis is necessary for historical inspection; current reliance is a separate, source-vintage- and purpose-dependent question.
- A valid XLSX hash proves content bytes, not perimeter comparability, user understanding, semantic correctness, acceptance or institutional approval.
- A Job execution success, Artifact publication, Evaluation pass, authorized Decision and observed real-world effect remain distinct claims and must not inherit each other's status.
- These distinctions do not demand a persisted global ontology for every user action. Materialize separate objects only where lifecycle, authority, independent reuse or auditable consequences justify them.

**Preservation status:** **58 original material items** are now transcribed in full or exact wording and source-addressed in maintained Science. This producer transcription neither independently certifies their correctness nor closes all material propositions of the 3,884-line original.
