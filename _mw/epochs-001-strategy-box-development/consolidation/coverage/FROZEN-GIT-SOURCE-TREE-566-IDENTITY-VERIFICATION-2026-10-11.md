# Complete frozen Git source-tree identity check — 566 of 566 paths and blob hashes matched

**Date:** 2026-10-11. **Audit type:** producer mechanical identity check, **not** independent semantic content preservation. All new checkpoint and repository materials in this workstream are authored in English.

## Verification method

The authoritative `sources/CENSUS.csv` was fetched from `ForestTiger-GH/stratbox@main`. Its **566** rows were parsed as source identities with `repository`, frozen `commit`, `path` and `blob_sha`. For each distinct `repository@commit` pair, the corresponding GitHub Git tree was fetched using the `git/trees/<ref>?recursive=1` endpoint. All four trees reported `truncated=false`. Each row was compared against the exact **blob entry SHA** returned for the exact relative path. No content was inferred from filenames or the current `main` working tree.

| Original repository and frozen revision | Census paths checked | Path+blob SHA matches | Absent paths | SHA conflicts | Git tree truncation |
| --- | ---: | ---: | ---: | ---: | --- |
| `ForestTiger-GH/stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580` | 338 | **338** | 0 | 0 | false |
| `ForestTiger-GH/stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b` | 198 | **198** | 0 | 0 | false |
| `ForestTiger-GH/AppDock@a4d87c643e620e54e04083d4d0b8d867513e7065` | 17 | **17** | 0 | 0 | false |
| `ForestTiger-GH/stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97` | 13 | **13** | 0 | 0 | false |
| **Total** | **566** | **566** | **0** | **0** | Four untruncated trees |

All four pin groups were available at their exact declared revisions. This establishes that **every frozen census row identifies a repository blob at the declared path and baseline** in the observed GitHub trees.

## What this proves and what it cannot

**Passed — source identity integrity:** the census is a valid address book for all 566 known frozen Git sources. Code, test, Research, supplemental platform contract and historically generated artifacts do not have to share one meaning or confidence level to pass this identity test. A source file modified on `main` after the baseline does not change the frozen verified blob identity.

**Not tested — source census completeness beyond declared scope:** the check did not compare the initial input-closure commission against *additional files that should have been admitted but were never placed in the 566-entry census*. That is a separate closure and inclusion/exclusion review.

**Not tested — full source meaning conservation:** all 566 `material_unit_state` entries remain `unaccounted`. The fact that source bytes are addressable does not prove every substantive proposition, negative result, counterargument, domain qualification, code behavior or test limitation has its own maintained destination and explicit decision.

**Not tested — whole-file content reading:** at this point 76 source entries were marked `full_read`, ten governance entries `governing_read`, 480 `not_full_read`. Of the 76, 54 are substantive Research originals, one is an orientation file, and 21 are direct code/test files. Reading a file is not material verification.

**Not tested — independent evidence and delivery:** producer item-level text/translated-content comparisons, installed code execution, source-regulator external verification, runtime failure tests, public-private security and Product Decisions remain distinct requirements.

**Separate non-Git human carriers:** the byte-for-byte verified preparatory architecture source `SB-EXT-0001` and full-text-readable, raw-DOCX-SHA-unverified annotated topics source `SB-EXT-0002` are not included in these 566 Git paths. Their source status is recorded in [human carrier recovery](HUMAN-CARRIER-RECOVERY-AND-ASSURANCE-DELTA-2026-10-11.md); their exact original text remains outside the public repo.

## Consequence for subsequent assurance

The source identity dimension can now be treated as mechanically checked and **does not need to be repeatedly rediscovered** unless the census/baseline changes. Subsequent independent source→Science and reverse Science→source reviews should use these exact pins and focus on **material semantics**, not guess whether a source path is real. If a late source is added, repeat the census-closure test and provide an additive baseline; do not silently rewrite the verified historical revision.

**Gate result:** `FROZEN_GIT_PATH_AND_BLOB_IDENTITY=566/566_PASS`; `MATERIAL_SEMANTIC_CONSERVATION=OPEN`; `INDEPENDENT_RESEARCH_AMPUTATION=OPEN`.
