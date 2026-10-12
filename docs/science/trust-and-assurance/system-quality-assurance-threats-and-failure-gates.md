# System quality: threat boundaries, truthful failures and falsifiable assurance gates

**Scientific subject:** reliability, typed error truth, security/authorization, effect safety, concurrency, diagnostic evidence, durability, supply-chain integrity, resource use, accessibility and portability under a shared Strategy Box product contract. **Status:** source-grounded research and explicit negative test program, not a security certification, installed cross-node implementation, passed tests, adoption of 50 invariant IDs or chosen infrastructure topology. This paper is derived from the separately available **Topic 08 Trust/Safety/System Qualities primary study**, not the provisional trust bridge in the dated Topic 09 synthesis.

## 1. Reliability is a composite contract across a dozen failure boundaries

A useful full-path assurance chain is:

```text
verified actor, scope, policy and versioned binding
 → parameter/source/operation preflight
 → accepted immutable plan + idempotency identity
 → resource claim + observed worker Attempt
 → effect intent + bounded actual effect
 → receipt + validation or honest UNKNOWN
 → verified result/artifact publication
 → independently assessed Work outcome
 → recoverable state, safe diagnostics and authorized projection
```

These steps have independent failure windows. A UI spinner and a Python `ok=True` cannot establish a multi-layer success. **Five truths** need separate grounds: (1) execution terminal outcome, (2) physical effect state, (3) domain qualification and epistemic support, (4) Work acceptance, and (5) operational health/readiness. A `PARTIAL` domain result can have no process exception; a timeout after remote commit is not evidence that the effect was absent.

A direct Python/Colab domain operation may not need a durable Work or product IAM service. Conversely a real remote/multiuser managed profile needs the app to own accepted mutations independently of Qt widgets, with a truthful background/host availability contract. Both paths use the same subject algorithms, not separate rules for human, automated and machine actors.

## 2. Concrete baseline findings must remain scoped to exact code

The 2026-10-09 source study made several **static direct implementation observations**:

- [`LocalFileStore.listdir()`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py) returns `[]` for both an absent path and an existing object that is not a directory. It conflates two states with a genuinely empty directory. **This does not prove it suppresses every permission or network failure.**
- The same `LocalFileStore._abs()` treats its configured `root` as a relative-path convenience; absolute paths may bypass that prefix and containment is not proven. This is not inherently a bug for a general-purpose local Python FileStore, but **it cannot be used as the trust boundary of a Web/AI file API**.
- The [base FileStore copy](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py) may read the entire source into memory before writing. A wrapper named `open_read` is not a streaming guarantee if its concrete backend buffers content.
- The [core discovery runtime](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/runtime.py) has generic entry-point and fallback paths; whether silently selecting another provider preserves managed data/effect semantics is unverified and should be policy-gated.
- Core metadata `0.8.0` and Windows dependence/manifest on `0.2.1`, plus Windows manifest `4.0` versus smoke-test expectation `3.0`, create **declared install/test drift**. This is a static mismatch; it is not the result of a successfully executed or failed clean-install test here.
- Windows local [five-JSON history](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py), Qt coordinator, background scaffolds and `cancelled` vocabulary do **not** prove shared durable Job, scheduler, tested cooperative cancellation or coherent corrupt-data recovery.

The priority consequence is not to invent a wholesale replacement stack. It is to establish typed FileStore semantics, root-scoped authorized resources, installed release-tuple tests, explicit local-host lifetime, deterministic provider policy, and negative crash/effect experiments.

## 3. A threat map classified by trust crossing

