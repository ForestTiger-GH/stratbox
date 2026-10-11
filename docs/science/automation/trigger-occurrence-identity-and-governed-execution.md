# Trigger occurrences, background work and governed automation

**Question:** how schedules, source-change watches, event-driven rules and machine proposals become ordinary authorized Strategy Box Work/Run/Job without accidentally creating a second execution system or duplicating external effects. **Status:** scientific comparison of current scaffolds, explicit product intent and target protocols. None of the illustrated Automation/Trigger classes, durable scheduler, remote host or conditional watcher is certified as a current Strategy Box service.

## 1. The actual background scaffold and its missing promises

The pinned [Windows background registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/registry.py) exposes three conceptual entries: checking source publications, checking a workspace and updating caches. [BackgroundProcessStore](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) keeps enablement and reported status in memory, with manual result/error update functions. `schedule_label` describes intended cadence for UI, **not** a running scheduler, persisted occurrence or guaranteed task admission. Local [Qt ScenarioCoordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) admits one active foreground Scenario, not a general multi-job background service.

The external managed platform may own installed process/Node/Session uptime and activation. Its process state, however, is **not** the product's schedule, source condition, permission, statistical Result or Job terminal outcome. A future real host must prove that admitted tasks survive a disconnected Web/Android client; that behavior is distinct from the user's expressed default that fully local foreground computation generally stops when the desktop program exits.

## 2. Rule, trigger, occurrence, Run and notification are different truths

| Semantic object | Identity and lifetime | What it cannot imply |
| --- | --- | --- |
| **AutomationSpec** | Versioned enduring rule; owner, enabled state, run-as authority, target definition/preset, trigger and policy | A Job is running right now |
| **TriggerSpec** | Type and conditions to look for; calendar/source/event/manual/condition | A condition has already been observed |
| **TriggerEvaluation** | Actual check at time/source context with evidence and status | A Work must necessarily be admitted |
| **TriggerOccurrence** | One deduplicated meaningful match or due instant under the rule revision | A worker has started or an external effect succeeded |
| **WorkCandidate** | Proposed accountable objective from the occurrence | It has passed rights/plan validation |
| **Run/Job/Attempt** | Admitted plan, scheduling unit and physical execution under ordinary application authority | Source publication was valid or outcome accepted |
| **NotificationReceipt** | Targeted delivery, seen/acknowledged status and recipient | Source condition, domain fact or Job truth |

One AutomationSpec can generate zero, one or many occurrences over time. One occurrence can be skipped, coalesced, require approval, or produce a Run in an existing Work. A source watcher can truthfully report **NO_CHANGE** without creating an endless Work, and a scheduled Run can finish with PARTIAL/FAILED/UNKNOWN even if the triggering occurrence was valid. Disabling a rule stops future occurrences by default; it does **not** retroactively cancel already admitted work.

**Background** is a placement/lifetime property, not a separate kind of statistical scenario. A human can launch a Job in background; a scheduled Job may run while the client watches it; an AI proposal may be executed foreground under approval; a listener may continue observing without any Job running.

## 3. Five trigger classes have different evidence and identity

| Trigger | What is being assessed | Deduplication identity | Important error category |
| --- | --- | --- | --- |
| **Schedule** | A civil calendar instant is due | Automation ID + rule revision + resolved scheduled instant | DST fold/gap, missed period, duplicate after restart |
| **Source change** | A verified publisher/source snapshot differs in a relevant way | Source identity + old/new qualified source version + rule revision | Filename/mtime-only false detection, mirror double count |
| **Event** | A trusted scoped domain/platform event matches a rule | Authoritative event identity + rule revision/scope | Duplicate delivery, event schema change, unauthenticated event |
| **Manual trigger** | User explicitly requests the defined action now | Authorized command/request ID + effective parameter basis | Confusing “run now” with a calendar occurrence |
| **Condition watch** | A scoped predicate enters an actionable state or stays true per policy | Predicate/rule revision + evaluated evidence/time window + debounce state | False positive, repeated alert, unknown observation interpreted as false |

