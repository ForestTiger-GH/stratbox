# Post-publication navigation and scoped safety scan — 2026-10-09

**Exact inspected HEAD:** `93a53530749717e69a59d77118e3ff524336ba88`. **Method:** complete scan of all tracked `docs/**/*.md` at this Git tree, in two batches to respect connector limits; resolve relative Markdown link paths within tracked tree; scan maintained documentation for selected prohibited closed-source and methodological identifiers. **Actor:** producing agent, not an independent verifier.

| Check | Observation | Supported verdict |
| --- | --- | --- |
| Maintained Markdown files | 29 | File inventory only |
| Markdown inline links | 66 | Parsed URL syntax instances, not HTTP reachability |
| Local relative links | 44 | 44/44 resolved to tracked file paths |
| Broken local path links | 0 | PASS for local path resolution, not anchor/semantic link content |
| Selected public-safety identifiers in `docs/` | 0 matches | PASS for declared case-insensitive patterns only; not full semantic or Git-history security assessment |
| New Science evidence table | Four added source-use rows moved into the existing Markdown table | PASS for structural source-route placement; independent scientific assurance remains open |

**Boundary:** source-code and prior historical files were not modified. An earlier pre-existing public-code safety issue remains open for separately authorized work. No runtime tests, live package installation, independent cold reader, or full security clearance are implied by this report.

**Research Amputation:** global FAIL/OPEN. The source-unit census contains 553 stable source identities but retains `unaccounted` status pending independent complete semantic preservation. The 326 provisional units from 12 fully read sources are Work extraction evidence only.

**Reopen:** source path changes, new documentation publication, revised source/evidence claims, substantive Product Decision or independent security findings.
