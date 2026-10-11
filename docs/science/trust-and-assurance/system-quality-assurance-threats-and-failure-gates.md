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

The frozen independent [Topic 08 original, §10](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L795-L875) contains **50 explicitly enumerated candidate invariant/test pairs**. They are reproduced below with full original wording and source line, because a five-axis thematic summary alone loses material negative fixtures. **These are dated Research proposals**, not adopted `SB-Q-*` release policy IDs, not executed tests, not proof of cross-owner implementation and not a blanket demand that a pure standalone Python calculation implement user authentication and durable Work.

### Semantic/result truth — 8 source items

| Proposed research ID | Source-exact invariant | Source-exact negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-T01` | Ошибка транспорта не становится успешным пустым результатом | backend timeout during `listdir` → typed failure, не `[]` | [L803](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L803) |
| `SB-Q-T02` | `NotFound`, `PermissionDenied`, `Unavailable`, `Unsupported`, `WrongType` различаются | matrix для FileStore/HTTP/codec | [L804](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L804) |
| `SB-Q-T03` | Execution, effect, domain qualification и Work acceptance имеют разные статусы | successful export + invalid comparability → Work awaiting review | [L805](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L805) |
| `SB-Q-T04` | Семантическое `UNKNOWN` не заменяется default `0/False/empty` | отсутствует официальное значение → missingness, не zero | [L806](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L806) |
| `SB-Q-T05` | Representation не повышает provenance/evidence tier | UI не показывает слабую реконструкцию как официальный факт | [L807](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L807) |
| `SB-Q-T06` | Terminal outcome Job коммитится не больше одного раза | конкурентные cancel/success → один terminal record | [L808](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L808) |
| `SB-Q-T07` | `PARTIAL` возможен только при явном policy и residual ledger | один файл из пяти не записан → нет global success | [L809](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L809) |
| `SB-Q-T08` | Определение операции, binding, invocation и Attempt имеют разные ID | repeat/retry не теряют историю | [L810](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L810) |

### Effect and resource concurrency — 12 source items

| Proposed research ID | Source-exact invariant | Source-exact negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-E01` | Destructive plan идентифицирует точный scope, revision и postconditions | изменённый plan после approval отклоняется | [L816](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L816) |
| `SB-Q-E02` | Source не удаляется после неуспешного copy/verify | fault injection в N-й файл каталога | [L817](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L817) |
| `SB-Q-E03` | Частичное физическое удаление не возвращает подтверждённый full success | один `remove` denied → PARTIAL/FAILURE с receipts | [L818](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L818) |
| `SB-Q-E04` | Команда повторяется безопасно по key + request digest | duplicate Submit не создаёт второй Job | [L819](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L819) |
| `SB-Q-E05` | Та же idempotency identity с другим request digest отклоняется | key collision → conflict | [L820](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L820) |
| `SB-Q-E06` | Timeout после необратимого эффекта не вызывает blind retry | delayed ACK simulation | [L821](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L821) |
| `SB-Q-E07` | Expired worker не публикует под старой fencing generation | zombie-worker races | [L822](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L822) |
| `SB-Q-E08` | Resource conflicts координируются вне UI и без глобальной сериализации | concurrent READ разрешены; конфликтующие WRITE блокируются | [L823](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L823) |
| `SB-Q-E09` | Cancel request и terminal cancellation — разные факты | cancel после commit не меняет success | [L824](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L824) |
| `SB-Q-E10` | Один logical schedule occurrence не рождает два effectful Runs | crash between enqueue/ack/restart | [L825](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L825) |
| `SB-Q-E11` | Удалённый executor не получает больший authority, чем разрешённый binding | policy revocation during run | [L826](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L826) |
| `SB-Q-E12` | Неизвестный внешний эффект оставляет reconciliation evidence | network partition before ACK | [L827](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L827) |

### Durability and Artifact — 10 source items

