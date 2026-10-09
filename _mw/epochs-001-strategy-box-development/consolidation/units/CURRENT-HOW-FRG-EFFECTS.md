# Direct Current HOW addition — FRG cleanup effects

**Source census:** `SB-SRC-0278`, pinned core `8459dc58922b7e8df853cf1d9e8131fa9e132580`, blob `a51e1a905ddc9290dc1593e6d887564714b0bce4`. **Current owner:** `docs/current-how/frg-cleanup-effects.md`. The following are **selected** source-use observations, **not** exhaustive disposition of source file `SB-SRC-0278`.

| Selected observation | Direct code location | Claim / boundary |
| --- | --- | --- |
| `SB-OBS-0010` | `run_frg_cleanup`, lines 488–535 | `execute=False` produces the plan but no mutation-report rows |
| `SB-OBS-0011` | `apply_frg_cleanup_plan`, lines 273–318 | row-wise iteration, skip `will_execute=False` |
| `SB-OBS-0012` | lines 319–388 | copy/rename may remove existing destination before attempting the new write when replacement enabled |
| `SB-OBS-0013` | lines 389–449 | delete and archive actions; archive writes from collected memory bytes |
| `SB-OBS-0014` | lines 450–484 | exceptions appended as `error` with raw exception text; per-row processing continues |
| `SB-OBS-0015` | whole named function | no visible global rollback, digest verification or durable per-effect receipt inside the inspected source module |

**Caution:** negative observations are bounded to this file; upstream security and backend atomicity are separate unresolved evidence tasks. No code was run. `CENSUS.csv` stays unchanged because the full source file has not undergone independently assured semantic-unit extraction.
