# Current HOW — local filesystem observation and write-effect semantics

**Evidence:** direct static reading of `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`, not a runtime test, live filesystem observation or a universal assertion about every `FileStore` backend. The current source of record is [LocalFileStore](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py), its [generic Protocol](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py), and the [stat type](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/types.py).

## Direct implementation observations

| Operation | Actual behavior in the pinned local implementation | Boundary of the evidence |
| --- | --- | --- |
| [`listdir(path)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L66-L70) | Returns `[]` when the path does not exist, when it is not a directory, or when it is a genuinely empty directory. | The empty list is **not proof of a present empty directory**. There is no claim that every remote backend suppresses the same errors. |
| [`walk(top)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L92-L111) | Exits without yielded rows if the top path is absent or is not a directory; otherwise delegates to `os.walk`. | No rows do not prove a healthy, valid workspace root. |
| [`stat(path)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L53-L64) | Delegates to `Path.stat()` and returns type and optional timestamps/size. Missing files can raise; the implementation does **not** universally swallow exceptions. | Absence, file-vs-directory and permission outcomes may differ between local and other providers. |
| [`open_write(path)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L37-L42) | Creates parent directories and opens the target with `wb`, so an existing target can be truncated before a caller completes writing. | No atomic write or post-crash publication receipt is guaranteed by this primitive. |
| [`copy(src,dst)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py#L91-L98) | Generic implementation reads all bytes, then writes destination bytes. | Cross-store atomicity, resumability, rollback and destination digest verification do not follow. |
| [`rename(src,dst)`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L83-L89) | Creates destination parent and invokes `Path.rename`. | Atomicity and overwrite behavior for every platform, volume and other provider have **not** been established. |
| [`remove/rmdir/rmtree`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L74-L83) | Invokes direct filesystem methods. | Low-level primitives are **not** automatically user-authorized destructive capabilities; policy must live above them. |

The specific demonstrable issue is **local missing/not-directory `listdir()` mapped to `[]`**, not that all storage errors from all platforms are hidden. The distinction matters to completeness checks of banking/statistics source directories, artifact availability, and trust in a user's reported output.

## Effect and artifact implications

A command may require a simple 'file unavailable' status when an expert manually moves a previously generated workbook. That limited UX requirement does not authorize reporting an inaccessible required source directory as "zero input files." Critical source reads and managed output publication need explicit knowledge of presence, completeness, and execution outcome, separate from display convenience.

A direct `FileStore.write_bytes` call writes through a generic `open_write` (and `copy` uses the same path), so a consumer must not assume atomic, fully committed output or hard reset behavior after interruption. Whether a higher-level writer stages, validates, and publishes safely is **caller-specific and requires direct evidence**; it is not certified here.

## Path resolution is not a sandbox

[`LocalFileStore._abs`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L25-L32) converts backslashes to forward slashes, expands the configured `root` only when the supplied path is relative, and returns a `Path`. It does **not** resolve and verify the final target against the configured root. Absolute paths bypass the relative-root prefix, and `..` segments may escape that root when used by a filesystem operation. It does not demonstrate symlink/junction containment.

**Scope:** a general-purpose filesystem adapter is not necessarily intended as an authorization sandbox. Its path behavior becomes a security issue **if** a remote Web/AI/API capability treats `root` as a confinement guarantee or forwards an untrusted path without independent validation. A future server-side workspace access boundary should validate the principal, authorized workspace/Artifact reference, resolved target and allowed effect before invoking FileStore, with explicit symlink and race-condition policy. This is a conditional design obligation; no existing public endpoint vulnerability is asserted by the file adapter code alone.

## Direct Research reconciliation: Topics 08 and 09

The frozen [Trust, Safety and System Qualities study #08](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L310-L324) identifies the `listdir` empty/missing collision, and the [whole-system architecture study #09](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md#L908-L919) records the broader false-success risk. The code confirms **this bounded current behavior**; proposed typed error/result classes and a universal managed artifact publication state are still candidates.

## Negative cases for future conformance (unexecuted)

1. Compare `listdir()` on a valid empty directory, missing path and regular file: the current local implementation returns `[]` in all three cases.
2. Test `stat()` for those paths and a permission-denied case; qualify platform-specific exceptions.
3. Terminate after `open_write('wb')` truncates a previously committed file, before all bytes are written. A high-level committed artifact must never claim success solely from opening the file.
4. Trigger failure between a cross-store copy and separate delete. Do not claim atomic move without a verified provider-specific contract.
5. Retry a destructive mutation after the response is lost. Preserve an unknown-outcome receipt and reconcile effects before repetition.
6. Manually move an artifact. The user's existing chat link may become inactive without forcing a global filesystem search.
7. Check source-directory discovery where `[]` would incorrectly pass a completeness gate; distinguish a known truly empty publication from a missing input root.
8. Under a confined-workspace threat model, pass absolute paths, parent traversal, symlink/junction escapes and raced target replacement; authorize after canonicalization at the actual effect boundary.

**Qualification:** neither CI nor a filesystem failure simulation was executed during this static review. A safer typed domain-level listing or source receipt is a proposed improvement, not an existing universal API. See [source download/registry Current HOW](source-download-receipts-registry-choice-and-coverage-limits.md) and the [Science of effects and outcome uncertainty](../science/execution-and-diagnostics/effect-receipts-and-unknown-outcomes.md).
