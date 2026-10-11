# Shared state consistency, restore generations, backup epochs and retention

**Domain:** the consistency obligations of one authoritative Strategy Box application store when it has user work, scheduled occurrences, independent file effects, event delivery, artifact manifests and multiple clients. **Status:** evidence-qualified engineering Science and unresolved design alternatives. The examined [Windows history writer](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) is a local five-JSON implementation, **not** a certified shared transactional database. See also [file-state and crash recovery alternatives](authority-durability-and-recovery.md) and [authorized event cursors](../collaboration/authorized-streams-read-cursors-and-private-work.md).

## 1. Three different truth classes can share one disk without sharing an authority

**Authoritative state** is accepted Work/Run/Job, exact revisions, assignments, approvals, schedule occurrences, artifact catalog lifecycle and permission decisions. **Recoverable projections** are counters, cached UI lists, search indexes and some progress views. **Local convenience state** is geometry, current tab or resettable draft. A single SQL store is not a logical requirement for all these types; five independently overwritten JSON files are not a reliable unified authority either.

For each state family record **owner, identity, scope, lifetime, mutability, concurrency, storage requirements, recovery policy and authorized projection**. One Node may contain several workspaces or access levels. One authority writer can commit many short state transitions while several independent data calculations execute in parallel. A Node directory is a physical locator; it is not an authorization protocol.

The [pinned Windows case/event/history code](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application) does not demonstrate one atomic group write across cases, events, artifacts, logs and assignments; malformed history can appear empty. Such a fallback may be acceptable for a disposable cache with a visible diagnostic, never as the silent answer for valuable committed Work.

## 2. State writer, DB tables, journal, outbox and effect publisher are distinct

A **single logical writer** accepts commands under verified principal/resource rights and revision constraints; it may be in one desktop process or in an actual host service. A shared directory readable by Windows and Android is **not** the application command/query/subscription API.

The source's early preferred physical design was current aggregate tables plus append-only application events and an outbox in local SQLite, with later PostgreSQL when justified. This has two advantages: transactional multi-aggregate admission and cheap queries on current state. But it also requires migrations, backup, concurrency policies, reliable storage and actual platform binding. A **later user-origin clarification explicitly permits verified file-backed state** (single versioned atomic snapshot or append journal plus snapshots) before provisioning SQL through AppDock. These are incompatible physical preferences but compatible logical invariants. **No backend is adopted**.

Full event sourcing is a different, more expensive architecture: every current value must be reconstructible from actual complete event semantics and migration/upcasting rules. A system with event history plus independently authoritative current tables **must not claim full replay** without proof. Conversely a notification outbox does not automatically make job state reconstructible.

An illustrative commit path:

```text
authenticate principal → authorize object/effect → check expected_revision/idempotency
  → validate semantic definition and immutable plan
  → under one proven logical commit: record state transition + event + outbox identity
  → acknowledge actual persisted revision, else outcome uncertain
  → asynchronously deliver event with stable ID; consumer deduplicates
```

Event schema version, store schema version, object revision, Node commit sequence, output content version and platform activation version are **different dimensions**. A schema name in a SQL example is not an implemented API.

**A subtle example of false uniqueness:** `UNIQUE(job_id, terminal_outcome_kind)` does *not* prohibit one SUCCESS row and one FAILED row for a Job; it only prohibits a duplicate of the same pair. The correct physical implementation needs one terminal record per Job or an atomic guarded transition. Likewise a time-expired lease does not prevent a former worker from still writing; an effect destination must enforce current fencing/generation where takeover is possible.

## 3. Artifact manifest, catalog and raw bytes have separate fields of authority

An immutable artifact **manifest** can be authoritative for content digest, list of parts, source lineage and producer version. An application **catalog** is authoritative for viewer rights, Work links, favorite/pin state, logical deletion and lifecycle. A physical storage **object** witnesses bytes under a provider-specific consistency promise, but grants neither permission nor completion of a financial analysis.

A possible publication trace is:

```text
effect intent/admitted Artifact ID → run-scoped staging
  → write/close/validate bytes → immutable manifest with digest
  → publish under actual backend guarantees
  → commit catalog version/status/event/outbox
  → reconcile any orphan bytes or catalog gap
```

