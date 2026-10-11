# Current HOW — LocalFileStore missingness and publication limits

**Scope:** direct static reading of `src/stratbox/base/filestore/{base,local,types}.py` at `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`. No filesystem fault-injection or live backend test executed. This document reports **ordinary public local storage behavior**, not environment-specific adapters.

## Directly established

| Current operation | Proven from implementation | Invalid stronger inference |
| --- | --- | --- |
| [`LocalFileStore.listdir`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L66-L70) | A missing path, a regular file supplied as directory, and an existing empty directory all yield `[]`. | Empty list always proves an empty existing directory. |
| [`LocalFileStore.walk`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L92-L111) | Absent or non-directory traversal root produces no rows. | No traversed rows proves an empty workspace root. |
| [`LocalFileStore.stat`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L53-L64) | Calls OS path `stat` and provides type, size, timestamps. | Every FileStore operation returns a uniform typed error. |
| [`open_write`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L37-L42) | Creates parent directories and opens destination in `wb` mode. | Direct writing is crash-safe or guarantees a complete published Artifact. |
| [`FileStore.copy` fallback](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py#L91-L98) | Reads complete source bytes, then writes complete destination bytes. | Two-step fallback implements atomic move, rollback, or verified publication. |
| [`rename`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L83-L89) | Calls the local filesystem rename after creating destination parent. | All storage providers and platforms share identical atomicity and overwrite guarantees. |

**Narrow factual conclusion:** the `listdir` and `walk` paths conflate physical absence with valid empty observation in some cases. This does not mean all backend exceptions are globally caught: `stat`, enumeration and writes can still raise.

The user's admitted goal permits a manually moved/deleted output file to become an unavailable chat reference without a global search. That is separate from a **source-completeness claim**: when a calculation expects a source directory, it cannot treat backend absence, path-type error or permission failure as measured zero/empty input without qualification.

## Relation to competing original studies

Earlier [whole-system architecture Topic 09](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md#L896-L919) explicitly marked its quality block as provisional while specialized Topic 08 was absent from its original evidence cutoff. Later [Topic 08, §4.3](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L310-L324) identified the narrower current behavior, now verified against direct implementation. The later work refines the earlier provisional risk analysis; it does not automatically approve a new storage API.

Proposed negative fixtures: existing empty directory versus missing directory versus regular file; missing after workspace change; denied listing; interruption after destination was opened for writing; attempted publication of incomplete bytes. **None has been executed here.** The future strict result/status profile remains a Product/Implementation decision tied to risk. See also [source receipts](source-download-receipts-registry-choice-and-coverage-limits.md) and [Artifact publication](../science/artifacts/output-identity-publication-and-availability.md).
