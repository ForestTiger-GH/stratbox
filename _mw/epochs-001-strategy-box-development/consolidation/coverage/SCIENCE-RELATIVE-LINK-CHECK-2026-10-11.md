# Bounded Science publication integrity check — 2026-10-11

**Source tree observed:** `stratbox@c8664a0f9ad29134515c8eb6460ef104e57b6dec`. This check supersedes the previous 28-file/117-link snapshot after two Science modules were added.

| Bounded property | Direct observed result |
| --- | ---: |
| Science Markdown source files | **30** (28 standalone subject papers + 2 index/source-guide files) |
| Fetched/read successfully at `main` | **30/30** |
| Inline Markdown local relative file-link occurrences | **125** |
| Missing relative file destinations after Git-tree path normalization | **0** |
| Hits in these 30 files for selected restricted-name spellings (case-insensitive) | **0** |
| Implementation/runtime tests executed by this check | **0** |

The four disjoint read batches contained **8, 8, 8 and 6 Markdown files**, respectively, and **53, 11, 51 and 10** local relative links. Each visible `[label](target)` link with a non-URL, non-fragment target was normalized relative to its actual source file directory and compared against the complete Git-tree blob-path set at the observed tree revision. The restricted-name lexical screen looked for `stratbox[-_]plugin` and `stratbox.plugin` spellings in the retrieved Science body. This is a deliberately narrow confidentiality sanity check; no private implementation was analyzed as part of publication.

**PASS, within bounded scope:** all 125 checked local relative file paths existed in the same observed tree, and no selected lexical hit appeared. **Not checked:** target anchors; reference-style Markdown; HTML links; external site reachability; factual accuracy; contract/commit/code source validity; all private-information classes; semantic source conservation; independent review; cold-reader Research Amputation; installed Python/Windows or host runtime. A structural link success is not a global publication-security or product-readiness certificate.

The producer should rerun this test after link/path modifications, independently inspect source→Science and Science→actual direct evidence, and obtain separate authorized security clearance before calling any global publication complete.
