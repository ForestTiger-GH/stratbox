# Bounded Science publication integrity check — 2026-10-11

**Git tree inspected:** `ForestTiger-GH/stratbox@df7581c5f7b5c6dced3403998ab9b82eb32ed233`. This verification supersedes earlier 28-file/117-link and 30-file/125-link source-tree snapshots.

| Directly observed scope | Result |
| --- | ---: |
| Enumerated `docs/science/**/*.md` files | **34** (32 standalone thematic Science articles, 2 README/navigation files) |
| Successfully read Markdown files | **34/34** |
| Inline Markdown local relative links checked | **130** |
| Links whose normalized destination file was absent from the same Git tree | **0** |
| Selected restricted-name lexical hits (`stratbox[-_]plugin` or `stratbox.plugin`, case-insensitive) | **0** |
| Installed runtime/fault-injection/a11y tests performed | **0** |

**Method:** inspect the exact recursive Git tree; enumerate each Science Markdown file; fetch the contents in four disjoint batches of **9 + 9 + 9 + 7** files; parse simple inline Markdown `[text](destination)` syntax; for each non-external and nonfragment path resolve `..` and `.` relative to its source folder and compare against Git-tree blob paths. Batch local link counts: **57 + 14 + 49 + 10 = 130**, with zero missing paths. A narrow selected lexical scan was performed on all 34 file bodies. This is a mechanical limited negative screen, not a private-information conformance certificate.

**Not tested:** fragment/heading anchors, reference-style links, HTML, external URI availability, source Git commit availability to anonymous readers, provenance/factual accuracy, confidential semantic descriptions outside selected spellings, approved product architecture, user-accessible UI, installed code/test/build behavior, complete source-unit extraction, independent Science→primary-code trace, audience authorization and Research Amputation.

**Bounded verdict:** `SCIENCE_RELATIVE_FILE_LINKS_PASS_34_FILES_130_LINKS`. It establishes only the checked tree-path structure, not global publication or semantic conservation. Re-run after future path/link changes and pair with independent evidence/security review.
