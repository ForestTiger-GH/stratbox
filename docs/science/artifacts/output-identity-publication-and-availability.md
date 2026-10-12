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

## 10. Additional original Artifact-layer alternatives: bundles, metadata ownership and old-content readability

The long [frozen 2026-10-06 Artifact architecture Research](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md), `SB-SRC-0027`, contained several materially independent **alternative designs and counterarguments** beyond its sixteen final headed recommendations. The distinctions below preserve the original research roles and tensions rather than promoting them to mandatory implementation objects.

| Original material and direct locator | Retained scientific distinction | Transfer/reliance boundary |
| --- | --- | --- |
| [§19–20: CAS versus event sourcing](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L452-L490) | A separate content-addressed blob layer and metadata DB can scale remote immutable output, but infrastructure cost can exceed the needs of an editable desktop workspace. **Event-sourcing every Artifact transition is an alternative, specifically judged excessive at this stage**; bounded audit events could coexist with a simpler operational catalog. | Neither CAS, event sourcing, S3 nor a SQL service is Product-admitted merely because the older Research recommended a path. |
| [§67–69: cache, directory, bundle, ZIP](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L1573-L1625) | A semantic cache key should reference actual immutable input identities, operation/method revision, meaningful parameters and classification revision; filename + mtime is insufficient for reproducibility. A **multi-part logical Artifact** need not be a physical directory or ZIP: object stores may realize a directory as a key prefix and ZIP may be one optional export representation. | Proposed only when multi-part content and reusable computed outputs warrant this complexity; do not force an Artifact onto every workspace directory. |
| [§72–73: Operation Result and effects](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L1660-L1705) | A computed result, diagnostic warning, failure, metric, provenance and successful Artifact identity are distinct roles; a list of output paths loses distinctions. Operation declarations of reads, writes, network access and destructive effect classes could support UI/preflight/AI exposure planning, **but declarative flags do not themselves authorize an effect**. | The example Python `OperationResult` and effect-flag names are Research sketches, not current API signatures, accepted schemas or a proven permission system. |
| [§79: three metadata roles](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L1854-L1896) | **Content/creation metadata** (parts, digest, generation, method), **operational lifecycle metadata** (published state, locations, retention, tombstone, GC) and **user/UI preferences** (favorite, pinned, read and grouping) have different revision and access semantics. None should silently rewrite immutable content proof. | Separate semantic ownership is valuable even if the first application embeds several views in one storage file; no compulsory three services/tables. |
| [§83–85: retention and reference-aware collection](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L1975-L2033) | An immutable content hash does not mean infinite retention. In a proposed CAS profile, deletion requires **no live manifest references**, elapsed grace period, no active operation/lease and permitted policy. An accessible Artifact link cannot outlive actual bytes without being marked unavailable. | These are risk and retention conditions only *if* a managed immutable store is adopted. They do not imply continuous filesystem crawling or recovery of a user's manually deleted editable files. |
| [§88–90: schema evolution and source-of-truth allocation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2058-L2106) | **Breaking old Python APIs and preserving readability of already committed user data are separate decisions.** If durable immutable manifests exist, a new reader either supports their old revision or uses a declared migration; simply discarding old metadata may erase historical evidence. The original also argues against prematurely merging Artifact Catalog with Case/Event/Log/Assignment storage into one monolith. | No old deployed Artifact schema, historical migration requirement or application service is thereby claimed to exist. For a future accepted data-retention profile, a concrete migration/restore policy needs owner approval and validation. |

**Cross-research conflict explicitly retained:** the historical design favored rich Artifact/Blob/Catalog/Manifest layers and often an immutable managed content copy. Later user-directed work gives priority to verified completion of everyday **user-controlled editable files**, and only selective retention and stronger manifests when consumer risk/replay needs justify them. The options can coexist as *different admitted profiles*; they should not be fused into a mandatory universal service or presented as an existing backend. A research alternative's absence from a prototype is not, by itself, a defect.

**Preservation/verification status:** selected source-first author-side restoration of six material distinction groups. Other passages and their exact evidence dependencies in the 2,935-line original remain subject to complete material-unit accounting and separate independent Research Amputation. No domain backend was tested, no Product Decision was made, and no independent semantic verifier participated.

## 11. Original sixteen Artifact-layer physical design recommendations and counterarguments

The frozen [2026-10-06 file/artifact architectural original, §112](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2579-L2647), Git blob `12c68fd388cabd4b5c3b9e228491201d2160a8b3`, contains **sixteen specific recommendations**. Their original Russian source titles, ordinal identity and source line remain recoverable; the English formulations below preserve the producer's interpretation as **Research proposals**, not executed software or accepted Product contracts.

