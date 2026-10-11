# Epistemic attribution repair and direct source-receipt code audit

**Date:** 2026-10-11. **Status:** bounded producer challenge with direct code evidence; not a global lossless/independent audit, original user-carrier recovery, accepted API migration or runtime conformance pass.

## 1. Why a previously published `HUMAN_INTENT` status was too strong

The twelve dated `04-ai-raised-topics` originals frequently restate developer comments from an annotated research-topics document. The exact original human carrier `SB-EXT-0002` remains unavailable in this consolidation environment, while `SB-EXT-0001` (a separately required preparatory architectural study) is also missing. The original 04 paper can be read and pinned, but **the existence of a statement in Research does not independently attest the exact original user's phrasing or commitment**.

An eight-source? **No:** the inventory is **seven** affected source ledgers, exactly **30** tagged unit rows out of those seven ledgers' **512** units. The complete 12-paper 04 unit inventory comprises **885** items, of which 30 had status `HUMAN_INTENT`. A direct reassessment of the seven ledgers confirmed exactly **30/30** now also carry:

```text
human_intent_original_carrier_verification = UNVERIFIED_EXACT_USER_CARRIER
human_intent_attribution_basis = primary_Research_reports_developer_instruction; exact underlying annotated human input unavailable
human_intent_product_admission = NOT_INFERRED_FROM_RESEARCH
```

The original `semantic_status`/`epistemic_status` is preserved for forensic continuity. The added machine-readable layer **qualifies** it; it does not invent a new original user command, retroactively withdraw an actual human commission, or label all engineering content false. Some independent user instructions may be verified by another actual human source; until exact corroboration that link remains open.

| Primary 04 unit ledger | Research-reported human items | Original human-carrier status |
| --- | ---: | --- |
| `units/LATE-04-ONTOLOGY-0554.jsonl` | 2 | UNVERIFIED |
| `units/LATE-04-LIFECYCLE-0555.jsonl` | 9 | UNVERIFIED |
| `units/LATE-04-STATE-0556.jsonl` | 4 | UNVERIFIED |
| `units/LATE-04-SURFACES-0560.jsonl` | 5 | UNVERIFIED |
| `units/LATE-04-SOURCE-0562.jsonl` | 4 | UNVERIFIED |
| `units/LATE-04-OWNERSHIP-0563.jsonl` | 5 | UNVERIFIED |
| `units/LATE-04-METHOD-0565.jsonl` | 1 | UNVERIFIED |
| **Total** | **30** | **30/30 qualified** |

The specific published Science `docs/science/data-and-knowledge/source-observation-vintages-and-replay.md` was corrected to say that source topic 09 **reports** developer preference for lightweight actual-download-time receipts, optional method links and avoiding an exhaustive indicator database. The exact original annotated user document was unavailable. The preference remains a research-reported input, not a freely invented future requirement.

## 2. Direct pinned evidence: generic downloader versus source fact

Core baseline `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`:

| Code witness | Observed mechanics | What is NOT established |
| --- | --- | --- |
| [`src/stratbox/base/net/http.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) | `DownloadResult(ok, status_code, content, error, final_url, headers)`, retries and minimum bytes | Universal receipt with `observed_at`, digest/source snapshot, official publication edition, parser/method revision or retained raw payload |
| [Collector `downloader.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/downloader.py) | Per-item attempted errors, success bytes/size, obvious HTML checks, continue-on-error option | Whether bytes faithfully represent a regulator publication or correct economic measure |
| [Collector `contracts.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/contracts.py) | Requested/success/failure counts; individual errors; `ok` means no recorded failures | All expected reporting periods and semantic statistical content complete |
| [Collector `operations.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/operations.py) + [`file_names.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/file_names.py) | Unique file names enforced before standard save; duplicate collisions receive numeric suffixes | Lower-level ZIP helper's standalone arbitrary unsanitized input; global byte-digest retention |
| [Collector `save.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/save.py) | ZIP or files, overwrite optional | Immutable publication-vintage history; per-input digest persistence |
| [`registries/_loader.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) | Selects packaged resource with maximum file `mtime`; mtime failure returns 0.0 | Official issue chronology, coherent `data/meta/structure` release, byte identity |
| [CBR forms `common/runner.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/runner.py#L91-L125) | Failed/unavailable archive `continue` suppresses individual requested period in returned date list | Date-specific persisted error receipt or complete-period manifest |

A tempting negative claim had to be **rejected**: `save.py` constructs a ZIP payload as a dictionary keyed by `file_name`, but the public `collect_cbr_files` route always first runs `ensure_unique_download_file_names`. Therefore a normal public collector call is *not shown* to discard same-name files; the source filename helper addresses the collision. A raw save helper called outside that route has a different precondition. This distinction is retained in maintained Science as a **counterexample to premature risk inference**.

## 3. Direct test-file evidence and missing negative case

At the frozen core revision, read:
- `tests/unit/macrobanks/cbr_forms/test_form802.py`: direct row count and source-code identity, missing/zero distinction, float REGN, duplicate raw physical keys;
- `tests/unit/macrobanks/cbr_forms/test_excel_profiles.py`: quarterly 802 reporting dates, 3-sheet canonical/hierarchical export;
- `tests/unit/macrobanks/cbr_forms/test_models.py`: model schema, unique IDs and order, direct/formula constraints;
- `tests/unit/macrobanks/cbr_forms/test_optional_dbf_fields.py`: optional correction fields and fake DBF physical schema handling.

They contain useful **statically inspected test assertions** but were **not executed** in this session. In the inspected subset, no complete negative test was established that requests three periods, makes the middle HTTP request fail, and verifies an explicit date-specific result and user-visible warning. This is a gap in *observed test evidence*, not a proof that no test or external integration ever covers the case.

Full observed Current HOW, with exact source paths, read/verification scope and explicit current/future separation: [source download receipts and registries](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/source-download-receipts-registry-choice-and-coverage-limits.md).

## 4. Evidence hierarchy and further gates

| Claim type | Established here | Left open |
| --- | --- | --- |
| Research reports an original developer comment | Yes, from exact 04 source; 30 unit records retain that attribution | Original `SB-EXT-0002` wording and authority, human final acceptance |
| HTTP result and FileStore collection behavior | Yes, static direct source at exact pinned commit | Live source correctness, network failure behavior and installed backend |
| Registry local mtime ordering | Yes, direct pinned loader implementation | Actual present installed-wheel mtime and coherent official edition |
| Bank form date-skipping condition | Yes, explicit code branch | Result after a live reproducible missing-period failure |
| Full Science/Research lossless | **No** | Original exact carriers, material disposition of 566 sources, independent reverse evidence and Research Amputation |
| Implementation future behavior | **No** | Authorized Product WHAT/HOW, development, fault-injection and integration conformance |

**Decision posture:** a bounded lightweight source-use receipt with actual acquisition time and optional byte hash/method link can be investigated, but it must not silently turn research-reported developer preferences into hard product constraints. Physical registry version selection, coverage declarations and archive-retention costs require a real domain consumer and authorized tradeoff decision.

**Current global accounting unchanged:** all 54 Research original files read; **435 exact item transfer subset producer-checked**, **566/566 Git source material dispositions still unaccounted**, two mandatory user originals unavailable, independent full lossless certification open.