A long-running remote listener differs from polling in process/resource needs, yet meaningful events must still be normalized through the same **occurrence and admission** boundary. Neither a watcher nor a cron expression is allowed to bypass the effect authorization and idempotency checks used for manually started operations.

Source freshness deserves special care. `HTTP 200` does not prove new official content; two mirrors may carry one source version, and the same URL can deliver revised bytes. A source-change event should bind actual source identity/period/content/version and validation strength. Publishing a status such as “no updates” after authentication failure or inaccessible source would be misleading; preserve `NO_CHANGE`, `UNKNOWN`, `UNAVAILABLE` and `EVALUATION_FAILED` distinctly.

## 4. Scheduling follows civil-time semantics, not a countdown label

The exact time rule needs an **IANA time zone and an accepted calendar interpretation**, including daylight-saving gaps and folds. “08:00 every workday in Europe/Moscow” is not the same contract as every 24 elapsed hours; devices in Helsinki or elsewhere must see one shared intended rule rather than reinterpreting it using their local time zone.

A candidate per-rule policy should define:
- missing local time on spring DST transition: `skip` or `next_valid`;
- repeated local hour in autumn: once with chosen fold, or explicitly twice;
- missed occurrences during an offline week: `skip`, `latest_only`, `coalesce`, bounded catch-up, or review;
- overlapping Runs: skip, queue one, coalesce or parallel only if resources/effects permit;
- clock changes, rule revision, pause/resume, source freshness and calendar-definition upgrades;
- catch-up and retry **budgets** so outage recovery cannot produce an uncontrolled burst.

The **intended wall-clock occurrence**, resolved instant, evaluation time, accepted Run time and actual start time differ. Recording only `next_run_at` or a schedule label loses these distinctions. Existing occurrences remain bound to the original rule revision when automation settings change.

## 5. Evaluation state and admission state must not be collapsed

A candidate event flow:

```text
Evaluate TriggerSpec under rule revision + verified input scope
   → OCCURRENCE OBSERVED / NO_CHANGE / UNKNOWN / FAILED
   → apply duplicate, debounce, misfire and suppression policy
   → SKIPPED | SUPPRESSED | NEEDS_INPUT | NEEDS_APPROVAL
   → ADMISSION REQUEST with trusted run-as principal and event evidence
   → validate Operation/Scenario/Scheme versions, available provider bindings,
      typed params, source/registry versions, effects, resources, grants
   → durably accepted Work/Run + Job(s), or explicit rejection/conflict
   → executor Attempt(s) with effect intents, receipts and qualified Result
   → permitted user notifications and Work acceptance/closure
```

The actor of a trigger is not automatically the **security principal** under which resulting work can delete/export files. `run_as` needs verified delegation, current rights and expiration policy. A machine or AI-generated plan remains a proposal until the same deterministic validation gate is satisfied. A revoked grant while queued must be checked again at the protected effect boundary; previously approved plan digest cannot cover changed destructive targets.

There is no new scientific `BackgroundScenario` or `AIScenario` engine required here. Automation chooses *when* to propose the same subject Operation/Composition. The domain library can still be called directly from an authorized Python script without creating a universal Work database.

## 6. Crashes, repeats and the exact-once illusion

A scheduler may evaluate the same due instant twice after crash/restart; transport can resend a command after losing admission acknowledgement; an HTTP client, domain source downloader and JobManager may each independently retry. If left uncoordinated, two Runs or duplicate external effects can be produced even when the task definition appears idempotent.

Use independent keys:
1. **Trigger occurrence identity** to suppress duplicate calendar/source/event matches;
2. **Admission idempotency identity** to return the same accepted logical Run for the same submitted request;
3. **Attempt identity** to preserve each new physical execution;
4. **Effect identity/postcondition** to determine what actually happened to a particular output generation;
5. **Resource claim** to serialize conflicting writes or constrain source/API traffic.

A timed-out publish may already have succeeded. The safe state is `OUTCOME_UNKNOWN` until an effect receipt, actual verified published digest/generation or authorized manual investigation establishes a disposition. Blindly repeating a destructive action “because the scheduler says failed” is unsafe.

