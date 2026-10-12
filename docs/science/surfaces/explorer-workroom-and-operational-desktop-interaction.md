# Explorer, workroom and operational desktop interaction: competing mental models

**Scientific question:** how to make a banking-statistics workbench learnable and operationally truthful when files, conversations, repeatable scenarios and long-running Jobs share one screen. **Status:** research-qualified, unapproved interface options; descriptions of the current desktop are bound to the [pinned Windows implementation](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). No user study, accessibility audit, native-device trial or deployed redesign is asserted here.

## 1. Why four different metaphors coexist

A dashboard centers monitoring indicators; an IDE centers files/editors and developer command surfaces; a messenger centers human discussion and unread state; a computation control plane centers authoritative Jobs, steps, progress and failure. Strategy Box needs elements of all four without making any one the universal representation.

| Mental model | What is valuable | What goes wrong when dominant |
| --- | --- | --- |
| Dashboard | Fast health and issue scanning | Cards hide file discovery, parameter preparation, provenance and multi-step execution |
| IDE | Strong panel geometry, keyboard search, logs, file navigation | Technical density and terminal vocabulary impose developer expertise on analysts |
| Messenger | Chronological context, collaborators, recoverable history | A Run wrongly becomes a text bubble and a Job failure becomes social “message delivery” |
| Workbench + control plane | Object-specific actions, lifecycle visibility and persistent outputs | Excess technical panels can crowd analytical content |

An effective synthesis uses **one active object**—Work, folder, Scenario, Run or Artifact—and a stable shell: navigation destination → contextual selector → main object view → optional inspector. The right pane is details for the selected object, not another competing global navigation system. The main surface should retain enough width for tables and documents; technical logs should expand only when needed.

The currently observed [manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) enters Scenario chat, and the dated desktop implements six rail modes: Explorer, Scenarios, Cascades, Background, Participants, Assignments. Those existing modes are historical implementation facts. The **four proposed logical destinations** below are an information-architecture experiment, not evidence of released navigation.

## 2. Four logical work areas, but not four mandatory buttons

| Destination | Primary user question | Core interaction | Context rather than separate root |
| --- | --- | --- | --- |
| Work | What am I investigating or discussing, and what needs my attention? | Thread/Work history, decisions, messages, linked Runs, approvals | Participants and assignments unless their real workload justifies a task center |
| Explorer | Which input, working file or published result is available to me? | Root-scoped file tree, details list, preview, provenance | Artifact metadata and permitted actions |
| Scenarios | What repeatable capability can I invoke? | Search, category, typed parameters, previews, favorites, presets | Cascade as composition/category of scenario |
| Runs | What is actually executing, queued, waiting, interrupted or completed? | Node/work-scoped run table, steps, accurate progress, logs, retry/cancel eligibility | Background as execution property, not a parallel job system |

A global Runs view and a Thread timeline should reference the **same Run identity**: the former optimizes cross-Work supervision; the latter answers how a particular investigation evolved. Each filtered view must respect access rights. A standalone “Participants” top-level route is warranted only if independent team administration or presence tasks actually emerge; a local avatar model does not prove that threshold. An empty “Background” screen without a scheduler must never suggest that enabling a flag schedules real execution.

The earlier idea of placing six distinct technical concepts on the activity rail maximizes feature discoverability in a prototype, but grows navigation entropy with every new entity. Conversely, compressing everything into Chat creates a weaker operational map. Both drawbacks explain the four-area candidate; empirical learnability and discoverability remain untested.

## 3. Long-lived Work and concrete Run must remain distinct

A Thread/dialog can contain several human and permitted machine messages, two or more Runs, evidence attachments, an approved result, a request for review and a later correction. Its reason to persist is *collaborative context*. A Run is one frozen execution with its own plan, attempts, outputs, effects, status and evidence. They have different closure and retention semantics.

```text
Work: monthly banking-source review
  Thread: questions, assigned review, approval of final claim
  Run A: refresh source snapshot, partial validation
  Run B: repeat after upstream schema diagnosis
  Artifact A: outdated workbook (superseded, retained by policy)
  Artifact B: verified workbook
  Outcome: accepted with one named residual uncertainty
```

A Run card in the Thread shows a stable link and truthful summary. It does not duplicate technical log lines, create another Run when the user scrolls, or silently mark Work complete on `job.succeeded`. A human message proposing an action, a permissioned action proposal, an accepted Job and a textual answer are four different visual and semantic objects. An agent suggestion should show target capability, parameters, expected effects, risk, required approval and outcome status rather than an ambiguous “I did it”.

## 4. Explorer should borrow familiarity, not the operating-system trust model

For analysts on Windows, **folder tree + Back/Forward/Up + breadcrumb + Search + Details list + optional preview + context menu** minimizes relearning. A spreadsheet directory is easier to scan in rows than as a wall of decorative cards. Base columns are Name, Type, Modified and Size; optional Scenario/Run/Provenance metadata belongs in a toggleable view rather than polluting the default file mental model.