| Input or boundary | Material threat | Minimum candidate proof |
| --- | --- | --- |
| Official/public/user-provided XLSX, DBF, ZIP, HTML, PDF | Wrong period/schema, HTML masquerading as XLSX, ZIP slip, decompression bomb, malicious XML/macros | Explicit content/schema/semantic validation, path traversal rejection, archive entry/expanded-size budgets; no executing document macros on read |
| User- or AI-supplied workspace locator | Absolute, `../`, symlink/junction escape, directory-vs-file confusion | Authority-side canonical resource reference, root/object grant and filesystem-specific containment tests |
| External storage/API after write begins | Lost ACK, duplicate destructive action, partial write | Stable effect identity, verification receipt, `UNKNOWN`, reconciliation before repeat |
| Two workers sharing output | Stale worker after lease expiration or conflicting writes | Resource lock, current worker fencing generation at publication, expected-target revision |
| Multiuser/event feed | Private message/path/event-count inference via raw global sequence gaps | Server-side ACL/filter, opaque authorized cursor, field-level projection and revocation tests |
| Support/diagnostic export | Secret, private path, user document contents and auth headers | Allowlisted redaction, permissioned support bundle and audit of export |
| Third-party executable contribution | Python code running with process privileges despite declarative manifest | Trusted activation or genuine process/OS isolation; `in_process` is never called a sandbox |
| Machine/automation user identity | Forged actor, stale delegated rights or prompt injection in source data | Verified principal, bounded delegation, pre-effect grant/approval revalidation, deterministic proposal validation |
| Crash/storage exhaustion | Lost state/effect ledger, corrupt history, failed audit | Protective degraded mode, tested restore, emergency logging and fail-closed risky actions |
| Low-end UI/large input | OOM, UI freeze, repeat-click duplicate effects, dangerous small controls | Resource admission, measured streaming/budgets, responsive/accessible actionable UI |

An official publication or model-generated response is *data* at the execution boundary. It cannot instruct Strategy Box to change target file paths or elevate permissions. An approved extension package may be trusted code at startup but its presence alone does not grant another human/agent every action available through that code.

## 4. Typed failure, not arbitrary empty values

One useful outcome taxonomy distinguishes:
`NotFound`, `WrongType`, `OutOfScope`, `AuthenticationRequired`, `PermissionDenied`, `Unavailable`, `Timeout`, `RateLimited`, `Unsupported`, `DependencyMissing`, `Corrupt`, `HashMismatch`, `SchemaMismatch`, `ValidationFailed`, `InsufficientEvidence`, `Conflict`, `PartialFailure`, `OutcomeUnknown`, and `InternalFault`.

These are **proposed category semantics**, not a finished common enum. `NotFound` is a fact about the requested object; `Unavailable` says an inspection could not be completed; `ObservationMissing` is the domain meaning of a statistical value. A network timeout cannot prove “the central bank published zero”; a parser error cannot prove “the ZIP does not exist.”

For managed execution, keep:
- lifecycle: prepared/queued/running/finalizing/terminal;
- terminal execution outcome: success/partial/failure/cancelled/unknown;
- side-effect state: staged/committed/verified/partial/unknown;
- capability readiness and health;
- domain completeness/freshness/evidence;
- user attention, approval and pending reconciliation.

`cancel_requested` is not a terminal cancellation. One Job must not have both independently committed `SUCCESS` and `FAILED` terminal records; uniqueness on `(job_id, outcome_kind)` is insufficient. Later evidence about a previously ambiguous effect should be appended/associated without erasing forensic observations.

## 5. Effect safety and the three kinds of recovery

Effect classes: **pure/read**, cache write, staged write, idempotent write with provider lookup, external mutation and destructive action. Blind retry policies differ by class. A destructive operation should use a reviewed immutable target plan with scope/revision/postconditions, current grant, resource claim, pre-effect verification, durable intent, provider receipt and actual postcondition check. An obsolete approval after target revision is a rejection, not an invitation to proceed.

A proposed managed Artifact path is `ArtifactIntent → run-scoped staging → size/digest/content verification → physical publication under verified backend guarantees → application catalog commit → permitted view`. A SQL commit does not atomically commit separate arbitrary filesystem bytes. Crash in the gap may leave orphan staged/published content, which needs detection, reconciliation/quarantine and protection of the previous good version. Content hashing is useful immediately; **mandatory CAS architecture is not decided**.

Three recovery operations are distinct:
1. **Client reconnect:** retrieve the same authorized Work/Run snapshot+cursor, no new execution.
2. **Worker retry/resume:** new Attempt/validated checkpoint, with actual effects and source revisions checked.
3. **Disaster restore:** recover a coherent set of product state, Artifact manifests/bytes, required source data, schema, ACL and active-effect uncertainty, protecting the new store generation from stale clients/workers.

