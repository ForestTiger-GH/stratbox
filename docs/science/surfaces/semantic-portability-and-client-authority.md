# Semantic portability, client surfaces, and application authority

**Problem domain:** reusing Strategy Box analytical and application meaning across a Windows desktop, a browser, and a prospective Android client without duplicating business rules, confusing presentation with execution authority, or treating a future platform capability as already deployed. **Status:** independently readable scientific/engineering analysis grounded in a pinned implementation baseline, direct user needs reported by the source research, and explicitly competing target alternatives. No web, Android, or standalone host release is certified here.

## 1. A shared product does not imply shared widgets

Three ambitions need separate tests:

1. **Product-semantic equivalence:** the same permitted operation, parameter meaning, accepted Run, terminal outcome, source/provenance and artifact identity remain consistent across clients.
2. **Source-code reuse:** a module or component is written once and consumed directly by multiple runtimes, or rendered from a shared, language-neutral contract.
3. **Visual similarity:** layouts, dimensions and exact pixels match.

The first is the essential consistency requirement. The second is an optimization that can fail when Windows is Python/Qt but Web uses TypeScript and Android uses Kotlin. The third may actively degrade browser tables, keyboard workflow, touchscreen ergonomics or accessibility. Shared **semantic tokens and actions** matter more than an identical screen.

A reusable design therefore distinguishes **domain code**, **application use cases and authorization**, **portable read projections**, **protocol schemas**, **presentation semantics**, **OS/runtime adapters** and **deployment/activation binding**. The relevant distinction is who owns a fact and who can change it, not merely where a class is physically placed.

## 2. The current baseline: reusable core, partially coupled Windows application

At pinned [core revision](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580), the statistical Python domains, parsers, reports and FileStore operate without Qt. Direct Python/Colab use is meaningful, even though not every domain exposes an identical canonical operation specification.

The pinned [Windows runtime bootstrap](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) imports the concrete Qt `ScenarioCoordinator`; the [Qt coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) owns one QThread/active Case. The [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) sequences selected steps and emits local events/artifact records. The [semantic scenario-chat projector](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/common/scenario_chat/projector.py) shows a useful Qt-independent mapping from stored cases/events to presentation messages, but is not itself an interoperable TypeScript/Kotlin data contract.

Other direct limitations:
- [Five local history JSON files](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) are not a shared transactional authority; malformed histories can be read as empty.
- Artifacts represented by native host paths are not directly usable as remotely authorized browser/phone file identities.
- In the pinned Windows [deployment manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json), the declared working surface is local/foreground desktop, not a released host/web/mobile capability.
- The cross-repository research observed version drift: core `pyproject.toml` at the studied snapshot reported `0.8.0`, while the Windows project and its manifest pinned `stratbox==0.2.1`; a Windows README reference to Connector `3.0` also differed from manifest `4.0`. Those are **dated static contract observations**, not successful package compatibility or installation tests.

None of these facts says the existing desktop is useless; they identify specific seams that must be qualified before making remote-running guarantees.

## 3. Competing architecture models

| Model | Attraction | Failure / cost | Evidence-calibrated assessment |
| --- | --- | --- | --- |
| **Remote control of a Windows GUI** | Minimal initial replacement | UI lifetime becomes job lifetime, poor browser interaction, desktop-local history and identity | Prototype only; unsuitable as the promised product-semantic owner |
| **Independent Windows/Web/Android application engines** | Every client can move fast with native language | Divergent permissions, parameters, effect retry and Run outcomes | Semantic duplication must be resisted |
| **One logical application authority, several clients** | One accepted Run and permission decision with client-specific projections | Requires a real executor, state owner, API/session, availability and reconnection | Strong target model, **physical location unresolved** |

