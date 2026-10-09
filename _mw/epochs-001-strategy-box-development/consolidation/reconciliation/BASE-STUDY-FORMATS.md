# FileStore formats and codec scope — Research material extraction

**Input:** `SB-SRC-0028`, complete L1–L2700, pinned blob `b54bfcefd0784a5c45366cd8382364193223577d`. Extracted 38 provisional units in `units/BASE-STUDY-0028.jsonl`. Source identity/commit/blob unchanged; only `read_state=full_read`; full independent semantic conservation remains `unaccounted`.

## Source claims, counterexamples and limitations

**Five levels are different capabilities:** opaque byte transport; format identification; generic decoding; generic encoding; and validated domain-specific semantic interpretation. This is more precise than a single boolean “supports XBRL/PDF/XLSB.” Actual supported modes can differ across read/write, platform and installation extras. FileStore itself remains format-neutral, while a shared FormatRegistry, codecs and source-specific/standards-specific semantic adapters are target candidates.

**Current evidence:** pinned `src/stratbox/base/ioapi/excel_xlsb.py` blob `01756eea7225da7127e37f8770f5392dea16d7d2` exposes a read path and a write stub; `docx.py` blob `f7df866e25b4b3ac3df5022286b7dfca70000bdf` has basic `read_text/write_text` paths; `zip.py` blob `735d40f5ebcffac57712114be4711562cc142b24` includes an `extract_to_memory` path; `excel_xlsm.py` blob `7d5e300cbf1e605dbdaf98ec635f786855f7f94b` includes `auto_install` paths. These static implementation facts do not prove installed engine availability, macro preservation, arbitrary ZIP safety or green tests.

**Material negative knowledge:**
- A filename suffix is insufficient identification when a server sends an HTML error/login response instead of an expected official data file.
- Generic XML/JSON parsing is not equivalent to full XBRL or SDMX semantics, including taxonomy/structure validation.
- Spreadsheet formulas, cached values, VBA macros, encrypted files, CSV encodings and archive traversal/decompression all need explicit behavior and error classes.
- PDF extraction, table parsing, OCR and report generation are four different contracts; the current text helper does not imply reliable document analytics.
- Archive extraction, document macros and externally supplied content require security/resource limits. These are proposed test criteria, not approved security assurance.
- Format registry and domain operation accepted formats are useful hypotheses; priority P0/P1/P2 matrices are Research choices rather than supported release capability claims.

**Reconciliation with artifact Research:** artifact identity is independent of byte-format identity; a physical encoding and domain-specific semantic source schema may coexist in provenance. Cache/materialization policies and byte integrity belong to the applicable owners, not to a magical universal file parser.

**Status:** full Research read, selected direct-source crosscheck and qualified provisional unit accounting. Independent exhaustive original-to-Science conservation, direct code coverage, current external standards validation, security assessment, Product commitment and Research Amputation remain OPEN.
