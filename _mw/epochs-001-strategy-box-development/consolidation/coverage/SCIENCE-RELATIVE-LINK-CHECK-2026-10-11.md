# Bounded Science publication integrity check — 2026-10-11

**Repository:** `ForestTiger-GH/stratbox@main`, source tree resolution returned `be09c5400566a452022fb7714c978c5a5fa6637c` during this producer-side check. **Scope:** all 28 Markdown files beneath `docs/science/`: 26 independently readable thematic papers plus the navigation and source-use README files.

## Exact measured results

| Check | Observed outcome |
| --- | ---: |
| Enumerated Markdown files under `docs/science/` | **28** |
| Markdown relative link occurrences matched by the basic `[label](target)` pattern | **117** |
| Missing file destinations after resolving `../`, `./` and relative paths against the Git tree | **0** |
| Source files unavailable to read by the connected GitHub API | **0** |
| Hits for selected restricted-name patterns `stratbox[-_]plugin` or `stratbox.plugin`, case-insensitive, among 28 files | **0** |

**Procedure:** obtain the recursive Git tree of `main`; enumerate each `docs/science/**/*.md` blob; fetch actual file contents at `main`; parse visible Markdown inline relative links; normalize each link path and compare with exact enumerated Git-tree blob paths. Counts are from three disjoint batches of nine, nine and ten source files, with respectively 50, 18 and 49 local link occurrences. The selected restricted-name scan is a very narrow mechanical screen, not a full confidential-information clearance.

## What this check does not establish

- Section anchors, link fragments, unusual Markdown reference-style link syntax, encoded external URLs, embedded images and absolute links were **not** comprehensively resolved.
- External websites, source commit freshness, publication authority, citation authenticity and link accessibility for a reader outside the authenticated connection were **not** revalidated.
- The restricted-name search covers only specified lexical patterns. It does **not** prove absence of confidential concepts, accidental identifiers or indirect descriptions.
- This is **not** independent Source→Science, Science→direct-evidence, cross-theme contradiction or cold-reader Research Amputation testing.
- Code, installed Windows/AppDock, Python behavior, backups, actual filesystem crash safety and GUI/host/multiuser behavior were **not tested**.

**Verdict:** `SCIENCE_MARKDOWN_RELATIVE_FILE_LINKS_PASS_BOUNDED`. This is a structural signal for the tested main-tree snapshot, not complete publication approval. Re-run on any later Science or documentation link change; pair with independent content, evidence, security and source-conservation checks before publishing a global Knowledge Product completeness claim.