The chosen logical role need not immediately become a separate repository or service. For a local-only Windows profile it might exist in-process behind neutral ports. To truthfully continue work after a remote browser closes, an actual host process with independent lifecycle is necessary. A separate `stratbox-host` repository becomes reasonable only when it has its own runnable entry point, release, API/persistence/authorization responsibility, tests and operational owner. An empty repository or shared code copied into each client has no equivalent value.

**Cross-research conflict:** an earlier platform-portability analysis suggested local SQLite as the first durable host metadata store; later storage and observability research explicitly allowed atomic file state or append-only event journal first, with future storage provisioned through the external platform. Both insist on one logical authority and verified recovery. **The physical backend, storage guarantee and process packaging remain Product/Architecture Decisions.**

## 4. A portability classification that follows authority

| Responsibility | Canonical owner or common semantics | Surface-specific realization |
| --- | --- | --- |
| Statistical algorithms and source semantics | The existing `stratbox` domain core | Invoked locally in Python or on a host; not reimplemented in browser |
| Operation IDs, typed parameters, output/effect semantics | Curated application/domain contract | Input controls, human labels, client-specific form rendering |
| Scenario composition and resolved planning | One application use-case owner | Step graph editor or simple form |
| Admission, durable Run/Attempt, effects and authorization | One local/host application authority when deployed | Submit buttons and progress cards |
| Thread/Case/Run read models | Shared DTO identities, statuses and audience projections | Qt, DOM and Android layouts |
| Artifact/resource identity | Logical refs with authorized file resolution | Native open/reveal, browser download, Android share |
| Identity, membership and object permissions | Verified server/local authority | Login forms, session storage, profile menu |
| Design semantics | Status roles, typography, density, spacing, icon/action meaning | QSS mapping, CSS variables, Compose/RN/Flutter theme |
| Offline drafts and layout preferences | User/device scope, never shared execution truth | Browser storage, Windows settings, Android storage |
| Root/activation/capabilities | Versioned external platform contract through adapter | OS/process-specific integration |
| Notifications/clipboard/shortcuts | Semantic notification and action type | OS/browser-specific affordance |

A Python class is not truly neutral if importing the application requires PySide6. A Python function reference inside `OperationSpec` may be valid for a host executor, but it is not a client-executable Web instruction. `Path`/`QDateTime` should not leak into cross-language DTOs. The external activation context, internal credentials and raw managed directory paths must not be serialized wholesale into browser responses.

## 5. A small portable product boundary

Two interfaces are substantively different:
- **Domain Operation API:** Python Request/Result, source retrieval, statistical methods, domain audit and file processing; usable without any GUI.
- **Product Application API:** authorized capability discovery, scenario form semantics, Run submission, lifecycle/status query, event cursor, artifact metadata/content, permissions and safe error projection.

A **third** adapter reads external deployment/Node/Session/Data/root information, validates versions and constructs application-safe capabilities. It does not make deployment manifest values authoritative for an actual effect or user identity.

A possible *illustrative* minimal external API has capability/form discovery, `submit_run(idempotency_key, typed_params)`, `get_run(run_id)`, snapshot/subscription with cursor, `get_artifact`, permitted `get_artifact_content` and session/node capability views. These are **roles**, not an existing route set or accepted wire signature. If a returned `RunProjection` includes `revision`, `as_of`, status, progress, author, artifact refs and `available_actions`, the last field is *advice for rendering*; every mutating command must re-check live permission/state.

Transport semantics require distinguishing `accepted`, `rejected`, `needs_approval`, `conflict`, `failed`, `partial`, and `unknown_effect`. A network timeout after submit cannot prove rejection; retry with the same idempotency identity should retrieve the original admitted Run. HTTP [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) offers a suitable *error representation*, not a replacement for domain Problem/Run status. [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.1.html) and [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/) provide interoperable descriptions; business effects and authorization still require live enforcement.

## 6. Snapshot and event-stream reliability

A minimal remote client may use request/response commands and queries plus [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) for live changes. WebSocket can be considered when truly bidirectional high-rate interaction is justified; using WebSocket does not in itself resolve reliability.

