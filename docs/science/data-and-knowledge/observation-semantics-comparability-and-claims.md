# Observation semantics, economic comparability, and evidence-qualified claims

**Domain:** making banking and macroeconomic observations interpretable without losing accounting perimeter, time/vintage, missing values, measurement units, source classifications and the inferential strength of derived figures. **Status:** maintained explanatory scientific model and clearly identified candidate generic contracts. It does not claim a deployed universal `Observation`, `ClaimStore` or multi-domain schema. **Baseline:** [core at `8459dc5`](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580); direct system-wide verification and independent corpus-conservation review remain open.

## 1. Eight boundaries that cannot safely collapse into “a file with values”

| Boundary | Two different things | Error if treated as one |
| --- | --- | --- |
| Source rule / observed publication | `SourceDescriptor` vs byte- and time-specific `SourceSnapshot` | A revised publication overwrites the analytical basis of past work |
| Entity or classifier / source acquisition catalog | The identities of banks, sectors and regions vs the addresses/procedures retrieving reports | A URL list becomes a regulator of what a bank or region means |
| Raw bytes / Observation | File bytes and parser positions vs a measurement with unit/period/scope | A numeric cell loses its economic interpretation |
| Dataset definition / dataset version | Stable schema/semantic series vs particular observations and their accepted inputs | A mutable DataFrame silently becomes “the same” historical dataset |
| Reported / derived / reconstructed | Publisher statement, calculation and evidence-bounded inference | An estimated or selected figure becomes “official” in downstream tables |
| Claim / Evidence | Statement about reality/use vs the grounds supporting that particular statement | One authentic CSV is offered as evidence of any causal or policy conclusion |
| AnalyticalResult / Artifact | Qualified domain findings vs XLSX/CSV/PDF or visual representation | A good-looking or technically readable workbook is treated as accepted analysis |
| Content digest / logical identity / locator | Bytes, named domain object and physical path | Renaming deletes provenance, or equal bytes collapse two different contexts |

These are **semantic distinctions**, not a mandate for eight separate classes, repositories or persistence services. A small object may carry references to several roles where that preserves independent meanings.

## 2. What constitutes an economic Observation?

An interpretable observation requires enough recoverable information for its specific analytical use:

1. **Subject identity:** exact bank/legal entity/consolidated group, region, economic activity, sector or sample population; a mutable display name is insufficient.
2. **Measure/construct definition:** the meaning of the indicator, not only its spreadsheet heading.
3. **Value semantics:** data type, scale, currency, precision, true zero, absent cell, special source code, published rounding or admissible interval.
4. **Reporting perimeter:** standalone vs consolidated, RAS vs IFRS vs prudential/statistical, inclusions/exclusions, securitization and accounting changes.
5. **Time:** stock date or flow period, source publication/revision, when information was observable and the applicable classification dates.
6. **Classification/mapping identity:** exact bank aliases/sets, OKVED code release, regional or source-specific mappings, report form version.
7. **Epistemic role:** reported, normalized, derived, reconstructed, selected, estimated or modeled, including assumption/evidence tiers.
8. **Provenance:** exact source snapshot and transformation/proof reference sufficient to establish how the observation came to exist.

This is an obligation to **retain material meaning** somewhere in a reconstructible dataset-level context. It does not mean storing the entire header/perimeter/registry bundle beside every data cell. A `MeasureDefinition`, `DatasetVersion` manifest and `SourceSnapshot` reference can serve thousands of rows if their actual scope and temporal validity are unambiguous.

### An IFRS/RAS comparability counterexample

A value labeled “Corporate customer lending, RUB bn” might concern an IFRS consolidated group, while a second source measures a standalone legal entity under RAS. It might include different receivables, related parties or post-securitization exposures. Converting one balance to RUB billions solves *currency and scale*, not *perimeter and recognition*. A valid comparison requires a supported bridge or explicit `NOT_COMPARABLE`/`COMPARABLE_WITH_LIMITATIONS`. A shared column title cannot prove a shared `MeasureDefinition`.

A similar issue appears in currency conversion: the exchange-rate source/snapshot, quote date, temporal convention, currency pair and rounding rules are part of the **transformation**, distinct from a changed bank reporting scope. Combining them into a single “normalize numbers” flag hides material assumptions.

## 3. Missingness is data, not UI decoration

A blank regulatory reporting field, genuine numeric zero, absent publication, suppressed/confidential entry, not applicable observation, unknown or invalid value, below-threshold disclosure and interval-valued result describe **different states of knowledge**. The source Study highlights current `cbr_forms` pathways where `blank != 0`; the SORS model makes the distinction more demanding by representing a published bucket and an admissible latent interval.

