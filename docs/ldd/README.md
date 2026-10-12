# Low-Level Design — selected risk-sensitive Strategy Box mechanisms

**Status:** bounded **candidate** specifications. They are not deployed code, not adopted external platform protocols and do not substitute for accepted Product Decisions. Design relations inherit conditional `TW-SB-2026-10-09-CANDIDATE-1`, `TH-SB-2026-10-09-CANDIDATE-1` and `PA-SB-2026-10-09-CANDIDATE-1` where relevant.

- [Twenty-eight execution observability, crash and recovery conformance cases](observability/execution-truth-and-recovery-vectors.md) — independent attempts, incomplete journals, failed log sinks, authorized streams, unknown effects, retention and lifecycle; all unexecuted.
- [Twenty-five machine-operation adapter conformance cases](capabilities/machine-operation-adapter-conformance.md) — curated cross-client/domain schemas, catalog identity, input/effect security, retries, long jobs and protocol version failure cases; all unexecuted.
- [Thirty scoped authority, privacy and effect conformance cases](security/scoped-authority-and-privacy-vectors.md) — conditional L0/L1/host/machine threat matrix with strict actor, plan, resource, field, log, cursor and unknown-effect boundaries; all unexecuted.
- [Staged → Verified → Published Artifact](artifacts/staged-publication.md) — candidate local publication states, recovery, tests and faults.
- [Neutral provider conformance vectors](extensions/neutral-provider-conformance-vectors.md) — 98 source-preserved public-neutral test intentions; not an implemented or executed certification suite.
- [Used-source receipt and byte provenance](data/used-source-receipt-boundary.md) — first local Python-core conditional seam with 18 negative tests, storage/evidence boundary and no universal Source Catalog.
- [Host attachment across Web and Windows/AppDock](hosting/host-client-attachment-boundary.md) — admitted planned host target, alternative Windows packaging and 51 unexecuted proposed host conformance vectors.
- [Host problem receipts and evidence degradation](observability/host-problem-receipts-and-evidence-degradation.md) — qualified diagnostic registration, recorder ambiguity, mandatory-audit and bootstrap/support-bundle boundaries with 24 unexecuted negative cases.
- [FRG cleanup plan trust, byte replacement and destructive-effects guards](application/frg-cleanup-effect-guards.md) — five *executed current-source fault characterizations* versus twelve **unexecuted** target admission vectors, scoped FileStore effects and stale archives.
- [Local scenario execution without Qt-owned application truth](application/local-scenario-orchestration-boundary.md) — candidate extraction of the existing sequential runner's semantics, error classes, observation and projections before any physical service split.
- [Activation and package-binding conformance](integration/activation-contract-verification.md) — pinned Windows/AppDock local integration defects and proposed release/fault tests, without creating a new manifest.

LDD provides reproducible states, checks and failure vectors only where a real engineering consumer needs them. Unresolved durable Job, ACL, multi-user authority and hosted API semantics cannot be certified until their actual scope and product policies are admitted.
