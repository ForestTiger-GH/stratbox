# Original Research 0020 and 0046 unspanned line-block triage

**Boundary:** work-only Research material-review packet for the same Strategy Box continuous consolidation. Input `stratbox@ddd1b2114b4cc8d3838802cabf24221837fbf47a`, CI [38251822535](https://github.com/ForestTiger-GH/stratbox/actions/runs/38251822535) SUCCESS.

## Why these originals

The preceding exhaustive **structural** source-span audit covered all 53 substantive Research originals and found no unreadable Git blobs or missing named Knowledge destinations. Twelve originals still contain nonblank lines outside *all* cited Work ledger spans: 0020 Windows current-state study (307 lines), 0046 whole-system model (62), 0016 business-refactor history (10), and nine smaller residuals. This is source-span **geometry**, not lossless scientific preservation or proof of omission.

Source 0020 sampled unspanned lines include its physical line 64 (Python file count in a dated tree), lines 106–107 (directory names within an ASCII file-tree), and 136/160/242/355 (Markdown framing, separators or chart/section boundaries). They already demonstrate that a naive rule “unspanned = missing material” is false. Conversely, an ASCII schema or table row **may** contain a material interface contract, and “looks like a tree” is not evidence that it can be discarded.

## New reproducible Work artifact

`tools/triage_unspanned_0020_0046_blocks.py` reuses the existing ledger coverage calculation and the pinned-source reader, then emits an exact-frozen line-envelope packet for **all** presently unspanned source blocks in 0020/0046. **Revised export boundary:** the retained JSON and CI console now include only original Git blob/revision, physical span, line count, count/shape-only heuristic and `reviewer_semantic_verdict=NOT_REVIEWED`, with a strict block-key allowlist; **no verbatim original-source text or truncated excerpt is emitted**. A qualified reviewer must read the pinned original separately through an authorized source channel. The JSON remains a Work-only CI artifact, outside `docs/` and distinct from Research.

The shape bins only organize human/independent work; the packet **does not** modify 566 census dispositions, mark whole sources as preserved or replace complete paragraph-level comparison. A real reviewer must classify each candidate as formatting/duplicate with identified canonical owner, preserved material with exact Science passage, conflicting alternative/defeater, or a concrete missing concept requiring repair. Repeat source↔Science and Science↔source tests after edits.

## Subsequent verification

At each future HEAD, check Work-only CI for exact path, original source identities and deterministic generation. Then inspect candidate prose/schema blocks for 0020 and 0046, update maintained Knowledge only for demonstrated material losses, and record independent verifier identity and verdict separately from producer. `LOSSLESS_PASS` and Research Amputation remain open until all-source evidence, not just this slice, passes.

## Public CI artifact minimization — 2026-10-12

The first triage tool version included original source lines in a retained GitHub Actions artifact and excerpt samples in CI logs. The original source corpus can contain contextual references unsuitable for a fresh public derivative; repeat export materially widens accidental disclosure without improving the structural gap counts. Starting with this revision the exported block schema is **explicitly allowlisted** to `span`, `envelope_length`, `untraced_nonblank_in_envelope`, `shape_hint_not_materiality` and `reviewer_semantic_verdict`. Top-level identity fields record the original Git version and file location; no original text is carried into `dist/` or console samples.

This change **does not erase previous CI artifacts**, alter the frozen original, independently classify any material, or certify that all upstream material is safe to publish. Earlier artifacts follow their GitHub retention/access controls; their status needs a separate review if restricted data exposure is suspected. Existing structural reviewer material remains reproducible by accessing the exact original separately. New HEAD must execute CI and show `METADATA_ONLY_NO_SOURCE_TEXT`, and source material dispositions stay unchanged.