A small candidate type vocabulary for domains that need it is `present`, `missing`, `not_applicable`, `suppressed`, `unknown`, `interval`, `invalid`, with source-specific distinctions and provenance. It is not an approved universal enum. A plain `None` can mean different things in different inputs, and automatically coercing it to `0` may falsify an aggregate or growth rate.

Negative cases:
- The source publishes a dash: without source convention, this is **UNKNOWN**, not necessarily zero or statistical secrecy.
- Bank A reports 0 lending; bank B has no disclosed field: their values are not equivalent for comparisons.
- An unpublished monthly release cannot become a zero row merely because the scraper returned no data.
- An official rounded value `6` with unit publication step may represent latent `[5.5, 6.5)`, not the exact underlying 6. The source's [SORS publication-rounding implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration/publication/rounding.py) provides a concrete implementation case.

These differences must survive parsers, long data, pivoting, exports and inference. Validation of the input container or schema cannot establish the meaning of a missing code.

## 4. Multiple definitions and time coordinates

The candidate `MeasureDefinition` includes semantic identity, formula where applicable, units, frequency, stock/flow semantics, consolidation perimeter, classification references, normative revision and known structural breaks. `EntityIdentity` is not a bank's label; one brand may correspond to different organizational/legal subjects over time.

Time must distinguish:
- **observation period** and flow/stock interpretation;
- **publisher's publication/release time**;
- **time available to an analyst**, which can differ from publisher date;
- **acquisition/observed timestamp**;
- **statistical vintage/revision**;
- **effective date of classification/method**;
- **time calculated, validated or re-assessed**.

A June 2026 observation first available in July and downloaded in August can be revised in September. A historical backtest must not assume the September revision was available in June, whereas a present-day analysis may intentionally use latest revised numbers. The two valid analyses need different as-of policies, not a global `is_latest` Boolean. See [source observations/vintages and R0–R4 replay](source-observation-vintages-and-replay.md).

## 5. Comparability is a qualified relation, not a universal Boolean

A `ComparabilityRelation` (candidate) would bind **two particular measures/dataset versions under a stated use** and an explicit transformation or bridge, with limitations. Economic equivalence may fail because of:
- bank grouping/standalone versus consolidated scope;
- accounting standard, excluded exposures or securitization;
- official definition or reporting-form version changed;
- region mergers, partial-region publication rows, boundary changes and geography aggregation;
- old versus current OKVED/sector group membership;
- revised source information as-of different dates;
- missing/suppressed observations mistaken for zero;
- currency and scale conversion with different FX or precision rules.

The core source research identifies geography as a concrete cross-domain mismatch: `cbr_industries` uses a publication-layout geometry with roughly 96 rows, SORS works with a different atomic/publication geometry, while escrow uses its own location handling. A flat file named `regions.csv` cannot decide whether “Russia,” a federal district, a municipality with modified territory, and a publisher-specific aggregate row have the same analytic identity. Better semantics use stable entities and **valid-time, source-specific mappings**. None of this proves a completed common geography registry today.

`Registry` is likewise polysemous. An official reference bank/OKVED registry, human aliases/policy overlays, source discovery catalog, domain rules (FRG families, form models, SORS mapping), and capability or style catalog have distinct authors and versioning rules. Selection by [filesystem mtime](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) reports a technical selector, not a valid published/effective release. A future manifest-based version reference is a qualified *candidate*, not current behavior.

## 6. A hierarchy of technical validation and scientific qualification

| Gate | What it can establish | Typical hidden remaining question |
| --- | --- | --- |
| Transport | An HTTP/IO operation returned content | Was the payload the expected official publication? |
| Container/format | ZIP/DBF/XLSX is technically readable | Are sheet/table fields the correct source release? |
| Structural schema | Required fields/typed layout match a known revision | Do codes, units and periods mean what expected? |
| Semantic normalization | Parsed values conform to declared construct | Is the derived interpretation economically justified? |
| Domain consistency | Accounting identities or crosswalk constraints hold | Are all material premises and exception cases covered? |
| Evidence qualification | Method, proof, source, assumptions and limitations recorded | Is the result suitable for this user's actual decision? |
| Consumer fitness/reliance | Specific-purpose requirements and authorized assessment satisfied | Does a later revision or purpose change require review? |

A `200 OK` returning HTML is transport success but format failure. An XLSX parser can succeed despite reading a different reporting perimeter. A domain-consistent reconstruction can be based on a weaker `ROUNDING_SELECTED` inference and must not be relabeled `STRICT_OFFICIAL`. A technically repeatable claim can remain unsupported or contested.

For individual domain observations, provenance can be lightweight. Where a claim is important, the model must retain scope, alternative hypotheses, negative checks and proof/assumption tiers rather than reducing everything to `valid=True`.

## 7. Claim, evidence, inference and reliance

A source may authoritatively establish **what it published in a given revision**, without making a later causal explanation or cross-source comparison true. The evidence chain therefore has two paths:

