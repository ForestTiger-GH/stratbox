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