The breadcrumb must be navigable, not a painted path. Suggested keyboard map: `Enter` open; `Alt+Left` back; `Alt+Right` forward; `Alt+Up` parent; `F2` permitted rename; `Ctrl+L` location; `Ctrl+F` contextual search; `F6` pane cycle. These bindings are **candidates** subject to collision checks with Qt native controls, screen readers and OS conventions.

A logical workspace tree does not imply permission to read the host filesystem directly. The current desktop has a local Explorer provider scoped to a workspace. A future remote client should obtain authoritative File/Artifact metadata and scoped actions from the application host. The UI can feel Windows-like while never exposing arbitrary server paths, other users' personal files or system storage. A “Reveal in Explorer” action has a meaning on a local desktop but may be unavailable on Web/Android; render only actions supported by the client *and* permitted by current server policy.

Dangerous actions require a true plan/apply distinction when consequences are material: show the candidate objects, identity, constraints and consequences; confirm the exact plan or ask for authorization; execute; then display observed result and partial failures. A green toast after a best-effort remote deletion is a false claim.

## 5. Scenario discovery and forms should scale with the catalog

When there are a few operations, cards are helpful. When there are tens or hundreds, searchable lists with stable categories, Favorites and Recent are more efficient for scanning; a secondary card view can support browsing. Users search for *what they want to do*; internal Command/Operation/handler identities are advanced metadata, not required navigation knowledge.

Form fields are generated from permitted parameter schemas. Recommended behaviors: basic fields first; advanced collapsed; bounded number/date pickers; derived or locked values displayed read-only; inline validation beside the erroneous field; a workspace-aware file picker; explicit effective defaults. Presets store **user-controlled parameter choices and references**, not duplicated mutable scenario definitions. A preset revision must be resolved under the current operation schema before launching.

A composite/cascade often reads best as a vertical sequence showing order, state and future actions. A graph is justified for real branching, parallel dependencies or debugging, not automatically for a four-step upload→parse→compute→export pipeline. The runtime plan can be more complex than the initial human-facing preview, but no omitted destructive effect may be hidden by that simplification.

## 6. Operational view and evidence-based progress

The global Runs surface answers operational questions that a conversation does poorly: *what is running across my authorized scopes, who initiated it, which resources are waiting, and what can I cancel?* A table can expose Scenario, actual stage, start/duration, initiator, foreground/background location, verified artifact links and status; sorting active/waiting first is a candidate, not a universal standard.

Progress is *determinate* only when a valid numerator and denominator exist. A step number does not equal fraction of total computational cost; animations that march toward 100% with elapsed time fabricate precision. During unknown-duration work, display the current stage, last reliable update, elapsed time, and a genuinely indeterminate activity indicator. “Cancel” and “Pause” only appear when executor capabilities and policies support them. A `cancel_requested` control is not proof that an external effect has stopped.

A dependable distinction is:
```text
Level 1 — Run card: stage + status + important actionable message
Level 2 — Inspector: per-step warnings, causal problem ID, artifact/attempt links
Level 3 — Separate log/problems panel: structured filtered technical evidence
```
A bottom execution panel has better horizontal width for long log lines, search and large file paths than a permanently narrow inspector. It should open contextually, virtualize large logs, allow copy with redaction, and separate raw debugging from an accessible user error explanation. Never broadcast restricted technical stack traces to everyone on a shared node.

## 7. Meaningful notifications, limited interruptions

A timeline with every heartbeat, retry or log record becomes useless. Keep *meaningful Work events*: admitted/run completed, significant warning, artifact published, approval requested, work assigned, correction or closure. Use a toast/OS notification for off-screen action needed, failed background work or explicit alert policy—not routine success while the user watches a Run.

The user-facing error should state **which action failed, on what stage, how trustworthy the partial results are and what can be done**. If next action is unknown, say so instead of fabricating a “Retry” button. A “technical details” drawer can contain safe identifiers for support while keeping full traces access-restricted. Accessibility means labels, focus, and textual statuses, not simply colored badges.

## 8. Geometry, typography, motion and responsiveness are hypotheses

The 2026 interface study proposed a four-part shell plus an optional bottom panel and quiet status strip, 4/8/12/16/24/32/48 spacing tokens, several radius tiers, and restrained type scale from compact metadata to prominent page titles. It suggested logical width regimes: **up to 640**, **641–1007**, **1008–1399**, **1400+**. These are *proposed thresholds* for testing, not measured invariants, and should be judged by content fit, translated text, font scaling, assistive technology and actual device widths. A right inspector that overlays at a smaller window must not make core work inaccessible.

The study's native-language proposal prefers Windows control and keyboard conventions, system/accessible typography, system/light/dark/high-contrast variants, quiet backgrounds and meaningful semantic colors. Styling should not convert success, failure or queued states into brand accents. It argued for small context-explaining animations rather than bouncing, parallax and ornamental transitions. It proposed inspector motion around 120–180 ms, subject to measured user experience and explicit reduced-motion preference. Later dedicated motion and visual studies refine timings and token values; the early numerical proposal is historically preserved here, **not** promoted as the current design specification.