```text
Publisher publication → observed bytes → interpreted Observation
                                        → qualified statement about publication

Observation(s) + MeasureDefinition(s) + assumed model + method
  → DerivedResult / Inference → EvidenceArgument → QualifiedClaim
  → review, permitted reliance and later revalidation
```

A material `QualifiedClaim` may need `proposition`, claim kind (reported, descriptive, comparative, explanatory, causal, predictive, conditional, evaluative), subject/perimeter/time scope, evidence references, premises/assumptions, unresolved contradictions, uncertainty, support state, information-as-of, currentness and permitted reliance. **These are semantic roles**, not a mandate to populate a heavyweight graph database for every Excel cell or raw file.

Important evidence roles are:
- **reported source:** publication text/measurement, distinct from an expert's conclusion about it;
- **semantic mapping:** typed correspondence between source layout/labels and economic construct;
- **aggregation identity:** accounting or arithmetic identity with scope;
- **transformation proof:** reproducible calculation and method version;
- **model assumption:** hypothesis, not reported truth;
- **inference certificate:** feasibility or constrained optimization result;
- **reconciliation:** explanation of conflicting sources/perimeters;
- **human review:** acceptance of use, not a magical enhancement of the publisher's authority.

Multiple websites reprinting **one original publisher document** do not form multiple independent evidence sources. Provenance should represent that common ancestor; consensus among dependent Research reports likewise is not independent validation.

**Specialized SORS detail:** the direct evidence system distinguishes `STRICT_OFFICIAL`, `SOURCE_PRESERVING`, `ROUNDING_OPTIMAL`, `ROUNDING_PREFERRED`, `ROUNDING_SELECTED`, carries publication buckets, inferred bounds, constraints and conflicts. Its rich proof ledger is not expendable when producing an XLSX; but it would be excessive to force its entire solver apparatus into a simple raw file collector. The generic boundary must **allow rich extensions without promoting status**. See [published quantities and latent uncertainty](publication-rounding-and-claim-strength.md).

## 8. A result is not necessarily a workbook or an accepted decision

An `AnalyticalResult` can contain findings, datasets, qualified claims, evidence, assumptions, limitations, unresolved questions, validity/currentness and relevant Artifact references. It may exist without a file, or have multiple XLSX/CSV/report materializations. A file can be physically committed while the expert declines to rely on its analytic claims. Approval to execute a file action is not acceptance of a claim after computation.

The research distinction between **Knowledge** and **ResearchHistory** is equally material. A saved historical research file documents what was proposed then. A maintained scientific explanation must reconcile known direct behavior, definitions, challenges, negative findings and live limitations. Archiving all Research files therefore does not make a lossless Knowledge Product. An independent ClaimStore or KnowledgeCatalog may be justified by actual cross-report review/use, but remains unapproved without consumer evidence.

## 9. Tests and falsifying cases

Candidate checks, **not executed** by this article:

| Case | A valid result must show |
| --- | --- |
| Two bank figures labeled alike, RAS standalone vs IFRS consolidated | Explicit perimeter bridge or noncomparability |
| 0 and blank in CBR form | Separate values after parse, long conversion and export |
| One source URL returns revised previous period | Two vintages and historical input identity |
| Exact same bytes but changed bank/industry mapping | New semantic result identity or qualification |
| Same bytes and number reused in different units/periods | Not silently merged into one Observation |
| SORS weak selection exported as Excel | Its weak evidence tier and feasible interval retained |
| File is valid XLSX, source period wrong | Format success and semantic failure separately |
| Three news sources copy one regulator announcement | One dependent evidence family, not three independent proofs |
| Region splits or publication-only aggregate row | Versioned mapping and explicit aggregation limits |
| Source missing one month | Result marked partial/unknown, not filled with zero by default |
| Analyst reviews a result | Review/acceptance identity distinct from mathematical proof |
| Derived number displayed in a stylish report | Renderer changes presentation, not epistemic strength |

**Open decisions:** standard missingness vocabulary, scope of dataset and claim identities, per-cell versus run-level evidence cost, semantic crosswalk and geography, criteria for acceptance, bank accounting normalization, downstream currentness/reliance profiles, source retention and security. Revisit when two or more real domains can share a typed semantic contract with verified roundtrip, a new official reporting schema requires interpretation or a counterexample falsifies an existing inference.

## 10. Primary-source banking/macro qualification and worked checks

The original [banking and macro specificity research, sections 61–62](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2764-L2822) explicitly warns that bank statement labels and macro time series cannot be made comparable by a generic file parser or spreadsheet header. The **four banking concerns, five derivation-status labels and ten macro-series qualifiers** below are copied or narrowly restated as research findings with source lines, **not a currently deployed universal observation schema**.

### Four banking identity/interpretation boundaries

