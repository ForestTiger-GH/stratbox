# Work-context navigation, shared projections and authorized actions

**Scientific question:** how a user returns to a long-running analytical task, chooses and launches a curated capability, sees trustworthy multi-run outcomes and navigates mutable files versus versioned results across Windows, browser and future Android. **Status:** a consolidated research interpretation of user goals and dated Windows source, not an approved navigation release or working Web/mobile client. A common domain/application authority remains a logical target, not an already deployed host.

## 1. From Scenario chat to Work context: a product change, not a tab rename

The pinned [Windows desktop](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b) has a three-zone Qt shell, Scenario chat/projector, Explorer, contextual inspector, local Case/Event/Artifact history, parameter forms, background/presence/assignment scaffolds and a managed installation manifest. The manifest's `entry_view=scenario_chat` and the six existing entry modes reflect the application's **current scope**; the presence of a navigation icon is not proof of a durable Work backend.

The research's **consolidated future direction** is a **Work/Thread-first experience** where a scenario is *one way to perform work*, not the compulsory root for every message, review, saved reference or action. This is neither an instruction to break the existing GUI immediately nor approval of new route names. It is a semantic choice that requires Product admission and usability testing.

**Thread:** conversation/context and its permissioned participants/messages. **Work:** accountable goal, acceptance requirements and obligations. **Run:** one admitted execution of a frozen plan. **Job/Attempt:** scheduled unit and physical try when separately relevant. **Scenario:** curated repeatable user-facing capability. **Artifact:** versioned managed result, with separate materialization and access. One Thread may discuss many Works, one Work may have multiple Runs; a visible Case card should not silently become the sole authority for all five kinds.

The desirable outcome is **returnability**: a user can open the same Work by an authorized stable reference tomorrow or on another device, see its latest confirmed state, and continue from the appropriate decision without the UI inventing a second Run or forgetting the old result. For a local-only foreground profile, detachment and UI shutdown guarantees may be weaker and must be honestly disclosed.

## 2. Four information domains, not four mandatory tabs

| Logical destination | Primary question | Main objects | Wrong role |
| --- | --- | --- | --- |
| **Work** | What am I investigating, and what needs my decision? | Thread, Work, pending reviews, messages, links to Runs and outputs | A live Node-wide log dump |
| **Explorer** | Which permitted inputs, workspace objects and results can I locate? | Scoped FileRef, WorkspaceObject, ArtifactRef, provenance | Deciding whether Work is complete |
| **Scenarios** | What can the product do, and how can I supply a correct request? | Curated Scenario/Capability, form schema, presets, applicability | Keeping its own Job history or effect authority |
| **Runs** | What is executing, queued, waiting for me or in doubt? | Run/Job/Attempt projections, status, actions, diagnostics | A second Thread/message system |

This **four-area model** replaces a research-stage proposal of six equally important Windows modes, but does not require four tabs on every device. A desktop may use a rail+list+main+inspector, Web may collapse secondary panels, and Android compact may show destinations or a nested task flow. Cascade is an optional composite/scenario presentation rather than a compulsory root; background is a mode, automation is a rule, participants and assignments are contextual until actual independent use justifies directories/inboxes.

**Initial home** is another unapproved Product Decision. A plausible first Work home lists recent/pinned Threads and Works requiring input plus compact verified Run status; a returning user could restore an existing permitted context. An empty workspace should offer actions to start Work or invoke a Scenario. Remembered navigation state is client convenience, not a new Work mutation.

## 3. The timeline is an editorial projection over authority

A readable Work/Thread timeline displays substantive messages, accepted/rejected proposals, Work decisions, representative Run cards, important problems, published Artifacts, approvals, assignments and actual closure. It should **not** append every heartbeat, log line, temporary file, HTTP retry, progress tick or raw worker state mutation. Those observations remain available in an authorized inspector or diagnostic viewer.

The [current Qt-free Scenario chat projector](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/common/scenario_chat/projector.py) demonstrates that semantic presentation logic can be separated from Qt rendering. It is **not yet** a multi-language JSON DTO nor a complete Thread/Work authority. Reusing a projector's semantic mapping is different from reusing its Python classes in browser TypeScript.

The composer needs two explicitly different action paths:

```text
User free text / attachment → Message, question, intent or AI proposal
Curated Scenario selected → structured RunDraft → validate params/rights/effects
Explicit authorized Run command → accepted/rejected/needs-approval outcome
```