If bytes commit but the metadata transaction fails, catalog visibility remains unconfirmed; a reconciler may finish under valid evidence or quarantine the object. An older published version must not be overwritten by a failed staging candidate. If the only copy of a source needed for replay resides in a supposedly disposable cache, its deletion weakens the effective evidence guarantee: either pin it or downgrade the claimed replay availability.

**Database rebuild limitations:** manifests can reconstruct a content-catalog subset; they generally cannot reconstruct private messages, ACL revisions, assignments, read receipts or approvals unless those were explicitly preserved. “The DB is always recoverable from artifact manifests” is false without a tested complete source-of-truth map.

## 4. Cross-store backup requires a consistent boundary, not two independent archives

A backup of current application metadata and an unrelated copy of `/output` can describe different moments. A managed restore set may need: schema/generation/Store ID and stable metadata snapshot; still-required immutable Artifact manifests and verified bytes; retained source snapshots for promised replay; user/policy data and receipts; appropriate secret **references**; and a `BackupReceipt` describing exact coverage/revisions and checksums.

A **candidate backup epoch protocol**:

1. Establish a consistent metadata revision or briefly pause new publish/catalog mutations.
2. Record immutable Artifact generations and source snapshots required by that revision.
3. Take a consistent metadata snapshot using a supported backend mechanism (for live SQLite, its documented [online backup API](https://www.sqlite.org/backup.html), not blindly copying an open database and discarding WAL).
4. Copy/verify relevant immutable bytes and manifests, or explicitly mark unmanaged user files outside backup coverage.
5. Bind the snapshot and objects to one `backup_epoch` and integrity receipt; include policy-relevant holds and schema version.
6. Validate with a restore drill on a separate non-production target, under a bounded RPO/RTO definition.

A backup receipt proving metadata alone does **not** prove user-managed XLSX bytes were backed up. The external managed deployment platform may supply storage/provision/backup mechanics, but the application defines which product records and files form a consistent recoverable set. Backup, crash restart, artifact reconciliation, availability after manual deletion and statistical input replay are separate guarantees.

## 5. Restore, clones, generations and split-brain prevention

The source highlights a dangerous non-obvious case: restoring a backup into a second node while the original is still active may execute one scheduled notification or destructive effect twice. A proposed `store_id + node_id + schema_epoch + generation + restore_epoch` identifies the actual authority at startup. An old writer or worker must be prevented from mutating the new generation.

A safe **candidate restore sequence**:
- Stop or fence the old mutation authority; verify backup scope and integrity.
- Import data into a staging location; verify schema, keys, causal links, retained Artifact bytes and critical index consistency.
- Choose explicitly between *replacement of the original*, *read-only sandbox clone* and *controlled re-identification for an authorized new deployment*.
- Create a new store generation and re-check participant identities/grants/credential bindings.
- Disable or rebind effect-capable automations in a sandbox clone; old occurrence IDs and external effect keys cannot be assumed universally safe.
- Reconcile pending Effects and interrupted Jobs, then publish new readiness and permissible commands.

A renamed folder with the same `node_id` does not become an independently safe Node. `last_heartbeat_at` and expired leases cannot prove the old worker is dead. Cross-host election, exclusive writer fencing and backup restore are physical responsibilities requiring actual deployment tests; a static architecture study cannot select HA policy.

## 6. Schema upgrades, retention and rights must preserve historical meaning

No compatibility requirement for old public Python APIs **does not imply no data migration**. One-time explicit import of valued old Case/Event JSON, with malformed-record quarantine, stable ID mapping, readback and atomic cutover, can preserve user work without permanent dual-write. A binary encountering unsupported future schema epoch should open read-only/diagnostic mode, not guess and overwrite data. A new binary lacking a verified old-data migration path similarly must refuse unsafe mutation.

Retention is class-specific, not a single `history_days`: Work/Run/Job, chat messages, event/effect receipts, source/registry snapshots, Artifact versions and bytes, notifications/cursors, diagnostic logs, backup sets, raw telemetry and disposable caches have different owners, dependencies and possible legal holds. Physical removal of an Artifact is not the same as removing a Work link or user-facing catalog entry.

A staged delete may use **authorize and inspect holds → tombstone/hide → grace period where policy permits → GC unreferenced materializations → retain narrowly permitted redacted audit evidence**. A user may deliberately move/delete an ordinary output file; a missing locator should be reported honestly without claiming that Work never existed. Search must be authorization-filtered at index/query time; indexing private titles/parameters and merely hiding result links in UI is insufficient.

Disk pressure, WAL/checkpoint growth, log rotation, outbox retry queues, segment compaction and long-running readers are operational failure domains. No user-specified quotas, retention durations or latency limits have been adopted in the studied corpus.

## 7. Twelve unresolved cross-theme holes, preserved individually

| Gap | Why it matters | Necessary future proof/decision |
| --- | --- | --- |
| **WS05-A Authorized stream** | Raw `node_seq` gaps can reveal private event existence | Two-principal filtered-feed and ACL-change test; opaque cursor |
| **WS05-B Backup epoch** | Catalog and bytes snapshots may be inconsistent | Cross-store `backup_epoch` + restore drill |
| **WS05-C Restore clone** | Two nodes might dispatch identical effects | Explicit restore mode, generation/fencing |
| **WS05-D External manual edits** | Mutable workspace output can be changed outside authority | Re-import/fingerprint/version policy, honest missing alerts |
| **WS05-E Private Work/shared Thread** | Work projection can leak private linked Thread/params | Field-level object authorization test |
| **WS05-F Receipt after compaction** | Read cursors can point outside surviving event history | Feed generation/cursor invalidation + resync |
| **WS05-G Collaboration/job split** | Two persistence adapters may create inconsistent user and Run records | One transaction where required or explicit cross-store reconciliation |
| **WS05-H Authority election** | Restart may create two scheduler leaders | Exclusive writer/lease, controlled election and fenced effects |
| **WS05-I Data erasure** | Messages, sources, evidence and audit may require incompatible retention | Legal/deployment-approved precedence and coverage |
| **WS05-J Rotating secrets** | Old immutable Run references may point to replaced credentials | Opaque secret reference with rebind or AUTH_REQUIRED state |
| **WS05-K Timezone DB change** | Recomputed future due time can reinterpret old schedule | Versioned calendar evaluation and retained admitted occurrences |
| **WS05-L External ProblemRef** | Platform problem occurrence may disappear/expire independently | Safe `PROBLEM_REF_UNAVAILABLE` product fallback |

All twelve are **still open**. Their consolidation as a table does not resolve them.

## 8. The fourteen Research conflict identities

The source's conflict register C05-01..14 contains materially different resolution levels:

- **C05-01** SQLite versus PostgreSQL can be a profile difference *within one semantic API*, without deciding current first backend; late Research adds the independent file-first option.
- **C05-02/03/06/08/13** local Case and JSON/unread/config/chat shortcuts are historical implementation facts, inadequate as future shared authority.
- **C05-04/11** manifest/content truth, application lifecycle truth and external platform Node truth coexist without a single global owner.
- **C05-05** internal Node sequence vs authorized feed cursor is a newly discovered protocol/security hole.
- **C05-07** presence is a TTL Session-derived projection rather than a permanently true Boolean.
- **C05-09** full event sourcing is unnecessary absent replay consumers; transactional current records+events/outbox is only a design candidate.
- **C05-10** a separate host repository is not justified until it has an independent runtime consumer/lifecycle.
- **C05-12** one-time persisted data migration is compatible with breaking runtime API changes.
- **C05-14** global content-addressed storage is conditional on actual workload and managed retention.

These are not fourteen independent approvals. Even the “resolved conceptually” items remain conditional on adopted profiles, current exact external contracts and tests.

## 9. Nine cross-store and collaboration failure traces

The original records nine scenario tests with different failure hypotheses:

1. **GUI closes while a host Job continues:** Node Job identity must survive a client Session; in the current local foreground profile that behavior is **not** proven or promised.
2. **Two users read the same stream:** per-user cursors diverge; filtered private events don't leak through sequence gaps.
3. **Concurrent Assignment edit:** an expected-revision conflict prevents lost updates.
4. **Scheduler restarts after outage:** a committed occurrence remains unique under its rule revision; missed-run handling follows policy.
5. **File publication before catalog commit:** reconcile verified orphan bytes and pending intent without double publication.
6. **Network loss during destructive action:** partial or unknown effect prevents blind retry.
7. **Corrupt metadata store:** diagnostic/read-only mode, never a fabricated empty Work history.
8. **Official source revised after prior report:** old Artifact retains its input snapshot and as-of context; new Run may revalidate.
9. **Restored Node clone:** new generation/identity decision fences old effect dispatch.

These are *design acceptance traces*, not results of actual fault injection.

## 10. Twenty-two falsifiable invariants and their evidence limits

The source records `ST-01..ST-22`. Their full specificity is retained here as testable criteria for a future selected deployment:

| Source IDs | Invariants |
| --- | --- |
| ST-01–04 | UI is not durable Work/Job owner; Work/Run/Attempt identities differ; shared mutation is authorized/revision-guarded; admitted command is idempotent |
| ST-05–08 | One committed Job terminal outcome; corrupted DB cannot become empty state; accepted event and state transition share real commit; retained events don't disclose secrets |
| ST-09–12 | Per-principal read receipts; presence from Session evidence; occurrence uniqueness under restart; unknown effect never blindly retried |
| ST-13–16 | Artifact has identity/manifest/verified bytes and Run; coherent backup of metadata+bytes; remote clients use API not network SQLite file; settings and managed policy authorities separated |
| ST-17–20 | Explicit persisted-schema migration and incompatibility handling; client disconnect doesn't change server Job; deletion respects refs/holds; search and feed don't reveal forbidden object existence |
| ST-21–22 | Domain, application and platform ownership survives recovery; a new process/repository requires a real lifecycle and consumer |

An edge case: `UNIQUE(job_id, terminal_outcome_kind)` allows multiple outcomes of different kinds, so cannot implement ST-05 as written by the original pseudo-DDL. A physical schema must enforce uniqueness by Job overall, not by Job+kind. Another edge: optimistic revision can prevent one lost update but never alone guarantee exactly-once effect publication across external FileStore calls.

**Actual verification status:** only selected pinned implementation paths and external technical documentation were read; no new SQL pilot, two-user network subscription, permission differential test, crash/backup restore drill, Windows/Android host handoff or disk-pressure benchmark was performed. The above is a falsifiable scientific obligation list, not the results of a completed test suite.

## 11. Source limitations and unresolved Product Decisions

The study assumes an application-controlled durable node state and recommends local SQLite in its 2026-10-09 edition. Subsequent direct user requirements, recorded in the later 04 Research, permit simpler file-first state under an external-platform-managed directory until a stable backend provider exists. Both agree on authority ownership, idempotency, effect reconciliation, controlled recovery, source/Artifact provenance and permission-safe projections, but the physical backend and lifetime of a first installed worker are **not selected**.

Further Product/Operations questions: shared scope and ACL/default visibility; exact one-Work/one-Run distinction; retention and erasure policies; who can approve/review or read logs; host versus foreground exit behavior; offline changes; source snapshot storage and artifact versioning; provisioned DB capabilities; backup scope; RPO/RTO; placement of personal settings; calendar and retry rules; measured performance/quotas; host repo/process topology; machine actor permissions; private Workspace multiplicity. The next valid milestone is a real fault-injected file/SQL/host pilot under approved conditions, not a synthetic “completed” status in documentation.

## 12. Original topic 03: fifteen state and durability trade-offs

The dated [State, Persistence and Recovery Research](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md) distinguishes state truth, scope, lifetime, durability and physical storage, and compares single-file commit with SQL-backed or event-journal approaches. The **15 English source-row interpretations** below retain its practical counterarguments. Research support is not an accepted platform storage contract, target RPO/RTO or proof that a shared StateStore already exists.

| Source ID | Source-supported distinction | Candidate implication | Frozen source line |
| --- | --- | --- | --- |
| `SB-SRC-0556/STATE-01` | A state item should be assigned an owner independently from its physical storage implementation. | `OWNER_INVARIANT` | [L135](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L135) |
| `SB-SRC-0556/STATE-02` | State scope distinguishes installation/node, user, workspace, chat, execution, source and Artifact; sharing a disk does not unify those scopes. | `SCOPE_SEGREGATION` | [L136](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L136) |
| `SB-SRC-0556/STATE-03` | Authoritative records, rebuildable projections, caches and ephemeral client state have different reliability consequences. | `TRUTH_CLASS` | [L137](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L137) |
| `SB-SRC-0556/STATE-04` | A state recovery policy can re-read, recompute, reconcile external effects or safely drop layout convenience depending on the object's role. | `RECOVERY_CONTRACT` | [L140](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L140) |
| `SB-SRC-0556/STATE-05` | Persist only information that cannot be safely regenerated or whose loss invalidates admitted user history; eternal storage is not an objective. | `RETENTION_PROPORTIONALITY` | [L175](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L175) |
| `SB-SRC-0556/STATE-06` | Chat text alone cannot prove an accepted command, effective parameters and actual execution outcome after a crash. | `CHAT_NOT_EXECUTION_LEDGER` | [L179](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L179) |
| `SB-SRC-0556/STATE-07` | G0/G1/G2/G3 durability tiers reflect different loss/rebuild/effect-reconciliation obligations, not one global 'persistent' checkbox. | `DURABILITY_TIER_SEPARATION` | [L191](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L191) |
| `SB-SRC-0556/STATE-08` | A durable record commit does not automatically provide zero data loss under total disk/power failure; backend/fsync profile and backups matter. | `DURABILITY_LIMIT` | [L196](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L196) |
| `SB-SRC-0556/STATE-09` | Analytical Data files and operational state can share a physical disk yet remain separate ownership/retention planes. | `STATE_DATA_SEPARATION` | [L219](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L219) |
| `SB-SRC-0556/STATE-10` | One atomic snapshot may be cheaper for low-write single-authority state than building a SQL service or full event journal immediately. | `PHYSICAL_ALTERNATIVE_CANDIDATE` | [L294](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L294) |
| `SB-SRC-0556/STATE-11` | File replacement guarantees depend on the actual filesystem; atomic single-file visibility does not atomically publish external XLSX and metadata together. | `CROSS_PLANE_ATOMICITY_LIMIT` | [L316](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L316) |
| `SB-SRC-0556/STATE-12` | SQLite WAL is not a safe multi-machine shared-file database merely because the file resides on a mounted network drive. | `SQLITE_FILE_SHARING_LIMIT` | [L328](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L328) |
| `SB-SRC-0556/STATE-13` | Acceptance of a dangerous command requires a durable authority transition before the system reports the Run as admitted. | `PRE_EFFECT_COMMIT` | [L405](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L405) |
| `SB-SRC-0556/STATE-14` | No requirement for backward-compatible old code APIs does not authorize silently discarding existing valuable user history; a one-time migration can preserve data. | `DATA_MIGRATION_DISTINCTION` | [L560](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L560) |
| `SB-SRC-0556/STATE-15` | A one-time verified import/cutover can preserve old valuable records without keeping legacy API adapters or indefinite dual-write. | `ONE_WAY_CUTOVER` | [L670](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md#L670) |

**Adversarial boundaries:** a UI tab filter can be reset; an accepted destructive effect cannot be reconstructed by guessing from a chat bubble. One atomic JSON document with a single writer may be adequate for a simple local deployment, but shared hosts and multiple writers may justify transactional coordination. SQLite's one-writer and network-share limitations rule out naive distributed access, not SQLite as a local database behind an authorized API. Removing compatibility code can be sensible while preserving preexisting user bytes through a strict one-time migration. Neither the source nor this paragraph fixes a compulsory database engine.

**Conservation ceiling:** fifteen material original statements are available in maintained Science, with open review of other evidence, deployment cost and complete 785-line source meaning.
