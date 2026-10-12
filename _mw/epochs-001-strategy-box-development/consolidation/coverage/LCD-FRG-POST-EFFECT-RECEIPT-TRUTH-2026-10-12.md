# FRG LCD after-effect receipt falsification and correction — 2026-10-12

**Producer design challenge, no product-code changes and no independent `READY` verdict.**

## Problem established directly in the prior maintained LCD

At starting `stratbox@144f7bde1270794488b8f81e9a4aca8f45095c2d`, read entire `docs/lcd/application/frg-cleanup-effect-plan-construction.md` and the exact extracted-doc probe tool `test_lcd_candidate_behavior.py` section `probe_frg_cleanup_effects` (L1373–1605). Existing `CleanupExecutor.apply_one()` returned `EffectTruth.VERIFIED` immediately after `FileEffectPort.conditional_finalize(...)->FileWitness` or `conditional_delete(...)->str`, without validating the returned receipt's file identity, destination digest, generation or actual absence. The documented fake always returned a trustworthy-looking value, so the previous synthetic passing probe could not falsify this error. No current FRG product module/underlying backend was changed or shown defective by this evidence.

## Target-design-only correction

1. Added candidate `DeleteEffectProof` with explicit root/path, original byte digest/generation, stated physical absence and backend receipt reference.
2. Exact documented executor now checks `conditional_finalize` receipt type, destination path and scope, existence, source digest and a generation; and verifies every required deletion proof field against the requested source.
3. A discrepancy *after calling a physical effect port* takes `OUTCOME_UNKNOWN` with pending reconciliation, not `FAILED_NO_EFFECT`, because a backend may have committed despite returning a misleading receipt.
4. Added test scaffolds FR-13/FR-14 in the existing LDD and ten negative fake-backend result variants to existing documentary AST-execution tool. Existing positive delete fake now returns the same candidate typed proof. These are a **self-authored executable candidate regression probe**, not an external authority attestation or storage proof.
5. Physical proof remains `LCD_BLOCKED`: the backend must attest the conditional write/deletion and generation/absence under race/crash, verify durable pending/receipt records, and enforce approved principal/resource scope. Typed class equality does not make remote physical bytes safe.

**Verification awaiting new exact CI:** source/AST fragment tests are registered in existing knowledge workflow; their actual result must be read at the resulting new commit. Do not infer test success merely from authoring or GitHub push.

**Independent scope and source accounting:** no 566-source census read state or material disposition changed, no Research→Science LOSSLESS claim, no production code implemented, no independent implementer clearance. Maintain `LCD_CANDIDATE` for local plan and `LCD_BLOCKED` for physical safe destructive mutations.

**Next:** check exact CI result and fix any documentary/fixture regressions; then risk-weight host admission, source-to-Artifact causal lineage and Science meaning gaps. Separate cold implementer assessment required for readiness.
