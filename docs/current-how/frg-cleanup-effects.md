# Current HOW — file-family cleanup plans, effects, and failure handling

**Maintained scope:** the FRG file-family cleanup mechanism in the analytical core, **not** a general durable JobManager, transactional artifact service, or full FRG domain study.  
**Implementation owner:** `ForestTiger-GH/stratbox`; exact code `8459dc58922b7e8df853cf1d9e8131fa9e132580`, file `src/stratbox/macrobanks/frg/cleanup.py`, blob `a51e1a905ddc9290dc1593e6d887564714b0bce4`.  
**Evidence:** direct static code read. No execution, filesystem mutation, synthetic fault injection, installed-environment check or user acceptance was performed.

## Entry, plan, and apply are different operations

`run_frg_cleanup(root_dir, delete_others=False, archive_latest=False, execute=False, replace_existing=False, filestore=None)` builds and returns a plan. The return record contains `catalog`, `latest`, `plan` and `execution` DataFrames. With its default `execute=False`, `execution` is an empty table: producing a plan is **not** proof of completed filesystem mutation.

Only when `execute=True` does it call `apply_frg_cleanup_plan(plan_df, ...)`, which obtains a FileStore and iterates plan rows sequentially. Rows with `will_execute=False` are recorded as `noop`, and recognized actions include `copy_latest`, `rename_latest`, `delete_source` and `create_archive`. [Source implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py).

The plan's `delete_others`, `replace_existing` and archive flags have separate meanings. The code permits existing targets to be removed when replacement is enabled, prior to copying or renaming a source. The archive path may likewise be removed before the new archive is written. These are **actual effect paths**—not evidence of an atomic replace or verified resulting bytes.

## Failure propagation and partial result

The implementation wraps each actionable row in its own `try/except Exception`. A failure is appended to the returned execution DataFrame with `status="error"`, the exception text in `message`, and input/output path metadata; processing then proceeds to subsequent plan rows. A successful action is recorded as `done`, a redundant action as `noop` or `skipped`.

This is a **best-effort per-row execution report**, rather than a transaction enclosing the complete cleanup plan. The checked function does not perform a global rollback, stop all subsequent mutations after the first failed row, write a durable effect receipt outside the returned in-memory DataFrame, or verify a copied target digest before recording `done`. These are bounded observations of the inspected module, **not** claims that the whole Strategy Box lacks every possible safety mechanism.

Because later actions may be evaluated after earlier failures, callers must inspect the per-row `execution` statuses rather than assume `execute=True` means every requested effect occurred. An out-of-band process or storage-backend behavior can change the actual effect; no real partial-loss incident has been demonstrated here.

## Representative causal paths

| Plan row and condition | Current control flow | What the caller can infer |
| --- | --- | --- |
| `copy_latest`, source exists, target absent | `fs.copy` → row `done` if no exception | Backend call returned; no source/target checksum proof here |
| `copy_latest`, target exists, no replacement | Row `skipped` | Existing bytes are not validated against the requested source |
| `rename_latest`, target exists and replacement allowed | `fs.remove(target)` → `fs.rename(source,target)` | Target removal and rename are not one proven atomic unit |
| `delete_source`, path exists | `fs.remove(source)` → `done` if no exception | One removal attempt returned successfully; no undo receipt |
| `create_archive`, eligible members exist | Collect members; optionally remove target; write ZIP from memory | Staging/verification and low-memory streaming not established here |
| Any action raises | Record `error` and continue to next row | Overall operation may be partial; later effects may still occur |

## Data exposure and observability limits

The execution result includes filesystem paths and the raw `str(exc)` message. That is direct implementation evidence with potential audience implications: copying the raw DataFrame into a shared notification would require a separate privacy review and redaction contract. This module itself is not a user-safe multiuser Problem projection.

The source does not establish plan revision binding, per-row actor authorization, resource fencing or cancellation receipts. Whether an upstream caller constrains scope, captures returned logs, enforces a confirmation UI, or persists artifacts must be evaluated at **that exact caller and deployment**, not inferred from this code.

## Current-versus-target boundary

The existence of a plan/apply split is useful current behavior. Staging, integrity verification, effect receipts, repair, idempotent submission, managed artifacts and coordinated resource claims remain **unapproved target candidates** elsewhere; their mention here describes missing assurance for this narrow implementation, not an adopted requirement.