A timeout after an external write may be `UNKNOWN`. Lease expiration alone does not terminate the remote worker, and fencing within Strategy Box cannot retroactively cancel an external API lacking a matching idempotency/receipt facility.

## 6. Observability and diagnostic privacy have several owners

| Observation | Scientific meaning and recipient |
| --- | --- |
| **Domain/Event** | Product fact and causal Work/Run/Artifact revision; durable when important |
| **Progress** | Measured stage/counter/unit or indeterminate; may be sampled/coalesced |
| **DiagnosticFinding** | Read-only result of health/schema/source inspection, with completeness limits |
| **ProblemOccurrence** | One registered incident/problem fact with owner, scope, safe code and evidence ref |
| **Condition** | Aggregated ongoing resource problem affecting appropriate users |
| **TechnicalLog/Evidence** | Process/per-Attempt traces and bounded physical logs for privileged troubleshooting |
| **AuditRecord** | Actor, permission, approval and material effect record, retention and integrity |
| **Notification** | Addressed user attention with delivery/acknowledgment, not source event |

An AppDock platform ProblemRef is valid only if the external platform recorder actually confirmed registration. A proposed product→platform adapter can result in confirmed, not-written or unknown outcome; it must never create a fake confirmed identifier. Platform process health is not a bank domain failure, while a SORS validation warning does not necessarily warrant a Node-wide platform incident.

A shared Data-root failure may produce one user-safe Condition and multiple affected Runs, with recipient-filtered notices. It does not justify broadcasting raw tracebacks, filenames, credentials or report bodies. Redact **before** crossing a trust boundary; a Web UI's final-layer filter is too late.

Logging failure itself is a health event. Optional debug sink loss may degrade a read-only job without fabricating its failure, but failure to commit **mandatory audit/effect evidence** must block an unsafe action. Diagnostic inspections should be read-only; repair needs its own authorized effect Plan and audit. A SupportBundle is a permissioned, bounded export with a redaction report and provenance, not a convenient zip of all private user files.

## 7. Identity, concurrency and durable state invariants

Rights depend on **Principal × Action × Resource × EffectClass × Time × PolicyRevision**, plus optional approved exact plan/delegation. Installed/discovered/bound/ready Capability and visible UI menu do not grant a per-object mutation. Per-user `ReadCursor` is distinct from a shared Event body; raw `node_seq` gaps may reveal private events, so subscribed clients require authorized opaque cursors.

Four independent concurrency domains:
- State: competing revisions to Work/Assignment/Artifact metadata;
- Resource: conflicting reads and writes to actual data/output;
- Worker custody: one Job and competing Attempt executors/fencing;
- Publication: multiple produced candidates for one committed Artifact generation.

Resource locks are not worker leases and are not permissions. Idempotent logical admission, retrying a worker Attempt, intentionally starting a new Run and reusing a verified computation are different operations. An admission key reused with *different request digest* should conflict explicitly. Full external exactly-once cannot be inferred from deduping a submit command.

Durable state comprises transactional accepted Work/Run/Job, effect intents, rights/revisions, automation occurrences, output manifests and significant events. Projections, presence snapshots, search and device layout have weaker lifetimes. A safe schema migration has a pre-migration backup, exclusive authority, checked transformation, postcondition verification and refusal to write unknown formats. The no-backward-API-compatibility rule does not authorize quietly losing meaningful old user data.

## 8. Resource budgets and accessibility are operational safety

Large banking datasets, nested archives, Excel writers and SORS optimizers may exhaust RAM, disk or CPU. A whole-object `copy()` and seek-emulated `BytesIO` can conceal memory use; backend capabilities must explicitly say whether streaming, range, seek, conditional replacement, multipart and spill-to-disk are real. A source image/ZIP may contain hostile sizes/paths. Per-Operation resource estimates, budget confidence and workload-specific limits remain **proposed**, with no measured global SLO.