| Source Research decision | English proposal | Limits and implementation qualifiers | Frozen source |
| --- | --- | --- | --- |
| `SB-SRC-0027/D01` | Retain FileStore | Keep narrow physical byte/path access abstraction. | [L2583](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2583) |
| `SB-SRC-0027/D02` | Limit FileStore responsibilities | Physical paths, streams, capabilities and storage errors; not domain Artifact meaning. | [L2587](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2587) |
| `SB-SRC-0027/D03` | Add a higher-level Artifact service | Proposed logical output/manifest/catalog service above physical bytes. | [L2591](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2591) |
| `SB-SRC-0027/D04` | Distinguish user Workspace from managed Artifacts | Mutable user-selected files and immutable published product outputs have different ownership. | [L2595](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2595) |
| `SB-SRC-0027/D05` | Committed managed Artifacts immutable | Once material output is declared committed, modification should create a successor version. | [L2599](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2599) |
| `SB-SRC-0027/D06` | Path must not be Artifact identity | File movement does not erase logical output lineage or guarantee continued availability. | [L2603](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2603) |
| `SB-SRC-0027/D07` | SHA-256 for content identity | Record actual bytes' digest where reproducibility/retention makes this meaningful. | [L2607](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2607) |
| `SB-SRC-0027/D08` | Minimal CAS from first implementation cycle | The source recommends content-addressed storage immediately; proportionality is contested. | [L2611](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2611) |
| `SB-SRC-0027/D09` | Local SQLite Artifact catalog | Suggested local persistence carrier, with server DB possible for later shared profiles. | [L2615](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2615) |
| `SB-SRC-0027/D10` | Portable immutable JSON manifests | A manifest is a transportable description; a catalog provides indexing. | [L2619](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2619) |
| `SB-SRC-0027/D11` | Connect SourceSnapshots through ArtifactRef | Proposed versioned, durable source-to-output lineage rather than volatile physical path. | [L2623](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2623) |
| `SB-SRC-0027/D12` | Return ArtifactRefs from operations | A proposed interface suitable for remote/mobile/machine projection. | [L2627](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2627) |
| `SB-SRC-0027/D13` | Run-centric provenance | Material links from inputs through actual Run to produced outputs. | [L2631](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2631) |
| `SB-SRC-0027/D14` | Agent access via authorized Artifact and Operation APIs | FileStore must be bounded separately if exposed to remote/machine actors. | [L2635](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2635) |
| `SB-SRC-0027/D15` | Treat fsspec as optional adapter or inspiration | Do not impose the external library as architectural foundation. | [L2639](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2639) |
| `SB-SRC-0027/D16` | External management platform should not own internal storage implementation | Share permitted capability/transport/health references rather than physical backend semantics. | [L2643](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md#L2643) |

**Material competing model:** The original argues for **mandatory early CAS and local SQLite** as a strong foundation, whereas a later direct developer annotation allows manually moved/deleted outputs to become simply unavailable and prefers limited, low-burden evidence collection. A CAS/digest/catalog model can deliver stronger retention and comparison, but at costs of indexing, garbage collection, migrations, privacy/retention, write protocols and recovery testing. These are separable decisions: `ArtifactRef` identity, truthful byte publication and historical preservation do **not logically require** introducing a universal CAS or local SQL database at the first release. Likewise a ContentDigest without retained bytes cannot guarantee replay.

**Alternative end states:** (A) direct workspace paths plus typed availability and optional run/source receipts for local Python or desktop; (B) staged verified bytes + small durable Artifact index for a real shared Work host; (C) content-addressed immutable content with retention/GC when cross-client reuse and historical reproducibility justify its cost. The priority/choice depends on admitted user profile, actual data volume, legal retention, security policy, recoverability and external platform contracts, and should be tested rather than copied from the 16 historical suggestions.

**Preservation scope:** all 16 specifically headed proposed options are now addressable with source lines. Their status remains producer-translated Research, not complete conservation of the 2,935-line original or independent semantic review.

## 12. Late source topic 04: sixteen physical and semantic Artifact boundaries

The [dated Artifact and Result Management Research](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md) identifies several distinctions between computed values, Artifact identity, physical bytes, file revisions, host-local paths, evidence of publication, and user permissions. Its **16 bounded English source-line interpretations** below retain specific failure cases and scope limitations. The observed failed-step artifact-card behavior and possible aggregate false success were **also confirmed in pinned Windows code** and added to [Current HOW](../../current-how/windows-application.md). Those observations are not evidence of a confirmed user data-loss incident.

| Source proposition | Source-grounded material meaning | Qualified status | Frozen source line |
| --- | --- | --- | --- |
| `SB-SRC-0557/ART-01` | FileStore byte operations are physical primitives, not a universal verified Artifact identity or publication API. | `FILESTORE_LEVEL` | [L98](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L98) |
| `SB-SRC-0557/ART-02` | A locally created ArtifactRecord may exist even when the output path does not, and contains no content digest or publication status. | `CURRENT_RECORD_LIMIT` | [L115](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L115) |
| `SB-SRC-0557/ART-03` | Current ScenarioRunner builds artifact cards for every operation output regardless of the operation success flag. | `DIRECT_CODE_FALSE_POSITIVE` | [L132](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L132) |
| `SB-SRC-0557/ART-04` | The operation-result object carries only a Boolean status, message, output paths and details; it does not attest published bytes. | `RESULT_CONTRACT_WEAKNESS` | [L140](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L140) |
| `SB-SRC-0557/ART-05` | A logical Artifact is not the same as the file bytes or a particular location of those bytes. | `SEMANTIC_ARTIFACT_IDENTITY` | [L175](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L175) |
| `SB-SRC-0557/ART-06` | One economic Result can have XLSX and CSV materializations; identical paths and identical underlying meaning are different relations. | `MULTI_REPRESENTATION` | [L178](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L178) |
| `SB-SRC-0557/ART-07` | A user-managed relocation does not erase the historical artifact record, although its old path may be unavailable without automatic rediscovery. | `EXTERNAL_MOVE_LIMIT` | [L188](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L188) |
| `SB-SRC-0557/ART-08` | A new calculation overwriting an earlier filename is generally a new content revision or Artifact, even with the same path. | `VERSION_LINEAGE` | [L191](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L191) |
| `SB-SRC-0557/ART-09` | File existence after a failed or partial write is not evidence that a workbook was validated or published. | `EXISTENCE_NONPROOF` | [L458](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L458) |
| `SB-SRC-0557/ART-10` | A minimal staged-file publish sequence requires completed staging, controlled finalization and an authoritative ready event; metadata detail may be proportional. | `PUBLISH_EFFECT_ORDER` | [L477](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L477) |
| `SB-SRC-0557/ART-11` | Filesystem bytes and relational metadata do not form one native ACID transaction; recovery must handle a committed file with missing metadata or vice versa. | `CROSS_PLANE_RECOVERY` | [L481](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L481) |
| `SB-SRC-0557/ART-12` | A package of independently useful files may validly be PARTIAL; all-or-nothing generation publishing is needed only for a genuinely consistent set. | `GROUP_PUBLICATION_COST` | [L495](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L495) |
| `SB-SRC-0557/ART-13` | Backend outage/denial must not be silently transformed into MISSING merely from an unsuccessful existence check. | `AVAILABILITY_TRUTH` | [L565](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L565) |
| `SB-SRC-0557/ART-14` | Visibility of an Artifact card does not entail permission to read its bytes or perform further effects on it. | `CARD_NOT_AUTHORITY` | [L599](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L599) |
| `SB-SRC-0557/ART-15` | Shared chats do not make host filesystem bytes anonymously available; remote authorization is checked by the actual host authority. | `SHARED_WORKSPACE_ACL` | [L610](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L610) |
| `SB-SRC-0557/ART-16` | An agent should use an authorized Artifact reference rather than arbitrary host paths; resolved access still requires scoped permission checks. | `AGENT_RESOURCE_BOUNDARY` | [L627](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md#L627) |

**Counterarguments:** A manually moved file can legitimately become unavailable in the historical chat rather than requiring aggressive global discovery. A cheap temporary CSV may not warrant permanent content-addressed storage. Conversely, an output path appearing after a failure must not be promoted to an accepted published accounting workbook, and a visible shared chat card does not confer download/delete rights on every viewer. The lowest trustworthy publication assurance is the one actually supported by the backend and observed effect receipt. A high-level staged publication model is a candidate, not installed generic code.

**Preservation limit:** the 16 original rows remain material partial coverage of this 986-line study; complete source-level lossless, the physical user DOCX hash and installed host/web tests remain open.

## Original Windows Study 0020: proposed client, artifact and collaboration maturity (source packet B)

**Source:** [frozen 2026-10-06 Windows study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md), exact blob `225128f2599f0792422c0b31cb3cbe1437991ced`; a dated future-option/release-maturity study, **not** binding architecture, accepted permission semantics or an executed host. Each row retains a competing disconfirming case.

| Address · epistemic role | Original material proposal or observation | Counterexample / limit | Original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/FUT-07` · `HISTORICAL_ARTIFACT_EXPANSION_CANDIDATE` | The proposed Artifact roadmap named preview metadata, lineage, hash, source links, retention, pin/favorite, controlled share/export and chaining. | A path-based ArtifactRecord does not already possess canonical byte digest, accessible generation, ownership grant, retention guarantee or safe remote publication. | [L1490–L1502](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md#L1490-L1502) |

**Evidence status:** a future AI actor label, mobile sketch, host execution backend or artifact field list cannot establish the relevant implementation or rights. This packet is a **producer source transfer**; independent review, complete source accounting and host/client release tests remain open. All frozen source dispositions are still `unaccounted`.

## Original automation Research 0041 — dated roadmap, logical architecture and example machine endpoints

**Frozen source:** [primary automation/AI study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. These are historical engineering alternatives with explicitly limited authority. A phase number, API-like name or deployment box in the original document is not evidence of an actual provider, Product Decision, accepted schedule or real effect.

| Material address and epistemic role | Source-defined proposition | Defeater, cost, competing choice | Primary lines |
| --- | --- | --- | --- |
| `SB-SRC-0041/ROAD-04` · `HISTORICAL_ARTIFACT_PHASE_PROPOSAL` | The artifact-intelligence phase grouped stable IDs, hashes, lineage, previews, table queries, sensitivity labels and agent-readable resources. | Some outputs require only a path or validated report; a blanket artifact database and AI query engine may overengineer direct Python use. | [L2063–L2071](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L2063-L2071) |

**Conservation limit:** this is a producer source-first packet; independent reverse review, empirical release tests and whole-original material accounting remain open. The current accepted Strategy Box host requirement supersedes only conflicting historical ownership/timing assumptions, not the original's record as a real alternative.

## Original automation Research 0041 — state, typed router, bounded agent and artifact-provenance specifics

**Frozen original:** [Strategy Box automation/AI study](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. The entries conserve exact historical design suggestions, evaluation logic and failure constraints. Schema/URI examples are not the accepted runtime implementation; the current application/host and protected effect boundaries require their own authority and execution evidence.

| Address and original status | Material source meaning | Contrary condition or denied inference | Primary source span |
| --- | --- | --- | --- |
| `SB-SRC-0041/ART-01` · `HISTORICAL_EXPANDED_DESCRIPTOR` | The historical Artifact descriptor enumerated stable ID, carrier kind/MIME/URI, hash, size, creation chain, parent/source snapshots, schema/period, sensitivity, query and retention fields. | Making each optional field mandatory for every output increases storage/cost and cannot guarantee any bytes were verified or permission granted. | [L727–L751](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L727-L751) |
| `SB-SRC-0041/ART-02` · `HISTORICAL_HANDLE_AND_TOOL_SURFACE` | Artifact IDs and controlled get/preview/table-slice/compare/export/open tools were proposed instead of arbitrary filesystem paths for future agents and cross-device clients. | An opaque ID by itself is not a capability grant; each read/export must check current resource permission, output generation and actual availability. | [L753–L775](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L753-L775) |
| `SB-SRC-0041/ART-03` · `RESEARCH_CONTEXT_ECONOMICS` | The study called for bounded table descriptions and filtered column slices rather than inserting whole million-row tables into a model context. | A query limit does not automatically prevent expensive scans, inference of restricted rows or loss of significant outliers beyond the sampled slice. | [L776–L794](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L776-L794) |
| `SB-SRC-0041/LINEAGE-01` · `HISTORICAL_PROVENANCE_GRAPH_PROPOSAL` | The source required tracing from original snapshot through canonical and derived data to Excel/report and proposed produced-by/input/source/registry/parameter links on artifacts. | An incomplete lineage graph can make false reproductions; actual consumed inputs and output digest/receipts must be established, not inferred from intended dependencies. | [L800–L829](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md#L800-L829) |

**Scientific qualification:** the historical proposal makes no claim that SQLite, agent orchestration, a broad catalog, Artifact query APIs or a production machine-provider bridge were implemented. An application can use a deterministic direct Python operation with no large shared Work/Agent database. Conversely hosted cross-user effects and sensitive resource handles require independent permission, replay and proof-of-publication boundaries. These meanings are producer-traced only; no independent reverse review or complete original source disposition is asserted.
