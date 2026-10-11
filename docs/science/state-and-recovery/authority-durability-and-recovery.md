# Strategy Box state: authority, durability, consistency and recovery

**Scientific scope:** truthful user history and analytical application state under crashes, concurrent mutations, file publication and storage migration. **Status:** maintained explanatory model and qualified implementation alternatives; physical backend, active deployment profile and numeric guarantees require Product decisions. **Direct Windows implementation baseline:** [stratbox-windows@959e9c4](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). Static reading does **not** substitute for a crash test on target hardware.

## 1. Begin with the meaning of state, not a choice of SQLite

Application state is neither merely a collection of JSON files nor an abstract “chat history.” It contains **different truth classes** with different owners, scopes, lifetimes, accepted loss budgets, audiences and consequences of recovery errors. First establish who may commit a fact and what must remain true after failure. Then choose the persistence mechanism.

Six useful state coordinates: **owner, scope, truth class, lifetime, concurrency model and recovery route**. Scope may be node, user, device, workspace, Thread, Run or source. Truth class may be authoritative record, projection, cache or ephemeral state. Physical directory co-location does not collapse these identities.

| Kind of state | Semantic ownership | Recovery appropriate to its role |
| --- | --- | --- |
| Installation, Node, activation and assigned roots | External managed platform and its verified contract | Re-read actual contract, perform preflight, degrade safely on mismatch |
| Admitted commands, Threads, Cases, Runs/Attempts, assigned Work and approvals | Application execution/Work authority | Recover last provable revision, diagnose corruption, reconcile unfinished effects |
| UI settings, filters, panel sizes and personal drafts | User preferences and possibly valuable individual work | Restore personal source; explicitly reset genuinely disposable projections where allowed |
| Per-principal read cursor | Individual read status of shared history | Restore separately; one reader must not mutate another's record |
| Presence, current selection, progress redraw and next-run preview | Ephemeral/derived projections | Mark expired presence stale, recompute from authoritative facts |
| Raw source snapshots, Registry revisions and versions | Analytical evidence | Re-fetch only when **the same edition** is provably obtainable; otherwise retain required historic raw |
| XLSX/CSV/ZIP and its Artifact card | Bytes and separate assertion about those bytes | Check current availability and identity; retain historical execution record even after manual file deletion |
| Parser/pivot/search cache and technical logs | Derived data and diagnostic evidence | Rebuild when possible or disclose lost observability; a log file is not terminal-state authority |

**Negative case:** returning an empty history after failed JSON reading conflates “no Work ever existed” with “authoritative state cannot be read.” The second needs diagnostics, prevention of dangerous new writes into a damaged authority scope, and a verified recovery route where available.

## 2. Current Windows evidence and its limits

The frozen [HistoryPersistenceService](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) writes **five independent collections**—cases, events, artifacts, logs and assignments—via individual `Path.write_text` calls. `_load_list` returns `[]` for read/decode failures and some invalid payloads; malformed items may be skipped. Direct static conclusions: there is **no atomic commit across five collections**, damaged state can look empty, and sequential recovery cannot prove one common snapshot revision. That does **not** prove a real user has already suffered data loss.

[Windows runtime configuration](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/config.py) writes `app.json` separately and may raise `AppConfigError` for invalid JSON—a **different** failure policy. Both paths use direct replacement/overwrite patterns; survival of power loss depends on target OS, filesystem and testing. [Windows Current HOW](../../current-how/windows-application.md) separately describes case execution and the minimal background-status scaffold.

A managed platform may supply authorized System/Node/Data roots and activation context. That fact does **not** prove availability of a public transactional StateStore, SQL endpoint, persistent Job database or arbitrary network-root durability. Platform health is not an authoritative banking Run outcome. The standalone core owns domain calculations and source evidence but should not automatically become storage for UI conversations and grants.

## 3. Four evidence/durability grades

- **G0 — ephemeral:** loss acceptable without reconstruction, e.g. hover position.
- **G1 — reconstructible:** state recoverable from a current authoritative source, e.g. search indexes, cache, previews or TTL presence.
- **G2 — durable record:** an acknowledged logical record must survive defined failures **within a declared storage profile**; atomic visible commit, integrity checks, writer ownership and backup policy matter.
- **G3 — effect-coupled:** G2 plus reconciliation against independent file, network, delete or delegated effects; requires recorded intent, effect evidence and an `OUTCOME_UNKNOWN` path.