Useful actual measurements: fetch size/time/retries; decompression ratio and entry count; solver topology/iterations/RAM; staging and publish latency; Job queue age; event backlog; virtualized list/preview memory; Android network/battery/offline cache; readiness and audit backlog. There are **no source-supported numeric promises** of latency, 99.99% availability or a maximum RAM class.

Accessibility is a correctness safeguard for potentially destructive work. Test keyboard-only focus/order, icon/control labels, high contrast, screen-reader state, non-color errors, reduced motion, preserved form drafts/scroll, safe confirmation on phone, and display of `UNKNOWN` without a misleading success/failure animation. Locale formatting must not alter domain bank entity IDs, economic units or UTC/IANA scheduler semantics.

## 9. The independent Topic-08 source's test and decision registers

The full source has **50 candidate `SB-Q` invariants**, grouped into five explicit namespaces:

| Group | Number | What is tested |
| --- | ---: | --- |
| `SB-Q-T01..T08` — semantic truth | **8** | Typed missing/unavailable, five success meanings, partial/unknown, unique terminal state, identity |
| `SB-Q-E01..E12` — effects/concurrency | **12** | Immutable destructive plan, copy-before-delete, dedup vs digest, fencing, cancellation, schedule uniqueness, reconciliation |
| `SB-Q-D01..D10` — durable state/artifacts | **10** | UI independence, verified publication, corruption, schema/backup, source and retention |
| `SB-Q-S01..S10` — security/audience | **10** | Actual ACL/approval, machine scope, private stream/paths, provider trust, mandatory audit |
| `SB-Q-O01..O10` — observability/UX | **10** | Causality, redaction, safe ProblemRefs/Conditions, diagnostic vs repair, telemetry failures, accessibility, version drift |

Additionally, **20 `C08-01..20` conflicts** classify current/source semantics versus target, **18 `R08-01..18` prioritized risks** distinguish static observed defects from unverified deployment impact, **36 `F01..F36` specific fault-injection scenarios**, and **26 `G08-01..26` open implementation/Product decisions**. Those are *four different registers*, not 100+ proofs that the current implementation meets them.

Important negative test selection for a first genuine qualification slice:
- Existing empty directory vs missing vs wrong type and network denied;
- ZIP path traversal/expansion, absolute and symlink escape;
- Staging interrupted by disk full, DB/catalog gap and restored backup missing Artifact bytes;
- Same idempotency key with identical versus conflicting payload;
- Lost ACK after actual external publish and zombie worker race;
- Two principals with private/public Work; revoked approval while queued;
- Corrupted state and unknown schema version on startup;
- Scheduled occurrence through DST and process restart;
- Unavailable mandatory audit sink vs optional debug sink;
- Revised publication at same filename, mismatched IFRS/RAS perimeter;
- Actual keyboard/screen reader/reduced motion; mismatched installed release tuple.

All were **specified as future tests, not run** by the original author or this article. Each true TestResult should itself record code/build/fixture/storage/OS revisions and observed evidence; a paper checklist is not a passing certification. In Topic08's dated prioritization, installation graph/version semantics and actual typed FileStore problems require attention before claiming safe shared-host/Web/AI rollout.

## 10. Physical trust, storage and policy alternatives remain open

An early 03 research preference was SQL-backed authoritative state and current tables+events+outbox; a later 04 source records a user-acceptable managed **file-first** single-writer/journal path until an external platform provisions stronger storage. The common duty is proved transition/idempotency/backup/effect certainty under declared profile, **not** choosing SQLite merely because it appeared in more studies. Likewise choice of headless process/repository, optional CAS, OTel collector, support-bundle protocol, security IAM, isolation and access roles needs real Product/Operations decisions.

The separate Topic09 Whole-System study said that *at its original preparation* Topic08 was not found and used a provisional §12 bridge. The frozen source tree contains this actual Topic08 study; that historical remark is evidence of **authoring sequence**, not grounds to ignore the primary 50-invariant/36-fault test matrix.