The essential portability relation is:
```text
same authorized action and same state meaning
        → different desktop/web/mobile presentation profiles
        → equivalent accessible user consequence
```
A touch client may use bottom navigation, pages and sheets instead of the Windows rail, splitters and hover menus. Native layouts can differ radically without forking authorization, Work identity or operation meaning.

## 9. Accessibility and falsification

Target candidate acceptance families: keyboard-only navigation from a new Work through parameter validation, Run submission, result review and safe cancellation; visible focus and tooltips for icon-only buttons; status and warning independent of color; screen-reader descriptions that distinguish a message, Run, Artifact and approval; high-contrast and 125%/150%/200% scaling; reduced-motion behavior; no controls clipped under narrower window and long text; keyboard alternatives for drag-and-drop.

Failure experiments should explicitly exercise: a very long path and filename; hundreds of scenarios; tens of thousands of Run/Artifact records; streaming logs at high rate; a disconnection during an approval; missing workspace while diagnostic screens must remain reachable; a successful Job with failed artifact publication; user access revocation while the Work is open; a Run blocked indefinitely without progress denominator; dynamic language expansion and font scaling; many simultaneous notifications. No passing measured results are yet recorded for these experiments.

## 10. Trade-offs and open authority

**Observed:** the dated desktop has Scenario-first chat, local stores, inspector and six-mode navigation, plus Qt orchestration. **Research conclusion:** the workbench, dialogue and execution-control semantics are complementary; Work and Run must remain distinct if collaboration/history become real product needs. **Unaccepted design candidates:** four logical destinations, global Runs table, panel composition, keyboard shortcuts, default Details view, search/palette, responsive breakpoints, color and motion tokens. **Counterarguments:** four destinations may bury team approvals for a heavily collaborative deployment; a dedicated Team/Inboxes screen may become necessary, and highly expert analysts may prefer denser layouts than a calmer default. **Reopen:** actual user workflows, accessibility tests, screen-size evidence, accepted information architecture, device-specific interactions or implementation updates.

Related Science: [Work navigation](work-context-navigation-and-authorized-actions.md), [visual tokens](visual-token-values-contrast-and-layout-profiles.md), [state-driven motion](state-driven-motion-scrolling-and-execution-feedback.md), [client portability](semantic-portability-and-client-authority.md), [shared warnings](../collaboration/shared-conditions-and-log-access.md), and [operational failure truth](../execution-and-diagnostics/causal-observability-and-failure-truth.md).

## Original thirty desktop-surface acceptance expectations, with scope

The frozen October 7 desktop interface Research, §31 (`#L1894-L1944`), Git blob `0668c3af7cec9862e638ad1b3f74b8f847404fca`, proposes **30 UX checks** under six UI concerns. They are preserved here as **dated, source-line-addressed English interpretations**, not an assertion that the Qt app currently implements them or an approved release gate.

| Original source item | Candidate user-visible behavior | Exact source line |
| --- | --- | --- |
| `SB-SRC-0039/NAVIGATION-01` | Current top-level mode remains visible | L1898 (`#L1898`) |
| `SB-SRC-0039/NAVIGATION-02` | Back/Forward have predictable behavior | L1899 (`#L1899`) |
| `SB-SRC-0039/NAVIGATION-03` | Selection persists when inspector opens/changes | L1900 (`#L1900`) |
| `SB-SRC-0039/NAVIGATION-04` | Pane resize is remembered | L1901 (`#L1901`) |
| `SB-SRC-0039/NAVIGATION-05` | Narrow layout retains admitted functionality | L1902 (`#L1902`) |
| `SB-SRC-0039/RUN-01` | Typical Scenario discoverable through search or catalog | L1906 (`#L1906`) |
| `SB-SRC-0039/RUN-02` | Basic Run does not require knowing internal Operation IDs | L1907 (`#L1907`) |
| `SB-SRC-0039/RUN-03` | Parameters are validated before submission | L1908 (`#L1908`) |
| `SB-SRC-0039/RUN-04` | Run appears in timeline and Runs promptly | L1909 (`#L1909`) |
| `SB-SRC-0039/RUN-05` | Progress updates do not freeze UI | L1910 (`#L1910`) |
| `SB-SRC-0039/RUN-06` | Result is reachable with one action | L1911 (`#L1911`) |
| `SB-SRC-0039/ERROR-01` | Failed step is identifiable | L1915 (`#L1915`) |
| `SB-SRC-0039/ERROR-02` | Human-readable cause is visible | L1916 (`#L1916`) |
| `SB-SRC-0039/ERROR-03` | A recovery action is discoverable when available | L1917 (`#L1917`) |
| `SB-SRC-0039/ERROR-04` | Raw technical log remains accessible by permission but not forced onto user | L1918 (`#L1918`) |
| `SB-SRC-0039/ERROR-05` | Failed Run remains in history | L1919 (`#L1919`) |
| `SB-SRC-0039/EXPLORER-01` | Familiar Windows filesystem model is immediately recognizable | L1923 (`#L1923`) |
| `SB-SRC-0039/EXPLORER-02` | Current path location is always intelligible | L1924 (`#L1924`) |
| `SB-SRC-0039/EXPLORER-03` | Back, Up and Search behave predictably | L1925 (`#L1925`) |
| `SB-SRC-0039/EXPLORER-04` | Details view scales to large directories | L1926 (`#L1926`) |
| `SB-SRC-0039/EXPLORER-05` | Strategy Box metadata does not displace core file-navigation mental model | L1927 (`#L1927`) |
| `SB-SRC-0039/CHAT_WORK-01` | Timeline favors materially meaningful events | L1931 (`#L1931`) |
| `SB-SRC-0039/CHAT_WORK-02` | AI, human, system and execution events are distinguishable | L1932 (`#L1932`) |
| `SB-SRC-0039/CHAT_WORK-03` | Run card is not visually confused with an ordinary message | L1933 (`#L1933`) |
| `SB-SRC-0039/CHAT_WORK-04` | History is searchable | L1934 (`#L1934`) |
| `SB-SRC-0039/CHAT_WORK-05` | Thread may carry multiple Runs without being their execution owner | L1935 (`#L1935`) |
| `SB-SRC-0039/ACCESSIBILITY-01` | All critical flows support keyboard-only operation | L1939 (`#L1939`) |
| `SB-SRC-0039/ACCESSIBILITY-02` | Status can be distinguished without relying solely on color | L1940 (`#L1940`) |
| `SB-SRC-0039/ACCESSIBILITY-03` | High-contrast mode preserves hierarchy | L1941 (`#L1941`) |
| `SB-SRC-0039/ACCESSIBILITY-04` | Text scaling does not clip critical controls | L1942 (`#L1942`) |

