# Research census verification — 2026-10-09

**Purpose / Work:** exact source accounting without substantive claim synthesis.  
**Method:** read the pinned CSV and three exact Git trees via GitHub API; compare every row's path and blob SHA, preserve stable IDs; compare the pinned core tree against execution HEAD. No runtime tests executed.

| Declared subset | Exact pinned revision | Expected / recorded | Found and matching blob SHA | Missing / mismatched / extra within declared subset |
| --- | --- | ---: | ---: | ---: |
| Core full tree | `8459dc58922b7e8df853cf1d9e8131fa9e132580` | 338 / 338 | 338 | 0 / 0 / 0 |
| Windows full tree | `959e9c4ce1441124af5111c1e025041714e04d3b` | 198 / 198 | 198 | 0 / 0 / 0 |
| AppDock selected contracts | `a4d87c643e620e54e04083d4d0b8d867513e7065` | 17 / 17 | 17 | 0 / 0 / 0 |
| **Declared CSV** | preserved file census | **553** | **553** | **0** |

**ID integrity:** 553 unique `SB-SRC` identities; no repeated IDs. All 553 are still `unaccounted` at semantic-unit level. Reading indicators: 541 `not_full_read`, 9 `governing_read`, 3 `targeted_read_not_extracted`. Previous read labels describe preparatory reading only; this verification has **not** promoted them to extracted/reconciled/verified.

**Boundary:** 17 AppDock entries are an explicitly selective integration-contract cohort. AppDock's pinned full tree has 1966 blobs, so **1949 are intentionally outside this declared selection**; absence from this selection is neither evidence of irrelevance nor a completeness claim about the platform. User-provided architecture research is an additional candidate input, indexed separately below because it has no Git blob in the pinned source trees.

**Core late-delta:** execution `stratbox@5cff9157460c2035aa42758b505cce65b7c53f47` is two commits beyond the pinned census core revision. Commit comparison reports exactly nine changed paths: `AGENTS.md`, `_mw/AGENTS.md`, `_mw/README.md`, `consolidation/BASELINE.md`, `CYCLE.md`, `METHOD-ROUTER.md`, `README.md`, `STATE.md` and `sources/CENSUS.csv`. **No changes in `src/`, `tests/`, `docs_old/`, `examples/` or `scripts/`** in this delta. Existing pinned identities remain a valid frozen evidence baseline; local governance at execution uses current checked-in files.

## Supplementary human input — separately bound, not a new CSV row

- **Identifier:** `SB-EXT-0001` (separate from original `SB-SRC-0001..0553` sequence).
- **Type:** Human-supplied, preparatory public-safe architectural Research, dated 2026-10-09.
- **Carrier name:** `Strategy_Box_Knowledge_Consolidation_Architecture_Research_2026-10-09(3).md`.
- **Bytes/lines:** 141617 bytes / 1229 lines.
- **SHA-256:** `55566a99bd7efd3311b428a374273796a06634fd2a963475344001816d4a584b`.
- **Access:** supplied to current Commission; not mounted in or mirrored to public GitHub. Its source-level claims need validation with direct owners. It is a Research input, **not adopted Target WHAT/HOW**.
- **Current disposition:** admitted for bounded inspection and KPA challenge; substantive material units not fully extracted; reproducibility requires obtaining the exact carrier from the authorized user/attachment context.

## Additional proof obligations

1. Research-derived assertions and synthesis 00–09 must be reconciled with original studies and direct code.
2. Study 08 ↔ 09 requires exact cross-theme qualification; older 09 states that 08 was not available when it was written.
3. `docs_old/` content requires eighteen independent source-to-owner dispositions; archived-byte preservation alone is insufficient.
4. Source-representation and source-use ledgers remain unbuilt; file completeness and semantic conservation must never be conflated.
5. Public security review applies to `docs/`, work reports and eventual diff, with no restricted-source identity imported.

**Result admission:** PINNED FILE CENSUS VERIFIED / SEMANTIC CONSERVATION OPEN. No edits to the existing `CENSUS.csv` are warranted on these findings.