**Source coverage and reopening conditions:** revisit when actual code changes, exact platform contract revision, user-approved deployment/retention model, measured resource needs, security/fault-injection evidence or a failed source-to-Science conservation check materially alters the claim. Full deployment-safe status, WCAG/ASVS conformity and global source lossless conservation remain unverified.

## 11. Exact research-source assurance matrix: fifty falsifiable candidates

The frozen independent Topic 08 original, §10 (`#L795-L875`) contains **50 explicitly enumerated candidate invariant/test pairs**. They are translated into English below with stable original IDs and exact source-line links. The translations retain the bounded original meaning and negative fixture; they are **not verbatim text reproductions**, and the frozen primary original remains the wording authority. A five-axis thematic summary alone would lose material negative fixtures. **These are dated Research proposals**, not adopted `SB-Q-*` release policy IDs, not executed tests, not proof of cross-owner implementation and not a blanket demand that a pure standalone Python calculation implement user authentication and durable Work.

### Semantic/result truth — 8 source items

| Proposed research ID | English rendering of source invariant | English rendering of original negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-T01` | A transport failure must not become a successful empty result. | Backend timeout during listdir must produce a typed failure, not [] | L803 (`#L803`) |
| `SB-Q-T02` | NotFound, PermissionDenied, Unavailable, Unsupported and WrongType must remain distinct. | Exercise a FileStore / HTTP / codec error matrix | L804 (`#L804`) |
| `SB-Q-T03` | Execution, effect, domain qualification and Work acceptance have separate statuses. | Successful export with invalid comparability leaves Work awaiting review | L805 (`#L805`) |
| `SB-Q-T04` | Semantic UNKNOWN must not silently become default 0, False or empty. | A missing officially published value remains missing, not zero | L806 (`#L806`) |
| `SB-Q-T05` | Presentation must not strengthen provenance or evidence tier. | UI must not present weak reconstruction as an official fact | L807 (`#L807`) |
| `SB-Q-T06` | A Job terminal outcome is committed at most once. | Concurrent cancel/success attempts produce one terminal record | L808 (`#L808`) |
| `SB-Q-T07` | PARTIAL requires explicit policy and a residual-work ledger. | Failure to write one of five files cannot yield global success | L809 (`#L809`) |
| `SB-Q-T08` | Operation definition, binding, invocation and Attempt retain different identities. | Repeat/retry preserves distinct history | L810 (`#L810`) |

### Effect and resource concurrency — 12 source items

| Proposed research ID | English rendering of source invariant | English rendering of original negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-E01` | A destructive plan identifies exact scope, revision and postconditions. | Reject a target plan changed after approval | L816 (`#L816`) |
| `SB-Q-E02` | Do not delete source after failed copy or verification. | Inject failure on the Nth file of a directory | L817 (`#L817`) |
| `SB-Q-E03` | Partial physical deletion cannot be confirmed as full success. | One denied remove yields PARTIAL/FAILURE with receipts | L818 (`#L818`) |
| `SB-Q-E04` | Deduplicate retry of identical command by key and request digest. | Duplicate Submit creates no second Job | L819 (`#L819`) |
| `SB-Q-E05` | Reject one idempotency key reused with a different request digest. | Key collision yields a conflict | L820 (`#L820`) |
| `SB-Q-E06` | A timeout following an irreversible effect must not cause blind retry. | Simulate delayed acknowledgment | L821 (`#L821`) |
| `SB-Q-E07` | An expired worker must not publish under its former fencing generation. | Race a zombie worker against successor | L822 (`#L822`) |
| `SB-Q-E08` | Coordinate resource conflicts outside the UI without global serialization. | Allow concurrent READ, block conflicting WRITE | L823 (`#L823`) |
| `SB-Q-E09` | Cancellation request and terminal cancellation are separate facts. | Cancel after committed success does not change outcome | L824 (`#L824`) |
| `SB-Q-E10` | One logical scheduled occurrence must not create two effectful Runs. | Crash between enqueue, acknowledgment and restart | L825 (`#L825`) |
| `SB-Q-E11` | Remote execution receives no greater authority than the admitted binding. | Revoke policy while a Run is active | L826 (`#L826`) |
| `SB-Q-E12` | Unknown external effect retains reconciliation evidence. | Partition network before acknowledgment | L827 (`#L827`) |