**Competing original models:** the original prioritizes Explorer familiarity and workbench/chat/execution, but other work proposes epistemic Data/Knowledge/Decision navigation and Chat-first entry. The developer asked for useful minimal UI; an exact tab arrangement remains research. Android should preserve semantic status and permissions while rendering platform-native layouts.

A real acceptance run must exercise keyboard/focus, large-folder performance, truthful failures, authorized raw diagnostics, and status independent of color/motion. These thirty proposals do not prove a headless host, scheduler or shared Work service exists. Full semantic conservation of the other original 2,289 lines remains open.

## Additional original 01 surface evidence: twenty-two competing UX propositions

The earlier interface design note is a **historical UI research candidate**, not a current implementation contract or a newly admitted Product Decision. The following **22** source-row-traced English interpretations supplement the existing four original-heading references with material mechanisms, user-visible distinctions and falsifying cases. Status terms explicitly preserve conflict with later Work/Run/Thread, permission and device-portability research.

| Original source ID | Bounded English interpretation | Source-level disposition | Exact original line |
| --- | --- | --- | --- |
| `SB-SRC-0013/UX-DETAIL-01` | The first workbench sketch treated a messenger-shaped center as an operating surface for selecting, parameterizing, running and interpreting analytical Scenarios. | `HISTORICAL_UX_HYPOTHESIS` | L5 (`#L5`) |
| `SB-SRC-0013/UX-DETAIL-02` | The original Scenario object combined operations, parameters, events, artifacts, statuses, author, participants and change history; later Work/Run/Thread identity research challenges that aggregate ownership. | `CONFLICT_WITH_LATER_OWNERSHIP` | L7 (`#L7`) |
| `SB-SRC-0013/UX-DETAIL-03` | The UI document assumed a managed external platform would supply workspace, launch, diagnostics and file effects; this is a platform-contract assumption, not proof that every API was available. | `VERSIONED_PLATFORM_CONTRACT_REQUIRED` | L9 (`#L9`) |
| `SB-SRC-0013/UX-DETAIL-04` | Four visual zones were proposed: header, left navigation, central scenario conversation and right contextual panels. | `LAYOUT_ALTERNATIVE_ONLY` | L21 (`#L21`) |
| `SB-SRC-0013/UX-DETAIL-05` | Five left-navigation families were proposed: file Explorer, simple Scenarios, larger Scenarios, background processes and participants/assignments. | `LAYOUT_ALTERNATIVE_ONLY` | L36 (`#L36`) |
| `SB-SRC-0013/UX-DETAIL-06` | The Explorer was proposed as the default first view and carried file-opening plus copy/paste/delete actions; later design must distinguish browsing from authorized effects. | `AUTHORIZATION_AND_UX_PROFILE` | L44 (`#L44`) |
| `SB-SRC-0013/UX-DETAIL-07` | User presence and assignments were proposed to filter the shared conversation and operational evidence by participant; present permission model was not specified. | `COLLABORATION_CANDIDATE` | L52 (`#L52`) |
| `SB-SRC-0013/UX-DETAIL-08` | System settings were intentionally placed under a user menu instead of a dedicated primary rail item. | `NAVIGATION_CANDIDATE` | L54 (`#L54`) |
| `SB-SRC-0013/UX-DETAIL-09` | One dynamically updated chat card per Scenario Run was proposed, with author, time, phase, parameter snapshot and eventual outcome. | `PRESENTATION_NOT_CANONICAL_EXECUTION` | L60 (`#L60`) |
| `SB-SRC-0013/UX-DETAIL-10` | Per-user unread/read state was proposed for operational events; it is distinct from task acceptance or actual outcome receipt. | `READ_RECEIPT_SEMANTICS` | L64 (`#L64`) |
| `SB-SRC-0013/UX-DETAIL-11` | The pre-run scenario summary was expected to update as parameters changed, before the Run was admitted. | `PLAN_PREVIEW_CANDIDATE` | L68 (`#L68`) |
| `SB-SRC-0013/UX-DETAIL-12` | The original right sidebar was tentatively limited to a compact 20–30 percent screen region; this is a desktop geometry hypothesis, not cross-device law. | `UNVALIDATED_DESKTOP_GEOMETRY` | L72 (`#L72`) |
| `SB-SRC-0013/UX-DETAIL-13` | A unified event-log presentation was proposed for people and AI, but visibility of raw technical log payloads requires an independent permission and redaction boundary. | `PRIVACY_CONFLICT_WITH_RAW_LOGS` | L78 (`#L78`) |
| `SB-SRC-0013/UX-DETAIL-14` | Primary and advanced parameter groups were proposed with immediate reflection in the pending launch summary. | `CONTROLLED_PARAMETER_PREVIEW` | L82 (`#L82`) |
| `SB-SRC-0013/UX-DETAIL-15` | The early Operation record included handler, defaults, result kind and retry behavior; metadata alone would not make effects safe to repeat. | `MACHINE_CAPABILITY_SCOPE_CANDIDATE` | L88 (`#L88`) |
| `SB-SRC-0013/UX-DETAIL-16` | Background scheduled/event/monitoring behavior was conceptualized as a special class of Scenario; later Trigger/Occurrence/Job work challenges that identity collapse. | `CONFLICT_WITH_TRIGGER_JOB_MODEL` | L98 (`#L98`) |
| `SB-SRC-0013/UX-DETAIL-17` | Floating active-automation icons and event-based chat notifications were an explicit visual proposal, not a required status mechanism or accessible alternative. | `ACCESSIBILITY_AND_NOTIFICATION_CHALLENGE` | L102 (`#L102`) |
| `SB-SRC-0013/UX-DETAIL-18` | Participant online/recent activity and creator attribution were proposed as a lightweight collaborative view, conditioned on an authorized shared-node profile. | `SHARED_NODE_PROFILE_CANDIDATE` | L108 (`#L108`) |
| `SB-SRC-0013/UX-DETAIL-19` | The sketch envisioned AI reading structured operation and user history; unrestricted cross-principal history access does not follow from that UX goal. | `PRINCIPAL_PROJECTION_REQUIRED` | L118 (`#L118`) |
| `SB-SRC-0013/UX-DETAIL-20` | Explorer copy, delete and rename actions must be treated as scoped mutation intents, not implicitly authorized merely by displaying a file tree. | `EFFECT_AUTHORITY_SEPARATION` | L126 (`#L126`) |
| `SB-SRC-0013/UX-DETAIL-21` | User, work and system settings were proposed as separate groups; that grouping does not prove that every mentioned preference is useful or implemented. | `SETTINGS_MINIMALISM_UNADMITTED` | L134 (`#L134`) |
| `SB-SRC-0013/UX-DETAIL-22` | The sketch expected platform-provided activation/session/health context, while application-specific source/Work semantics remained a separate responsibility. | `PLATFORM_APPLICATION_OWNER_BOUNDARY` | L146 (`#L146`) |