| Proposed research ID | Source-exact invariant | Source-exact negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-D01` | UI не владеет durable Work/Job truth | закрытие Windows/Web, reconnect | [L833](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L833) |
| `SB-Q-D02` | Committed artifact ссылается на верифицированные bytes/manifest | mismatch digest → quarantine | [L834](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L834) |
| `SB-Q-D03` | Неполная staged запись не публикуется как completed artifact | disk full during XLSX writer | [L835](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L835) |
| `SB-Q-D04` | Path/name/mtime не являются полной artifact/source identity | одинаковый filename с новыми bytes | [L836](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L836) |
| `SB-Q-D05` | Broken/corrupt durable state не превращается в пустой новый store | truncated JSON/DB fault → degraded | [L837](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L837) |
| `SB-Q-D06` | State transition + event/outbox commit атомарны в scope authority | crash between two logical updates | [L838](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L838) |
| `SB-Q-D07` | Persisted schema несовместимость видна до mutating work | upgrade with old schema version | [L839](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L839) |
| `SB-Q-D08` | Backup содержит полный согласованный recoverability set | restore DB без artifact bytes → explicit failure | [L840](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L840) |
| `SB-Q-D09` | Retention не удаляет ещё referenced published bytes | GC under shared artifact references | [L841](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L841) |
| `SB-Q-D10` | Source/registry/algorithm versions доступны из существенного Result | reproduce historical report | [L842](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L842) |

### Security and audience — 10 source items

| Proposed research ID | Source-exact invariant | Source-exact negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-S01` | Effective permission проверяется в authority, не в UI | forged API command despite disabled button | [L848](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L848) |
| `SB-Q-S02` | Approval связана с конкретным plan/effect/scope/version | changed destructive targets → new approval | [L849](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L849) |
| `SB-Q-S03` | AI/Automation не наследует бессрочные или неограниченные grants | revoke permission then fire occurrence | [L850](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L850) |
| `SB-Q-S04` | Client не получает чужие raw logs, paths, artifacts и secret data | two-user ACL/fetch subscription matrix | [L851](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L851) |
| `SB-Q-S05` | Provider discovery не равен trusted activation | malicious descriptor cannot self-activate | [L852](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L852) |
| `SB-Q-S06` | Публичные core/surface не зависят от конкретных закрытых реализаций | static dependency/import scan | [L853](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L853) |
| `SB-Q-S07` | Untrusted source content никогда не становится executable instruction | prompt injection in PDF/HTML metadata | [L854](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L854) |
| `SB-Q-S08` | User-controlled filesystem references не выходят за разрешённый namespace | `../`, absolute, symlink/junction escape | [L855](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L855) |
| `SB-Q-S09` | Обязательная audit/effect запись предшествует destructive commit | unavailable audit sink → action denied | [L856](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L856) |
| `SB-Q-S10` | Опубликованная projection фильтруется до transport | event feed с чужими объектами и cursor | [L857](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L857) |

### Observability and operations — 10 source items

| Proposed research ID | Source-exact invariant | Source-exact negative test | Source line |
| --- | --- | --- | --- |
| `SB-Q-O01` | Каждый Job/Attempt имеет восстанавливаемую причинную цепочку | inspect failures after worker crash | [L863](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L863) |
| `SB-Q-O02` | Raw exception/traceback — evidence, а не durable product state | serializable state schema rejects exception | [L864](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L864) |
| `SB-Q-O03` | Confirmed ProblemRef не выдумывается при failed/unknown recorder | simulated recorder timeout | [L865](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L865) |
| `SB-Q-O04` | Общий сбой показывается affected users через safe Condition | shared backend outage; privacy matrix | [L866](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L866) |
| `SB-Q-O05` | Diagnostic check не скрытно исполняет Repair | offline diagnostics must be read-only | [L867](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L867) |
| `SB-Q-O06` | Потеря telemetry отмечается отдельно от business terminal truth | log sink crash during successful read | [L868](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L868) |
| `SB-Q-O07` | User status объясняется доступным текстом, не только цветом/анимацией | screen reader/reduced motion mode | [L869](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L869) |
| `SB-Q-O08` | Progress не объявляет выдуманную полноту | unknown total, stalled stage | [L870](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L870) |
| `SB-Q-O09` | Contract drift ловится release test до distribution | manifest/tests/package tuple mismatch | [L871](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L871) |
| `SB-Q-O10` | Система безопасно деградирует при storage/config/health failure | DB unavailable; diagnostic-only boot | [L872](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md#L872) |

### Reconciliation and reliance limits

1. **Materiality/profile:** for a pure function without external effects, a server-side permission or durable Job invariant may be inapplicable. For a public Web client, local shared-team nickname trust is insufficient to meet genuine object/operation authorization.
2. **Coherence with earlier Topic 09:** its §12 was explicitly provisional while a dedicated Topic 08 was absent from the *author's then-current source set*. Topic 08 now exists and supplies a stronger qualified threat model, a 50-test matrix and 26 open Decision/Gap records. It refines, but does not retrospectively convert, Topic 09 architecture proposals into Product commitments.
3. **Current code defect versus target policy:** the frozen `LocalFileStore.listdir` indeed maps a missing/non-directory path to `[]`; direct source reading supports that narrow observation. Assertions of swallowed **all** exceptions or actual network-backend behavior are not warranted. A future high-risk user-facing operation needs scoped error/effect semantics, subject to admission.
4. **Counterexamples remain:** unsafe fallback, stale source vintage, unknown external effect, unverified artifact publication, model-generated proposal presented as Decision, inaccessible diagnostic sink and ignored user permissions are different negative results, not one global `OK/FAIL` flag.

**Conservation status:** **50 exact invariant/negative-case pairs** from a frozen original have new direct maintained Science destinations. This is a producer source-text preservation check, **not** independent proof of scientific soundness, exhaustiveness of Topic 08, or any current passing conformance report.
