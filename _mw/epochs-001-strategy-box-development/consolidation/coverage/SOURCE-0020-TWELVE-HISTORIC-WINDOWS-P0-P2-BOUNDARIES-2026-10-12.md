# Historical Windows original 0020 P0–P2 code and release modernization proposals

**Evidence grade: bounded original-first producer interpretation.** Input `stratbox@5a1379a9ca51c7c4d3a1e976142a58bdf53a33a8`, [CI 38252060431](https://github.com/ForestTiger-GH/stratbox/actions/runs/38252060431) exact SUCCESS. Source blob `225128f2599f0792422c0b31cb3cbe1437991ced` at the frozen 2026-10-06 Windows study, lines L1303–1380.

## Source gap and preservation

The exact geometry triage marked original 0020 block L1327–L1366 among unspanned text. Direct source review shows this is **substantive**: distinct P0/P1/P2 proposals, not boilerplate or new actual code. All 12 named headings §§71–82 have been preserved in existing maintained `docs/science/architecture/product-system-model-actors-and-repository-boundaries.md` as `W20-P71..82`, with explicit source-proposed status and acceptance countercases. They cover drift between manifest/tests/docs, tracked generated state, neutral public documentation, portability and host capability gaps, version provenance, incomplete local persistence and candidate cleanup of unreachable configuration.

### Current observation boundaries

- The earlier Windows source has a Qt-owned coordinator even though domain execution callbacks are partly toolkit-independent. A distributed host is still an approved logical target, not an installed Windows process.
- Local background status, presence and assignments are actual code/UI objects; schedule execution, remote user presence and shared delivery do not follow from those labels.
- A real pinned `runtime/version.py` probe uses Git subprocess commands, falling back to `unknown` when Git is unavailable. The existing direct-pinned WEX-07 fake-directory characterization documents that behavior; packaged release identity remains a different external evidence owner.
- The dated priority list does not prove these same defects continue in later Windows revisions; use direct code for each exact SHA and real native tests.
- Public-source notes are kept generic and contain no environment-specific confidential configuration detail.

## Verification plan

Add a Work-only source-identity check for the twelve exact original headings and twelve maintained Science row IDs. This is **structural producer coverage**; no independent meaning verification, owner approval, deployed host or tested Android extraction follows.

Other 0020 original gap envelopes (including a dated source history and target architecture sketch) remain separate candidate reviewer inputs. `SB-SRC-0020.material_unit_state` and all 566 source material states remain `unaccounted`; complete semantic Research Amputation and LCD implementation-ready status remain OPEN.
