# Dynamic admission, effect evidence and journal subscriptions

Date: 2026-11-25. Scope: P11-R2 and journal subscriptions for the four capability kinds. Status: implemented and locally verified. Implementation checkpoint: c40f4827fd84d0af000933721063302bb3a8efc3.

The corrections retain the existing capability catalog, compiler, execution session, value owners, effect authority and notification runtime. Execution commits journal facts; subscriptions select verified positioned records, prepare immutable intents and use the existing delivery and reconciliation path.

## 1. Audit decisions and regression evidence

| Item | Confirmed defect and correction | Regression owner |
| --- | --- | --- |
| R12 | Dynamic fragments lost selected bindings and forwarded unresolved selector references. One fragment admission installs tasks, scopes and binding identities with their obligations. Selection values resolve under owned reads; scientific input and parameter evidence remains intact. | tests/unit/composition/test_dynamic_selection.py; tests/unit/execution/test_external_wait_deadlines.py |
| R13 | A competing CAS rejection could leave the actual confirmed destination without a current record. Writer contention, destination state, analytical basis and attempt authority now have separate qualification. Ambiguous physical ordering remains explicit uncertainty. | tests/unit/execution/test_effect_current_competition.py; tests/integration/capability_pilots/test_effect_lifecycle.py |
| R14 | Preparing new notifications reread released source records for unrelated completed history. An intent now pins minimal verified selection evidence; finished unrelated dispatches cannot block a later obligation. Pending handoff still performs its actual admission checks. | tests/integration/capability_pilots/test_required_notification.py |
| R15 | A single page could omit required dispatches or report a prefix as complete. Required preparation fixes a journal head, completes source preparation, scans bounded pages and freezes the entire selected dispatch set. Incomplete preparation or selection fails before handoff. | tests/integration/capability_pilots/test_required_notification.py; tests/unit/notifications/test_capability_selectors.py |
| R16 | Internal detached reads, map iterators and parameter copies could outlive memory accounting. Internal reads now require explicit scopes; iterator and child readers retain leases for their full lifetime. Plan isolation copies bound materials once while reusing immutable graph metadata. | tests/unit/execution/test_values_consumption.py; existing placement and session retention regressions |
| R17 | Publication pressure could wait indefinitely without a consumer, and result-wait timeout did not define execution lifetime. Snapshots expose acknowledgement waits. Autonomous waits have a finite configurable policy; managed waits resume on acknowledgement. Execution timeout and result-wait timeout are distinct. | tests/unit/execution/test_external_wait_deadlines.py |
| R18 | declared_sources did not check actual operand provenance. Each operand now declares and proves its source requirements against actual qualified SourceUse relationships. Portable calculation evidence preserves operand roles and actual uses. | tests/integration/capability_pilots/test_ratio_declared_sources.py |

## 2. Journal-first notification semantics

All four kinds publish accepted named outputs and their own terminal completion facts. Exact subscription coordinates select capability identity, capability kind, logical scope path and output name. An independently accepted useful output can be notified even when its enclosing scenario later fails; that acceptance does not imply successful aggregate completion.

The retained fact contracts are value.accepted version 2, effect.confirmed version 2 and capability.finished version 1. Technical outputs may have no processing role. Canonical owned values still require their admitted canonical identity; the journal contract can also explicitly represent an external acceptance occurrence without claiming a content hash.

notify.required serves a complete obligation for the chosen journal topic. notify.accepted restricts its topic to accepted outputs; notify.saved restricts it to confirmed effects and its exact storage receipt. Explicit run, effect, subscription and request selectors intersect. notify.reconcile uses the original attempt evidence and does not blindly resend unknown deliveries.

Pure notification capabilities are excluded from business subscription facts to prevent recursive self-notification. Mixed business and notification work retains its ordinary result and completion facts. A root capability's own completion is consumed after that capability finishes; an internal step cannot require its enclosing completion to have already occurred.

Additional regression owners: tests/integration/capability_pilots/test_capability_subscriptions.py, test_journal_subscription_semantics.py, and tests/unit/execution/test_service_journal_boundary.py.

## 3. Integration findings

- Reference admission compared a raw content digest with the canonical revision-aware descriptor fingerprint. It now validates the same identity that preparation pins.
- An explicit source_run_id was ignored when an exact saved effect was present. Both constraints now apply together.
- A command containing both business effects and notification effects could be classified as pure service work. Suppression now requires genuinely pure notification semantics.
- Zero-sized metadata-only plan copies unnecessarily occupied a reservation identity. Material ownership omits zero-byte reservations.
- Expanded operand-source evidence changed the embedded snapshot language. Observation metadata now has edition 4, with its registered processing adapter updated; edition 3 is rejected explicitly rather than interpreted under a different shape with the same schema identity.
- A material's opaque source locator could fail the accepted-fact projection's logical identifier field. The owned value retains its complete source evidence; the public journal projects only an admitted logical source ID. A real material.read-to-notification regression verifies that a URL locator cannot suppress the accepted-output fact.

## 4. Verification and continuing scope

The final complete suite passed: **1,950 passed, 7 skipped**, 7 warnings, 322.77 seconds. This adds 76 passing cases to the P11-R checkpoint. The catalog contains 22 commands, 13 operations, 2 scenarios and 1 cascade (38 definitions). The exact wheel and sdist share one verified implementation inventory. A fresh installed wheel passed pure catalog and subscription discovery, all reference-manifest validation, the offline SDK example and retained-output lifetime without optional numerical, workbook or HTTP backends. Import direction, release integrity, executable registry admission, reference editions, maintained README links and whitespace checks passed. No GitHub Actions were used. The adjacent validation.json retains exact distribution digests, the source checkpoint, prior measurements and evidence limits.

All 120 original acceptance cases retain their scoped status and verification routes. The regression evidence covers the stated local mechanisms and controlled pilots. Complete domain migration remains P12-P18; complete machine surface and transition removal remain P19-P21. Actual durable-host and external-protocol guarantees remain H01/H02.