**Reopen:** `frg/cleanup.py` or FileStore adapter revision; changes to callers/permissions and output writers; reproducible filesystem fault-injection or authenticated installed-runtime evidence. This Current HOW slice is sufficiently grounded for code-review questions about the named functions, **not** a global FRG or recovery assurance certificate.


## Source-level refinement and five executed synthetic effect failures — 2026-10-12

Six additional pinned core files were read in full and verified against the frozen census Git blobs: [domain README](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/README.md) (`SB-SRC-0274`), [public API](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/api.py) (`0276`), [catalog](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/catalog.py) (`0277`), [cleanup](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py) (`0278`), [stub dispatch](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/dispatch.py) (`0279`) and [latest selection](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/selection.py) (`0290`). Source SHA witnesses remain in the [single source census](../../_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv). The README promises that unrecognized files are left alone under the ordinary catalog-derived plan; this is upheld by `_should_delete_row` during **plan construction** (`is_recognized` required). That claim must not be transferred without qualification to direct execution of an arbitrary plan.

[CI run 38188245744](https://github.com/ForestTiger-GH/stratbox/actions/runs/38188245744) passed **five source-executing offline fault cases**, using the exact checked-in `cleanup.py` functions with synthetic FileStore, DataFrame and ZIP writer rather than a real filesystem: [test harness](../../_mw/epochs-001-strategy-box-development/consolidation/tools/test_frg_cleanup_observed_faults.py). The resulting facts are stronger than a prose-only suspicion, yet demonstrate only this pinned source and injected behavior, **not a reported user's data-loss incident**.

| Synthetic scenario exercised | Actual inspected call sequence / tested result | Truth limit |
| --- | --- | --- |
| `copy_latest`, existing target, `replace_existing=True`, next `copy` raises | `fs.remove(target)` runs first; `copy` then errors; original target is **gone**, source remains | No transactional replace or rollback in this function |
| `rename_latest`, same replacement setting, next `rename` raises | Existing destination removed; rename errors; source remains, old destination absent | A successful plan is not a safe final mutation |
| Existing ZIP, then archive writer fails | Old archive removed before `write_zip_from_memory` fails | No guarantee of retaining previous ZIP on failed replacement |
| Fresh source, stale internal target, `replace_existing=False`, then archive | Copy step skips because target exists; archive member helper prefers **existing target bytes** over source bytes | ZIP can contain **stale target** despite selecting newer source by name |
| Caller passes handcrafted `delete_source` row directly to `apply_frg_cleanup_plan` for a non-FRG file | Direct apply removes specified path without rerunning `is_recognized` check | Safe ordinary **builder** does not prove safety of untrusted **apply input**; scope/authorization belongs to caller |

The source-derived distinction matters. A standard `run_frg_cleanup(root, ...)` call constructs its own plan from recognized catalog entries. A separately reachable lower-level `apply_frg_cleanup_plan(plan_df)` function assumes its caller supplied a trusted plan, and its execution phase does **not** verify a frozen plan identity, source/target digest, root scope, current recognition, authorization or freshness before applying each row. This is a **capability/plan-trust risk if a future host or AI adapter exposes arbitrary user-controlled plan rows**, not evidence that an existing installed external client can do so.

There is also a real semantic difference between **plan step succeeded** and **finished archive represents the chosen latest raw version**. The helper `_collect_archive_members_from_plan` checks the target first and falls back to the source only when the target does not exist. Therefore, a `skipped` copy due to an old target can produce a successful archive write that preserves old bytes. The read/copy/ZIP routine has no source-to-member digest cross-check or monotonic generation guarantee. `selection.py` itself selects one valid newest-by-named-period entry per recognized family and favors internal names on certain ties; this is **filename-policy recency**, not an authenticated publisher edition or byte authenticity guarantee. `dispatch.py` still routes to parsing **stubs**, so a `dispatch` row alone is not financial-data semantic validation.

**Future requirements are separate:** stage replacement bytes, verify and publish under a proven backend contract, enforce scope/plan revision and approval at a host effect boundary, and condition archive membership on the **actual accepted latest source** rather than merely a preexisting target path. These are candidate designs; the five tests **characterize current failure**, and **none certifies those future safeguards**. Real target OS crash, permissions, network-mounted storage and recovery testing remain necessary.