AI text saying “I have run it” is neither admission nor effect receipt. A saved Scenario default differs from a local unsent draft, a reusable preset and the immutable effective parameters bound to an accepted Run. Any approval for a dangerous plan is constrained by the actual effect target/revision, not a text button in chat.

## 4. A Run has two useful representations, one identity

A compact card in a Work timeline answers **“What happened to my task?”** A Runs list answers **“What is happening across the permitted scope?”** Both link to the **same Run ID, outcomes, Artifacts and event history**. The Run list can filter active, queued, waiting approval, completed, failed, partial and needs reconciliation. Its priority order may put actionable and active work ahead of recent history.

Avoid misleading user states:
- `100%` of computation does not imply Artifact publication or Work acceptance;
- `cancel_requested` is not `cancelled`;
- `unknown_effect` deserves inspection/reconciliation rather than a “Retry now” button;
- a lost browser/Android connection is `stale/disconnected`, not `Job.FAILED`;
- `Automation.enabled` does not mean a worker is currently active;
- app-wide Qt `is_busy` is the present foreground limitation, not desired resource-level scheduling.

Controls such as cancel, replay, download, approve, review or inspect logs are shown with eligibility and reason codes; the application reauthorizes at command/effect time. A user able to view another colleague's Run does not automatically gain permission to cancel it or inspect private full logs.

### Active Thread ordering is a derived, viewer-scoped projection, not a Job queue

A background-Work study raised a more concrete UI problem than “show a spinner”: when several linked Runs exist, a user should be able to find a conversation needing action, without progress-tick churn, lost pinned order, accidental sharing, or confusing enabled automations with actually running tasks. It proposed a **candidate** ordering with (1) manually pinned Threads, (2) attention or active Threads, (3) remaining ordinary Threads and (4) archived Threads in a separate view. This is one useful **Research-level alternative**, not an adopted universal sorting rule or a requirement to materialize a new table per list.

The sort key is derived from **permissioned, authoritative** Work/Run/Job data and each viewer's settings. Relevant countercases:

| Situation | Correctly qualified presentation | Invalid shortcut |
| --- | --- | --- |
| Chat pinned by a particular viewer | Preserve that viewer's manual pinned order; show any active state within the row. | A background job silently moves the pinned item or changes another viewer's pin choice. |
| One linked Run is awaiting this viewer's actual approval | Place in an action-needed group under a candidate ranking policy, with a permissible action and stable state-change timestamp. | Every progress event reorders the entire chat list or grants the viewer approval rights. |
| Run is queued, executing, cancellation requested or resource-waiting | Show the actual known class and count of permitted **incomplete logical Cases**, not raw OS threads or repeated Attempts. | `enabled=True` on an Automation becomes a running badge, or a joined physical Job is counted twice. |
| A completed Run has an unread result, warning or unresolved Condition | Show an appropriate unread/attention signal subject to user settings; distinguish it from an active worker. | The Thread remains permanently at the top as “running” after all execution has ended. |
| Thread archived while its host Job continues | Keep the archive navigation choice, maintain independently authorized Run access through the task center, and optionally warn at archive time. | Force-unarchive the Thread, cancel the Job, or delete its immutable history as a side effect of hiding chat. |
| Viewer loses Thread permission or another participant has private Run inputs | Reproject or remove unauthorized links, badges and details under current ACL; check Work/Artifact/Log rights separately. | Membership in the Thread grants raw task parameters, absolute paths, private logs or cancel privileges. |
| User opens a different client or reconnects after missed events | Recompute scoped aggregates from the host snapshot+revision/cursor, label stale UI and avoid inventing a new Run. | Reactivate the Job, replay all progress as chat messages or apply client-local status as server truth. |

A candidate **anti-jitter invariant** groups on meaningful transitions and respects user controls: changes to `phase_progress`, log line count or ETA alone must not change sort buckets or bump `last_meaningful_activity`; a real `QUEUED→RUNNING` transition may change the group once; a verified terminal result may count as one meaningful activity event. The original proposal prioritized urgent approval over running and queued work, but personal attention policy and manual sort remain Product/UX decisions. A lower persistent activity strip was proposed **only for real active/action-needed runs**, not for every configured scheduled rule. A Task Center/Runs view has its own authorized aggregate and does not take execution ownership away from the host.