**Adversarial product distinction:** a smoothly animated Scenario card does not certify a durable Run or external effect; a per-user read check does not signify acknowledgement of a problem; an AI actor's wish to inspect the same logs does not override each principal's authority. A layout optimized for four-pane Windows does not define Android/Web navigation, while an isolated worker can legitimately expose fewer capabilities than a hosted, authenticated multi-user environment. Background monitoring being displayed near a Scenario does not make scheduled Occurrence and one-shot execution the same semantic identity. A future Product decision needs a tested journey, workload and implementation owner for each adopted surface.

**Conservation limit:** these twenty-two addressable original propositions preserve a dated design alternative and known tensions, not the full meaning of all 178 physical original source lines or independent validation of preferred UI geometry. The source is retained for historical inspection; maintained Science remains the ordinary entry point.

## Residual concrete interaction claims from the original historical interface note — producer re-read

**Scope:** `SB-SRC-0013`, frozen historical source blob `2f2b05d1a1af3401fb402bfb43c8cc36a907d9fe`; fourteen **additional fine-grained source meanings**, not new Product Decisions. The preceding 22 source locators remain useful but do not exhaust the original note. This section retains operational details which could affect a later design challenge. The original is a **historical proposal**: the dated current Windows code and manifest, applicable external runtime versions and accepted product owners take precedence for current facts and commitments.

