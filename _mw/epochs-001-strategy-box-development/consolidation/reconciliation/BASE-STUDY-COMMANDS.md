# Commands, Scenarios, Cascades, and planning — bounded source extraction

**Original:** `SB-SRC-0024`, complete source L1–L2085, blob `201ca931a09f5bf7bba15e364da50726fdca291f`, from pinned core research corpus `8459dc58922b7e8df853cf1d9e8131fa9e132580`. **Extraction:** 32 provisional material units with locators, role, disposition and evidence boundary in `units/BASE-STUDY-0024.jsonl`. Original research unchanged. The master census retains `material_unit_state=unaccounted`, advancing only `read_state=full_read` for this exact source.

## Current implementation and terminology drift

The selected Windows implementation contains an operation catalog, an atomic Scenario wrapper for enabled operations, one composed Scenario, and a sequential scenario runner that builds per-step results, logs and artifacts. This provides a real *starting mechanism*, not evidence of a compiled DAG planner, multi-job executor, cross-run deduplication, or durable Cascade model.

Core uses `Operation` in the sense of a stable subject-level use case, while the study proposes a narrower technical `Command` inside user-facing `Scenario` and multi-scenario `Cascade`. That distinction is a **research language/model proposal**; no canonical `CommandSpec`, `CascadeSpec`, `ExecutionPlan` signature or UI mode is authorized by this extraction. An earlier 2026-10-07 execution-control study also uses the terms Operation/Scenario/Case, so consumer-specific meaning must be reconciled before final Target WHAT, rather than treating terminology as a mere rename.

## Critical scientific/technical distinction: equivalence of effects

A planner cannot deduplicate two requests simply because their command names match. Equivalent computation inputs may permit common computation, while separate writes to different output destinations remain distinct effects. Reuse may require comparing canonical parameter values, input snapshots, source freshness requirements, permission scope, target destinations and allowed side effects.

In-plan **deduplication** answers whether two currently requested nodes can share one result; **cache reuse** answers whether an older stored result is still eligible. Neither establishes remote idempotency or guarantees an externally visible effect happened once. A shared resource such as source access may be modeled as a capability/lease instead of repeating a 'connect' command.

A stricter freshness requirement can sometimes satisfy a weaker one, but not vice versa. Such substitution needs explicit validity proofs; it cannot be inferred from an apparently more recent filename alone.

## Alternative designs and negative space

- A Scenario is a meaningful user task whether internally linear or DAG-shaped; Cascade composition across tasks need not copy scenario definitions.
- Explicit Cascade membership gives a fixed reproducible list; selection by tags/conditions offers dynamic convenience at the cost of stronger version/policy binding.
- Parallel DAG nodes require resource and effect coordination, whereas the existing sequential loop offers simpler reasoning. A separate planner is a **candidate investment**, not mandatory for all small workflows.
- Technical command browsing belongs chiefly to development, diagnosis and advanced operation; front-page catalog saturation is a research UX risk.
- A permitted external cognitive consumer remains scoped to allowed operations/plans, not arbitrary Python, host shell or raw filesystem authority.
- Retry, Resume, Repeat and Cancel are different identity/effect transitions. Nested retry policies can multiply network attempts and unintended external effects.
- Cascade outcomes should preserve partial, unknown and independently failed components rather than being collapsed into a single boolean.

The study contains suggested folder layouts, API fields, roadmap phases and analogies to workflow products. They remain historical Research, not source of current implementation truth or Product Authority. No tests or running deployment were verified in this Work.

**Lineage:** this study draws on current-state Windows/core and overlapping execution/observability work. Common conclusions across files are dependent evidence, not independent confirmation. Downstream SCIENCE requires a direct proof lane for operational/semantic assertions and an independent source-to-owner conservation check.

**Next:** the original multiuser/single-node state and authorization study `SB-SRC-0036`, followed by cross-theme reconciliation of the activated execution/ownership role cluster.
