# Source-first 0557 — twenty Artifact acceptance cases and five storage profiles

**Producer evidence tier / 2026-10-12:** `SELECTED_SOURCE_MATERIAL_CASE_IDENTITY_CONSERVATION`; **no** independent source-wide semantic losslessness, Product or infrastructure selection, actual NTFS/NAS/remote capability or released Artifact backend.

**Frozen primary:** `SB-SRC-0557` at `stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97`, blob `57ae0d79c91b8a5839668f73abfd7af4284f1142`, `research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md`, §15.1 L785–L808 and §15.2 L810–L824. **Scientific owner:** `docs/science/artifacts/output-identity-publication-and-availability.md`, new chapter `Original Topic 04 — twenty exact output/publication failure cases and five storage conformance profiles`. Current `docs/current-how/windows-application.md` and `docs/current-how/local-filestore-missingness-and-publication-limits.md` remain observed-code owners; `docs/lcd/artifacts/local-output-publication-construction.md` is a blocked candidate construction, not current behavior.

## What was preserved / what remains open

The Science already represented five distinct objects (domain Result, File payload, content revision, logical Artifact identity, locator), five-valued physical availability and separate Run/output/diagnostic publication truth. Original §15.1 contained **20 named test stimuli**, not just those general invariants. The previous producer Article's `ALT-01..12` history rows are separate source-conservation units, not a replacement for the actual A01–A20 test cases.

New existing-owner table conserves the one-to-one original:
- `A01–A05`: verified XLSX and Step identity, failed partial stream, non-existent output path, diagnostic-only successful log amid failed primary output, and independently ready files from a partly failed multi-output Run.
- `A06–A10`: intentional user rename/move/delete requiring no automatic search/restore, actual disconnected storage `UNAVAILABLE`, and object-level `ACCESS_DENIED` not generic missingness.
- `A11–A15`: no-clobber replacement, colliding concurrent publish, crash between bytes-finalization/catalog and catalog/UI refresh, and corrupt state with no silent erased history. A13 now uses explicit `OUTCOME_UNKNOWN` pending generation/intent reconciliation.
- `A16–A20`: a file-less output with no fabricated Artifact, mutable directory output not automatically a byte-immutable bundle, symlink/reparse/root traversal, cross-Thread origin and authorization, and same filename in two distinct Runs preserving separate Artifact identities.
- Five **different** storage conformance profiles: real Windows/NTFS sharing and Excel handles, Linux/POSIX fsync/EXDEV, SMB/NAS ACK and server semantics, object conditional generation/multipart, remote host/client read/reconnect/authorization.

All tests remain **target UNEXECUTED**, not new source-executing product safety outcomes. Local file operations, source and Windows synthetic evidence continue to have separate explicit limited truth. Source §15.2 does not authorize one universal backend transaction promise.

## Exact mechanical source check

New `tools/verify_artifact_0557_twenty_acceptance_cases.py` opens the exact primary Git source bytes with `pinned_source.read_pinned_blob`, requires source `A01..A20` in order with nonempty input/expected evidence, verifies five distinct original backend headings, then checks publication owner has **exactly one** meaningful table row for each `A01..A20`, five profiles and explicit `UNEXECUTED` qualification. The single existing CI workflow executes it. The validation is **structural** and cannot prove original Research meanings have been perfectly translated, any real filesystem is safe, or an actual output producer is available.

Intermediate [CI 38244428683](https://github.com/ForestTiger-GH/stratbox/actions/runs/38244428683) initially failed while Science's A13 row lacked the expected explicit `OUTCOME_UNKNOWN` label. The Science owner was corrected. [CI 38244521150](https://github.com/ForestTiger-GH/stratbox/actions/runs/38244521150) then identified an erroneous escaped Markdown-backtick pattern in the verifier, not a domain defect. After repairing literal-backtick matching, **[CI 38244608955](https://github.com/ForestTiger-GH/stratbox/actions/runs/38244608955)** at `stratbox@fb7210d2a681328dfd56cdc276d9842607771548` completed **SUCCESS** for this source-bound check and all existing workflow gates. No claim of independent 20-case acceptance execution follows from the green workflow.

**Bounded disposition:** directly source-addressed tests and physical backend distinctions now independently navigable from final Knowledge without re-opening Research. `SB-SRC-0557.material_unit_state` remains `unaccounted` until genuine other-reader whole-source verification; all 566 frozen source identities remain one census and the global `LOSSLESS_PASS` remains `BLOCKED`. The separate source 0560 five-contract/twelve-client case research correction has its own Work note and is not a second source denominator.
