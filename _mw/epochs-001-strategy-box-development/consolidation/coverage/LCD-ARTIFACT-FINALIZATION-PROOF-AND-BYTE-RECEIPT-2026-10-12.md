# Artifact LCD finalization proof and uncertain byte receipt — 2026-10-12

**Evidence level: PRODUCER_CANDIDATE_REPAIR / NATIVE_UNEXECUTED.** Continuous Work Program, exact incoming `stratbox@f4b7632e6294300d03c72563133c8560c99f7350`, previous [CI 38248841499](https://github.com/ForestTiger-GH/stratbox/actions/runs/38248841499) SUCCESS.

## Faulty prior design assumptions

- The documented `ScopedWriterPort.finalize()` returned a string and the candidate publisher catalogued it without validating Artifact ID, generation, target or byte identity. An unrelated backend reference could appear successful if independent final bytes matched.
- The post-finalize generic exception path returned `ByteReceipt=None` after bytes had already been sealed, verified and a catalog record might have been created; this loses relevant evidence for reconciliation.
- Initial authorization or staging-creation exceptions were outside the bounded result path, risking raw exception escape.

## Source-shaped, nonproduction correction

- A typed `FinalizationProof` now binds final reference, Artifact ID, generation, target, byte count, digest and confirmed commit assertion; invalid post-effect return yields `OUTCOME_UNKNOWN`, preserves pending reconciliation and never records `COMMITTED`.
- The existing literal-Markdown-AST Work-only test exercises seven fake finalizer receipt errors (wrong identity, generation, path, size, digest, missing commit, empty ref). The actual source definition is executed with controlled memory-only ports.
- Generic post-finalize errors preserve already known `ByteReceipt`; preeffect authority/staging failure returns safe bounded status. LDD adds future target vectors AP-09..11.

**Limits:** the proof struct is not an authenticated storage attestation; native filesystem/NTFS/SMB/object-store, strict generation fencing, race safety, fsync, process death, transactionally reconciled catalog and actual protected-principal tests were not performed. Owner decisions remain open; this is not implementation-ready certification.

After commit, inspect that commit's own CI. Frozen source census unchanged: 566 entries, 566 independent material dispositions unaccounted. No product code or restricted internal details edited.