A simple illustrative pure ranking predicate is `archived → pinned → needs_action → has_incomplete_case → regular`, **computed after access filtering** and with stable tie-breaks; this is not a released Algorithm, stored `ChatThread.status`, a CPU-scheduling priority or permission grant. Screen-reader announcements, compact badges, handling of thousands of Runs, notification rate and cross-device usability require native tests and real Product acceptance. A user hiding a notification does not cancel an execution, close a Condition or delete an Artifact.

## 5. Explorer unifies access while retaining two object types

**Workspace FileRef** locates a permitted mutable file/folder in a managed resource scope. **ArtifactRef** names a committed versioned product result, linked to Run/source/algorithm/style and possibly several byte materializations. A workbook generated into a folder is not automatically a verified Artifact, and editing the original input does not silently rewrite a previously committed Artifact.

Navigation could show permitted common Data, personal files, a managed result library, and links from the current Work. Temporary staging and system roots do not become ordinary editable user folders. A source category and a managed final result may appear near each other in Explorer while preserving their different access, deletion and retention policy.

Native actions intentionally differ:
- **Windows:** tree/breadcrumb/detail table, multiselect, keyboard, drag/drop where effect rules allow, local open/reveal.
- **Web:** server-backed pagination, signed or authorized bounded upload/download/preview; never a raw host absolute path or open static workspace.
- **Android:** scoped file picker, share/open-with, touch list/search and limited cache; complex bulk edit is not guaranteed.

A destructive workspace action needs preview/plan/permission and truthful partial/unknown effects. Removing a visible row does not demonstrate that the storage backend applied an authorized delete.

## 6. Inspector, search, preview and diagnostics serve selected objects

A semantic **InspectorView** follows selection identity: a Work inspector shows goal, due review and Runs; a Run inspector shows steps/outcome/related Artifact/evidence; a Scenario inspector shows purpose, fields and last executions; an Artifact inspector shows producer, source versions, style and authorized output links. It may render as a Qt right pane, Web drawer, Android detail or bottom sheet. **Selection is a logical object reference**, not a widget index.

A technical depth hierarchy is useful: short safe error/action in the card → details/steps/warnings in inspector → restricted logs/Problem evidence in a dedicated pane. These layers must not broadcast source credentials, private input paths or raw traceback to all Thread participants.

One global search entry could federate authorized Work, Thread, Scenario, Run, File and Artifact queries, keeping result kinds and partial/unavailable states visible. Full-text index, ranking, ACL propagation, source file indexing, quota and performance remain **unknown**. Shortcut/command palette and contextual menu may expose the same stable ActionDescriptor, not duplicate business logic.

Previews are separately authorized, size/format- and policy-bounded transformations. “Preview Excel on Android” requires testing actual workbook sizes, parser risk, memory and redaction; an open path is not a valid Web preview API.

## 7. Notifications, assignments and read positions

A domain Event is a recorded fact; a Notification is delivery to selected recipients; a Condition groups an ongoing problem; a technical log is diagnostic evidence. Their authors, retention, privacy and recovery differ. A shared Data-root impairment can produce one Condition and tailored warnings to affected Work owners without leaking any private traceback.

Presence must be derived from actual Session/heartbeat TTL rather than a persistently true Boolean. Multiple devices for one human do not become multiple people. Read cursors and notification acknowledgements are per principal and scope, not a shared `unread` field on a message. Assignments create accountable human obligations; Approvals authorize bounded planned effects. An Android push may route a user to a secure approval view, but **must not itself execute a destructive approval**.

**Attention budget:** unread, approval and true error badges should reflect independently meaningful action. A flood of badges on every navigation item conceals priority. Thread-card notices, global inbox and platform conditions need controlled audience and deduplication.

## 8. Three contracts between state truth and screen pixels

```text
Application authority: durable Work/Run/permissions/Artifact and current revisions
  → Authorized product projection: typed object summaries, actions, reasons, refs
  → Surface adapter: navigation, local draft, OS file/share/clipboard/notifications
  → Qt / DOM / Android renderer with device-specific layout and accessibility
```

A sample target **projection** can carry `view_kind`, stable object kind/ID, revision, permission-filtered data, an opaque feed cursor, `as_of`, freshness and permitted ActionDescriptors. `available_actions` is a display hint from verified scope, not an authorization token. A sample *command* can carry semantic Action ID, target reference, expected revision, idempotency key and typed parameters; the authenticated principal comes from actual session authority.

