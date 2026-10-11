# Machine Scheme ownership, semantic composition and execution placement — unresolved research divergence

**Producer conflict record / NO ACCEPTED PRODUCT DECISION.** Compared exact frozen original studies `SB-SRC-0032` (blob `a0a1212e394b57792ec3b4f05066d5dbf540d21c`) and `SB-SRC-0029` (blob `8eafe0b9c74582d721ce24cdd67d010e6975cda5`). This is an explicit source-vs-source divergence rather than proof that either research view is already correct. Repository topology, names and package APIs remain Product/Engineering choices.

## The competing statements

| Research source and direct pinpoint | Original proposal | Important interpretation |
| --- | --- | --- |
| [`SB-SRC-0032`, L1926–L1945](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L1926-L1945) | The `stratbox` core/domain layer should own `SchemeSpec`, `Scheme graph`, `OperationSpec`, capability lifecycle, domain validity, effect/cancellation limits and provenance semantics. | Treats machine Scheme as part of importable domain capability supply, directly reusable by standalone Python consumers. |
| [`SB-SRC-0032`, L1947–L1965](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md#L1947-L1965) | The application/runtime owns actual queue, workers, retries, schedules, checkpoint storage, resume, user approval and actual placement. | Separates declarative Scheme semantics from physical job execution, but does not distinguish reusable domain-only from user-commissioned workflow composition. |
| [`SB-SRC-0029`, L1936–L1950](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L1936-L1950) | `CanonicalOperation` and source/registry semantics belong to `stratbox`, while `MachineScheme`, `Work`, `Run`, `ActivationBinding` and `ExecutionPlan` are assigned to a product/application-semantic `stratbox-core` owner. | Treats Scheme as product-composition semantics, separate from standalone domain core, and explicitly distinguishes Plan from host execution. |
| [`SB-SRC-0029`, L1103–L1152](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md#L1103-L1152) | The semantic application owner and durable headless host/process carrier differ; they may share a physical repository and are distinguished by ownership, not file count. | Clarifies placement of persistence/Jobs but does not prove all composition graphs must belong to one service. |

These propositions are **genuinely different** for a machine Scheme used both by a standalone Python notebook and a multi-user Work scheduler. Calling their `stratbox`/core vocabulary equivalent would erase an important source-level architecture decision.

## Three competing resolution models

| Model | Advantages | Costs, counterarguments and failure cases |
| --- | --- | --- |
| **A. All Scheme definitions belong to domain `stratbox`** | Standalone Python composition and testing; one stable discovery source shared across clients; avoids redefining deterministic domain graphs in the GUI. | Domain core can absorb user approvals, cross-app Work state, peer delegation, collaboration and host-placement assumptions; inappropriate dependency on application semantics. |
| **B. All Scheme definitions belong to product application core** | One uniform user Work/Scheme catalog with admission, Authorization, sessions, artifacts and planner; simpler shared execution semantics. | Standalone domain consumers must depend on product core to compose even purely mathematical transformations; nested source/domain pipeline might be recoded outside its authoritative owner. |
| **C. Semantic composition split by actual responsibility** | Domain exposes stable `OperationSpec` and optional domain-bound reusable pure compositions, while product application owns Work-facing `SchemeSpec`, activation, resolved plan, approvals and scheduling; reuse through explicit contracts. | Requires rigorous identity/adapter mapping and rules to prevent duplicate definitions, nested version drift, insufficient effect propagation and accidental circular imports. One named “SchemeSpec” may need more than one typed composition profile. |

**Current producer finding:** Model C is worth an explicit pilot because it preserves the independent standalone domain use case and the broader Work/Authority case without demanding two duplicative semantics. This is **an inference/hypothesis**, not a final disposition; Models A and B remain viable if actual user operations prove different. A physical `stratbox-core` repository or package is **not** required solely to express the product/application owner.

## A discriminating pilot, not a diagram-only compromise

1. Compose a source fetch, parsing, normalization and qualified export **without a user/session/host** in a Python notebook. It should retain source/registry versions, effects and domain Result meaning without importing Qt or a product Job store.
2. Include the same domain capability in a durable shared Work with an approval-required external write, a scheduled trigger and two remote clients. The Work owner should retain Authority, plan revision, exact activation, Job and artifact state; the domain definition should not import these runtime services.
3. Supply one reused operation in two schemes with changed source schema. A single canonical operation meaning changes or fails applicability consistently, while the Work activation and schedule semantics remain separately pinned.
4. Crash after externally committed write but before acknowledgment. The Run/Job layer persists `effect=UNKNOWN` and reconciles; neither graph definition silently converts a retry into a second write.
5. Verify that a machine consumer can inspect type/effects/validity for a top-level composition with **no arbitrary source introspection** and that the plan can be bound to exact definitions with no circular import.
6. Change the host carrier or UI while preserving source semantic identity and Work state: no transport-specific `SchemeSpec` duplication is allowed.

## Consequences for maintained Knowledge

The broad science article [compiled capabilities](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/science/capabilities/compiled-domain-capabilities-validity-and-deoptimization.md) correctly distinguishes `Capability`, `Scheme`, `ActivationBinding`, `ExecutionPlan` and `Run`, but it should not imply that **their final module/package ownership is settled**. Maintained [semantic ownership science](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/science/engineering/semantic-ownership-method-transfer-and-proportional-materialization.md) treats owner versus carrier as the decisive split, not source-filename naming.

**Required future decision:** determine semantic profiles of reusable domain compositions, product Work-facing compositions and activation plans through a real end-to-end pilot; then admit their ownership and determine package/repository realization. Preserve both historical source proposals with reasons if one is superseded. Do not create compatibility layers for old prototype names absent a current consumer.