### Durability and Artifact — 10 source items

| Proposed research ID | English rendering of source invariant | English rendering of original negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-D01` | The UI is not authoritative for durable Work/Job truth. | Close Windows/Web and reconnect | L833 (`#L833`) |
| `SB-Q-D02` | Committed Artifacts reference verified bytes and manifest. | Digest mismatch causes quarantine | L834 (`#L834`) |
| `SB-Q-D03` | Incomplete staged bytes are never published as a completed Artifact. | Fill disk during XLSX writing | L835 (`#L835`) |
| `SB-Q-D04` | Path, filename and mtime are insufficient for full Artifact/Source identity. | Reuse same filename with different bytes | L836 (`#L836`) |
| `SB-Q-D05` | Broken or corrupt durable state does not silently become a new empty store. | Truncated JSON/database triggers degraded status | L837 (`#L837`) |
| `SB-Q-D06` | State transition and event/outbox must commit atomically within one authority scope. | Crash between the two logical updates | L838 (`#L838`) |
| `SB-Q-D07` | Detect incompatible persisted schema before admitting mutations. | Upgrade while old schema remains | L839 (`#L839`) |
| `SB-Q-D08` | Backup covers a coherent recoverability set. | Restoring DB without required Artifact bytes fails explicitly | L840 (`#L840`) |
| `SB-Q-D09` | Retention never deletes published bytes that are still referenced. | Run garbage collection with shared references | L841 (`#L841`) |
| `SB-Q-D10` | Material Results retain source, registry and algorithm version access. | Reconstruct a historical report | L842 (`#L842`) |

### Security and audience — 10 source items

| Proposed research ID | English rendering of source invariant | English rendering of original negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-S01` | Effective permission is checked by the actual authority, not only UI. | Forge API command despite disabled button | L848 (`#L848`) |
| `SB-Q-S02` | Approval is scoped to exact plan, effect, target and version. | Changed destructive targets require new approval | L849 (`#L849`) |
| `SB-Q-S03` | AI and automation receive no unrestricted or permanent grants by inference. | Revoke permission before a scheduled occurrence fires | L850 (`#L850`) |
| `SB-Q-S04` | Clients cannot access others' raw logs, paths, Artifacts or secrets. | Two-user ACL and subscription matrix | L851 (`#L851`) |
| `SB-Q-S05` | Provider discovery is distinct from trusted activation. | Malicious descriptor must not activate itself | L852 (`#L852`) |
| `SB-Q-S06` | Public core and client surfaces remain independent of particular nonpublic implementation internals. | Run static dependency/import scan | L853 (`#L853`) |
| `SB-Q-S07` | Untrusted source content never becomes an executable instruction merely by being read. | Prompt injection in PDF/HTML metadata | L854 (`#L854`) |
| `SB-Q-S08` | User-controlled filesystem references cannot escape the authorized namespace. | Parent traversal, absolute path, symlink/junction escape | L855 (`#L855`) |
| `SB-Q-S09` | Required audit/effect record is durable before destructive commit. | Unavailable audit sink denies the operation | L856 (`#L856`) |
| `SB-Q-S10` | Filter published projections for audience before transport. | Event stream containing another user's objects and cursor | L857 (`#L857`) |

### Observability and operations — 10 source items