Stable deep links identify kind+ID+optional revision and require Node/tenant routing, authentication, current ACL and handling of missing/archive/stale objects. A URI example such as `strategybox://work/…` is **illustrative** and not a registered scheme. Opaque feed cursors must not disclose the count of hidden private node events. See [authorized feeds](../collaboration/authorized-streams-read-cursors-and-private-work.md).

Client cache state needs `current/stale/unknown` separate from actual Job status. The server commits a consistent permission-scoped snapshot+cursor; the client subscribes, deduplicates, handles gap, and resynchronizes. Offline personal drafts are not shared state and require schema/policy revalidation before submission. Mirroring window widths, selected tab and scroll across devices is optional and can be counterproductive.

## 9. Alternative surfaces and the limits of parity

A browser is a **real product client**, not a screenshot of Windows: dense keyboard tables/forms/search and usable without any AI actor. REST plus SSE is a reasonable first experimental command/query/event transport; WebSocket remains conditional on measured bidirectional demands. The actual authentication/CSRF/session/file boundary must be implemented and tested before Internet exposure.

A first Android **remote-first companion** could show current Work, Runs, meaningful warnings, approvals, artifact previews, share and lightweight forms. A fully featured Explorer, huge graph editor, unrestricted offline executor and native push are **separate roadmap decisions**. Phone, foldable and tablet layouts should follow available window geometry rather than one universal “Android=single column” rule.

A notification/tray/widget/CLI narrow surface may support just permitted read summaries and a safe deep link. When it lacks space to show an approval's actual destructive effect scope, it must defer to a full client, not weaken safety context.

No Web server, Android binary, independent host, remote state store, SDK, cross-client authentication or true installed surface tests were produced by this research.

## 10. Source conflict register and open design questions

The original topic-07 research identified **18 C07 conflicts**: Scenario chat vs Work/Thread, six modes vs four logical destinations, auto-Scenario wrapping, Case/Work, background as area vs mode, Qt lifetime vs headless ownership, whether a separate design repository, UI theme vs artifact styles, arbitrary shell changes by extensions, desktop density vs mobile geometry, SSE/WebSocket, PySide/native Android, Settings info tabs, platform identity vs product collaboration, optimistic success vs unknown effect, presence directory, Artifact/CAS vs Explorer and pixel-identical multi-client navigation.

Twelve particularly important unresolved questions are separate: server versus client construction of safe projections; deep-link routing; ACL-aware global search; Work inbox/unread priorities; preview formats/resource limits; multiwindow concurrency; first useful AI scope; slow PC/Android performance budgets; drafts and offline writes; actual screen-reader/locale acceptance; common-source UI library packaging; and integration of platform/provider/domain problems without duplicate warnings.

The source's **29 proposed UX/conformance checks** cover Work/Run cardinalities, command/session identity, Form/Action parity, effects, source/result identity, stale/reconnect, keyboard/mobile a11y, virtualized 10,000-item lists, user themes and product security. They are **not passing tests**. Product decisions on four navigation areas, toolkit, first-run default, search, notification precedence, render preview and performance need actual user workflows and signed acceptance.

**Verdict:** one semantic product can have multiple native, adaptive surfaces **only if** each display maps back to an authorized state/action truth. The target is coherent meaning and trustworthy continuation of Work, not identical widgets or a second execution world per device.

## 11. Twenty-six source-backed cross-surface conformance candidates

The frozen Topic 07 product-surface Research, §26 (`#L1171-L1209`) provided **twenty-six proposed cross-platform checks** spanning semantic identity, state/reconnect, security ownership and accessibility. The following English interpretations retain exact source lines; they are **not tested Windows/Web/Android capabilities, approved UX behavior or release commitments**. Several cases are relevant only when a real hosted multiuser application, browser service or mobile companion exists.

