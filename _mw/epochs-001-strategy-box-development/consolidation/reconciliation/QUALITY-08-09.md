# Bounded reconciliation — system qualities (research topics 08 and 09)

**Result state:** RECONCILED FOR DECLARED CROSS-TOPIC INTERFACE, **not** exhaustive extraction of either full Research Result.  
**Commission:** 2026-10-09 Knowledge consolidation, narrowed Theme Contract `SB-T-QUALITY-08-09`.  
**Purpose/consumer:** supply a non-contradictory bounded safety/quality bridge for subsequent Science and Product-review work without promoting either Research to Product Authority.

## Exact source set and information baseline

- `SB-SRC-0047`: Topic 08, Research Result `Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md`, blob `636c854e25bde15d380e757aa6e4762cf587b3b8`; assigned spans §10–§11 and §14, with orientation §0 and cross-boundary context.
- `SB-SRC-0055`: Topic 09, Research Result `strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md`, blob `00e38a158a4538052930e677cce3e9aff449b026`; assigned spans opening/currentness §0, §12–§14.
- Both are represented in pinned `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`. Their related study lineage is **not independent evidence** merely because two files exist.

## Reconciled answer

The text of Topic 09 states that the standalone Topic 08 was missing in the *author's available input set* at the time its synthesis was assembled. The pinned target corpus contains Topic 08. Therefore the statement is **historically true within that earlier reading context** but **false as a present-day corpus absence claim**. Retain Topic 09 byte-identically as Research; its §12 is labelled provisional and should be interpreted as a bridge rather than a substitute for current Topic 08.

There is no substantive need to choose between the two quality models:

- Topic 09 §12–14 contributes system-wide cross-plane requirements, owner allocation and 32 `INV-*` candidate invariants, linked to a proposed logical whole-system architecture.
- Topic 08 §10 contributes a more detailed negative-testable catalogue of **50** research candidate invariants, split into truth (8), effects (12), durability (10), security (10), and operability/UX (10), plus detailed gap and fault-injection programmes.
- The catalogues are **not** a one-to-one supersession and their labels are not accepted specification IDs. Different formulations and granularity express different concern boundaries.

## Scoped semantic dispositions

| Concern | Topic 09 span | Topic 08 span | Qualified reconciliation / next owner |
| --- | --- | --- | --- |
| Currentness of independent Topic 08 | Front matter and §12 | Whole independent Result | **Historical availability correction**, Research text unchanged; both are now admitted Research inputs |
| Error vs missingness | §12.2, INV-09/10 | SB-Q-T01..T05 | **Compatible**; direct code evidence needed before Current HOW; candidate Science topic is semantic certainty |
| External effect, retry, idempotency | §12.2, INV-11/12 | SB-Q-E01..E12 | **Compatible at different detail**; effect outcome must not be inferred from caller timeout; exact product guarantee OPEN |
| Durable state, artifact commit | §12.2, INV-18/19/29 | SB-Q-D01..D10 | **Compatible**; extra 08 tests for corruption, crash windows and backup set remain material; physical persistence OPEN |
| Trust, audience and authorization | §12.3, INV-13/14/31 | SB-Q-S01..S10 | **Compatible**; 08 adds audience-filtered cursor and specific privilege/test cases; authorization/product policy remains Decision-owned |
| Operational diagnostics | §12.4, INV-26 | SB-Q-O01..O10 and §5 | **08 refines** distinction between run evidence, product state and a safely reported shared condition; platform schema unconfirmed |
| Quality invariants | §13: 32 broader `INV` items | §10: 50 detailed `SB-Q` items | **BOTH retain Research authority only**; no mechanical union, de-duplication or direct conversion to Product requirements |
| Architecture allocation | §14 owner matrix | §11 and §14 gaps | **Complementary scopes**; Topic 09 informs candidate responsibility allocation, Topic 08 informs assurance risk and negative tests |

## Counterarguments and unresolved issues

A tempting reading is that the later, more detailed Topic 08 simply replaces Topic 09 §12. This would erase Topic 09's whole-system interactions and its independent logical responsibility argument. Conversely, retaining only the high-level 09 invariants would lose testable negative cases. Correct result is a **typed relation: provisional synthesis refined by independent later themed Research, neither Product admitted**.

The assigned interface is reconciled at claim-role level, but no claim is made that the 148 KB / 176 KB file versions are entirely extracted or that their every material unit is transferred. Broader 08↔09 conflicts outside the assigned spans remain for the later complete corpus synthesis. External contract maturity, quantitative SLO, exact protection policy, cross-device applicability and build/runtime evidence remain open.

**Proof / validity:** the correspondence is from source text and exact source revisions; no test execution, architectural Product admission or independent verification occurred. Reopen if sources, Theme Contract, accepted WHAT, externally observed runtime or specialized assurance obligations change.