| Proposed research ID | English rendering of source invariant | English rendering of original negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-O01` | Every Job/Attempt has recoverable causal lineage. | Inspect failed Attempts after worker crash | L863 (`#L863`) |
| `SB-Q-O02` | Raw traceback is diagnostic evidence, not durable product state. | Serialized state schema refuses raw exception object | L864 (`#L864`) |
| `SB-Q-O03` | Do not invent a confirmed ProblemRef when problem recording failed or is unknown. | Simulate recorder timeout | L865 (`#L865`) |
| `SB-Q-O04` | Shared faults reach affected users as safely scoped Conditions. | Shared backend outage with audience/privacy matrix | L866 (`#L866`) |
| `SB-Q-O05` | A diagnostic check does not secretly perform repair. | Offline diagnostic mode is read-only | L867 (`#L867`) |
| `SB-Q-O06` | Telemetry loss is distinct from business terminal truth. | Log sink fails during a successful read | L868 (`#L868`) |
| `SB-Q-O07` | User-visible state is explained in accessible text, not color/motion alone. | Screen reader and reduced-motion modes | L869 (`#L869`) |
| `SB-Q-O08` | Progress never claims fabricated completeness. | Unknown total or stalled stage | L870 (`#L870`) |
| `SB-Q-O09` | Release checks detect contract/version drift before distribution. | Manifest/tests/package version tuple mismatch | L871 (`#L871`) |
| `SB-Q-O10` | System degrades safely when storage, configuration or readiness fails. | Database unavailable triggers diagnostic-only boot | L872 (`#L872`) |

### Reconciliation and reliance limits

1. **Materiality/profile:** for a pure function without external effects, a server-side permission or durable Job invariant may be inapplicable. For a public Web client, local shared-team nickname trust is insufficient to meet genuine object/operation authorization.
2. **Coherence with earlier Topic 09:** its §12 was explicitly provisional while a dedicated Topic 08 was absent from the *author's then-current source set*. Topic 08 now exists and supplies a stronger qualified threat model, a 50-test matrix and 26 open Decision/Gap records. It refines, but does not retrospectively convert, Topic 09 architecture proposals into Product commitments.
3. **Current code defect versus target policy:** the frozen `LocalFileStore.listdir` indeed maps a missing/non-directory path to `[]`; direct source reading supports that narrow observation. Assertions of swallowed **all** exceptions or actual network-backend behavior are not warranted. A future high-risk user-facing operation needs scoped error/effect semantics, subject to admission.
4. **Counterexamples remain:** unsafe fallback, stale source vintage, unknown external effect, unverified artifact publication, model-generated proposal presented as Decision, inaccessible diagnostic sink and ignored user permissions are different negative results, not one global `OK/FAIL` flag.

**Conservation status:** **50 exact invariant/negative-case pairs** from a frozen original have new direct maintained Science destinations. This is a producer source-text preservation check, **not** independent proof of scientific soundness, exhaustiveness of Topic 08, or any current passing conformance report.

## 12. Thirty-six exact-identified Topic 08 fault-injection scenarios

**Source-preserving Research supplement, not completed tests or Product admission.** These 36 source-identified scenarios come from the same original Topic 08 and belong in this existing canonical qualities and assurance article, not in a second parallel Science owner.

Original Trust, Safety & System Qualities, §13.2 (`#L961-L1001`). These 36 `Fxx` tests were **proposed**, not executed. Their exact source identity is preserved; descriptions below are **English interpretations** and retain each negative-case expectation. Actual applicability differs among pure Python, local Windows and remote shared-host profiles.