| Original checklist item | English research-proposed observable property | Original source line |
| --- | --- | --- |
| `SB-SRC-0054/SURFACE-01` | One Work can contain several Runs, and one Thread several Works; navigation must preserve identities without duplicating Work. | L1175 (`#L1175`) |
| `SB-SRC-0054/SURFACE-02` | One Run ID represents the same execution across Windows, Web and Android when those clients are available. | L1176 (`#L1176`) |
| `SB-SRC-0054/SURFACE-03` | Shared typed capability descriptors drive field validation and eligible actions; independent UI validators cannot redefine meaning. | L1177 (`#L1177`) |
| `SB-SRC-0054/SURFACE-04` | An Operation definition is distinct from its use-case Scenario and actual invocation. | L1178 (`#L1178`) |
| `SB-SRC-0054/SURFACE-05` | Managed ArtifactRef and workspace file locator remain different identities even for equal filenames. | L1179 (`#L1179`) |
| `SB-SRC-0054/SURFACE-06` | The UI must not inflate evidence confidence, execution success or actual observed progress. | L1180 (`#L1180`) |
| `SB-SRC-0054/SURFACE-07` | Closing a surface does not implicitly cancel a genuinely host-owned Job; actual session profile controls lifecycle. | L1184 (`#L1184`) |
| `SB-SRC-0054/SURFACE-08` | Offline, stale and epistemically unknown states must be visually and semantically distinguishable. | L1185 (`#L1185`) |
| `SB-SRC-0054/SURFACE-09` | Reconnect must handle missing, repeated and out-of-order event delivery against an authoritative snapshot. | L1186 (`#L1186`) |
| `SB-SRC-0054/SURFACE-10` | Concurrent multi-tab/multi-device submissions require revision/idempotency controls appropriate to effects. | L1187 (`#L1187`) |
| `SB-SRC-0054/SURFACE-11` | Personal unread/notification receipts cannot mutate the shared authoritative timeline. | L1188 (`#L1188`) |
| `SB-SRC-0054/SURFACE-12` | Automation enabled status differs from one current running Job state. | L1189 (`#L1189`) |
| `SB-SRC-0054/SURFACE-13` | Qt/browser/mobile renderers must not duplicate domain banking computation algorithms. | L1193 (`#L1193`) |
| `SB-SRC-0054/SURFACE-14` | Analytical core remains usable without importing a platform UI toolkit. | L1194 (`#L1194`) |
| `SB-SRC-0054/SURFACE-15` | Visibility of an action button is not permission; service owner must reauthorize. | L1195 (`#L1195`) |
| `SB-SRC-0054/SURFACE-16` | Remote clients receive scoped object references, not privileged physical storage paths. | L1196 (`#L1196`) |
| `SB-SRC-0054/SURFACE-17` | Destructive confirmation shows concrete effect scope/targets and is revalidated at the actual owner. | L1197 (`#L1197`) |
| `SB-SRC-0054/SURFACE-18` | Neutral extension APIs must not silently grant unrestricted shell/navigation override. | L1198 (`#L1198`) |
| `SB-SRC-0054/SURFACE-19` | Public source and documentation retain neutral interface concepts and avoid private implementation specifics. | L1199 (`#L1199`) |
| `SB-SRC-0054/SURFACE-20` | Deep links resolve the same authorized Work, Run or Artifact identity on each supported client. | L1203 (`#L1203`) |
| `SB-SRC-0054/SURFACE-21` | Responsive resizing must not delete a user's current unsubmitted analytical draft. | L1204 (`#L1204`) |
| `SB-SRC-0054/SURFACE-22` | Phone-sized interfaces expose primary actions without hover-only or tiny targets. | L1205 (`#L1205`) |
| `SB-SRC-0054/SURFACE-23` | Keyboard/screen-reader/focus/high-contrast/reduced-motion behavior requires real device/accessibility tests. | L1206 (`#L1206`) |
| `SB-SRC-0054/SURFACE-24` | Large event/file sets require efficient virtualization or pagination with a workload-specific responsiveness budget. | L1207 (`#L1207`) |
| `SB-SRC-0054/SURFACE-25` | System/dark mode changes cannot alter semantic error or permission meaning. | L1208 (`#L1208`) |
| `SB-SRC-0054/SURFACE-26` | Error and UNKNOWN projections provide comprehensible next actions and a permissioned diagnostics route. | L1209 (`#L1209`) |

**Limits:** a shared semantic view model does not imply that Android, browser and Qt should share widget code or repository topology; some accessibility/performance budgets require actual tests on real screens. A visually coherent offline card cannot certify current remote job status. This appendix transcribes **26 concrete original proposed tests**, and does not independently conserve the entire 1,414-line study or accept any product UI topology.