Important sequence: **retrieve an authorized snapshot and cursor → subscribe after cursor → deduplicate by event ID → detect gaps/expired cursor → retrieve a new snapshot**. Disconnected or stale is the **client's synchronization condition**, not the Run's failure. High-rate progress can be coalesced, while terminal events and effect confirmations need durable semantics.

A background browser tab, PWA service worker or Android Activity is not the authority for a long-running banking Job. In a local foreground profile, closing Windows may interrupt execution; in a true host profile, closing a client merely detaches it. The deployment must say which behavior is available, and reconnect must not fabricate fresh worker status from an expired heartbeat.

## 7. Web and Android are distinct consumer profiles

The user-backed direction in the dated research gives **Web explicit importance** (not merely optional Android portability). Initial Android use is **remote-first**, focusing on selecting a permitted task, checking multiple active Runs, submitting a manageable form, viewing verified results, receiving warnings and opening an artifact. Heavy offline computation and a full local Python/data estate were hypothetical future options. Those statements carry *user-intent* weight in the source Research, **not evidence of completed releases or approved scope dates**.

A desktop browser needs tables, dense forms, keyboard/drag-and-drop and large-workspace navigation. A phone often needs concise cards, touch-size actions, share intents and compact state; a tablet may support more. Adaptive breakpoints should follow available window size rather than a simplistic platform label. A responsive Web/PWA can test mobile needs before commissioning a native APK; it does not guarantee native-equivalent background execution, notifications or OS integration.

Three different offline promises must remain distinct:
1. **Offline read-only view** of last-synced information, marked stale.
2. **Offline personal drafts**, protected and revalidated at submit.
3. **Offline analytical execution**, needing a separate local runtime and data/source profile.

Automatically replaying queued *destructive* work after reconnect is unsafe because permissions, inputs or planned effects may have changed. Revalidation and new confirmation may be necessary.

## 8. Semantic design system rather than widget copying

A scalable visual system has four levels: **semantic roles** (success/warning/unknown etc.), **design tokens** (color, type, spacing, density, motion), **component semantics** (RunCard, ScenarioForm, ArtifactRow, ErrorSummary, NodeStatus, ApprovalAction), and **renderer** (Qt Widgets, Web HTML/CSS, Android Compose/RN/Flutter). The shared contract is the set of states and actions, not Qt stylesheet or DOM structure.

A RunCard can render as a desktop row with inspector/menu, a browser ARIA-enabled responsive card, and an Android summary/bottom-sheet. They must agree on `run_id`, outcome, progress, author and available actions. Accessibility requirements such as keyboard focus, contrast, reduced motion, screen-reader semantics and touch targets should be checked in actual renderers; [WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) and [Android window-size guidance](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes) are relevant standards, **not tests of this product**.

Current technology alternatives with different strengths:
- **React/TypeScript Web + Android Compose:** idiomatic browser/Android behavior, duplicated renderer source.
- **React/TypeScript Web + React Native/Expo Android:** potential reuse of TS state/forms/hooks, with separate DOM/data-grid limitations.
- **Flutter Web + Android:** high UI source reuse and strong mobile story, but browser semantics and accessibility need a concrete spike.
- **Qt/Qt Quick on Android:** possible toolkit support, yet Windows Qt Widgets source and CPython wheels do not become automatically portable.
- **Responsive Web/PWA first:** lower deployment cost and useful mobile learning, but native affordances remain conditional.

There is **no measured winner** for Strategy Box. The current Qt desktop need not be rewritten merely for source reuse. Compare the same ScenarioForm + RunTimeline across candidate renderers using measurable build, a11y, input and latency criteria.

## 9. Internet-accessible Web introduces a trust boundary