An expired worker lease does not force-stop a stale worker. Resource locks, leases and actual **fencing at publication** are distinct. A single-writer local profile may reasonably avoid distributed leases; a future takeover-capable host profile needs stronger tests.

## 7. Capability and provider changes across rule revisions

The rule may reference a published Scenario or Operation revision plus an approved preset. Before a Run starts, a planner should record the actual resolved operation contract, source snapshot/freshness policy, provider binding versions, output target and permitted effect class. A provider installed today but missing on tomorrow's scheduler host cannot be treated as automatically ready. A changed provider, permission or source schema may require replan and new approval.

The user-visible automation card should distinguish:
- **Rule enabled:** future evaluations are allowed;
- **Trigger last evaluated:** verified evaluation time and its outcome;
- **Next due:** scheduled instant and timezone;
- **Last admitted Run:** a real accepted identity and actual lifecycle;
- **Current workers:** live/unknown from an actual executor;
- **Last result:** qualified analytics/artifact with partial/unknown and freshness states.

Showing “running” solely because a rule is enabled, or “no changes” solely because an HTTP request failed, falsifies execution history. Client-safe warnings can be routed to a rule owner, affected Work participants or a resource audience, without broadcasting raw private logs.

## 8. Candidate vertical probes; none are passed results

| Probe | Failure it must catch |
| --- | --- |
| Same calendar occurrence processed twice after restart | Duplicate accepted Run or effects |
| DST skipped/repeated hour | Unplanned zero or double invocation |
| Week offline with catch-up | Unlimited burst or changed source-as-of |
| Disabled rule while its Job runs | Premature cancellation without separate action |
| Source URL unchanged but bytes revised | False “no update” |
| Mirror A and B publish identical upstream bytes | Duplicate independent source-change event |
| HTTP auth refused | Misleading `NO_CHANGE` instead of `UNAVAILABLE` |
| Condition stays true over many polls | Repeated spam absent debounce/ack policy |
| Listener reconnects with repeated event | Second occurrence rather than same one |
| Approval revoked while Run queued | Unauthorized output effect |
| Provider revision changed before new Run | Invisible binding substitution |
| Lost ACK after workbook publish | Blind overwrite instead of effect reconciliation |
| Shared heavy solver and periodic watcher | Starvation or underestimated resources |
| Two devices view same rule | Different invented Job truth per client |

Operational parameters such as watcher cadence, acceptable false positives, CPU/memory/traffic caps, exact notification audience, RPO/RTO and whether host autonomy is needed require Product/Operations approval and real benchmarks. This article performs no live scheduler, timezone-misfire, node-outage, effect-loss or cross-client test.

## 9. Decisions and cross-theme relationships

The dated consolidated extension/automation research contains **32 CX candidate system invariants, 25 historical conflicts and 32 unresolved implementation questions**, only some directly about scheduling. Important unresolved automation questions include predicate/evidence representation, event-source trust, exact occurrence identity after retrospective revisions, civil-time parser/zone rules, misfire/catch-up, listener-versus-polling choice, use of cached credentials, fairness, retention/cursor compaction and authorized machine action.

It also preserves a physical-design conflict: an early SQL-backed universal JobManager is one proposal, whereas later user-focused research permits simpler validated file-backed single-writer storage under the external platform's managed root. Neither backend is an accepted requirement. The invariant is one trustworthy admission and effect-reconciliation authority under the selected deployment profile.

Related maintained topics: [Work planning and scheduling](../work/admission-planning-resource-scheduling-and-recovery.md), [interruption and checkpoints](../execution-and-diagnostics/interruption-cancellation-retry-and-checkpoints.md), [provider discovery and readiness](../extensions/provider-discovery-binding-readiness-and-conformance.md), [semantic definitions vs invocation](../capabilities/composition-identity-and-user-machine-projections.md), [source-vintage integrity](../data-and-knowledge/source-observation-vintages-and-replay.md), and [authorized event feeds](../collaboration/authorized-streams-read-cursors-and-private-work.md).

**Scope-constrained conclusion:** durable rules and occurrence identities are required *if* product-owned background automation is delivered; they do not justify declaring the present in-memory UI scaffolds a service, nor do they force a separate workflow engine, host repository or machine-only business logic.
