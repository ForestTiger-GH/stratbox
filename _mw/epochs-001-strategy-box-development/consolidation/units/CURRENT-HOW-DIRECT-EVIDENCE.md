# Bounded direct-implementation observations — source-use ledger

**Evidence boundary:** exact file contents read at pinned commits. Each row is one *selected* material observation, not a declaration that its entire file has been semantically conserved. The master census keeps all 553 `unaccounted` until exhaustive original unit extraction and source-to-owner verification.

| Local observation | Source ID | Exact source use / scope | Evidence role and qualification | Maintained current owner |
| --- | --- | --- | --- | --- |
| SB-OBS-0001 | SB-SRC-0129 | `base/runtime.py`; provider loading and process cache | direct static control flow; installed environment UNKNOWN | `docs/current-how/core-runtime-network.md` |
| SB-OBS-0002 | SB-SRC-0127 | `base/net/http.py`; retries and typed `DownloadResult` | direct code; network outcomes untested | `docs/current-how/core-runtime-network.md` |
| SB-OBS-0003 | SB-SRC-0347 | `appdock/manifest.json`; desktop v4.0 declaration | manifest claim; not execution | `docs/current-how/windows-application.md` |
| SB-OBS-0004 | SB-SRC-0361 | `adapters/appdock/entry.py`; validation and exit code | direct static control flow | `docs/current-how/windows-application.md` |
| SB-OBS-0005 | SB-SRC-0518 | `runtime/bootstrap.py`; Qt coordinator import | direct dependency witness | `docs/current-how/windows-application.md` |
| SB-OBS-0006 | SB-SRC-0423 | `application/scenarios/runner.py`; step order and fail-fast | direct static control flow; no runtime proof | `docs/current-how/windows-application.md` |
| SB-OBS-0007 | SB-SRC-0384 | `application/history/persistence.py`; five JSON files and lossy read | direct code; corruption not experimentally injected | `docs/current-how/windows-application.md` |
| SB-OBS-0008 | SB-SRC-0376 | `application/background/store.py`; only status store in this class | negative code evidence bounded to named file | `docs/current-how/windows-application.md` |
| SB-OBS-0009 | SB-SRC-0531 + SB-SRC-0347 | smoke contract assertions vs current manifest | two directly compared files; outcome logical, tests not run | `docs/current-how/windows-application.md` |

**Status:** nine direct-source uses reconciled with bounded Current HOW narrative. This is **not** the complete material-unit accounting of those files, the package or the Research corpus. No `SB-SRC` census row has been promoted.
