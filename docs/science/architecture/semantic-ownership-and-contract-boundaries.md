# Semantic ownership and integration-contract boundaries

**Scope:** where the truth of statistical calculations, user tasks, execution, external effects, artifacts, deployment and diagnostics should reside as the same Strategy Box product moves from direct Python and local Windows usage to conditional headless/multi-client operation. **Status:** supported classification and candidate architecture, not an accepted host/service/storage design. The direct implementation snapshot is pinned to [core `8459dc5`](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580) and [Windows `959e9c4`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). Static evidence does not equal installed runtime certification.

## 1. The decomposition criterion is ownership of truth, not repository count

Five useful coordinates:

| Coordinate | Question | Example |
| --- | --- | --- |
| **Semantic owner** | Who defines what an output or transition means? | A statistical transformation belongs to the domain core; an accepted job state to the application |
| **Authoritative state owner** | Who may record the final accepted value? | A shared Run or chat requires one application writer; package deployment has a different owner |
| **Physical executor** | Which actual process performs a requested action? | Desktop process, host worker, or direct notebook |
| **Physical custodian** | Where do affected bytes, metadata and logs live? | Local or host Data binding, product state namespace, protected log root |
| **Presentation consumer** | Who renders a safe, possibly stale projection? | Windows UI, browser, Android, CLI or permissioned machine client |

These five roles can coincide on one computer yet separate when a host serves multiple devices. Moving code to a common package does **not** establish a shared writer. Starting a process does **not** establish that a domain effect succeeded. The basis is an architectural interpretation of [Parnas's information-hiding criterion](https://doi.org/10.1145/361598.361623) and [Cockburn's Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture/), not proof that any particular package arrangement is already deployed.

## 2. The three meanings of runtime and their failure domains

