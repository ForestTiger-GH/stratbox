# Bounded evidence progression: 568 checked source items, 20 candidate source routes

**Checkpoint:** 2026-10-11, English maintained research record. **Status:** full GitHub Actions producer *traceability* checks PASSED; complete semantic losslessness and independent adversarial assurance remain OPEN. This file supersedes earlier 435-item numerical *producer progress* claims, not their frozen historical evidence.

## 1. Executed GitHub Actions evidence

[CI run 38174342407](https://github.com/ForestTiger-GH/stratbox/actions/runs/38174342407), head `8143d4194062b91734abe0228f21baa3e0b5b91a`, completed successfully. The real GitHub checkout executed:
- `tools/verify_exact_material_transfers.py`: **568/568** identified source item mappings passed original Git blob/line and maintained destination/relative-link checks. **53** Science Markdown files and **261** relative Science links were present. **83** maintained Markdown files and **325** local relative links resolved; zero reported trace/link issues.
- `tools/audit_research_material_coverage.py`: inventory source identity check passed, and all **566** frozen Git source identities matched expected SHA/paths.

[CI run 38174464629](https://github.com/ForestTiger-GH/stratbox/actions/runs/38174464629), head `ce25003fe1bd5908520fa5c67c45f107b931e69e`, also passed after a key epistemic classifier correction and source-route inventory were added.

This **is executed code in a full checkout**, unlike the older GitHub-connector-only checks. However, the checker intentionally tests **identity, source position, English text presence and file-path integrity, not whether an English translation has retained every original qualification or whether the original proposal is scientifically valid**. Product runtime/pytest/conformance, installed host, browser and external statistical publication validation were not exercised.

## 2. Do not combine different evidence classes

| Evidence class | Registered units | Actual strength |
| --- | ---: | --- |
| Source-exact material transcriptions | **485** | Original source wording and/or exact source rows recorded with a maintained destination; **producer**, not independent semantic conservation. Includes an existing 50-invariant Topic 08 inventory. |
| Original-row-traced English interpretation | **83** | **47** Topic 09 invariant/test rows already maintained plus **36 newly added Topic 08 fault-injection cases**. Source IDs, exact original lines, SHA and English destination are checked; translated meaning is not independently verified. |
| Producer-provisional semantic candidates | **3,849** | Preliminary addressable findings from Research; no material equivalence guarantee. |
| Section locator only | **1,435** | Headings/sections for navigation; not material-semantic claims. |
| Direct code/test source reads | **21** | Static evidence of exact frozen implementation/test source, not test execution. |
| Source-level candidate routing entries | **20** | Proposed primary and alternate maintained Science destinations for otherwise unassigned Research sources, **not successful transfer of their material meaning**. |

These categories use different units and can overlap at the original-source level. **Do not sum them as a global semantic completeness numerator.** The 568 check concerns **source-item links**, not 568 independently proven economic/scientific facts.

## 3. Why a duplicate Science page was deleted

The existing canonical [Topic 08 Science owner](../../../../docs/science/trust-and-assurance/system-quality-assurance-threats-and-failure-gates.md) already contained the 50 source-exact `SB-Q` candidates. The existing [Topic 09 architecture Science owner](../../../../docs/science/architecture/system-architecture-profiles-decisions-and-evidence-gates.md) already held 32 English `INV` and 15 `TQ` rows. A new page generated during this pass redundantly copied those 97. It was **removed**, along with its 50/47 duplicate locators.

The genuinely missing **36 source-addressed `F01–F36` Topic 08 failure fixtures** were instead added to the existing canonical quality article (§12). Their single [JSONL ledger](../units/QUALITY-08-NEGATIVE-36-ENGLISH-LOCATORS.jsonl) records exact original rows and their English interpretations. The original Research is preserved; no source content was erased. The public Science count stays **51 thematic articles plus two guides = 53 Markdown files**.

## 4. Correction of the coverage inventory itself

The first version of the automated inventory inferred evidence class from an incomplete list of ledger prefixes. As a result, its initial output called the **47 already line-traced Topic 09 rows** and **36 new Topic 08 fault injections** only provisional semantic interpretations. That incorrectly erased their concrete source-line/destination evidence.

The corrected tool has distinct, deliberately weaker-than-semantic-assurance classes:
- `exact_text_transcription` = **485**, containing explicit original wording;
- `source_row_traced_english` = **83**, containing original-id/source-line/English rendered meaning without a verified exact-text equivalence claim.

The current inventory check passed, with **66 JSONL ledgers**, `inventory_issues_count=0`. The tool also separates `source_routing_only` from material source-to-Science destination. This is a methodological integrity correction, not a newly discovered product requirement.

## 5. Twenty Research originals with candidate destinations, not yet conserved

All **53 substantive Research originals** have primary-read status and at least a producer-provisional unit set. But **20 original files** had no substantive destination recorded by the inventory. They now have explicit **source-level routing candidates** in [a 20-row JSONL ledger](../units/RESEARCH-ORIGINAL-CANDIDATE-ROUTING-20.jsonl) pointing to existing canonical Science owners, with each source's frozen path/blob SHA and an English route rationale.

Routing does **not** close material coverage: the audit continues to report **20 originals without an actual Science material destination** and all **566/566 material source entries as `unaccounted`**. It separately reports **zero originals lacking even a candidate route**. Exact or English source-row mappings exist for **nine substantive original files**; the other **44** still lack such item-level trace in the automated inventory. Their numerous provisional units cannot be silently promoted to exact transfers.

No new user feature, host implementation, AI capability, or physical repository was approved in this routing process.

## 6. Corpus denominator and human-source identity

Frozen Git census: **566 entries** = **77 `full_read`** (53 substantive Research originals + 3 orientation READMEs + 21 code/test sources), **10 `governing_read`**, **479 `not_full_read`**. This corrects the earlier erroneous label of **54 substantive Research originals**: one extra research README had been included as if it were a substantive study.

Separately mandated user carriers:
- `SB-EXT-0001`: **reconstructed exact 141,617 bytes and verified SHA-256**, full primary reading;
- `SB-EXT-0002`: full ten-topic annotated primary text read through Library; **original DOCX binary SHA-256 still unverified** due to restricted raw materialization.

Thirty source-attributed user-intent claims have individual primary-text qualifiers. These remain distinct from accepted Product Decisions.

## 7. Open gates and next accountable sequence

1. **Substantive destination gaps:** transfer missing material propositions, negative results and competing models from the twenty routed original sources into canonical Science, then audit original↔destination in both directions.
2. **All 53 Research originals:** verify every materially distinct passage and its relevance/disposition, not merely the 568 item subset or 3,849 provisional findings.
3. **Remaining 479 frozen Git files:** dispose by role—source/test/asset/current code/forensic material—rather than pretending all code must become Science prose.
4. **Exact human DOCX identity:** resolve binary SHA or preserve text-only uncertainty; do not infer hash from extracted text.
5. **Independent assurance and cold-reader Research Amputation:** adversarial audit of Science scientific truth, countercases, source semantics, and full ability to work without opening historical Research.
6. **Product authority:** require explicit approved choices before admitting host persistence, multi-user Web scope, exact machine APIs and acceptance gates.
7. **Public confidentiality review:** do not duplicate closed implementation-specific statements from historical Research into public Science, even if frozen source already contains them.

**Bottom line:** the producer **traceability** gate has a real passing CI result and a corrected non-overclaiming evidence inventory. The **whole-product lossless** gate is **not** met.
