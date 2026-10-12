# LCD: unimplemented FRG rename/archive are not completed or ambiguous effects — 2026-10-12

**Exact input:** `stratbox@6c6c6ad72751adf5146672428c705a6593407784`, prior [CI 38247417681](https://github.com/ForestTiger-GH/stratbox/actions/runs/38247417681) success. Existing Work Program, producer design test only. The previously maintained FRG LCD construction and exact literal-fragment test were read.

## Demonstrated candidate design mismatch

- `RENAME_LATEST` was dispatched to the same code branch as `COPY_LATEST` and yielded `EffectTruth.VERIFIED` after a target copy. No source deletion was performed or confirmed. The downstream word *rename* would falsely imply a completed move.
- `CREATE_ARCHIVE` created a pending intent and then deliberately raised `NotImplementedError` inside a catch-all that returned `OUTCOME_UNKNOWN`. No archive port was called; that classification invents physical uncertainty.
- Both errors occurred in **documentation-only candidate source**, not a production FRG implementation.

## Corrective source-shaped contract

- Restrict the example `CleanupExecutor.apply_one` to COPY and guarded DELETE. Other candidate enum values fail with explicit `NotImplementedError("ACTION_HAS_NO_VERIFIED_EXECUTION_PLAN")` **before** calling the authorization port, pending receipt port or effect port.
- Update the actual Markdown-extracted Python test tool with one frozen candidate `RENAME_LATEST` and one `CREATE_ARCHIVE` case. Require no effect calls and no pending/result records. The earlier erroneous archive-UNKNOWN expectation is removed rather than retained as a passing oracle.
- Add FR-15..16 to the existing LDD, expressly `UNEXECUTED` target acceptance vectors. A full future rename needs two controlled physical effects; archive needs a frozen member manifest and a separately verified staged publisher.
- Only producer documentary fragment execution can be expected of the workflow. Full real FS/Windows/host durability, approval, semantic source selection and independent cold implementer remain `LCD_BLOCKED`.

**Evidence boundary and continuation:** new HEAD CI needs exact observation after publication. Frozen census counts and 566 unaccounted material verdicts are unchanged; no Source↔Science global LOSSLESS_PASS or product implementation.