| Source meaning | Historically proposed mechanism | Disposition / falsification limit | Original witness |
| --- | --- | --- | --- |
| `SB-SRC-0013/UX-RES-01` | Operational log list ordering explicitly elevated scheduled, running and background operations before completed operations; completed rows were expected to display start, end and duration. | Ordering is an operational view preference; a display order proves neither scheduler existence nor clock accuracy. | L76 (`#L76`) |
| `SB-SRC-0013/UX-RES-02` | Artifact disclosure proposed linked Scenario/Run/author metadata, open/reveal/copy-path/jump-to-Scenario/open-log shortcuts and collapsed detail until expanded. | Quick actions must be supported by platform capability and resource-specific permission; a path is not a durable artifact receipt. | L80 (`#L80`) |
| `SB-SRC-0013/UX-RES-03` | Two right-hand zones were expected to scroll independently so parameters remain usable during inspection of long execution logs. | The original proposed two independent vertical regions; current drawer/tab geometry must be established from implementation, not inferred. | L84 (`#L84`) |
| `SB-SRC-0013/UX-RES-04` | Background process cards proposed trigger conditions, last and next execution, latest check outcome and a specific event journal. | Those fields are proposed UX vocabulary, not evidence that any scheduler or trigger executor existed. | L100 (`#L100`) |
| `SB-SRC-0013/UX-RES-05` | Floating active-process indicators proposed displaying the initiating user on hover and filtering both Scenario conversation and logs on activation. | Hover-only authorship is not accessible cross-platform; an icon or click does not attest actual active process state. | L102 (`#L102`) |
| `SB-SRC-0013/UX-RES-06` | Assignment display proposed active-first ordering, retained completion time and a link to originating Scenario or Artifact. | A local row does not prove delivery, remote ownership, permission or completion acceptance. | L120 (`#L120`) |
| `SB-SRC-0013/UX-RES-07` | The file navigator proposed a reverse path from files to the producing Scenario, creation time, initiating author and technical log. | Associating a path to a run requires trustworthy retained origin identity; renamed or externally edited files can break naive lineage. | L128 (`#L128`) |
| `SB-SRC-0013/UX-RES-08` | The three settings categories carried concrete examples: appearance/density/filter/notification and remembered form values; workspace/scenario/preset/artifact display; environment/diagnostics/update/log/platform integration. | Grouping and scope of listed preferences were proposal-level; no need, value, implementation or host edit permission established. | L134 (`#L134`) |
| `SB-SRC-0013/UX-RES-09` | The environment status view proposed separate indications of workspace availability, active mode, source, readiness, errors, recent launches, logs and results. | A visible node status summary must not flatten source readiness, live process health and recoverable evidence. | L136 (`#L136`) |
| `SB-SRC-0013/UX-RES-10` | The early user-facing status vocabulary explicitly distinguished ready, running, waiting, attention required, completed, completed with remarks, error and active background process. | Status labels are proposed translations, not a proven executor state machine; partial effects and observation failure need independent truth. | L140 (`#L140`) |
| `SB-SRC-0013/UX-RES-11` | Attention events were proposed across chat/log/rail unread indicators, with short explanation and context actions to inspect log, retry, open folder, diagnose or copy path. | The existence of a retry button must not assert repeatability after unknown effects or permissions; actions are conditional. | L142 (`#L142`) |
| `SB-SRC-0013/UX-RES-12` | A specific split was proposed between app-owned operational state/log/cache/runtime storage and user-selected Data-workspace output files. | This is a deployment sketch, not independently verified implementation or an obligation that platform and app stores use one transaction. | L148 (`#L148`) |
| `SB-SRC-0013/UX-RES-13` | The original developer-facing sketch argued to use supported external managed-platform functions to their fullest and avoid duplicating those functions in the application. | The anti-duplication rationale survives, but exact responsibility depends on an attested platform version; application-owned business semantics must not be abdicated. | L152 (`#L152`) |
| `SB-SRC-0013/UX-RES-14` | The original end-to-end journey began with Explorer visible, selected a Scenario, edited right-side parameters, then displayed a dynamic run card and promoted completed logs and accessible artifacts; a participant or AI could follow the history. | This is not the frozen manifest's actual default scenario-chat launch, nor proof of full cross-user/AI authorized history access. | L174–178 (`#L174-L178`) |

**Cross-reading and conflict preservation.** The 2026 historic note combines a visually appealing single-screen end-to-end path with assumptions about unrestricted team/AI access, a functioning background schedule, live file-to-run lineage and an external managed-platform bridge. Each is separable. At the pinned Windows manifest the default entry is `scenario_chat`, whereas the older proposed journey starts in Explorer. The historical background indicators are not execution receipts, and a completed log row is not evidence that a remote effect was durably committed. The anti-duplication preference is a design constraint *conditioned on actually supported external capabilities*; the analytic core and application must still own their own domain operations, source claims and run semantics.

**Reverse route and assurance limit.** All fourteen entries refer to the exact pinned original lines and are independently readable from this maintained Science section, but the producer performed the source comparison; no different authorized reviewer, full 179-line original disposition, live UI, native accessibility trial, storage implementation test or Research Amputation has passed. The fourteen additions do **not** alter `SB-SRC-0013`'s census `unaccounted` status.

## Windows Research 0020 — runtime workspace, Explorer and workroom boundary challenge

