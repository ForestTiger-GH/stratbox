# Producer exact-material reconciliation: 323 source-addressed units

**Checkpoint:** 2026-10-11. **Status:** PASS for bounded exact-text source→Science/LDD comparison performed with GitHub connector; **not** full semantic assimilation, an independent source audit, executable conformance or Product acceptance. The exact source revisions are frozen by `sources/CENSUS.csv`. No source meaning was promoted into an accepted product contract by this exercise.

## 1. What materially changed

Four original research papers whose meaning had been represented mainly as topical prose and coarse section locators now have exact item-level source and destination traceability. Together with the 98 preserved generic provider vectors already present at the previous checkpoint, **323 individually identified claims/tests** have exact source-content destinations:

| Frozen Research | Preserved content group | Exact item count | Item-level ledger | Maintained destination |
| --- | --- | ---: | --- | --- |
| `SB-SRC-0025` | Generic neutral-provider conformance verification vectors (46 generic, 25 byte storage, 10 secrets, 10 network, 7 passive report style) | **98** | `units/PROVIDER-EXACT-VECTORS-0025.jsonl` | `docs/ldd/extensions/neutral-provider-conformance-vectors.md` — **LDD candidate only** |
| `SB-SRC-0032` | Machine-readiness **24 MUST, 15 SHOULD, 9 MAY** and **22 original review questions** | **70** | `units/MACHINE-READINESS-EXACT-ITEMS-0032.jsonl` | `docs/science/capabilities/compiled-domain-capabilities-validity-and-deoptimization.md`, §12 |
| `SB-SRC-0029` | **40 research target invariants** and **20 proposed discarded target doctrines** | **60** | `units/SEMANTIC-INVARIANTS-EXACT-ITEMS-0029.jsonl` | `docs/science/engineering/semantic-ownership-method-transfer-and-proportional-materialization.md`, §10 |
| `SB-SRC-0031` | **15 integration readiness checks**, **12 cognitive-scope warning signals**, **10 standalone/domain ownership invariants** | **37** | `units/COGNITIVE-BOUNDARY-EXACT-ITEMS-0031.jsonl` | `docs/science/automation/bounded-agent-routing-and-evidence-safe-automation.md`, unnumbered source-preserving appendix |
| `SB-SRC-0019` | **20 complete epistemic architecture acceptance-test questions** and **38 inference/authority/status firewalls** | **58** | `units/EPISTEMIC-TESTS-AND-FIREWALLS-EXACT-0019.jsonl` | `docs/science/data-and-knowledge/semantic-promotion-firewalls-and-bounded-reliance.md`, §11 |
| **Total** | **Disjoint per-source row identities across five original files** | **323** | Five unit ledgers | Four Science articles and one explicitly candidate LDD |

These items are **concrete preserved material**, not automatically all material meaning in their source files. Each source also contains arguments, illustrations, proposed architecture, conditions, alternatives, dependencies, scope and other content. Many such passages have topical Science coverage, but their complete material conservation has not been established. The 323 units are a *subset*, not a new denominator for the whole 566-file corpus.

## 2. Bounded verification performed by producer

An ad-hoc GitHub-connector checker fetched all five JSONL ledgers, the five frozen original source bodies and five corresponding destinations directly. For each unit it verified:
- exact source blob SHA matches the unit's recorded frozen SHA;
- the claimed original source line exists;
- the exact source row/text or full acceptance-test body is present in the declared destination;
- the persistent item ID or test ID survives in maintained destination;
- category row counts per source (98 / 70 / 60 / 37 / 58).

**Result: 323 passed, zero textual source/destination mismatches in that bounded check.** Independent domain-meaning review was **not** performed. Text inclusion can pass even when a claim is misunderstood by a reader, normatively misclassified, later contradicted, or scientifically unsupported.

The source corpus `CENSUS.csv` continues to state **566/566 material records as `unaccounted`** because full-source semantic dispositions and independent reverse assurance remain incomplete. The item ledgers use an explicitly qualified producer disposition (`exact_text_preserved`, `research_candidate`) rather than `independent_review=PASS`. They must not be counted as global source closures.

## 3. Reproducible checking for later checkout

New producer-only stdlib tool:

`_mw/epochs-001-strategy-box-development/consolidation/tools/verify_exact_material_transfers.py`

From the cloned repository root:

```bash
python _mw/epochs-001-strategy-box-development/consolidation/tools/verify_exact_material_transfers.py
```

The tool is designed to compare the source records against Git's own blob hashes, validate required item counts and duplicate IDs, recover source spans and exact wording, inspect destination transcriptions and resolve local Science links. It emits structured JSON and a nonzero status on disagreement. **Execution of this Python script in an actual local checkout has not been performed during this GitHub-only consolidation session**; its intended behavior is supported by the bounded connector-side check, not a claimed installed test pass.

## 4. Contradiction found across originals

New `reconciliation/MACHINE-SCHEME-OWNER-AND-EXECUTION-PLAN-DIVERGENCE-2026-10-11.md` records a genuine original-source difference:
- `SB-SRC-0032` makes the importable domain library owner of `SchemeSpec` and the composition graph while the application retains actual Job/queue/approval/recovery;
- `SB-SRC-0029` assigns `MachineScheme` to an application-level semantic owner, with `CanonicalOperation` in the domain library.

Three alternatives are preserved: all composition in domain; all in application; or ownership split by actual domain-only versus commissioned Work semantics. A **typed pilot and real direct-Python versus durable Work consumers** should discriminate them. No new repository name or runtime ownership was unilaterally approved.

Existing operational versus epistemic navigation conflict also remains open.

## 5. Science integrity and public-contract boundaries

No product source code or extension implementation was changed during this research continuation. The published output contains generic, environment-neutral provider conformance tests only. The two required exact human inputs remain unavailable; this is a separate blocker to global lossless certification.

Science file count remains **51 topical articles + two guides**: this continuation strengthened four existing articles without artificially multiplying topics. Last complete structural pass counted **53 Markdown files and 257 local relative links**, all existing; new source references added in this continuation are absolute GitHub links. The reproducible tool can re-evaluate current local link integrity at later revisions.

## 6. What qualifies as completed, and what does not

| Gate | Status |
| --- | --- |
| Full primary reading of 54 substantive Research originals | CLOSED at prior checkpoint |
| 323 item identities + exact source-line mapping to four Science articles/one candidate LDD | **PRODUCER SOURCE-TEXT CHECK PASSED** |
| All material units of these five original files transferred with explicit correct semantic disposition | OPEN |
| All material meanings of all 566 Git files conserved and independently confirmed | OPEN — 566/566 source records unaccounted |
| Both mandatory exact human source carriers received/read | BLOCKED |
| Full bidirectional Science ↔ original evidence, negative-result and contradiction check | OPEN |
| Independent hostile challenge and cold-reader Research Amputation | OPEN |
| Authorized Product Decision/Target WHAT/HOW admission | OPEN |
| Installed application, solver, worker, client, permission and real-backend testing | OPEN |
| Complete public-secret/confidentiality review | OPEN |

**Next research direction:** extract remaining material clauses (not heading proxies) from the long 02 originals, especially acceptance applicability, epistemic results, extension failure semantics, cognitive actor concurrency, preservation of alternative architectures and banking examples; then independently challenge the exact Science consequences and proofs. Eventually reclassify an entire source as conserved only after all distinct material units receive complete dispositions and a separate review.
