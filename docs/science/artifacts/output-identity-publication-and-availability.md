# Artifact identity, result publication, and physical availability

**Scientific scope:** relationships among analytical results, generated files, content revisions, catalog identity, publication evidence, and user-controlled file availability. **Epistemic status:** maintained, source-qualified explanation of the current implementation and of proposed alternatives; no universal artifact service, immutable-content mandate, or storage backend selection is claimed as implemented. **Direct reference baselines:** `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`, `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. Related Science: [execution evidence](../execution-and-diagnostics/causal-observability-and-failure-truth.md), [state recovery](../state-and-recovery/authority-durability-and-recovery.md), [source observations](../data-and-knowledge/source-observation-vintages-and-replay.md).

## 1. The actual user problem and its deliberate limits

The primary need is to give the analyst a correctly completed file in an ordinary Data/workspace directory, make it easy to find and open from the originating conversation, and allow a later task to consume it where authorized. Non-file numerical or narrative results may remain messages or structured previews. **An artifact catalog is not mandatory for every transient value or intermediate DataFrame.**

The user may rename, move, edit, or delete a working XLSX outside the application. A stale link may then simply report **“File not found”** on access; automatically searching the entire disk, identifying renamed files by digest, recovering deliberately deleted files, or retaining every old revision was never established as a baseline requirement. This is a meaningful *negative scope decision*, not a missing implementation detail to fill with an elaborate content-addressed storage system.

By contrast, the application **is** responsible for the truthfulness of its own publication. A file that was merely opened for writing, partially generated, or mentioned by a failed operation must not automatically acquire the status “ready”. These two expectations coexist: rigorous verification at the moment the application publishes an output, modest lazy availability checks thereafter when the user controls the workspace.

## 2. Five independent semantic objects

| Object | What it means | Important limitation |
| --- | --- | --- |
| **Computed/Analytical Result** | Domain calculation, value, table, findings, or analytical conclusion before export | A result can exist without any file or catalog row |
| **File / payload** | Physical sequence of bytes accessible through one storage backend | Its path is a locator, not durable identity |
| **Content Revision** | Precisely observed version of bytes, possibly a digest/generation | Hash identity does not imply retained or accessible bytes |
| **Artifact** | Application-recognized, linkable output with stable artifact identity and provenance | A catalog item is not automatically an immutable snapshot |
| **Materialization / Locator** | One place where a representation is expected to be accessible | Can become missing, denied, changed, or unavailable without erasing the creation event |

A single result may generate both XLSX and CSV, each a distinct physical representation. A logical recurring report may yield many separate artifacts. Several locations may contain the same observed bytes, and one file path can point to different bytes after overwrite. A catalog need not materialize five separate tables for every output: these are **semantic roles** required to avoid false statements.

For a simple editable output, a useful scope is `artifact_id + producer_run + recorded scoped locator`. A stronger managed snapshot additionally needs the exact verified bytes or a retained immutable backend generation, published digest/size, and a separate retention promise. Externally edited working bytes should never inherit an old verified digest as though no change occurred.

### Identity under changes

- **External rename or move:** the historical Artifact ID still identifies the created item and its original Run. The old locator may now resolve as missing; the application does not have to hunt for the new location.
- **App-controlled relocation:** keep Artifact ID if moving the very same output is the declared operation; update its locator under controlled confirmation.
- **External content edit:** the historical creation event persists; the currently reachable file may be changed relative to its recorded content revision.
- **New calculation overwrites `report.xlsx`:** a new artifact or revision is preferable to silently rewriting the old Run's identity. An optional `supersedes` or `report_series_id` may link releases.
- **XLSX and CSV of one computation:** link both to one result identity without asserting that their raw bytes are identical.

**Negative case:** `published → user deletes file → delete artifact history` is semantically wrong. Instead, preserve the historical creation and record a later `AvailabilityObservation(MISSING, checked_at)`, with an inactive opening action.

## 3. Direct implementation: why path-shaped output is not an artifact receipt

The core [`FileStore` protocol](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/base.py) supplies `open_read/open_write/exists/stat/listdir/rename` and basic convenience byte methods. [`LocalFileStore`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/filestore/local.py) uses ordinary file operations and `Path.rename`, but exposes no universal atomic-publish transaction, storage generation, content checksum, or durable receipt. On the pinned local implementation, opening an existing file for writing can truncate its former bytes before generation succeeds; file existence after an exception therefore cannot prove successful replacement.

In Windows, [`ArtifactRecord.from_path`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/artifacts/models.py) generates a UUID, assigns a path/name/kind/time/author and links Case/Scenario/Operation/Log. The file's extension or existence affects kind, but successful publication is **not** a precondition for creating the record. [`ArtifactStore`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/artifacts/store.py) keeps these records in a local dictionary and uses local path comparison; it is not an authoritative cross-host locator service.

The critical gap is in the [Windows scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py): for **each** `result.outputs`, it constructs an `ArtifactRecord.from_path` and emits artifact events without conditioning this conversion on `result.ok` or verifying the output bytes. The [operation-result contract](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/requests.py) describes outputs as a tuple of paths. A failed operation may still return a log path; this may be valuable *diagnostic output*, but the current broad conversion risks making a candidate file or partial output look like a ready business artifact.

This is **direct static behavior**, not proof of a production file-loss incident. Neither current source path provides end-to-end confirmation that a workbook is complete and usable. The [five-JSON history mechanism](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) also lacks a single atomic catalog+Run commit and can recover malformed collections as empty.

## 4. Minimal sufficient record and distinct availability status

A possible conceptual, **not released**, artifact record carries:

```text
artifact_id                 stable opaque identity
kind / display_name         representation and human label
locator                     storage_scope + relative_path, not canonical host absolute path
created_at / published_at   actual event timestamps
producer                    run_id?, step_run_id?, operation_id?, result_id?
actor_ref                   stable initiating/producing identity where applicable
publication_state           preparing | ready | failed | unknown
optional                    byte_size, sha256, media_type, format, input/source/method refs
optional                    supersedes / series_id, policy / visibility metadata
```

Separately, a **mutable observation of availability** may be `UNCHECKED / AVAILABLE / MISSING / ACCESS_DENIED / CHANGED / BACKEND_UNAVAILABLE / UNKNOWN` plus time checked. Do not put selected-row, favorite, card color, read cursor, or preview loading state into immutable artifact identity.

A more expressive `OperationResult` can distinguish `output_role=primary/secondary/source_bundle/diagnostic`, `candidate_locator`, `publication_status`, `artifact_ref` only after confirmed admission, and partial warnings. The result of a failed Step may include **one verified ready file** plus a failed file and a diagnostic log. An entire Run's terminal failure must not retroactively make its already committed earlier outputs disappear.

**Provenance minimum:** producer Run/Operation/Step, creation time, actually used inputs/source snapshots if known, method/code revision when available, and byte evidence appropriate to its retention profile. An author string embedded in XLSX/DOCX metadata is distinct from stable actor identity and permissions. Changing only document styling or author metadata may change the output byte digest without changing the underlying economic results.

## 5. Three physical spaces and a host-neutral locator

An installed runtime/package is **not** a writable output workspace. Product state (Run/Artifact metadata, publish intents, diagnostic records) belongs to its permitted system/application scope. User-owned CSV/XLSX/ZIP and source files belong to an authorized Data workspace. Ephemeral staging/cache and physical technical logs require their own managed lifecycle. The environment's provided roots must be resolved from the actual platform binding; no user-facing record should assert a single hard-coded Windows drive as a universal identifier.

A portable candidate `StorageLocator` is `(storage_scope='workspace_data', relative_path='output/reports/report.xlsx')`. The host authority resolves it, checks permissions at the moment of open/consume/download, and returns bytes or a permitted local representation. A Web/Android client must not treat `C:\\Users\\...\\report.xlsx` as a meaningful remote URL.

Scope resolution must reject path escapes, including `..`, absolute injection, symbolic links, Windows junctions/reparse points, case/Unicode ambiguity, and check/open races. The naive `str(path).startswith(str(root))` test does not enforce an authorized filesystem boundary. A link visible in a shared Thread **does not grant** file read, overwrite, delete, remote transfer, or permission to use that file as the input of another operation. Machine/AI consumer rights are checked against actor, action, resource and policy, rather than inherited from knowing the Artifact ID.

A directory output is especially different from an immutable bundle. A **folder locator** is suitable for “open the downloaded sources directory”, without proving the set of children has not changed. A **versioned bundle** requires a closed manifest of member paths/hashes or a verified archive. A folder icon is not evidence of an immutable dataset.

## 6. Publication is an effect protocol, not `exists(path)`

A robust **candidate** local output publication path distinguishes:

```text
1. Resolve authorized workspace and destination; reserve or select conflict-free name
2. Create unique staging file on the destination filesystem
3. Generate all bytes into staging; capture errors without announcing ready
4. Close/flush writer; synchronize according to an explicit storage durability tier
5. Validate the relevant format/container and verify size; optionally checksum bytes
6. Record a publish intent or equivalent recovery reference
7. Finalize staging to destination through a supported atomic/conditional operation
8. Confirm actual final target/generation
9. Commit artifact metadata and a canonical artifact-published event
10. Render the chat card, optionally ahead of the overall Run's completion
```

This is **not** claimed as present in current FileStore/Windows code. Simple local deployments may combine some phases, but must not confuse their causal meanings.

For a local filesystem, atomic visibility of a rename may be possible under filesystem-specific constraints; `Path.rename`, `os.replace`, fsync and closing a file do **not** establish universal power-loss durability on arbitrary Windows/POSIX/SMB/NAS implementations. Linux [rename(2)](https://man7.org/linux/man-pages/man2/renameat2.2.html) and Microsoft [moving/replacing files](https://learn.microsoft.com/en-us/windows/win32/fileio/moving-and-replacing-files) describe different supported operations. A crash after physical finalize but before catalog commit may leave a valid file **without a catalog card**; this is preferable to a ready card with missing/unverified bytes. It is reconciled from an admitted publish intent, *not* by searching all files in Data.

For object/remote storage, finalize may be a conditional write or object generation, not filesystem rename. [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html) distinguish `If-None-Match`, `If-Match`, and conflict/precondition failures; [Google Cloud Storage preconditions](https://cloud.google.com/storage/docs/request-preconditions) use object `generation/metageneration`. AWS S3 `ETag` is not universally an MD5 checksum, notably with multipart uploads and some encryption ([AWS Object API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Object.html)). A provider-neutral `StorageCapabilities` may declare `atomic_replace`, `conditional_create/replace`, `native_version`, `streaming`, `checksum`, and read-after-write scope, but these values must be validated against the real target storage.

**Conflict case:** two independent Runs attempt to overwrite the same workbook. “Different chats” is not an output lock. Use exclusive resource reservation, unique run-scoped output naming, conditional write or explicit overwrite approval. Reject/queue when collision cannot be safely resolved, rather than silently choosing last-write-wins. `overwrite=false` is a defensible *candidate default*, not an approved universal setting.

## 7. Failure matrix and what can honestly be recovered

| Failure moment or observation | What can be asserted | What to do or show |
| --- | --- | --- |
| Before staging | No new artifact bytes | Failure without a ready card |
| During generation or writer close | Partial or unreliable staging | Do not publish; own staging may be quarantined/cleaned by policy |
| Format validation or digest fails | Bytes do not meet declared proof | No ready state; diagnosis |
| After verification, before finalize | Verified staging only | Recover *known* intent or abort; no published claim |
| After finalize, before metadata commit | Final bytes may exist without a catalog record | Reconcile exact destination/intent; avoid global Data scanning |
| After metadata commit, before UI refresh | Canonical ready artifact exists | Reload projection and deliver event idempotently |
| Remote finalize ACK lost | Effect may or may not have committed | `OUTCOME_UNKNOWN`; inspect exact key/generation before retry |
| Later Run Step fails after an earlier artifact was published | Earlier committed file stays ready | Display per-output status and overall partial/failure distinctly |
| User renamed/deleted file | Locator no longer points to original bytes | Lazy `MISSING`; no mandatory search or restore |
| Authentication denied | File may exist | `ACCESS_DENIED`, not `MISSING` |
| Backend disconnected | Existence is unknown | `BACKEND_UNAVAILABLE`, not absence |
| New writer changed reachable bytes | Historical record and current bytes disagree | `CHANGED` only after actual digest/generation comparison |
| Catalog corrupted | Physical files may still exist | Restricted recovery/read-only state, never silent empty catalog |

An `exists=false` report is reliable evidence of *missing* only if the authorized backend successfully checked a known location. Some lower-level FileStore methods coalesce missing and empty directory cases; a strict Artifact resolver needs typed failures. A UI can communicate “File not found”, “Access denied”, “Storage unavailable”, “File changed” and “Publication could not be confirmed” without teaching users every internal state machine.

**Backup distinction:** backing up a transactional artifact catalog does not back up the user-managed XLSX bytes. Conversely, a directory backup without a Run/Artifact catalog may retain files but lose the historical explanation. Backup policy must state metadata and payload coverage, and the actual recovery profile. Existing public [staged-publication LDD](../../ldd/artifacts/staged-publication.md) is a **candidate contract**, not a passed deployment test.

## 8. Alternatives, opposing evidence, and prohibitions on overdesign

| Alternative | Useful contribution | Limit |
| --- | --- | --- |
| Just paths and chat cards | Minimal UI and filesystem integration | No reliable publish, identity or recovery; current implementation is too weak for stronger claims |
| **Verified file + small catalog** | Matches user-owned Data workspace and low deployment overhead | Limited replay after external edits/delete; best candidate basic profile |
| Selective staged files + manifests/snapshots | Better evidence and downstream reproducibility for high-value results | More bytes, retention/permission cost; conditional enhancement |
| Mandatory global CAS for all outputs | Immutable identity and potential dedup | Doubles large editable files, complicates GC, UX and recovery |
| Sidecar JSON next to every XLSX | Portable metadata for exported bundles | Easy for users to separate or edit; poor large-scale catalog lookup |
| SQLite as local node metadata owner | Transactional catalog/links | Single host authority, backup and deployment conditions; not automatically provided by platform |
| PostgreSQL, DVC/DataLad/lakeFS | Collaborative/larger-scale versioned datasets | Infrastructure overhead without proven user need |
| Full W3C PROV graph or RO-Crate for everything | Interoperable research bundles | Conceptually useful, but RDF store/packaging not needed for every workbook |

[W3C PROV-O](https://www.w3.org/TR/prov-o/) supports *Entity → Activity → Entity*, linked to an Agent. [FAIR principles](https://doi.org/10.1038/sdata.2016.18) support meaningful identity and qualified reuse; neither demands automatic restoration of a deleted local XLSX. [RO-Crate](https://www.researchobject.org/ro-crate/specification/1.2/data-entities.html) may be useful as an exportable research bundle, and [DVC](https://doc.dvc.org/user-guide), [DataLad](https://doi.org/10.21105/joss.03262), or [lakeFS](https://docs.lakefs.io/guides/version-data/) are viable under different scale and governance needs, not established first-release requirements.

A material difference between research generations must remain visible: earlier artifact-layer studies considered strong Blob/Manifest/Catalog/CAS architecture as a promising target; later direct user constraints favor **minimal verified user-owned files plus a small authoritative catalog**, with immutable retention only for selected important results. Earlier local SQLite preference and a separate later file-first storage preference likewise remain **unresolved physical backend alternatives**. Neither is adopted by counting research documents.

## 9. Conformance challenges and policy decisions

No fault-injection/storage-profile test has been run as part of this Science publication. Future tests must cover:

- Successful XLSX export produces verified bytes, Run/Step linkage and a ready card.
- A handler that fails halfway or returns a nonexistent path does **not** create a ready artifact.
- A diagnostic log from a failed run is labeled as technical evidence rather than business output.
- In a multi-output scenario, ready members remain ready when a later member fails.
- Manual rename/move/delete yields lazy missing indication without a background crawler.
- Temporary backend failure and permission denial are not reported as missing bytes.
- No overwrite under `overwrite=false`; concurrent publication to the same destination produces a conflict or explicitly versioned result.
- Crash before/after finalize and before/after catalog commit recovers by exact known intent.
- A folder locator makes no false claim about immutable members.
- `..`, symlink and Windows reparse-point scope escapes are prevented.
- Two Runs using the same name obtain distinct artifact identities.
- Remote consumers are authorized on open/read/consume and never receive unrestricted host paths.
- Local NTFS, POSIX, SMB/NAS, object storage and remote-host profiles require different fault/atomicity tests. A clean restart alone is not a crash-consistency test.

**Unresolved Product Decisions:** which outputs get Catalog IDs; retention of cards versus bytes; whether ready files from a failed Run remain available; default overwrite policy; user-controlled author metadata and document style; artifact/series/revision IDs; availability-check caching; host sharing and access; approved Data binding; backup responsibilities; how much source/provenance must be attached; supported storage profiles and their durability claims.

**Conclusion:** a scientifically defensible artifact contract must separate **computational truth**, **physical output bytes**, **proof of publication**, **persistent creation history**, **current availability**, and **permission to access**. The user can control working files without forcing Strategy Box to reconstruct arbitrary external changes. The application must, however, never treat a bare output path as proof that a requested file was completed and published.