| Source fixture | Injection / setup | Evidence expected by Research | Source line |
| --- | --- | --- | --- |
| `F01` | List an existing, truly empty directory | Successful empty response with observed directory presence | L965 (`#L965`) |
| `F02` | List an absent directory | Typed NotFound, not a successful empty list | L966 (`#L966`) |
| `F03` | List a file path as though it were a directory | WrongType, not successful empty result | L967 (`#L967`) |
| `F04` | Fail network/permission access to a statistical source | Distinct typed error; never claim no data | L968 (`#L968`) |
| `F05` | Serve HTML/error page in place of a workbook | Validate/reject inappropriate payload | L969 (`#L969`) |
| `F06` | Inject corrupt ZIP, parent traversal or decompression expansion bomb | Reject safely, enforce path and resource budget | L970 (`#L970`) |
| `F07` | Supply parent traversal, absolute path, or symlink/junction escape | Enforce authorized workspace bounds per platform | L971 (`#L971`) |
| `F08` | Fail during the Nth file of directory copy | Retain source, quarantine partial destination, no success | L972 (`#L972`) |
| `F09` | Fail one removal during recursive destructive cleanup | Per-object residuals, never full completion | L973 (`#L973`) |
| `F10` | Fail while streaming an XLSX writer | Abort/reconcile staged bytes, no exposed incomplete Artifact | L974 (`#L974`) |
| `F11` | Fill disk after bytes publication before catalog commit | Reconciler resolves orphan bytes/intent | L975 (`#L975`) |
| `F12` | Corrupt artifact bytes despite committed database row | Digest mismatch and explicit damaged state | L976 (`#L976`) |
| `F13` | Submit same command twice with same idempotency digest | Exactly one Job/Run per admitted scope | L977 (`#L977`) |
| `F14` | Reuse idempotency key with a different request digest | Conflict rather than misleading reuse | L978 (`#L978`) |
| `F15` | Lose acknowledgement after successful remote publication | UNKNOWN effect; inspect receipt; do not blindly retry | L979 (`#L979`) |
| `F16` | Race workers with two fencing generations | Stale generation cannot publish | L980 (`#L980`) |
| `F17` | Two users mutate/rename the same resource concurrently | Revision or serialization conflict at authority | L981 (`#L981`) |
| `F18` | Crash between Run-to-Job transition and event/outbox append | Transactional consistency; recoverable event | L982 (`#L982`) |
| `F19` | Corrupt persisted JSON/state database | Diagnostic degraded state, no silent empty reset | L983 (`#L983`) |
| `F20` | Upgrade against unknown persisted schema | Refuse/controlled migration while retaining old state | L984 (`#L984`) |
| `F21` | Restore only DB, omitting referenced artifact blobs | Coherence failure with missing refs, no green health | L985 (`#L985`) |
| `F22` | Revoke permission while automation awaits execution | Recheck and deny at authoritative effect boundary | L986 (`#L986`) |
| `F23` | AI proposes an unauthorized destructive plan | Reject or await scoped approval | L987 (`#L987`) |
| `F24` | Leak another user's events into subscription stream | Filter before transport and protect cursor scope | L988 (`#L988`) |
| `F25` | Close client UI while a host-managed Job executes | Host Job continues; reconnect by same identities (host profile only) | L989 (`#L989`) |
| `F26` | Race terminal success with a late cancel request | One committed terminal outcome, no successful-to-cancelled rewrite | L990 (`#L990`) |
| `F27` | Restart scheduler at exact due occurrence boundary | Occurrence/effect identity prevents duplicates | L991 (`#L991`) |
| `F28` | Exercise repeated or nonexistent daylight-saving local hour | Deterministic timezone/misfire occurrence policy | L992 (`#L992`) |
| `F29` | Lose mandatory audit recorder during dangerous action | Deny before irreversible effect | L993 (`#L993`) |
| `F30` | Lose optional debug-log sink during safe read-only Job | Degraded diagnostics while business truth remains honest | L994 (`#L994`) |
| `F31` | Attempt expensive whole-object decoding of huge input | Budgeted/spill-to-disk or controlled failure, not unbounded OOM | L995 (`#L995`) |
| `F32` | Change official source bytes under unchanged file name | New source version; historical Results keep old dependency | L996 (`#L996`) |
| `F33` | Use screen reader and reduced motion during run, error and cancellation | Full textual/accessible state without relying on color/motion | L997 (`#L997`) |
| `F34` | Distribute incompatible package/manifest contract tuple | Reject activation with explicit diagnostics | L998 (`#L998`) |
| `F35` | Compare IFRS versus RAS figures from different reporting perimeters | Qualify domain comparability before a conclusion | L999 (`#L999`) |
| `F36` | Telemetry recorder reports OUTCOME_UNKNOWN | No invented confirmed ProblemRef; safe unknown recovery | L1000 (`#L1000`) |

**Discriminating evidence:** any claim that a fixture *passed* requires runner/release versions, injected fault, actual input/environment, observed output and a failure-capable oracle. A table of expected properties alone does not constitute a test implementation. Some host durability tests are deliberately inapplicable to a local foreground profile; a documented `NOT_APPLICABLE` disposition with evidence is stronger than assuming the system passed.
