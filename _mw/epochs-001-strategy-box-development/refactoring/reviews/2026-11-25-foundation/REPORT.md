# Foundation audit resolution: P11-R

Date: 2026-11-25. Scope: capability foundation P00-P11. Status: implemented and locally verified. Implementation checkpoint: 76d8e58b444283709becc1e486d1e8f22a0a64d7.

The confirmed defects are resolved within the existing capability, composition, execution, value, effect and observation owners. One session still executes the graph. Source-specific migration remains a separate P12-P18 responsibility.

## 1. Decisions and executable evidence

| Item | Disposition and resulting behavior | Regression owner |
| --- | --- | --- |
| R01 | Confirmed and fixed. Strict older-first resource priority removes aged waiter cycles while preserving independent work and large-claim admission. | tests/unit/execution/test_resource_fairness_order.py |
| R02 | Confirmed and fixed. All graph/scope/map/collection projections retain one managed placement owner; spill clears its resident payload and reads/copies hold accounted leases. | tests/unit/execution/test_values_placement.py; test_values_placement_session.py |
| R03 | Confirmed and fixed. Parent and local conditions form a conjunction for calls, maps and collection branches; disabled parents cannot authorize nested writes. | tests/integration/capability_pilots/test_condition_conjunction.py |
| R04 | Confirmed and fixed. Public outputs resolve through their own command/operation/scenario/cascade acceptance record. Named predicates admit independent outputs; cross-output predicates wait for their whole dependency group. Accepted nested results remain separately accessible after parent rejection. External invocation prerequisites gate acceptance and fact publication. | tests/unit/execution/test_scope_acceptance_records.py; test_scope_global_predicates.py; test_scope_external_prerequisites.py |
| R05 | Confirmed and fixed. In-flight and completed permissions are distinct; exact prepared identities and actual input/parameter provenance govern consumers. Equal payloads cannot borrow another source or calculation basis. | tests/unit/execution/test_reuse_runtime_policy.py; test_work_reuse_assessment.py |
| R06 | Confirmed and fixed. Selection flows through exact, goal, call and map preparation. Used group, recipe, method, profile, schema and reference identities are pinned and checked again. Typed authoring references have distinct fingerprints. | tests/unit/capabilities/test_binding_admission.py; tests/unit/composition/test_audit_preparation.py |
| R07 | Confirmed and fixed. Receipt lifetime follows result/read/cache/recovery owners; completed attempts and known history are bounded. Source freshness requires an explicit owner-admitted current-edition policy, separate from storage CAS and run ordering. | tests/integration/capability_pilots/test_effect_lifecycle.py; tests/unit/execution/test_effect_authority.py |
| R08 | Confirmed and fixed. Pre-admitted, bounded immutable publication obligations survive a full journal. Additional physical writes require additional publication credit before mutation. Dynamic expansion distinguishes impossible claims from temporary pressure. | tests/unit/observability/test_publication_obligations.py; tests/unit/execution/test_publication_admission.py |
| R09 | Confirmed and fixed. READABLE and PRODUCTS roles differ; extraction produces coherent observations, coverage and findings. Actual evidence supplies qualification. Analytical pairs explicitly specify compatible semantics and provenance. Axis coverage and complete coordinate coverage are distinct. | tests/integration/capability_pilots/test_functional_semantics.py; test_coordinate_coverage.py |
| R10 | Implemented. Regressions include real retained-memory release, parent guards plus effects, unknown write recovery, live required notification handoff, exact effect selection, bounded history and source-edition races. | tests/integration/capability_pilots/test_required_notification.py; existing and new foundation tests |
| R11 | Verified the complete local suite, exact wheel and sdist, installed minimal environment, owner imports, executable registry, reference editions and current milestone. | validation.json and the current refactoring milestone |

## 2. Additional defects closed during integration

- A predicate over a partial output map could accept early and later revoke acceptance. Predicate dependencies now settle before any affected output is exposed.
- A dynamic slice larger than total publication capacity could wait forever. It now fails with an explicit unsatisfiable claim.
- Equal semantic parameter values with distinct input receipts could share work. Full parameter evidence is now part of eligibility.
- Matching all marginal subjects/metrics/periods could claim completeness for a sparse diagonal dataset. Analytical completeness now uses explicit exact grain coordinates; axis coverage has its own status. No Cartesian product is inferred.
- Observation metadata edition changes exposed a stale source-context adapter. The registered adapter now matches edition 3 exactly; source identities, groups and releases survive roundtrip.
- An embedded FNS snapshot reader duplicated the common metadata layout. It now delegates reconstruction to the canonical codec, preserving actual evidence and source uses while rejecting unsupported schema editions.
- Empty pass-through scopes could finish before external inputs were accepted or publish accepted facts before external ordering prerequisites settled. Both public acceptance and fact publication now wait for those prerequisites; explicit failure guards retain their intended fallback behavior.

## 3. Functional contracts and operational boundaries

Extraction exposes observations, coverage and findings as one coherent result. Findings retain the scope of their actual assessment even when a later view filters observations. A caller choosing an observation-only output still receives a value carrying its actual evidence.

calculate.ratio requires an explicit analytical pair: exact input semantics, periods, releases, origin rules and output meaning. Technical numbers.evaluate remains the arithmetic primitive. The pair and actual method/profile/reference basis survive views, representations and portable snapshots.

Source and document revision labels remain opaque. A host can admit an exact current basis through an explicit publication policy; a later run with older inputs cannot gain publication authority merely by starting later or obtaining fresh storage CAS.

Required notifications operate in a real prepared graph. notify.saved selects the actual saved effect; unrelated historical intents cannot satisfy the current obligation. Unknown handoffs reconcile without a second delivery. Intent preparation is bounded and pageable.

The accepted-fact journal and its bounded outbox are process-local. Acknowledgement releases retained journal positions only after all relevant consumers have retained their intents or waived interest. Actual crash-durable state and an external protocol adapter remain H01/H02.

## 4. Continuing scope and evidence limits

The six top-level owners and the planned P12-P21 sequence remain in place. The existing 356 domain declarations, 90 sources, 144 profiles and 19 route templates remain migration inputs. Their initial callable dispositions are preservation candidates; each domain migration must refine them by actual responsibility.

All 120 original acceptance cases remain traced. A local mechanism regression supports its stated slice; it does not certify every publisher, historical layout, future domain stage or external host. The pilot source relationships are grounded in existing profiles, and their workbook contents remain controlled fixtures.

## 5. Validation

The complete final suite passed: **1,874 passed, 7 skipped**, with 7 warnings in 315.29 seconds. This adds 95 passing cases to the preceding P00-P11 checkpoint. The catalog contains 22 commands, 12 operations, 2 scenarios and 1 cascade (37 definitions). The exact wheel and sdist share one verified implementation inventory. A fresh wheel installation passed metadata discovery without optional numerical/workbook libraries, reference-manifest validation, the offline SDK example and retained-output lifetime checks. Owner imports, release integrity, executable registry admission, reference editions, maintained README links and whitespace checks passed. GitHub Actions were not used. Distribution digests, implementation identity, prior-checkpoint measurements and evidence limits are recorded in the adjacent validation.json.
