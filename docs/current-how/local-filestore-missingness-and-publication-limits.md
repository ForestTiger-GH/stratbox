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

Earlier whole-system architecture Topic 09 (`#L896-L919`) explicitly marked its quality block as provisional while specialized Topic 08 was absent from its original evidence cutoff. Later Topic 08, §4.3 (`#L310-L324`) identified the narrower current behavior, now verified against direct implementation. The later work refines the earlier provisional risk analysis; it does not automatically approve a new storage API.

Proposed negative fixtures: existing empty directory versus missing directory versus regular file; missing after workspace change; denied listing; interruption after destination was opened for writing; attempted publication of incomplete bytes. **None has been executed here.** The future strict result/status profile remains a Product/Implementation decision tied to risk. See also [source receipts](source-download-receipts-registry-choice-and-coverage-limits.md) and [Artifact publication](../science/artifacts/output-identity-publication-and-availability.md).

## Additional direct owner evidence: path confinement is not implied by a root parameter

At [`LocalFileStore._abs`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py#L25-L32), the constructor's configured root is only prefixed to a **relative** path. The method does not canonicalize and check that the final effective target remains inside that root. An absolute path is accepted independently of the root, and parent traversal/symlink resolution is not confined by this helper. In a general-purpose filesystem API such freedom can be intentional; it is **not evidence of an exploitable remote endpoint**.

A hypothetical Web/MCP/AI workspace service must **not** treat this adapter root as its server-side authorization policy. It should authorize principal, workspace object, canonical target and effect under a separate enforced boundary, with explicit symlink, race-condition and OS-specific handling. The exact policy and implementation remain Product/Architecture questions for any real Internet-facing service.

**Additional unexecuted negative tests:** absolute user-supplied path with an assigned root; `../` and symlink escapes; target replacement between check and write; `wb` truncation before durable artifact publication; cross-store copy followed by failed delete; separate `NOT_FOUND`, `WRONG_TYPE`, `ACCESS_DENIED` and truly empty-dir domain outcomes. These tests belong to the future consumer/effect boundary. Direct FileStore code alone cannot certify a sandbox.


## Five executed temporary-filesystem observations — 2026-10-12

The earlier path-confinement risks have now been **tested against actual checked-in public core Python code**, not only inferred from source text. [CI 38188491459](https://github.com/ForestTiger-GH/stratbox/actions/runs/38188491459) ran five standard-library-only tests in a disposable system temporary directory. They loaded frozen `types.py/base.py/local.py/tmp.py` directly with explicit lightweight import scaffolding; **5/5 passed**. All outside-root test paths remained *inside the test's own temporary directory*; no actual user, network, corporate or host file was accessed.

| Current local adapter case | Actually observed current behavior | Reliance boundary |
| --- | --- | --- |
| Configured root plus relative `../outside.bin` | `LocalFileStore.write_bytes` replaces a sibling file outside the assigned root | Root convenience is not a sandbox or host ACL |
| Configured root plus absolute path | Absolute target is used rather than forced into assigned root | User input must not become unrestricted file authority in a host |
| Symbolic link inside root to a sibling directory | Writing through link reaches a directory outside assigned root | Lexical prefix checks alone cannot enforce a safe filesystem boundary |
| Missing directory versus empty directory versus ordinary file | `listdir` returns `[]` in all three cases; `walk` yields no rows for missing and wrong-type paths | Empty observation is weaker than verified valid-empty source |
| Existing output opened for write; synthetic producer exception | `wb` truncates previous bytes and leaves partially written replacement | FileStore write return/abort lacks staging and verified Artifact publication |

The tests **establish actual source-code behavior under controlled temporary filesystem conditions**. They do *not* establish remotely accessible path traversal, prior user data loss, Windows/SMB parity, power-failure durability or a tested host authorization endpoint. A general-purpose local Python `FileStore` may deliberately permit absolute paths for trusted notebook use. The **future Web/Windows host application boundary**, not arbitrary domain Python calls, must authorize each caller's workspace/Artifact and explicitly validate resolved paths, symlinks, changes between check and use, and relevant OS-specific storage rules.

Two additional frozen core files were now fully read and Git-blob-checked: [`filestore/__init__.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/__init__.py), census `SB-SRC-0103`, blob `7ea27a19c934c921aebc922f3f38d2b6dba5b992`; [`filestore/tmp.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/tmp.py), census `SB-SRC-0106`, blob `42caa4237081c29877928b9b38cc4becb8ba2e7d`. The module exports `make_workdir` and `workdir`; `make_workdir` intentionally leaves a created temporary folder until the caller removes it, whereas the `workdir` context manager tries to clean up on exit and suppresses deletion failures. Thus a successful context exit does not prove its temporary directory was removed. This is a **static** observation about cleanup behavior; the five execution cases above do not test failed temp cleanup.

**No target permission implementation or release certification** follows from these tests. Scientific applicability and the relevant future hosted security/Artifact paths remain separate maintained owners.
