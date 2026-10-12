# FRG file-family selection, cleanup plans and effect evidence

**Status:** independent, qualified scientific/engineering guidance drawn from previously documented domain behavior and the current source-based [FRG cleanup study](../../current-how/frg-cleanup-effects.md). Historical names, cutoff dates and output modes are **dated behaviors**, not universal live provider guarantees. A reader needs no archived Research/Work links.

## 1. Filename recognition is weaker than source validation

A historical FRG stage-one scanner generated three distinct tables: `catalog` listing filename/path/period/family and recognition reasons, `latest` selecting one candidate per recognized family, and `dispatch` logging routing to parser *stubs*. A successful `dispatch` was not evidence that a full workbook parser or downstream bank-data validation had run.

The historical family selection recognized monthly, weekly, regional, card, mortgage, refinancing and quarter-like families. It normalized date separators and monthly/week numbers from filenames. An older region-schema cutover of **April 1, 2026** excluded recognized earlier regional files from `latest` but retained them in the full catalog. A publication date inferred from a filename is, at best, a naming claim; it is weaker than both the publisher's authenticated source vintage and the digest of the bytes actually used.

**Negative case:** two filenames map to the same family/period but have different bytes. Preference for a canonical naming scheme does not prove which file contains the authoritative latest regulator/provider release. A processing surface should reveal this choice and its limits instead of silently inventing a source-version receipt. [Source identity and reproducibility](source-identity-and-reproducibility.md) defines the necessary distinction.

## 2. Cleanup planning is separate from destructive authorization

The historical cleanup workflow had a safety-oriented **plan versus execute** distinction. Its documented policy scanned only the selected top-level folder and left subdirectories untouched. Files whose names were unrecognized or invalid for unrelated reasons remained untouched; a recognized old-period file could be considered for a specific supersession rule. The operation did **not** open or rewrite spreadsheet cell values: FileStore effects dealt with copying, renaming, deletion and byte bundling.

| Historical mode | Intended file treatment | Failure risk requiring a stronger application boundary |
| --- | --- | --- |
| Classify and select | Build catalog with eligibility/reason and per-family latest candidate | Filename parser conflates period ambiguity or unsupported schema with a valid publisher dataset |
| Copy without deletion | Copy the latest recognized file under normalized family/period name | Destination already exists; a stale plan may overwrite bytes or fail after partial copy |
| Destructive cleanup | Rename chosen latest and remove older *recognized* eligible duplicates or explicitly superseded files | Human approves one plan, filesystem changes, new file gets accidentally deleted |
| Dated ZIP of latest | Byte-bundle the result candidates under a date-stamped archive name | Existing archive overwritten; no stable previous revision/backup receipt |
| Background/automated mode | Same operation invoked without GUI when properly admitted | Scheduler label, provider readiness or static metadata bypasses actual per-effect authorization |

The correct safety invariant for any future app client is **plan identity and exact target set → applicability/authorization/approval → resource revalidation → bounded effect → verified receipt**. For risky rename/delete/replace, a later changed file must invalidate the earlier approval or force a fresh plan. A displayable preview is not effect authority. The current [FRG observed fault work](../../ldd/application/frg-cleanup-effect-guards.md) distinguishes executed synthetic failure characterizations from unexecuted target conformance.

### A frozen action is only meaningful inside its exact approved plan

A typed `FrozenAction` object is **not independently authorized** merely because its structure is valid. A caller could compose an action from a different plan, change the source/target after user confirmation, duplicate an action identifier or supply a previously valid `delete_source` whose file now belongs to another recognized family. The correct future host construction must check the action's **unique exact membership** in the frozen plan, compare the canonical target-set digest to the actual plan contents, require source and target within the approved scope, and revalidate the selected source bytes/generation and recognition/period before a destructive operation. An old record that says a file *was* recognized is not evidence about the bytes now at its path.

A failed in-memory precheck can justify `FAILED_NO_EFFECT` **only before the backend mutation starts**. Once a physical delete/rename/replace has begun, loss of response alone is ambiguous until a backend receipt or generation-specific reconciliation establishes the effect. Even a successful re-read of source bytes before deletion has a TOCTOU window; a real storage adapter must enforce compare-and-delete/replace against the same generation rather than trust a filename or dataclass. A local application method may add these candidate guards without inventing a distributed IAM engine, but the existing direct Python `apply_frg_cleanup_plan` function remains a separate, less guarded implementation at the pinned revision.

The scoped [FRG candidate LCD](../../lcd/application/frg-cleanup-effect-plan-construction.md) illustrates checks and their artificial test doubles. They are **not** evidence that the present core has frozen-plan authenticity, verified approval, OS-level confinement or generation-fenced effects. Those qualities require actual implementation and native/storage fault testing; domain source/version claims additionally need real byte receipts, not filename chronology.

## 3. Weekly files and normalized-name ties

For a historical family with several weekly files in one month, earlier weeks could be classified `superseded_by_newer_week_in_same_month`; the rest of the dataset catalogue must retain that exclusion reason. When a raw supplier file and an internally normalized filename refer to the same family/period, the historical selector preferred the internal format. This is a **local file selection policy**, not an official updated-data receipt.

The earlier output ZIP followed a `FRG_Actuals_YYYY-MM-DD.zip` naming convention and could replace a same-named archive. That makes the apparent daily archive name inadequate for immutable version identity unless byte digest, actual publication/collection times, provenance and overwrite policy are recorded by the relevant operation.

**Negative cases:** (1) an overwritten archive is mistaken for an unchanged original source; (2) a weekly cutoff applied to the wrong month drops the only valid candidate; (3) unknown files are destructively treated as old; (4) a successful output path masks a failed partial file operation. The financial source's actual publication content and the application approval are distinct from a convenient FRG filename pattern.

## 4. Application and core responsibilities remain separate

The reusable `stratbox` library should expose stable useful domain operations and source-defined file rules independent of a particular desktop, browser or future Android widget. The product/application layer chooses user-friendly forms, presentation, confirmation and authorized effects. A provider/network/FileStore runtime may offer transport and byte operations, but **discoverability is not authorization** and a historical `dict` of DataFrames is not proof of a stable machine-executable operation-result schema.

**Open validation:** a future release needs real source-family fixtures, malformed/unrecognized filename adversarial cases, locale/date/version tests, deterministic selection receipts, symlink/alias protection as applicable to the host deployment, stale-plan mutation injection, ZIP overwrite/failure consistency and per-user/automation authorization. No such live application conformance is claimed here.