G2 does **not** imply RPO=0 after hardware destruction. **Crash recovery, backup recovery and effect reconciliation are three distinct tasks.** RPO sets permitted data-loss horizon; RTO sets recovery duration; neither follows from the name of the storage engine ([NIST SP 800-34 Rev.1](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)).

## 4. Three separate atomicity boundaries

**One state file:** under verified filesystem conditions, `temporary file in the same directory → flush/fsync → atomic replace → directory synchronization where supported` may give an observer either old or new complete snapshot. Claims still depend on OS, filesystem, mount, power-loss behavior and fault tests. Python [`os.replace`](https://docs.python.org/3/library/os.html#os.replace) alone does not certify durable semantics of every provider; see [OSDI 2014](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai) and [ASPLOS 2016](https://doi.org/10.1145/2872362.2872406).

**Admission of a user action:** chat record, accepted Run, identity and external-effect intent may need one *logical* commit/revision. A lost response after commit should find the same `mutation_id` rather than admit a duplicate Run. `commit(expected_revision, mutation_id, change)` is a **candidate port signature**, not current code.

**External file/effect:** computing values, writing staging bytes, validating, publishing a final filename and persisting metadata are distinct operations and usually **not one distributed transaction**. A published file and catalog row can disagree, yielding orphans, missing refs, duplicate effect or unknown outcome. [Unknown effects](../trust-and-assurance/uncertain-outcome-vs-observed-error.md) and [staged publication candidate](../../ldd/artifacts/staged-publication.md) address different parts.

### Crash windows for a single snapshot

| Crash point | Defensible claim after restart |
| --- | --- |
| Before creating temporary file | Prior verified revision remains authoritative |
| During temporary write | Partial temporary object is not a committed revision; isolate it |
| After syncing temp, before replace | Old document still governs |
| Replace happened, caller ACK was lost | Inspect stored revision/`mutation_id`; no blind second effect |
| During directory sync or power loss | Outcome depends on tested filesystem semantics, not Python call sequence |
| Valid committed state re-read after restart | Resume from exact revision; detect corruption rather than reset to empty |

## 5. One authority for mutations matters more than choosing SQL

**Application authority** is the logical owner allowed to accept final product-state changes. It can run within one local desktop process in a simple profile. For a shared node, one accepting host service may be preferable, with Windows/Web/Android clients using authenticated commands, snapshots and events. That does **not** require a new repository, microservice, or SQL engine in advance.

Parallel computation across independent tasks is compatible with serializing short state commits. By contrast, clients directly writing one common JSON/SQLite file through a network share constitutes a different and riskier concurrency model. A shared path is **not** equivalent to an application API and authorization.

`expected_revision` detects lost updates; `mutation_id` may deduplicate **command admission**, not independently guarantee exactly-once mutation by a remote API. After restore or backup cloning, `store_generation`/`restore_epoch` should fence stale workers before accepting new writes under the restored identity.

A global `unread: bool` cannot encode two participants' independent read state; per-user cursors are necessary. A previous `online` status must be refreshed or TTL-qualified on reconnect.

## 6. Two storage planes with independent responsibility

**Operational state** (rights, versions, accepted Work/Run, history) belongs in an application-authorized private/system scope. **Analytical Data** (input files, archives, tables, outputs) belongs in the Data root and FileStore. These may reside on one disk but still have different permissions, lifetimes and guarantees.

A user deliberately moving/deleting an XLSX can cause the old Artifact card to display “file not found” without obligating the app to scour all disks or restore the deleted file. The historical Run still happened. A platform-provided path is a **locator**, not an ACID guarantee. A future `StateStorageBinding` might report scope, locality, durability/transactions, permissions, quotas, backup and provider version, but no unverified external descriptor should be presented as an implemented platform contract.

## 7. Storage alternatives and operational cost

| Model | Material advantage | Counterargument/failure burden | Research disposition |
| --- | --- | --- | --- |
| RAM only | Minimal overhead | Not sufficient as the sole G2/G3 authority | Negative candidate |
| Five separately overwritten JSON files | Transparent and already observed | No shared revision, torn writes, silent empty recovery | Current mechanism; insufficient for stronger promise |
| **One atomic versioned document** | One small commit, simple single-writer model | Full rewrite cost as state grows; no multiwriter semantics | Possible simple initial profile |
| Append-only segments plus snapshots | Reduces full rewrites, preserves history | Framing/CRC, compaction, partial tail, corrupt middle, replay, fencing | Conditional |
| SQLite on local authority disk | Transactional relationships, indexes, WAL readers, one writer | Backup, locking, synchronous durability, ownership/migration must be measured | Strong conditional candidate |
| Managed PostgreSQL | Server concurrency, PITR and established operational tools | Always-on host, network/security, administration and cost | For demonstrated server requirement |
| Existing document/NoSQL provider | May use already provisioned infrastructure | Name alone proves neither ACID nor recovery | Alternative requiring actual contract |
| Full event sourcing/distributed log | Fine-grained replay in a mature engine | Schema evolution, projections, retention, recovery complexity | Disproportionate without real consumer |

In a custom append-only log, a provably **partial trailing record** may be truncated at the last accepted sequence, but **mid-stream corruption** must not be silently skipped while claiming complete history. The snapshot is a projection of the one log authority, not a second owner. If building a journal turns into implementing a mini-SQL engine, reconsider its cost.

[SQLite WAL](https://www.sqlite.org/wal.html), [transaction isolation](https://www.sqlite.org/isolation.html) and [SQLite over networks](https://www.sqlite.org/useovernet.html) establish that WAL can serve multiple readers with one writer, **not** multiple computers writing the same SQLite WAL database over a shared network filesystem. `synchronous=NORMAL` and `FULL` differ under power loss; WAL does not itself guarantee RPO=0 ([PRAGMA](https://www.sqlite.org/pragma.html)). Remote clients can access SQLite **through an API on one owning host**, rather than sharing its file.

**Scientific conclusion:** choose the least complex mechanism that meets *verified actual requirements*. Neither “always JSON” nor “always SQL” is proven universally correct.

## 8. Execution lifecycle and human-facing history

Chat text is not the authoritative ledger of execution truth. A committed action needs at least a command/Run identity, exact Request and Operation revision, outcome, timestamps, actor, Attempt/Effect/Artifact refs and safely resolved parameters. A large event-sourcing engine is not automatically necessary; user messages can be projections of canonical Run history.

`Failed`, `Interrupted` and `OutcomeUnknown` differ. Worker termination cannot prove a remote effect did not happen. On restart, inspect coherent state, find unfinished Runs, reconcile real worker/effect receipts, then record justified termination or UNKNOWN. Retrying destructive UNKNOWN actions can duplicate damage. GUI-only close may stop local workers; in a genuine host profile, client disconnect may leave authorized work running. **Persisting the fact of execution is different from keeping its process alive.**

A reconnecting client needs a revisioned snapshot and audience-filtered cursor/event delta. A stream gap requires resnapshot rather than pretending the last known state is fresh. Offline collaborative CRDTs and HA consensus remain distinct future options, not prerequisites for a small trusted node.

## 9. Backup, restore, schema changes and cloned authority

**Crash recovery** recovers consistent state after interruption. **Backup restore** covers media destruction/accidental deletion. **Reconciliation** links files and external effects to the recorded state. Each has different tests.

A meaningful backup set may include canonical state revision/schema/generation, committed Artifact manifests and *managed* bytes, irreplaceable SourceSnapshots, policy/user records and a `BackupReceipt` identifying version, hash, coverage and time. Cache, transient presence and raw support logs may be excluded under explicit policy. A database backup **does not automatically back up unmanaged user files**.

A **candidate coherent two-plane backup**: establish short commit barrier or stable revision; snapshot metadata; enumerate referenced immutable Artifact bytes; copy/verify managed objects or explicitly label unmanaged refs; record backup coverage; release barrier. [SQLite backup API](https://www.sqlite.org/backup.html) and [PostgreSQL PITR](https://www.postgresql.org/docs/current/continuous-archiving.html) protect their databases, **not arbitrary XLSX outside the DB**.

Restore should stop previous mutation authority, validate backup/coverage, stage the restoration, check integrity/references, publish a new store generation, fence old workers, rebuild derived projections, reconcile unknown external effects and run a domain smoke test. Simultaneously activating the original and an identically named restored clone with write privileges creates split-brain risk.

**Breaking API compatibility policy does not excuse loss of valuable persisted data.** A one-time verified import from existing five JSON files should account for malformed records, object counts, ID mapping, reference integrity, read-back, rollback and atomic cutover. Permanent dual-write between old and new stores risks two competing truth sources; a one-time controlled migration need not maintain the old public API.

## 10. Negative cases and experimental program (not executed)

| Fault or injection | Truthful outcome needed |
| --- | --- |
| Kill during JSON write, disk full | Old/new valid snapshot versus corruption, surfaced safely |
| Crash between Case and Artifact metadata | Shared committed revision or explicit discrepancy |
| Invalid JSON or malformed record | Corrupt/quarantine distinct from truly empty history |
| Two writers/editors mutate same Thread | Revision conflict instead of silent lost update |
| Submit ACK lost after server commit | Same `mutation_id`/Run rather than second admission |
| GUI closes during network effect | Interrupted versus OutcomeUnknown based on actual facts |
| XLSX partially written or orphan file | Staging/verified/orphan and safe reconciliation |
| Artifact card remains, user deletes file | Bytes missing but historical Run retained |
| Network Data root disconnects | Unavailable distinguished from empty directory |
| Host survives UI crash | Continued hosted Job versus stopped local worker |
| Old client writes after backup restore | New generation/fencing rejects stale authority |
| Backup includes metadata only | Explicit incomplete Artifact coverage |
| WAL/files placed on network FS | Unverified atomicity/locking never reported as proved |
| Two people read same Thread | Independent read cursors, not shared unread flag |
| Corrupt log middle versus trailing partial record | Mid-stream corruption cannot be silently skipped |
| Crash at each migration stage | Old authority remains until verified read-back and cutover |

Passing requires both actual bytes/state and accurate UI explanation. These are **future test candidates**, not executed experiments. Local profile measurements should include history growth, full-rewrite time and startup; shared profile adds two principals, idempotent resubmit, reconnect, ACL and read cursors.

## 11. Decisions, counterarguments and reopening

**Open Product Decisions:** first authority scope, storage binding location/API, managed database necessity, retention for Threads/Runs/logs/sources, saved parameters without secrets, local-close versus host-detach semantics, RPO/RTO and backup cadence, restore ownership, direct/single-host API, timing of JSON→SQLite migration, manual Artifact deletion policy, immutable audit depth, HA, clone generation and remote user preferences.

Seven strong counterarguments and their limits:

1. **“A DB automatically fixes history.”** Transactions within one DB do not define product authority, protect unrelated files or create backup operations.
2. **“Five atomic JSON files are sufficient.”** Each file may be whole but five distinct revisions do not form a coherent Case/Event/Artifact set.
3. **“Store everything under Data.”** The user-controlled Data root may be moved or modified and has a different retention/security lifecycle.
4. **“Everything is failed after a crash.”** An external effect may have succeeded despite missing acknowledgment; UNKNOWN requires checking.
5. **“Any event history requires event sourcing.”** Canonical Run records plus linked message projections can suffice until full event replay has an actual consumer.
6. **“Old API compatibility is needed for migration.”** A one-time verified transfer of persisted user facts does not require permanent old API compatibility.
7. **“Python fsync guarantees durability.”** Actual guarantees depend on filesystem, target storage profile and fault testing.

**Reopen when:** persistence code or external platform contract changes, a durable host/shared node exists, state growth/mutation rates are measured, a verified crash/data-loss incident occurs, security/privacy requirements change, RPO/RTO targets are tested, or backend assumptions are independently demonstrated.

## 12. Direct sources and the limits of knowledge

**Exact implementation witnesses:** [Windows history persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py), [UI config](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/config.py), [runtime composition](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py), [session projection](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/session_runtime.py). Interpretations are limited to those frozen source branches.

**External primary references:** Python `os.replace`, SQLite WAL/isolation/backup/atomic-commit research, OSDI 2014, ASPLOS 2016 and NIST SP 800-34, each with its own applicability boundary. Tables and proposed effect/authority designs are analytical hypotheses and falsifiable future specifications, **not a newly executed experiment**.

**Not established:** behavior of exact Windows/Linux filesystems under deployed fault modes, an available generic external transactional StateStore, running shared database, deployed host/remote execution or independently sampled field-failure statistics. Backend, privacy, recovery and retention remain decisions of appropriate Product Authority.
