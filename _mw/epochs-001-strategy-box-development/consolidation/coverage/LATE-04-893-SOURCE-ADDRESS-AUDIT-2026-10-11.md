# Late research program 04: 893-unit source-address and Science-route structural audit

**Date:** 2026-10-11. **Status:** PRODUCER-EXECUTED STRUCTURAL CHECK / SEMANTIC CONSERVATION NOT CERTIFIED. This is a separate recorded pass over all **twelve** frozen late-04 Research originals (`SB-SRC-0554` through `SB-SRC-0565`). It does not assert an independent expert review, that a file route establishes meaning preservation, or that global lossless consolidation is complete.

## Scope and actual checks

1. Fetched `sources/CENSUS.csv`, the twelve source-unit JSONL ledgers, and **all twelve original Research files** at their exact frozen Git commit `388e3d61ec01350d3b7d35ea4a97a21db0b36f97`, rather than relying on their mutable present-day `main` links.
2. Verified that all twelve original Git blob SHAs **exactly matched** the frozen census and unit references.
3. Parsed **885 original source-addressed entries**; checked source identity, recorded blob SHA, `source_span` syntax and in-file line-range bounds, and nonempty `meaning`. **Zero malformed/out-of-bounds ranges** found.
4. Verified **885 distinct unit IDs**, **14 distinct existing Science destination files**, and that every referenced numbered destination section exists in the maintained Science at the time of the pass. The original inventory had **651 section-level destinations** and **234 document-level-only destinations**. Document-level-only pointers are materially weaker than exact per-claim anchors.
5. Reconstructed a union of the original line-range coverage: **11,713 / 11,769 source lines** were within at least one source unit; **56 lines were not address-covered**. This is **line address coverage only**: broad windows and overlapping spans do not ensure individual claims have been extracted.
6. Examined the uncovered line text directly. Recovered **eight additional first-party research units** that preserve substantive prefaces/method interpretation: four `SB-SRC-0556` state-study entries, three `SB-SRC-0562` source-vintage entries, and one `SB-SRC-0565` alignment-matrix legend. Each is `OPEN` for semantic review and has a located candidate Science owner; none is treated as a new user instruction or Product Decision.
7. Re-ran range arithmetic after additions. Final **893 unique candidate material units**, **11,741 / 11,769 source lines address-covered**, **28 uncovered**. No new invalid source span was found. The 28 uncovered lines were primarily blank/separator lines, with two section headings; no claim of a complete *semantic* scan of every sentence is made.

## Per-original structural evidence

| Frozen original ID | Original lines | Candidate unit rows now | Unaddressed source lines | Nature of remaining uncovered text |
| --- | ---: | ---: | ---: | --- |
| `SB-SRC-0554` | 1,555 | 80 | 0 | All raw lines lie within at least one section window. |
| `SB-SRC-0555` | 1,143 | 75 | 0 | Broad and overlapping windows, not exact claim preservation proof. |
| `SB-SRC-0556` | 785 | **80** (+4) | 12 | Mostly empty lines/separators, plus a section heading at line 75. |
| `SB-SRC-0557` | 986 | 64 | 3 | Section heading 540; blank lines 541, 718. |
| `SB-SRC-0558` | 1,206 | 76 | 1 | Terminal blank line. |
| `SB-SRC-0559` | 1,166 | 72 | 0 | Entire source line range addressed. |
| `SB-SRC-0560` | 704 | 68 | 0 | Entire source line range addressed. |
| `SB-SRC-0561` | 1,264 | 86 | 0 | Broad and overlapping source windows. |
| `SB-SRC-0562` | 684 | **75** (+3) | 12 | Separators/empty lines; source executive premise recovered. |
| `SB-SRC-0563` | 759 | 70 | 0 | Entire source line range addressed. |
| `SB-SRC-0564` | 892 | 75 | 0 | Entire source line range addressed. |
| `SB-SRC-0565` | 625 | **72** (+1) | 0 | Original 44-row matrix legend restored as a separate claim. |
| **Total** | **11,769** | **893** | **28** | **11,741 lines within at least one window; 99.76% mechanical address coverage.** |

The eight new records are not counted as independently transferred exact quotations. Their `mapping_status` is `newly_extracted_from_unmapped_source_lines_semantic_validation_open`; their destinations are candidate owners. Research-derived high-level conclusions are separate from actual human commands and from code-observed behavior.

## Primary-human attribution integrity

The original annotated ten-topic questionnaire is fully available as an authorized Library **text extraction**; its raw DOCX bytes remain unavailable for SHA-256 attestation. The **30 historical `HUMAN_INTENT`-tagged unit records** have individual scope/classification fields: **14 direct comments, four with engineering or trust-profile interpretation, eight mostly Research interpretation, two unsupported technical details, one question-author prompt, one composite**. The authoritative original file has **ten** annotated topics, not twelve. The `SB-SRC-0562` rows now explicitly say the annotated text has been read, while retaining the unresolved original DOCX binary identity. These facts restrict what Target WHAT may call a developer instruction.

## Limits that remain materially open

| Gate | Actual result |
| --- | --- |
| Exact frozen source identity for twelve 04 originals | **PASS: 12/12 original blob SHA matches.** |
| Basic source-span syntax and bounds, unit identity | **PASS: 893 candidate rows; no invalid range; IDs unique on structural pass.** |
| Science destination existence | **PASS: 14 distinct named Science files; 659 section-level pointers resolve to existing numbered headings, 234 have only file-level destinations.** |
| Raw line union address coverage | **11,741/11,769 (99.76%)**, includes broad windows and overlaps; not equivalent to semantic coverage. |
| Per-unit semantic equivalence, assumptions, alternatives and negatives | **OPEN.** A `meaning` paraphrase and a `Science §N` locator may still omit or distort original nuance. |
| Exact source-to-claim anchor within destination | **OPEN** for all provisional units; 234 document-level-only destinations require stronger traceability. |
| Reverse audit from every Science claim to direct sources | **OPEN.** File existence and heading existence are necessary but insufficient. |
| Independent, adversarial semantic check / Research Amputation | **OPEN** beyond the separately recorded eight-question producer sample. |
| Complete 566 Git source material dispositions and true final Product decisions | **OPEN**; no general lossless claim permitted. |

## Next meaningful semantic gate

Select representative and risk-weighted units from **each of the twelve** 04 papers, especially all Research-attributed human choices, negative findings, material architectural contradictions, and source-specific domain behavior. For each record, compare the **exact original line context** against the **actual destination paragraph and qualifiers** and identify: `PRESERVED`, `REFINED_WITH_CAUSE`, `CONFLICT_PRESERVED`, `OPEN_WITH_OWNER`, `OMITTED` or `UNSUPPORTED_STRENGTHENING`. Where the destination is only a file path, assign an exact section or explain why a multi-section consolidation is essential. Repeat with independent reviewers and reverse-audit over Science claims. Only then may a unit state leave `unaccounted`.

**Publication/language policy:** this audit is written in English. The 12 primary historical source originals retain their original language; their texts and any protected source bytes have not been copied into maintained Science. No application business logic or Product Decision was changed in this pass.