**Primary source:** frozen Windows source study, Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`, contrasted with pinned public `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b` and bounded source executions. The 18 cross-owner items below conserve distinct original meanings, invalid inferences, competing physical states and one demonstrably false original generalization. This is a source-first producer packet; it is not an independent scientific conservation finding or a Product Decision.

| Research address and evidential status | Material meaning | Challenge / limiting countercase | Original lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/WS-01` · `DATED_SCHEMA_SHAPE` | The built-in default workspace schema lists a derived selector profile, a display workspace dirname, input/output required folders and directory auto-creation options. | Schema attributes describe potential behavior; actual resolver branches decide whether selected Data root is reused directly or a named workspace is derived. | L359–L380 (`#L359-L380`) |
| `SB-SRC-0020/WS-02` · `ORIGINAL_OVERGENERALIZATION_FALSIFIED` | The original generalized every selected non-root Data directory as nesting a Strategy Box Data workspace; pinned resolver instead uses a normal non-drive selector path directly. | WEX-14 executes selected non-drive directory with derived schema: workspace equals selected directory, input/output created there, no named nested directory. | L359–L380 (`#L359-L380`) |
| `SB-SRC-0020/WS-03` · `DIRECT_CODE_CORROBORATED_MODEL` | Data-root selector identity/status and resolved workspace path/status are separately recorded with a resolution mode and diagnostic provenance. | Selector existence and workspace writable flag are not OS-enforced permissions or protection from directory aliasing. | L382–L400 (`#L382-L400`) |
| `SB-SRC-0020/WS-04` · `DIRECT_CODE_CORROBORATED_CONDITIONAL` | The Windows context creates a core FileStore only when its resolved workspace is available; workspace-requiring operations receive that file reference. | A neutral FileStore path is not a host resource grant and cannot by itself enforce future remote-user filesystem scope. | L401–L405 (`#L401-L405`) |
| `SB-SRC-0020/WS-05` · `DIRECT_CODE_CORROBORATED_LIMIT` | The historical desktop Explorer exposed local directories/files and an ExplorerProvider protocol, with only LocalWorkspaceExplorerProvider instantiated in pinned source. | Protocol-shaped provider injection is not evidence of actual remote provider, host artifact store or authorized cross-client file access. | L407–L426 (`#L407-L426`) |
| `SB-SRC-0020/WS-06` · `ORIGINAL_BOUNDARY_CONTRADICTED_BY_EXECUTION` | The original asserted navigation bounded inside the workspace; direct location_for_path checks resolved containment, but enter_entry accepts an in-root symlinked directory without rerunning that check. | WEX-11 rejects direct external navigation while WEX-12 enters a directory symlink and lists a synthetic external file on a Linux CI filesystem. Not a tested deployed remote exploit. | L407–L426 (`#L407-L426`) |
| `SB-SRC-0020/UI-01` · `DATED_PRESENTATION_INVENTORY` | Original Qt layout put a mode rail/left panel beside filtered Scenario chat, background strip and composer, with a right-side Case/Logs/Artifacts/Parameters inspector. | Three-zone geometry and labels are not a requirement to clone pixel layout on Web or Android or evidence of functional background execution. | L792–L808 (`#L792-L808`) |
| `SB-SRC-0020/UI-02` · `HISTORICAL_NAVIGATION_SHAPE` | Six navigation modes grouped Explorer, atomic Scenarios, composites, Background, Participants and Assignments. | A displayed Background/Participants/Assignments mode is an IA affordance, not an operational scheduler, collaboration service or verified task exchange. | L810–L821 (`#L810-L821`) |
| `SB-SRC-0020/UI-03` · `DIRECT_CODE_CORROBORATED_PROJECTION` | The pinned Scenario-chat projector maps local Cases and notices, actors, statuses, stage, parameters and linked artifacts into independently typed display messages. | WEX-13 copies synthetic sensitive-looking params and raw local Artifact path into an incoming case projection; UI projection is not an authorization sanitizer. | L823–L850 (`#L823-L850`) |
| `SB-SRC-0020/UI-05` · `DATED_LOCAL_INTERACTION` | A Scenario composer accepts selected Scenario parameters and disables during a local is_busy interval. | Busy disablement is a single-client local coordination behavior, not a globally serialized host Job queue. | L852–L856 (`#L852-L856`) |
| `SB-SRC-0020/UI-06` · `DATED_VIEW_RELATION` | Case/Logs/Artifacts/Parameters inspector tabs select local evidence by Case ID. | Matching Case ID does not establish permission to reveal logs, raw files or parameters to another principal. | L858–L867 (`#L858-L867`) |
| `SB-SRC-0020/UI-07` · `HISTORICAL_UI_ROUTE` | The historical user menu connected Node view, Settings, refresh, Diagnostics and exit as local desktop entry points. | An exposed Node panel and menu action do not prove authoritative remote session control, official source validity or stable host diagnostics. | L869–L877 (`#L869-L877`) |

**Important resolution of the source's workspace wording:** the user-facing label `derived_from_selector` does **not** force `<selector>/Strategy Box Data` for each directory. The actual pinned resolver treats a normal non-drive selected directory as its explicit workspace root; special drive-root and system-drive cases can derive a child or user-profile workspace instead. A positive `available` diagnostic is not a guarantee of configured write rights, safe effect publication or remote authorization. This is not a replacement for the separate [Current HOW](../../current-how/windows-application.md) implementation owner.

