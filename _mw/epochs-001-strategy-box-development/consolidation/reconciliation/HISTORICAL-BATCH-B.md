# Historical Research extraction — batch B (sources 0015–0016)

**Status:** all historical files in `SB-SRC-0012..0016` have now been read in full and provisionally extracted. No source has been admitted as a fully conserved Scientific Knowledge source; each master `material_unit_state` remains `unaccounted` pending independent semantic-role review and final-source owner confirmation.

## Direct source accounting

| Source | Pinned blob | Full original read | Provisional units |
| --- | --- | --- | ---: |
| `SB-SRC-0015` | `a2339ebc79f72a075d290b761fda7b8997b15710` | yes, L1–L107 | 14 |
| `SB-SRC-0016` | `d04fece78c89063c2ac2dac775179f1517c7fea9` | yes, L1–L1927 | 32 |

**Authoritative Work ledger:** `units/HISTORICAL-0015-0016.jsonl`. Repetitions in the 1,927-line refactoring source have explicit derivative dispositions, not a false increase of independent confirmation. `CENSUS.csv` keeps exact identities/commit/blob and changes only the two `read_state` fields to `full_read`. The corpus denominator remains 553.

## Historical/current reconciliation with direct code

| Historical point | Current direct evidence (pinned) | Result / importance |
| --- | --- | --- |
| FRG stage-one output was a dictionary of three tables | `src/stratbox/macrobanks/frg/api.py` blob `25d53f4502242a2979f0bc5dd2ea1c4faf8ff807` | **CONFIRMED** this bounded return shape; proposed typed operation family remains unadmitted |
| Regulatory forms batch produced file paths | `src/stratbox/macrobanks/cbr_forms/api.py` blob `392cca41ce2124e7aef7101d6f7aa65fb56a248b` | **CONFIRMED** `dict[str,str]` of exported paths; no evidence of a separate full-result public model in this entrypoint |
| Early raw-source collection used a different name and pipeline shape | `src/stratbox/macrobanks/cbr_file_collector/operations.py` blob `ae8b70122491f9930182c5139a90e6254195b53e` | **STALE NAME**; current `collect_cbr_files(request)` uses typed request/result and explicit partial failure counts |
| Early escrow summary said export dominated the public interface | `src/stratbox/macrobanks/escrow/operations.py` blob `c8427310fa235146954ff3e24b63f8d24dcb1f0b` | **STALE CLAIM** for full public layer: discover and history-build operations now exist separately, besides export |
| Earlier app and library were described as residing in the same repository | current `stratbox` root README, current `stratbox-windows/appdock/manifest.json` blob `98004fb56cb6e19c3c88990fd51d6aa7724828c9` | **SUPERSEDED PHYSICAL TOPOLOGY**; preserve original for historical reconstruction, not target/current implementation |
| Historic domain patch reported green compilation/import/mock checks | Historical prose alone, no executed test receipt in this Work | **HISTORICAL REPORT**, not current test pass |

## Meaning that must remain distinct

- Subject operations, product projections, user scenarios, execution runs and platform exposure are different semantic roles. The old three-register proposal may inform a future decision; it must not dictate physical package layout, public API IDs or Product acceptance.
- Read-only collection, planned cleanup and applied destructive actions have materially different risks and confirmation requirements.
- Source schema differences, missing indicators, raw-byte preservation, source filenames and period-specific variants affect the analytical consumer even when they seem like implementation details.
- Historical quality judgments are mixed: neutral core infrastructure and existing domain functionality were praised; UI coverage and contracts were criticized. Preserve both and do not convert the critique into an unverified claim about today's code.
- One narrowly located historical statement is **excluded from public derivation** under the publication boundary. Its exact wording is retained only in the unchanged original. Nothing identifiable from that statement is reproduced in the Work ledger, maintained documentation or report.

## Readiness and next route

The five historical files have **full-read** source flags and **provisional extraction** ledgers containing a total of 76 units. This is a material improvement in input accountability but **not** an independent proof of complete semantic conservation or of accepted Target obligations.

**Next authorized input:** the 27 substantial `02-base-study` documents, with independent source IDs and original line spans. Begin with the exact base-study README and the directly evidenced current-state core/Windows studies, then expand across interrelated concern families. Maintain a single census, new distinct material units, source-use relations, and explicit common-origin rather than counting repetition as new evidence.