| Original item | Source-specific obligation | Source line |
| --- | --- | --- |
| `SB-SRC-0019/BANK-IFRS_RAS` | **Same label across IFRS and RAS.** Система должна считать bridge explicit. | [L2768](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2768) |
| `SB-SRC-0019/BANK-BANK_GROUP` | **Bank legal entity versus consolidated Group.** Обязательна perimeter semantics. | [L2779](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2779) |
| `SB-SRC-0019/BANK-DERIVATION_STATUS` | **Transformation status must remain recoverable.** В интерфейсе и Excel: | [L2783](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2783) |
| `SB-SRC-0019/BANK-HISTORICAL_REVISIONS` | **Historical vintage remains addressable.** Historical analysis должен быть способен использовать exact vintage. | [L2803](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2803) |

### Five different provenance/derivation statuses, not synonyms

| Original item | Exact original term | Interpretive difference to keep visible | Source line |
| --- | --- | --- | --- |
| `SB-SRC-0019/DERIVATION-01` | `reported` | Value as published under its actual source/perimeter/version, prior to product recoding. | [L2786](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2786) |
| `SB-SRC-0019/DERIVATION-02` | `normalized` | Source published amount after a controlled mapping/unit/scoping normalization; publisher remains ground truth only for the original form. | [L2787](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2787) |
| `SB-SRC-0019/DERIVATION-03` | `derived` | Explicit transformation/computation over other values, with method and input identity. | [L2788](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2788) |
| `SB-SRC-0019/DERIVATION-04` | `estimated` | A supported estimate under an uncertainty/model regime rather than an exact observed amount. | [L2789](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2789) |
| `SB-SRC-0019/DERIVATION-05` | `restored` | An inferred or reconstructed amount under a recoverable evidence/rounding/constraint envelope, as in SORS. | [L2790](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2790) |

### Ten original macro-series comparability dimensions

| Original item | Exact research term | What a consumer should ask | Source line |
| --- | --- | --- | --- |
| `SB-SRC-0019/MACRO-01` | `seasonality` | Seasonally adjusted versus unadjusted, adjustment method and available revisions. | [L2811](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2811) |
| `SB-SRC-0019/MACRO-02` | `revisions` | Has the release publisher revised the observation, estimation or definition? | [L2812](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2812) |
| `SB-SRC-0019/MACRO-03` | `real-time vintage` | What statistical information was actually observable at the queried decision time? | [L2813](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2813) |
| `SB-SRC-0019/MACRO-04` | `classification changes` | Was the measure/classifier definition changed or rebased over the interval? | [L2814](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2814) |
| `SB-SRC-0019/MACRO-05` | `price/current vs constant terms` | Are amounts at current or constant price terms and what deflator/base are used? | [L2815](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2815) |
| `SB-SRC-0019/MACRO-06` | `index base` | Is the index reported relative to which reference base and scale? | [L2816](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2816) |
| `SB-SRC-0019/MACRO-07` | `chain linking` | Are components chain-linked or additively comparable at this level? | [L2817](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2817) |
| `SB-SRC-0019/MACRO-08` | `geography` | Which geographical aggregation, boundaries and effective region codes apply? | [L2818](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2818) |
| `SB-SRC-0019/MACRO-09` | `observation vs estimate` | Is this a direct publication/measurement or an estimate with its own method? | [L2819](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2819) |
| `SB-SRC-0019/MACRO-10` | `nowcast vs forecast` | Is the target a current unobserved state estimate or a future forecast and what is its issuance vintage? | [L2820](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md#L2820) |

### Concrete failure tests

1. An RAS standalone report and consolidated IFRS report use the same Russian profit label: require explicit reporting perimeter, accounting basis, period/cumulative convention and reconciliation, or return qualified incomparability.
2. A regulator republishes a previous period under the same URL: the original observation vintage and derived report must retain their own exact data/transform version; a current revised series is a successor, not silent history replacement.
3. One statistic is `restored` under a rounding interval and another `reported`: a viewer must distinguish which publisher actually asserted and which calculation inferred the value, even if the numbers coincide at displayed precision.
4. A nominal macro aggregate is compared to a deflated/constant-price level or a chain index after rebasing: require comparability transformation with its assumptions; a matching column name is insufficient.
5. A source lacks the latest expected release: distinguish genuinely zero, unavailable retrieval, not-yet-published and failed import; the [current CBR forms runner](../../current-how/cbr-forms-semantic-model-and-missing-periods.md) demonstrates a specific risk of silently skipping missing archive dates.
6. An AI report describes a nowcast as an observed statistic or a conditional stress as a forecast: preserve claim type and historical information status rather than infer certainty from formatting.

These are **proposed assurance examples**, not observed passing system-level tests. The original contains additional arguments not exhausted by these nineteen source-addressed terms; product governance should test the required profile before adding a mandatory universal metadata table.