**Directory alias fault:** the source's broad “navigation remains in workspace” statement must be narrowed. The pinned `location_for_path` resolves and rejects a path outside start root, whereas the independent `enter_entry` path uses lexical `relative_to` after accepting a directory-like symlink, enabling `list_location` to enumerate synthetic external children through that alias. Separate scope-validating entry/recheck and actual OS permissions are candidate protections, not presently enforced host rights. No real sensitive directory was traversed in the test.

**Source→Current→Science distinction:** source study called the interface a generic Provider seam; the actual implementation currently uses local filesystem and Qt presentation, and projection creates display identities, not immutable authorized Artifact receipts. Whether filesystem browsing belongs to a future remote-host profile remains an accepted Product/Design question.

**Conservation boundary:** these 12 additional rows are producer-traced source passages only. The original 0020 contains 1,741 physical lines, has additional unpartitioned material, and keeps census state `unaccounted`. A distinct verifier must review bidirectionally before a whole-source terminal disposition.

## Complete historical UX source 0013 — late-discovered visual and owner distinctions (producer)

A bounded **full-original producer read** of the 178-line early workbench sketch found six additional material source clusters after the existing 22 general and 14 concrete positions. Each is **historical and proposed**, not observed Windows implementation or accepted UI design. The underlying source's declared use of the external managed platform has to be read as an old expectation, not evidence of a currently delivered capability or transfer of product-owned execution authorization.

| Original source item / status | Material original meaning | Negating or limiting case | Frozen source |
| --- | --- | --- | --- |
| `SB-SRC-0013/UX-RESIDUE-01` · `HISTORICAL_VISUAL_SYSTEM_PROPOSAL` | The early visual brief explicitly favored a calm blue-gray/white/metallic Fluent-like desktop palette, outline icons, light borders, quiet motion, rounded panels and messenger-like center. | This is a dated taste and accessibility hypothesis, not a mandatory theme, platform-wide brand palette or proven contrast/motion specification. | L11-L17 (`#L11-L17`) |
| `SB-SRC-0013/UX-RESIDUE-02` · `HISTORICAL_HEADER_MENU_AND_VIEW_RELATION` | The proposed header kept the product title left and user menu right, while a left selector, central Scenario conversation and right contextual inspector formed the main working layout. | Menu position and availability of restart/update actions require actual native and platform capability; they are not the authoritative current Windows screenshot or Product commitment. | L28-L30 (`#L28-L30`) |
| `SB-SRC-0013/UX-RESIDUE-03` · `HISTORICAL_CONCRETE_MENU_EXAMPLES` | The five navigation destinations used CBR escrow and raw-file collection as atomic examples, broad data refresh/report packages as composite examples and source checking/cache refresh as proposed background examples. | Examples of an operation in a menu do not prove registry implementation, nor a real background scheduler, completeness of banking capabilities or safely executable update workflow. | L46-L50 (`#L46-L50`) |
| `SB-SRC-0013/UX-RESIDUE-04` · `HISTORICAL_SCENARIO_TO_CASE_ASSOCIATION` | The source proposed a Scenario as an ordered composite with dependencies, error rules and expected outputs; submission creates one user-visible Case collecting steps, operations, participants, events and result status. | The proposed Case aggregation should not collapse identity of a reusable Scenario definition, accepted Run, actual Job Attempt or user chat Thread; current sequential runner does not prove all proposed dependency semantics. | L90-L94 (`#L90-L94`) |
| `SB-SRC-0013/UX-RESIDUE-05` · `HISTORICAL_ACTOR_TAXONOMY` | Five original event-actor labels were human user, host user, AI, system and background process; the sketch proposed a common presentation of their attributed actions. | Actor display labels alone do not authenticate a principal, authorize a machine action, prove a remote presence channel or establish that any AI or scheduler actually operated. | L110-L116 (`#L110-L116`) |
| `SB-SRC-0013/UX-RESIDUE-06` · `HISTORICAL_MINIMUM_DESKTOP_COMPOSITION` | The original minimum desktop brief enumerated header, icon-only mode rail, mode panel, central Scenario chat, prelaunch bar, logs and Artifacts panes, parameter inspector, Explorer, participants/assignments, background view, user-menu settings and structured events. | A long UI inventory is a design snapshot, not a set of independently justified Product commitments; later information architecture and Android/Web accessibility may require fewer/different surfaces. | L154-L170 (`#L154-L170`) |

**Full-original producer disposition (limited):** all fifteen numbered sections, plus title, concept and flow, now have a classified destination in the maintained UX Science through 22 original details, 14 former concrete residuals and six additional positions. Section coverage can include nonmaterial headings, redundant examples and connecting prose; multiple claims within a paragraph may have different owners. The source-first section accounting kept in the separate Work evidence corpus states which claims were treated as repeated, superseded or unsafe as current fact. This is **not a separate independent reader** and whole-source census state remains `unaccounted` until competent adverse reverse verification and full Research Amputation.