1. **Core infrastructure runtime** ([`base/runtime.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/runtime.py)) selects process-local providers such as FileStore and secrets for Python work. It is not a durable job authority.
2. **Application execution runtime** means accepting work, authorizing resources, scheduling attempts, tracking states, reconciling effects, maintaining shared chat/artifact links. In the pinned Windows application this exists in a narrower local Qt-bound form, **not** as a separately certified host.
3. **External platform runtime** manages package/install/Node/session/activation, provided storage roots and process/platform health under its own versioned contracts. It does not decide whether a bank statistic was computed correctly.

At startup, a platform process can fail before a domain operation is ever admitted. Conversely a domain validation can fail while the platform Node is healthy. A storage adapter can report incomplete write after the core successfully calculated data. **Each failure needs its own owner and reliable projection.**

[Core FileStore protocol](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py) supports filesystem-like access; it is *not* by itself ACID, object authorization, durable Job storage, or an artifact publication registry. The [HTTP downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) provides transport result/failure evidence, not user-work lifetime. Domain core must remain independently callable from Python/Jupyter with no fabricated Thread/Run or external manager dependency.

## 3. An owner map that forbids silent cross-boundary promotion

| Object or effect | Meaning owner | What another layer may do | Mistake to avoid |
| --- | --- | --- | --- |
| Source series, banking identity, classifier, calculation and numerical evidence | `stratbox` domain logic | Render or serialize typed results | UI changes statistical truth by formatting |
| Domain `Request→Result` | Core | Invoke from notebook or authorized application | Force every direct function call into a Chat/Job |
| Operation descriptor and machine discovery | Curated domain/application definition | Present available operations subject to policy | `visible=true` mistaken for permission |
| Scenario definition and resolved parameters | Application semantics | Different forms render it | Widget value silently becomes canonical historical params |
| Shared Thread/Case/Run/Job/Attempt/cursor | One logical application authority when shared state is adopted | Client reads/sends commands | Every client writes its own copy of shared JSON |
| Principal authorization, approval and destructive effect boundary | Application policy/enforcement in managed profile | Client requests/reports status | Nickname, disabled button or agent tool listing treated as grant |
| Actual file write/rename/delete | Storage/backend, constrained by caller | Return receipt and errors | A returned path assumed durable/publicly available |
| Artifact metadata, publication and access | Application catalog if managed | Authorized viewer resolves logical ref | Physical existence equated to a published artifact |
| Installation, package identity, Node/Session, activation, runtime health | External managed platform | Application validates and safely projects capabilities | Platform Node considered a Run state |
| App log, domain finding and platform problem | Separate producer/diagnostic owners | Reference a confirmed record with scoped visibility | Raw exception broadcast as shared chat message |
| Theme, tab, pane geometry, local picker, draft | Individual surface/user scope | Persist for convenience | Device-specific setting overwrites host authority |

The user-origin constraint reported in the dated research is that **state should live where the work actually runs**: on the device in fully local mode; significant shared state and Data on the executing host in host mode; client-local directories for secondary personal information. This does *not* imply putting everything called “user data” into a physical user root. Semantic responsibility and managed placement must be decided in that order.

## 4. Four physical organizations compared

**A. Application remains entirely inside Windows.** This describes a useful current local prototype, with minimal operations. It is unsuitable as the intended permanent owner of remote browser/mobile Jobs: closing the UI may end execution and the local JSON files cannot act as node-wide truth.

**B. Shared application library loaded in each client.** Improves code reuse but does not solve mutual exclusion, canonical revision, authorization or consistent multiuser history. It can be used as an internal code organization only with one actual mutation authority per active workspace.

**C. One logical headless application authority serving distinct clients.** A coherent target for hosted use: one authenticated command admission, consistent Run state, resource claims, effect reconciliation and safe subscriptions. It may initially be a modular monolith with local workers, rather than many services. The physical host repository/process is an independent decision determined by lifecycle, not naming.

**D. Transfer all application-owned chats and jobs into the deployment platform.** Reject as semantic design: deployment infrastructure can supervise a process, allocate a Node and provide valid roots, but it does not own Strategy Box scenarios, domain errors or the meaning of Excel publication. An explicit adapter can delegate platform-owned lifecycle and diagnostics, subject to proven contracts.

The same library can therefore support local in-process authority and hosted authority without demanding HTTP inside direct Python computation. Adding queues, brokers, full event sourcing, Temporal-like workflow replay or distributed locking “just in case” would introduce independent state owners before an operational need has been shown.

## 5. Deployment profiles and the difference between local and hosted guarantees

| Profile | Core execution | Accepted Work/Run authority | Client and storage implication | Status |
| --- | --- | --- | --- | --- |
| **P0 direct Python / notebook** | Caller Python process | May have no managed Run at all | Caller owns input/output and its evidence | Core usage current |
| **P1 local Windows foreground** | Desktop process | Local application and its limited stores | Device-owned state and workspace; UI close may interrupt | Current partial Windows behavior |
| **P2 local headless** | Independent local process | Local host application | Loopback clients; durable execution only if explicitly implemented/tested | Candidate |
| **P3 shared team host** | Host workers | One host/workspace authority | Shared chat/Jobs/artifacts and affected Data live under host custody | Candidate |
| **P4 Internet-accessible Web** | Host workers | Host authority | TLS/authenticated clients; stronger permission/object-access gate | Conditional |
| **P5 Android remote companion** | Host workers | Host authority | Device keeps session/draft/limited cache, not full authoritative Job | Conditional |
| **P6 Android local compute** | Phone compute runtime | Device local authority | Separate data/toolchain/storage feasibility | Hypothetical |

One managed platform Node need not always equal one application workspace; multiplicity and isolation need an explicit Product Decision. For small profiles, one workspace per installed application instance is a *candidate simplification*, not a mandated multi-tenancy contract.

**Foreground versus host:** P1 may end an in-flight action when the UI/process ends, but the next launch should not fabricate a successful or completely failed external effect. P3 can continue after a browser closes only when its executor and state genuinely outlive that client. “Durable accepted record,” “durable running worker,” and “automatic workflow replay” are three different service promises.

## 6. Admission, permission and effect truth are consecutive but separate

A possible managed command path:

```text
intent from UI / permitted machine caller
  → authenticate and bind verified principal
  → validate current operation version, parameters and workspace revision
  → authorize action, resource, effect class and any approval
  → reserve idempotency/request identity and admit intent durably if promised
  → schedule attempt subject to per-resource concurrency
  → execute typed core Request→Result
  → observe file/network effect receipt and reconcile uncertainty
  → finalize application outcome and authorized artifact index
  → project safe events/links to clients
```

A display nickname describes a participant to humans; it is not a credential on Web/agent boundaries. A platform session may provide trusted identity only if its explicit contract actually attests that principal and applicable scope. Direct Python execution instead relies on the caller/OS/FileStore permissions and must not require Web authentication.

**Three completion questions differ:**
1. Has the calculation produced its domain result?
2. Has the external file/network/destructive effect been verified?
3. Has a permitted result/Artifact been published and made accessible to the viewer?

For example a workbook can be computed in memory, writing to Data root can time out after possibly committing, and the artifact catalog can still have no verified publication. `computation=success; effect=unknown; publication=pending` is a meaningful composite outcome. A UI success icon cannot infer all three from a Python return.

To handle lost acknowledgements, the request identity binds a principal/workspace/payload to one logical admission. Its reuse with a *different* payload needs a conflict; effect idempotency and reconciliation are additional obligations. A network retry alone never guarantees exactly once. Resource controls apply to affected files/workspaces, **not to the number of chat windows**: two independent read-only runs may proceed together while two writes to one canonical output require serialize/version/conflict.

For a basic FileStore, a *candidate* safe publication protocol stages bytes, checks integrity, publishes according to actually supported backend atomicity, then records the authorized Artifact. Destructive cleanup is different: plan, preview/approve, execute, verify, and preserve partial/unknown. The default user file may remain a simple path/locator and become `missing` if manually moved or deleted—no automatic whole-disk tracking required.

## 7. A minimum contract topology, with explicit variants

| Contract family | Intended role | What is already current? |
| --- | --- | --- |
| `CoreOperation`, typed `Request/Result` | Call a domain operation from any authorized Python consumer | Exists in some domains; uniform catalog is not proven |
| `OperationDescriptor` | Stable ID, input/output types, effects and requirements | Partial Windows operation specs; general runtime admission open |
| `ScenarioDefinition` | Composition and effective parameter interpretation | Local Windows sequential scenario model |
| `InvokeCommand` / `CommandOutcome` | Managed admission, rejection, conflict and unknown response | Candidate across client boundaries |
| `RunSnapshot`, `JobStatus`, `EventFeed/Cursor` | Shared lifecycle with revision and reconnect | Only narrower local representations current |
| `PermissionDecision` | Principal × action × object × effect policy | Needs actual managed authority to enforce |
| `ArtifactReference` | Stable result with authorized availability | Local record exists; remote resolver candidate |
| `StorageCapabilities`, `ExecutionBackend` | Backend operations and execution placement | Basic FileStore, local runner; advanced portability candidate |
| `PlatformActivationAdapter`, `PlatformHealthAdapter` | Versioned external environment state | Limited Windows integration, rest conditional |
| `ClientViewModel` | Safe labels/cards/forms without Qt at semantic boundary | `presentation/common` partially demonstrates this |
| `Machine/agent adapter` | Governed external invocation through same application authority | Future optional consumer |

An illustrative `InvokeCommand` might include opaque `request_id`, workspace/chat/operation refs, operation version, parameters, expected revision and idempotency key. **Principal identity must be obtained from authentication**, not arbitrary browser POST fields. `accepted` and HTTP `202` mean the request was admitted for processing, not that the workbook is finished ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). The exact field names and REST routes are research examples, **not installed wire API**.

Versions are multidimensional: distribution/core code, domain operation schema, application command/state API, artifact schema, storage schema, host wire version, Windows/Web/Android client, and external manifest/activation/session contract versions. A single field called `platform_version` cannot certify them all. Unknown required capability should result in explicit `UNSUPPORTED_CAPABILITY` rather than silent emulation.

Dependency rule: **clients → product application contract → domain core + narrow platform-neutral ports**; external platform adapter → specific supported platform contract; storage adapter → backend. Prohibited inversion: core imports Qt or platform internals; UI writes shared DB; browser obtains host absolute path; external platform defines bank-sector result semantics.

## 8. Platform integration as a capability check, not a promise

External managed deployment has separate partial source declarations, authoring/resolved configuration, actual package/release layout and installed activation/runtime truth. Its Node/process outcome and platform diagnostic refs differ from the application Run/effect record. An AppDock [observability status at exact revision `a4d87c6`](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) reports bounded milestone 5E source work complete with native Windows certification pending; that does **not** verify future generic host execution, shared product state or a ready external product recorder.

[Windows manifest at pinned revision](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) describes local foreground Windows execution, not a ready remote host. Connector manifest, surface activation and runtime/session versions are different contract families, and the observed manifest/README/smoke/core dependency drift requires its own exact reconciliation and installed test. `supports_presence` in a declaration is not proof of network presence.

The platform supplies a permitted physical root or provider binding; Strategy Box supplies its private history schema and its domain-specific validation. Named future platform APIs must not be invented. Without confirmed feature negotiation, the correct user-visible result is restricted/unsupported/degraded, **not** “integration succeeded.”

## 9. Evidence of collaboration requires one state writer

For shared Thread history, an application authority may store `node/workspace`, `thread`, message, Case/Run, Attempt, effect, Artifact and per-participant read cursors. One chat may host multiple concurrent Runs. One Run may involve many attempts and effects. A nickname and timestamp are useful author display; an immutable principal and actual executing Node identify responsibility.

Clients retrieve a permitted snapshot with revision/cursor and subsequent events; on reconnect a gap triggers a new snapshot. The application event feed and platform health/problem feed are **different** even when the UI combines their safe summaries. Technical logs should stay with the actual executor and be referred to through permission-checked logical references.

State backend recommendations conflict in the late Research: this ownership study discusses single-host SQLite as an economical first transactional backend, whereas subsequent storage/observability studies explicitly allow verified atomic files or append-only journal first and defer the DB choice to the externally provisioned storage profile. These are **competing physical proposals**, not evidence that one was adopted or deployed. For SQLite WAL, a host-local file served via API differs fundamentally from a network filesystem opened by every client ([SQLite WAL](https://www.sqlite.org/wal.html)). Stronger durability, backups and auto-resume require explicit failure-profile tests and owner approval.

## 10. Negative cases and verification obligations

The future contract can be challenged by at least the following scenarios, which are **proposed tests, not measured passes**:

| Counterexample | What a valid implementation must distinguish |
| --- | --- |
| Direct Jupyter run without GUI/platform | Core remains callable; no invented chat Job |
| Two runs in separate threads/chats | Independent Run IDs and real resource admission |
| Two writers to one output | Conflict/serialize/version, never invisible overwrite |
| Close Web during true host execution | Verified Job continues independently of client |
| Kill local foreground worker | Interrupted/Unknown vs unwarranted success |
| Network drops after output commit before ACK | Reconcile effect via identity/receipt |
| Export built in RAM, Data root write failed | Compute success vs publication failure |
| File manually renamed/deleted | Honest `missing` with historical record retained |
| Spoofed browser `principal_id` | Server ignores forged author and checks real identity |
| Machine caller asks for destructive permission | Same managed policy denies unauthorized effects |
| Connector manifest and tests have incompatible versions | Build/contract gate finds drift before release |
| Platform unavailable during direct Python run | Core remains functional; managed client reports startup issue |
| Shared Data root absent | Degraded/read-only state or explicit denied writes |
| Two clients rename one chat | Revision conflict rather than last-write-wins loss |
| Viewer may see Thread but not raw logs | Safe summary allowed; traceback protected |
| Persisted history corrupt | Typed corruption/recovery, not “first run with empty state” |
| Stale worker finalizes output | Fencing/version guard for actual multiworker profile |
| Web/Android attach during active run | Shared snapshot+cursor lifecycle truth |
| Unsupported platform remote feature | Explicit unsupported rather than invented success |
| Platform startup failure | Platform failure is not a fabricated domain Job failure |
| Operation schema drift from handler | Contract/fixture test catches mismatch |
| Result adapter drops economic units or evidence | Semantic fidelity preserved, not generic `ok` only |

The test pyramid includes direct core fixtures, application rule tests with fake ports, exact external contract validation, cross-client DTO fixtures, host E2E concurrency/fault injection and installed runtime gates. None has been executed by this article. Revisit choices on accepted deployment profiles P0–P6, actual storage RPO/RTO, scope of machine consumers, public Web authorization, retention, workspace multiplicity, host lifecycle, external platform versioned contracts and measured workloads.

## 11. Open questions that require owner action

This source research enumerates 14 application/platform Product Decisions: whether P1 needs a headless process; crash/power-loss retention; automatic interrupted-job replay; permitted read/write/destructive operations; multiple workspaces; authoritative Web/Android identity; state store; record/log/artifact retention; default Artifact; exact platform remote bindings; polling/SSE/WebSocket; separate host repository; Android parity; optional agent protocols. These remain **questions**, not accepted requirements. Also unresolved is whether profile P3 or P4 will exist in the first funded release, which determines the required headless lifecycle and security floor.

The smallest robust next experimental proof is a **real vertical Run** invoked from direct Python and a managed client, with actual typed result, permission decision, staged artifact publication, reconnect and lost-ACK negative case. That experiment could falsify a proposed authority boundary at much lower cost than creating five empty service repositories.

**Negative conclusion:** a common vocabulary and contract table are not evidence of production cross-platform compatibility; a GUI Run label is not durable history; a storage path does not imply recoverability; and a platform Node supervision record is not a domain effect receipt.

## Original automation Research 0041: conflicting physical ownership and MCP placements

**Frozen original:** `SB-SRC-0041` at `8459dc58922b7e8df853cf1d9e8131fa9e132580`, Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. **Status:** historical Research candidate; source-line-qualified producer assembly, *not* an implementation or accepted Product Decision. This old diagram is historically important *because it conflicts with later, explicitly accepted product direction in places*. It recommended a broad external platform gateway and suggested application semantics initially co-located with Windows. Current product authority instead admits the need for a logical Strategy Box host in two deployments; process/repo split and specific machine transport remain undecided. The three original alternatives are preserved below as evidence of design freedom, not current installed components.

| Original unit / epistemic role | Material original distinction | Countercase and permitted inference | Source |
| --- | --- | --- | --- |
| `SB-SRC-0041/OW-01` · `RESEARCH_CORE_BOUNDARY` | The original allocation kept banking domain operations, source contracts, validation, calculations, provenance and artifact generation in independent stratbox core without scheduler/LLM/MCP dependencies. | The accepted independent core boundary does not imply one concrete API or that every prototype helper is mature. | [L1899–1913](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L1899-L1913) |
| `SB-SRC-0041/OW-02` · `HISTORICAL_APPLICATION_OPTION` | The research described a logical shared application owner for catalogs, orchestration, jobs, cases, events, artifacts, automations, approvals, assignments and AI-facing capability descriptors, without Qt. | Its initial proposed physical residence under neutral stratbox-windows is not a Product Decision; host implementation location is still open. | [L1915–1935](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L1915-L1935) |
| `SB-SRC-0041/OW-03` · `HISTORICAL_COMPETING_PLATFORM_ALLOCATION` | The historical sketch allocated a maximal bundle of scheduler, execution broker, identity, secrets, AI provider, MCP gateway and notification duties to AppDock. | A conceptual external platform role cannot supersede accepted Strategy Box host authority or prove those external service backends exist. | [L1937–1953](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L1937-L1953) |
| `SB-SRC-0041/OW-04` · `HISTORICAL_CLIENT_PORTABILITY` | The sketch expected native Windows and future Android presentations over the same logical application semantics, with client-specific adapters and approval/notification UI. | Android target attachment is future; shared semantics do not prove actual portable UI toolkit or hosted service. | [L1955–1977](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L1955-L1977) |
| `SB-SRC-0041/OW-05` · `HISTORICAL_PREFERENCE_NOT_ADMITTED` | Three physical MCP alternatives began with a product-owned endpoint and then an AppDock gateway, which the original research explicitly preferred for centralized auth, remote transport and neutrality. | The preference is conditional on verified gateway capability and separately accepted Product choices; it has no present authority over host ownership. | [L1983–2004](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L1983-L2004) |
| `SB-SRC-0041/OW-06` · `HISTORICAL_HYBRID_OPTION` | The third historical MCP arrangement was a hybrid: a Strategy Box in-process capability provider wrapped by an external protocol adapter. | A clean logical adapter shape does not guarantee the external adapter exists, supports tasks, or enforces permissions. | [L2006–2018](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2006-L2018) |

**Status after producer reconciliation:** material meanings are addressable in this maintained Science module, and the original counter-options remain traceable. There is **no independent semantic-verification PASS** for these items, no whole-source `LOSSLESS_PASS`, and no actual cross-device release conformance. The source-wide material census remains `unaccounted`.

## Original automation Research 0041 — dated roadmap, logical architecture and example machine endpoints

**Frozen source:** [primary automation/AI study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. These are historical engineering alternatives with explicitly limited authority. A phase number, API-like name or deployment box in the original document is not evidence of an actual provider, Product Decision, accepted schedule or real effect.

| Material address and epistemic role | Source-defined proposition | Defeater, cost, competing choice | Primary lines |
| --- | --- | --- | --- |
| `SB-SRC-0041/SCHEMA-01` · `HISTORICAL_LOGICAL_ARCHITECTURE_SKETCH` | The Appendix A diagram placed catalogs, Jobs, Cases, approvals and capacity descriptors in logical application semantics, a deterministic runner alongside external runtime adapters, and financial calculation in stratbox core. | The diagram assigned broad scheduler/permissions duties to AppDock; an explanatory sketch cannot prove installed external modules or decide the physical Strategy Box host owner. | [L2232–L2267](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2232-L2267) |

**Conservation limit:** this is a producer source-first packet; independent reverse review, empirical release tests and whole-original material accounting remain open. The current accepted Strategy Box host requirement supersedes only conflicting historical ownership/timing assumptions, not the original's record as a real alternative.

## Original application note 0014 — dated Git launcher and core-embedded GUI model

**Research-only provenance:** [exact historical original](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md), Git blob `c10ee7d96f24996f6480d95adf2b005c0651122e`, 125 physical lines. It proposed a self-updating Launcher and GUI co-located inside the analytical core; **the contemporary owner split and accepted host need differ**. Material original wishes about easy installation, FileStore-independence, transparent progress, logs, watcher reuse and graceful failure remain useful as qualified UX/reliability constraints. Original branch names, paths and EXE descriptions are not active Product Decisions.

| Source address · status | Original material point | Counterargument/current authority | Frozen original |
| --- | --- | --- | --- |
| `SB-SRC-0014/APP-01` · `SUPERSEDED_PHYSICAL_COLOCATION` | The old design placed GUI and task configs physically inside the stratbox core repository, loaded from GitHub by a separate Launcher EXE. | Current public owner separation is stratbox domain core plus distinct stratbox-windows application; physical co-location must not be silently reintroduced. | [L21–L25](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md#L21-L25) |
| `SB-SRC-0014/APP-03` · `HISTORICAL_STORAGE_ABSTRACTION_OPTION` | The early FileStore reasoning wanted business logic independent of physical data location and treated an external drive mount as a local filesystem interface. | Treating a mapped network volume as a Path does not establish safe concurrent writes, durable state, provider atomicity or official source identity. | [L29–L29](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md#L29-L29) |
| `SB-SRC-0014/ARCH-01` · `SUPERSEDED_REPOSITORY_LAYOUT` | The old proposal tied launcher bootstrap to a UI in the same core repository, with task/profile configs, runtime/logger/path helpers and GUI resources. | Present core isolation and dedicated Windows surface were admitted subsequently; layout wording must not be treated as current engineering ownership. | [L37–L39](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md#L37-L39) |

**Limit:** producer source-line-preserved candidate Science only, not an installed Launcher, Git update path, enterprise-specific backend, actual Windows GUI test or complete independent original material disposition. Later explicit product ownership supersedes contradictory physical recommendations; no old runtime compatibility layer is required merely to retain source meaning.

## Original business-logic refactor study 0016: domain capability, product layer and FRG pilot

**Source character:** [dated historical primary study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md), exact Git blob `d04fece78c89063c2ac2dac775179f1517c7fea9` (1,927 physical lines), with an older in-core GUI layout that was superseded by the independent Windows repository. This source's domain and process proposals are preserved as conditional Science; the adopted application-host scope and existing core/source implementation retain separate authority.

| Source-material address / epistemic status | Original reasoning or candidate | Counterexample / present limit | Primary source location |
| --- | --- | --- | --- |
| `SB-SRC-0016/APP-01` · `HISTORICAL_APPLICATION_COUPLING` | The original found one legacy FRG adapter mixing output location choice, Excel creation, product result selection and application execution context. | This described an older physical src/app implementation; it is not the current independent Windows repository nor an accepted new app layout. | [L84–L101](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L84-L101) |
| `SB-SRC-0016/OWN-02` · `RESEARCH_DOMAIN_SCOPE_MODEL` | The proposed domain boundary owns analytical methods, file/network infrastructure required by domain and stable typed operations, but excludes AppDock-specific UI/forms/timeline/icons. | Environment-specific outbound transport, credentials and client presentation require explicit neutral contracts, not hidden imports or domain-specific UI dependencies. | [L103–L122](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L103-L122) |
| `SB-SRC-0016/ROAD-02` · `HISTORICAL_THREE_ROLE_ALLOCATION` | The proposed three-role model separated domain operations, app scenario/product projection and a thin external platform activation boundary. | Logical separation survives later owner changes, while physical GUI in core, connector topology and exact host process are not frozen by this old plan. | [L547–L573](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L547-L573) |
| `SB-SRC-0016/PORT-01` · `HISTORICAL_COMPETING_ARCHITECTURE` | The historical ideal rejected both script-bound GUI and accidental GUI-on-library layering; it proposed a broad domain library, product application and thin external platform adapter. | Present public repositories already separate core and Windows surface; this old description is a product-space argument, not a current directory map. | [L817–L828](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L817-L828) |
| `SB-SRC-0016/APP-02` · `HISTORICAL_PRODUCT_PARAMETER_PRESENTATION` | The old application-layer proposal owned contextual parameter presentations such as basic/advanced defaults, dynamic choice, path selectors, presets and display conditionality. | A saved preset must not override domain validation, input authorization or expose sensitive values to another user/agent. | [L1707–L1725](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1707-L1725) |

**Coverage and authority:** the old plan's exact capability names, file paths and suggested sequence are not current public APIs, not guaranteed FRG effect safety and not accepted release architecture. This packet is producer source-position routing only; extensive original remaining material and independent evidence/reverse checking remain open.

## Original historical refactor 0016 — qualified application seams and negative alternatives

This bounded **frozen historical Research recovery** preserves the original three-selection hypothesis, one-to-many product representation, typed FRG result and exporter alternatives, separated cleanup plan/execute, the *unconfirmed* post-Run failure suspicion, and layered conformance responsibilities. The older source locates UI/application code in its former repository structure; current repository and accepted logical host boundaries follow direct code and Product Decisions instead. No fixed number of physical registries or an additional application repository is implied by this Science.

| Original source-specific assertion | Conserved mechanism | Counterexample / evidence scope | Source |
| --- | --- | --- | --- |
| `SB-SRC-0016/SEAM-01` · `HISTORICAL_THREE_LOGICAL_CATALOGS` | The old refactor proposed three *different logical selections*: domain operation inventory, application-specific product projection, and the subset deliberately exposed at the external managed-platform boundary. | Three useful decisions do not require three physical registries, three services or a prescribed repository layout; an implementation could compile logical views from one validated catalog. | [L200-L240](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L200-L240) |
| `SB-SRC-0016/SEAM-07` · `HISTORICAL_LAYERED_CONFORMANCE_REQUIREMENT` | The old completion checklist separately demanded tests/documentation for domain operations, product projection, execution lifecycle and managed-platform activation rather than treating one smoke test as universal assurance. | Green unit/import tests cannot establish native platform deployment, full failure recovery or application authority; real integration and independent semantic checks remain distinct. | [L756-L770](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L756-L770) |

The old proposal must be interpreted as **scientific/historical design alternatives**, not Product Decisions. The accepted Strategy Box application host is a logical responsibility; shared semantic selection and visibility can be provided without prematurely creating physical catalog services, registries or packages. The complete large source `SB-SRC-0016` still has unexamined material and `source_material_state=unaccounted`.

## Original historical refactor 0016 — final whole-source producer residue

Six additional source-addressed historical meaning clusters make the earlier refactor's file-placement proposal, actual app maturity criticism and source-defined first-stage deliverables explicit. They are **dated Research propositions**, not current code, product-approved architecture, actual deployed managed-platform features or requirements to materialize a repository per logical term. Earlier source-specific FRG, domain-operation, request/result, exports and selective product-projection evidence is retained without duplicating its unit IDs.

| Historical source position | Original meaning | Limiting or contrary evidence | Frozen source location |
| --- | --- | --- | --- |
| `SB-SRC-0016/COMPLETE-01` · `HISTORICAL_PROPOSED_CORE_DIRECTORY_MAP` | The early study favored visible repository-local separation of domain operations, contracts and exporters from FRG internals such as parsing, naming, dispatch and registry helper modules. | The illustrated filenames and `src/` tree are a historical design proposal, not the installed tree or a reason to force a new physical package; semantic boundaries can exist without matching directory spellings. | [L1082-L1140](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1082-L1140) |
| `SB-SRC-0016/COMPLETE-02` · `HISTORICAL_SINGLE_REPOSITORY_APP_TREE` | The original proposed an application directory with product operations, parameter overlays, presets, presenters, runs, GUI and a narrow external platform directory, reflecting an older colocated-repository assumption. | Current implementation ownership separates analytic core and Windows surface. Common logical application meaning and an optional future package must be evaluated separately from this obsolete file placement. | [L1141-L1193](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1141-L1193) |
| `SB-SRC-0016/COMPLETE-05` · `HISTORICAL_THIN_PLATFORM_ADAPTER_DETAILS` | The source limited the proposed external managed-platform adapter to activation context, runtime status and optional Artifact/route projection, reserving actual bank/macro method details and product catalog to Strategy Box. | A thin adapter need not ignore platform security and capability negotiation, while the platform installation owner cannot be assigned product-specific Case and effect authority by an old sketch. | [L1797-L1831](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md#L1797-L1831) |

The historical proposal is qualified by actual direct owner boundaries: `stratbox` remains independent analytical core; current Windows orchestration must be read from its own pinned code; a shared logical application authority is admitted for future hosted work but physical layout is undecided. Section-level whole-original producer reconciliation is evidence **separate from** this self-contained Science. Independent original-first and destination-backward review is not complete.