A display nickname in a trusted local team is not identity for an Internet-exposed API. An initial small installation might use administrator-provisioned accounts rather than self-service email registration, but it still needs authentication and object-level authorization for each Run, Artifact and mutating action.

Baseline safeguards for a real public deployment include TLS, protected credential storage (e.g. salted adaptive password hashes), secure session cookies or equivalent transport, CSRF/origin defenses for cookie-authenticated mutations, login rate limits, logout/revocation, and server-side checks. Credentials cannot be hard-coded into frontend code or a public manifest. The browser's submitted `author_id` is not the trusted author of a Run; the server binds it to the authenticated principal. Separate **principal_id**, **participant/display identity**, and **device/session identity**.

This is a bounded security floor, not a request to build a custom enterprise IAM service. Later federation/OIDC is a possible adapter if demanded. See [authorization and effects](../trust-and-assurance/identity-authorization-and-effect-boundaries.md), [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) and [session/CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Shared visibility of team chats does **not** grant raw log download, arbitrary server filesystem access or permission to cancel another user's task. File responses must resolve logical references and deny traversal attempts such as `../` before touching host paths.

## 10. Deployment/activation truth is layered

The external platform's responsibilities must remain separate:
1. **Source manifest** states partial product requirements and supported surface intentions; it is not a secret vault.
2. **Authoring/resolved configuration** chooses permitted deployment and fills admissible installation-specific fields.
3. **Release/installation truth** confirms what executable/API/assets and runtime dependencies were actually packaged and installed.
4. **Activation/runtime** provides verified local Node/Data/Session/capability/endpoint bindings; the product tests real service readiness and current authorization.

A manifest declaring `remote` cannot make an uninstalled host API operational. A platform role of `host` does not prove worker availability. `available_actions` on the client do not confer permissions. Until a versioned external contract is confirmed, use one narrow adapter and explicit `unsupported/unavailable`, rather than inventing remote SDK methods. The platform owns installation and runtime handoff; Strategy Box owns statistical methods, Run admission, effects and result semantics.

For physical deployment, the *design space* includes local Windows authority, Windows remote client, host with Web assets and API, browser-only client, Android remote controller, and hypothetical Android local executor. In the pinned baseline only the local desktop profile is evidenced. Native/PWA packaging, host capability and remote authorization cannot be deduced from names in a manifest.

## 11. Negative tests, operational costs and unanswered decisions

Future acceptance probes should include:

| Probe | What an incorrect result would expose |
| --- | --- |
| Import portable application without PySide6 | GUI package remains hidden mandatory dependency |
| Python ↔ TypeScript/Kotlin DTO fixture round-trip | Inconsistent enum/date/path semantics |
| Two clients launch independent Runs | UI-global busy flag is mistaken for resource scheduling |
| Same idempotency key after lost response | Duplicate admitted Run or side effect |
| Close browser during host Job | Frontend incorrectly owns execution |
| Android resumes after offline | Old snapshot rendered as current status |
| Permission removed between view and action | UI `available_actions` trusted instead of live authorization |
| Input/form schema changed during a draft | Stale parameters/effects executed without revalidation |
| Download an uncommitted Artifact | Publication inferred from file existence |
| Move/delete host output | Wrong similarly named file served or history erased |
| Host path traversal or unauthenticated browser command | Missing namespace/auth boundary |
| Disconnected platform capability | Future hypothetical API treated as operational |
| Change Windows managed root or update | Hard-coded paths break state/diagnostics |
| Same UX on small phone and big desktop | Touch, data grid or keyboard tasks become unusable |
| Huge history/20–200 MB download on slow hardware | Unmeasured latency or unsafe all-in-memory transfer |
| PWA app moved to background | Browser mistakenly expected to run durable Python worker |

These are candidate tests only; no measured scores, working browser host or mobile APK are demonstrated here. Product Decisions remain open for initial Web feature scope, exact Android responsibilities, host process/repository ownership, DTO/schema versions, authentication policy, state durability, SSE vs WebSocket, client toolkits, PWA-first deployment, source-version requirements, and offline behavior.

**Strongest retained conflicts:** (a) desire for two new client repositories versus possible need for a separately owned host; (b) single UI codebase versus platform-native usability; (c) earlier SQL-first storage recommendation versus later platform-provisioned file-first profile; (d) local nicknames versus public Internet identity; (e) shared chats versus private artifacts/logs. Their common logical solution is not an already-approved infrastructure topology.

**Conditions to revisit:** validated end-to-end host slice, actual installed external-platform remote binding, new user-accepted Web/Android scope, performance/accessibility spike results, new security requirements, and direct changes to pinned Windows/core source.

## Original topic 07: eighteen cross-device architecture and authority conditions

The dated [Cross-platform Application Architecture study](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md) explicitly compared desktop mirroring, independently duplicated clients and a shared logical application authority. The **18 source-traced English statements** below preserve costs, failure modes and conditions. **The source's favored logical authority is a Research option, not authorization to create or release a new host repository, database or public service.** The existing Qt desktop remains the only observed substantial client in the source baseline.

| Original reference | Source-grounded alternative/limitation | Disposition | Frozen line |
| --- | --- | --- | --- |
| `SB-SRC-0560/CLIENT-01` | Making Web/Android merely control a continually running Windows GUI is a cheap prototype but leaves shared state, uptime and authority coupled to a desktop window. | `REMOTE_GUI_ANTI_TARGET` | [L174](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L174) |
| `SB-SRC-0560/CLIENT-02` | Duplicating scenario planning, authorization and effect logic separately in three client applications risks semantic drift and conflicting truths. | `DUPLICATE_CLIENT_LOGIC` | [L178](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L178) |
| `SB-SRC-0560/CLIENT-03` | A single logical application authority with thin device clients is one long-term Research candidate; it costs host sessions, durable state and API operations. | `SHARED_AUTHORITY_CANDIDATE` | [L182](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L182) |
| `SB-SRC-0560/CLIENT-04` | A logical shared authority does not require a new physical microservice or repository on day one; the initial local implementation may be in-process. | `LOGICAL_VS_PHYSICAL_OWNER` | [L184](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L184) |
| `SB-SRC-0560/CLIENT-05` | A separate host repository is justified only after an independently releasable headless entry, state/auth/Job API and tests/lifecycle actually exist. | `REPOSITORY_MATERIALIZATION_GATE` | [L190](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L190) |
| `SB-SRC-0560/CLIENT-06` | Banking/macro Python computations should stay in one domain owner; portable UI semantic reuse must not mean copying solvers into each frontend. | `DOMAIN_SINGLE_OWNER` | [L198](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L198) |
| `SB-SRC-0560/CLIENT-07` | A Web/Android disconnect affects client synchronization, not automatically the execution outcome of a host Job. | `DISCONNECT_NOT_JOB_FAILURE` | [L202](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L202) |
| `SB-SRC-0560/CLIENT-08` | Design token semantics may be shared while Qt, CSS and Android theme mappings differ legitimately across platforms. | `DESIGN_TOKEN_PROJECTIONS` | [L206](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L206) |
| `SB-SRC-0560/CLIENT-09` | A browser file explorer should invoke an authorized listing/reference API, not receive an unrestricted physical FileStore object. | `BROWSER_FILESYSTEM_BOUNDARY` | [L208](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L208) |
| `SB-SRC-0560/CLIENT-10` | Offline heavy Python analytics were not part of the first Android client proposal; host-first mobile tasks limit complexity. | `ANDROID_HOST_FIRST_SCOPE` | [L215](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L215) |
| `SB-SRC-0560/CLIENT-11` | An Android release can be useful with task selection, scoped launch, progress, alerts and artifact retrieval even without the complete desktop Explorer. | `MOBILE_JOB_CRITERION` | [L257](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L257) |
| `SB-SRC-0560/CLIENT-12` | Desktop Web has different high-density table/keyboard work needs from a phone-sized Android or mobile Web client. | `WEB_NOT_ENLARGED_PHONE` | [L261](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L261) |
| `SB-SRC-0560/CLIENT-13` | A responsive PWA can validate early mobile demand, but it does not automatically match native Android integration or background OS features. | `PWA_NATIVE_TRADEOFF` | [L265](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L265) |
| `SB-SRC-0560/CLIENT-14` | The domain Python Request/Result API and the application Work/Run/Permission API have different owners and consumer scope. | `DOMAIN_APPLICATION_API_SEPARATION` | [L337](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L337) |
| `SB-SRC-0560/CLIENT-15` | HTTP commands plus SSE are a candidate for one-way status flow; WebSocket should be justified by a real bidirectional interaction workload. | `TRANSPORT_COST_COMPARISON` | [L401](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L401) |
| `SB-SRC-0560/CLIENT-16` | A reconnect must start from a qualified snapshot/cursor, deduplicate events and refetch on gaps; stream loss must not mark host jobs failed. | `STREAM_CAUSAL_RECOVERY` | [L403](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L403) |
| `SB-SRC-0560/CLIENT-17` | Trusted internal nickname UX cannot authorize a publicly reachable Web action; authenticated principal is a separate security requirement. | `WEB_AUTHORITY_BOUNDARY` | [L423](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L423) |
| `SB-SRC-0560/CLIENT-18` | A shared-source UI library/repository is not justified until an actual second consumer can use the same code language; shared contracts can precede shared implementation. | `SHARED_CODE_PROPORTIONALITY` | [L540](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md#L540) |

**Competing perspectives:** A fully local Windows-only app may legitimately need no external host. A single logical authority becomes valuable for a real authenticated Web/Android audience, but deployment ownership, sessions, network exposure and resource costs must be proven. Qt signal objects are valid UI adapters, not cross-language execution contracts; equal semantics need not imply identical widgets. A mobile app that can read host status and retrieve an artifact may meet its first product purpose without carrying heavy Python models. External approval/ACL, honest cursor gaps and client-offline signaling remain separately testable requirements.

**Preservation limit:** these 18 source text interpretations retain separate arguments but cannot certify the complete 704-line study, actual Web/mobile delivery or Product-approved host topology.

## Original Windows source study 0020: local UI preferences, assignments and portability

**Provenance:** [original pinned Windows study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`, cross-checked against the unchanged public Windows source revision `959e9c4ce1441124af5111c1e025041714e04d3b`. Dated implementation descriptions, research recommendations, static source conflicts and real executed tests retain different evidence force. These addresses are historical Research meaning, not automatic Product Decisions.

| Address and role | Original material meaning | Defeater / countercase | Exact lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/PREF-01` · `DATED_SOURCE_CURRENT_SURFACE` | The dated study enumerated client window geometry, shell mode, inspector/tab, chat filters, last Scenario and saved Scenario input values. | Local user preference is neither host-wide application truth nor authorization to sync form values. | [L879–895](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L879-L895) |
| `SB-SRC-0020/PREF-02` · `DIRECT_CODE_QUALIFICATION` | Saved Scenario form values can contain arbitrary dictionaries; actual current local JSON serialization applies no field-level secret redaction. | A synthetic sensitive-looking sentinel survives saving and reloading, but no real secret or remote leak was examined. | [L879–895](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L879-L895) |
| `SB-SRC-0020/ASSIGN-01` · `DATED_SOURCE_WITH_DIRECT_CODE_WITNESS` | The original described MainWindow's automatic local 'review result' assignment on Case creation as a follow-up UI convention. | A local AssignmentRecord is not remote task delivery, recipient acceptance or a durable shared obligation. | [L968–989](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L968-L989) |
| `SB-SRC-0020/PORTABLE-01` · `RESEARCH_ALLOCATION_CANDIDATE` | The original recommended separating Qt-independent application semantics from Windows presentation to support future Android reuse. | A portable logical layer neither proves any host/client shipped nor selects the physical application repository. | [L1672–1682](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1672-L1682) |

**Qualified conclusion:** locally constructed UI records and saved form values are useful for one desktop but must be independently evaluated before they become remote shared identity, authorization or workflow facts. Reusing semantic application responsibilities across clients is distinct from copying widget code.

**Scope boundary:** this nine-row producer slice does not exhaust 1,741 physical original lines. The file's whole-source state is `unaccounted`; no independent Science conservation or Research Amputation has been performed.

## Windows Research 0020 — pinned application context, storage and runtime-projection distinctions

**Primary source:** [frozen Windows source study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`, contrasted with pinned public `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b` and bounded source executions. The 18 cross-owner items below conserve distinct original meanings, invalid inferences, competing physical states and one demonstrably false original generalization. This is a source-first producer packet; it is not an independent scientific conservation finding or a Product Decision.

| Research address and evidential status | Material meaning | Challenge / limiting countercase | Original lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/RT-01` · `HISTORICAL_CURRENT_CODE_DESCRIPTION` | The original AppContext composition bundled user settings, activation/session projections, source/data roots, FileStore, version, logger and identity hints in one local application context. | A composition object is not one authority for access control, durable Jobs or verified actual host identity; preserve field-origin distinctions. | [L246–L272](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L246-L272) |
| `SB-SRC-0020/RT-02` · `DIRECT_CODE_CORROBORATED_SCOPE` | The study distinguished available managed and standalone-dev startup from a dormant standalone-user-profile storage path present in a lower-level paths factory. | A declared StorageMode option cannot establish a reachable application startup profile; current _resolve_run_contract accepts only managed activation or explicit dev root. | [L274–L285](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L274-L285) |
| `SB-SRC-0020/RT-03` · `HISTORICAL_PHYSICAL_LAYOUT` | Five independent JSON history projections, user preferences and log/cache/runtime directories were located beneath app-owned local storage in the pinned desktop state. | Separate paths establish neither five-way atomicity nor a future shared-server storage layout; preserve local-vs-host scope. | [L287–L319](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L287-L319) |
| `SB-SRC-0020/RT-04` · `DIRECT_CODE_CORROBORATED_PROJECTION` | The local session client can consume external session/user/health surfaces and write an application runtime-state projection including selection, last Case, outputs, shutdown and timestamp hints. | A stored active_job or clean_shutdown hint is not independent proof of durable Job admission or external effect completion. | [L320–L345](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L320-L345) |
| `SB-SRC-0020/RT-05` · `DATED_IMPLEMENTATION_SCOPE` | The source described degraded launch as allowing desktop availability and diagnostics despite unavailable Data root, with workspace-dependent operations failing through controlled results. | A successful preflight does not establish availability of domain data or authorize downstream publication; behavior depends on actual flags and installed profile. | [L347–L353](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L347-L353) |

**Evidence resolution:** local composition, AppDock-provided projection references and direct domain FileStore are distinct authorities. A saved `active_job` string does not create a durable Job; a dormant storage mode does not create another deployable product profile; and a successful degraded-mode preflight can coexist with unavailable analytical data. Such qualifications matter more than mirroring every current `AppContext` field in future shared contracts.

**Conservation boundary:** these 5 additional rows are producer-traced source passages only. The original 0020 contains 1,741 physical lines, has additional unpartitioned material, and keeps census state `unaccounted`. A distinct verifier must review bidirectionally before a whole-source terminal disposition.

## Original Windows Study 0020: future portability and execution options (source packet A)

**Frozen source:** [Windows historical study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`. These 5 dated Research claims represent separately qualified proposed options, *not* delivered features or admitted Product commitments. [Windows current-state owner](../../current-how/windows-application.md) and actual implementation remain decisive for present-tense facts.

| Original address · role | Material historical meaning | Defeater or cost | Exact original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/PORT-01` · `HISTORICAL_PORTABILITY_HINT` | An OS-specific PlatformServices adapter exposed open/reveal/copy actions and a non-Windows xdg-open fallback despite a Windows-only declared surface. | A fallback command branch is not native Linux product support; Qt clipboard dependency and actual OS permissions remain. | [L1031–L1045](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1031-L1045) |
| `SB-SRC-0020/PORT-02` · `RESEARCH_REUSE_CANDIDATES` | The source identified reusable operation, Scenario, Case, Event, Artifact, Assignment, workspace and chat-projection semantics as candidates for Android reuse. | Python module importability and shared model names do not imply a running Kotlin/TypeScript client or identical Android storage. | [L1051–L1064](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1051-L1064) |
| `SB-SRC-0020/PORT-03` · `DIRECT_CODE_LEAK_WITH_DESIGN_OPTION` | The source pinpointed runtime/bootstrap importing the Qt coordinator, and proposed an application-level orchestration seam with thin platform presentation bridges. | Separating Qt imports is necessary for some headless packaging profiles but by itself does not create authorized host ownership or durable recovery. | [L1066–L1093](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1066-L1093) |
| `SB-SRC-0020/PORT-04` · `RESEARCH_VIEW_MODEL_OPTION` | The historical presentation/common expansion proposal included semantic navigation, filter, Case inspector, artifacts/logs, assignments, forms and action availability. | Transport-neutral projections need recipient-aware authorization and truth-bearing source state, not merely a shared set of view-model classes. | [L1095–L1112](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1095-L1112) |
| `SB-SRC-0020/PORT-05` · `DATED_EXTERNAL_TOOLCHAIN_CLAIM` | The original considered deploying Qt for Python to Android as an alternative to a separate native toolkit, while noting packaging/toolchain burden. | This is a dated option requiring current official Qt deployment verification, supported-platform tests and cost comparison; no Android build was performed. | [L1114–L1118](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1114-L1118) |

**Conservation boundary:** source-specific producer interpretation only, no native deployment, validated future API, whole-source `LOSSLESS_PASS` or distinct independent reviewer. All source file dispositions remain `unaccounted`.

## Original Windows Study 0020: proposed client, artifact and collaboration maturity (source packet B)

**Source:** [frozen 2026-10-06 Windows study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), exact blob `225128f2599f0792422c0b31cb3cbe1437991ced`; a dated future-option/release-maturity study, **not** binding architecture, accepted permission semantics or an executed host. Each row retains a competing disconfirming case.

| Address · epistemic role | Original material proposal or observation | Counterexample / limit | Original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/FUT-05` · `HISTORICAL_CLIENT_SCOPE_PROPOSAL` | The Android companion sketch prioritized Case state, catalogs, parameters, approval, health, Artifact/Log summary, assignments, notifications and lightweight launch, leaving heavy file computation at a host. | A mobile management list does not prove Android availability, authorize arbitrary host paths or mandate pixel-identical desktop UX. | [L1442–L1457](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1442-L1457) |
| `SB-SRC-0020/FUT-10` · `DATED_SYNTHESIS_AND_TARGET_RATIONALE` | The source concluded that the strongest existing structure was separation of analytical core and scenario-first desktop UI, while common application logic still leaked into Qt. | Useful architectural direction does not dictate a second repository, production host framework or full lossless Scientific Knowledge acceptance. | [L1672–L1682](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1672-L1682) |

**Evidence status:** a future AI actor label, mobile sketch, host execution backend or artifact field list cannot establish the relevant implementation or rights. This packet is a **producer source transfer**; independent review, complete source accounting and host/client release tests remain open. All frozen source dispositions are still `unaccounted`.
