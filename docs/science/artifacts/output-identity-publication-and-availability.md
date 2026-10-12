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

The long frozen 2026-10-06 Artifact architecture Research, `SB-SRC-0027`, contained several materially independent **alternative designs and counterarguments** beyond its sixteen final headed recommendations. The distinctions below preserve the original research roles and tensions rather than promoting them to mandatory implementation objects.

| Original material and direct locator | Retained scientific distinction | Transfer/reliance boundary |
| --- | --- | --- |
| §19–20: CAS versus event sourcing (`#L452-L490`) | A separate content-addressed blob layer and metadata DB can scale remote immutable output, but infrastructure cost can exceed the needs of an editable desktop workspace. **Event-sourcing every Artifact transition is an alternative, specifically judged excessive at this stage**; bounded audit events could coexist with a simpler operational catalog. | Neither CAS, event sourcing, S3 nor a SQL service is Product-admitted merely because the older Research recommended a path. |
| §67–69: cache, directory, bundle, ZIP (`#L1573-L1625`) | A semantic cache key should reference actual immutable input identities, operation/method revision, meaningful parameters and classification revision; filename + mtime is insufficient for reproducibility. A **multi-part logical Artifact** need not be a physical directory or ZIP: object stores may realize a directory as a key prefix and ZIP may be one optional export representation. | Proposed only when multi-part content and reusable computed outputs warrant this complexity; do not force an Artifact onto every workspace directory. |
| §72–73: Operation Result and effects (`#L1660-L1705`) | A computed result, diagnostic warning, failure, metric, provenance and successful Artifact identity are distinct roles; a list of output paths loses distinctions. Operation declarations of reads, writes, network access and destructive effect classes could support UI/preflight/AI exposure planning, **but declarative flags do not themselves authorize an effect**. | The example Python `OperationResult` and effect-flag names are Research sketches, not current API signatures, accepted schemas or a proven permission system. |
| §79: three metadata roles (`#L1854-L1896`) | **Content/creation metadata** (parts, digest, generation, method), **operational lifecycle metadata** (published state, locations, retention, tombstone, GC) and **user/UI preferences** (favorite, pinned, read and grouping) have different revision and access semantics. None should silently rewrite immutable content proof. | Separate semantic ownership is valuable even if the first application embeds several views in one storage file; no compulsory three services/tables. |
| §83–85: retention and reference-aware collection (`#L1975-L2033`) | An immutable content hash does not mean infinite retention. In a proposed CAS profile, deletion requires **no live manifest references**, elapsed grace period, no active operation/lease and permitted policy. An accessible Artifact link cannot outlive actual bytes without being marked unavailable. | These are risk and retention conditions only *if* a managed immutable store is adopted. They do not imply continuous filesystem crawling or recovery of a user's manually deleted editable files. |
| §88–90: schema evolution and source-of-truth allocation (`#L2058-L2106`) | **Breaking old Python APIs and preserving readability of already committed user data are separate decisions.** If durable immutable manifests exist, a new reader either supports their old revision or uses a declared migration; simply discarding old metadata may erase historical evidence. The original also argues against prematurely merging Artifact Catalog with Case/Event/Log/Assignment storage into one monolith. | No old deployed Artifact schema, historical migration requirement or application service is thereby claimed to exist. For a future accepted data-retention profile, a concrete migration/restore policy needs owner approval and validation. |

**Cross-research conflict explicitly retained:** the historical design favored rich Artifact/Blob/Catalog/Manifest layers and often an immutable managed content copy. Later user-directed work gives priority to verified completion of everyday **user-controlled editable files**, and only selective retention and stronger manifests when consumer risk/replay needs justify them. The options can coexist as *different admitted profiles*; they should not be fused into a mandatory universal service or presented as an existing backend. A research alternative's absence from a prototype is not, by itself, a defect.

**Preservation/verification status:** selected source-first author-side restoration of six material distinction groups. Other passages and their exact evidence dependencies in the 2,935-line original remain subject to complete material-unit accounting and separate independent Research Amputation. No domain backend was tested, no Product Decision was made, and no independent semantic verifier participated.

## 11. Original sixteen Artifact-layer physical design recommendations and counterarguments

The frozen 2026-10-06 file/artifact architectural original, §112 (`#L2579-L2647`), Git blob `12c68fd388cabd4b5c3b9e228491201d2160a8b3`, contains **sixteen specific recommendations**. Their original Russian source titles, ordinal identity and source line remain recoverable; the English formulations below preserve the producer's interpretation as **Research proposals**, not executed software or accepted Product contracts.

| Source Research decision | English proposal | Limits and implementation qualifiers | Frozen source |
| --- | --- | --- | --- |
| `SB-SRC-0027/D01` | Retain FileStore | Keep narrow physical byte/path access abstraction. | L2583 (`#L2583`) |
| `SB-SRC-0027/D02` | Limit FileStore responsibilities | Physical paths, streams, capabilities and storage errors; not domain Artifact meaning. | L2587 (`#L2587`) |
| `SB-SRC-0027/D03` | Add a higher-level Artifact service | Proposed logical output/manifest/catalog service above physical bytes. | L2591 (`#L2591`) |
| `SB-SRC-0027/D04` | Distinguish user Workspace from managed Artifacts | Mutable user-selected files and immutable published product outputs have different ownership. | L2595 (`#L2595`) |
| `SB-SRC-0027/D05` | Committed managed Artifacts immutable | Once material output is declared committed, modification should create a successor version. | L2599 (`#L2599`) |
| `SB-SRC-0027/D06` | Path must not be Artifact identity | File movement does not erase logical output lineage or guarantee continued availability. | L2603 (`#L2603`) |
| `SB-SRC-0027/D07` | SHA-256 for content identity | Record actual bytes' digest where reproducibility/retention makes this meaningful. | L2607 (`#L2607`) |
| `SB-SRC-0027/D08` | Minimal CAS from first implementation cycle | The source recommends content-addressed storage immediately; proportionality is contested. | L2611 (`#L2611`) |
| `SB-SRC-0027/D09` | Local SQLite Artifact catalog | Suggested local persistence carrier, with server DB possible for later shared profiles. | L2615 (`#L2615`) |
| `SB-SRC-0027/D10` | Portable immutable JSON manifests | A manifest is a transportable description; a catalog provides indexing. | L2619 (`#L2619`) |
| `SB-SRC-0027/D11` | Connect SourceSnapshots through ArtifactRef | Proposed versioned, durable source-to-output lineage rather than volatile physical path. | L2623 (`#L2623`) |
| `SB-SRC-0027/D12` | Return ArtifactRefs from operations | A proposed interface suitable for remote/mobile/machine projection. | L2627 (`#L2627`) |
| `SB-SRC-0027/D13` | Run-centric provenance | Material links from inputs through actual Run to produced outputs. | L2631 (`#L2631`) |
| `SB-SRC-0027/D14` | Agent access via authorized Artifact and Operation APIs | FileStore must be bounded separately if exposed to remote/machine actors. | L2635 (`#L2635`) |
| `SB-SRC-0027/D15` | Treat fsspec as optional adapter or inspiration | Do not impose the external library as architectural foundation. | L2639 (`#L2639`) |
| `SB-SRC-0027/D16` | External management platform should not own internal storage implementation | Share permitted capability/transport/health references rather than physical backend semantics. | L2643 (`#L2643`) |

**Material competing model:** The original argues for **mandatory early CAS and local SQLite** as a strong foundation, whereas a later direct developer annotation allows manually moved/deleted outputs to become simply unavailable and prefers limited, low-burden evidence collection. A CAS/digest/catalog model can deliver stronger retention and comparison, but at costs of indexing, garbage collection, migrations, privacy/retention, write protocols and recovery testing. These are separable decisions: `ArtifactRef` identity, truthful byte publication and historical preservation do **not logically require** introducing a universal CAS or local SQL database at the first release. Likewise a ContentDigest without retained bytes cannot guarantee replay.

**Alternative end states:** (A) direct workspace paths plus typed availability and optional run/source receipts for local Python or desktop; (B) staged verified bytes + small durable Artifact index for a real shared Work host; (C) content-addressed immutable content with retention/GC when cross-client reuse and historical reproducibility justify its cost. The priority/choice depends on admitted user profile, actual data volume, legal retention, security policy, recoverability and external platform contracts, and should be tested rather than copied from the 16 historical suggestions.

**Preservation scope:** all 16 specifically headed proposed options are now addressable with source lines. Their status remains producer-translated Research, not complete conservation of the 2,935-line original or independent semantic review.

## 12. Late source topic 04: sixteen physical and semantic Artifact boundaries

The dated Artifact and Result Management Research identifies several distinctions between computed values, Artifact identity, physical bytes, file revisions, host-local paths, evidence of publication, and user permissions. Its **16 bounded English source-line interpretations** below retain specific failure cases and scope limitations. The observed failed-step artifact-card behavior and possible aggregate false success were **also confirmed in pinned Windows code** and added to [Current HOW](../../current-how/windows-application.md). Those observations are not evidence of a confirmed user data-loss incident.

| Source proposition | Source-grounded material meaning | Qualified status | Frozen source line |
| --- | --- | --- | --- |
| `SB-SRC-0557/ART-01` | FileStore byte operations are physical primitives, not a universal verified Artifact identity or publication API. | `FILESTORE_LEVEL` | L98 (`#L98`) |
| `SB-SRC-0557/ART-02` | A locally created ArtifactRecord may exist even when the output path does not, and contains no content digest or publication status. | `CURRENT_RECORD_LIMIT` | L115 (`#L115`) |
| `SB-SRC-0557/ART-03` | Current ScenarioRunner builds artifact cards for every operation output regardless of the operation success flag. | `DIRECT_CODE_FALSE_POSITIVE` | L132 (`#L132`) |
| `SB-SRC-0557/ART-04` | The operation-result object carries only a Boolean status, message, output paths and details; it does not attest published bytes. | `RESULT_CONTRACT_WEAKNESS` | L140 (`#L140`) |
| `SB-SRC-0557/ART-05` | A logical Artifact is not the same as the file bytes or a particular location of those bytes. | `SEMANTIC_ARTIFACT_IDENTITY` | L175 (`#L175`) |
| `SB-SRC-0557/ART-06` | One economic Result can have XLSX and CSV materializations; identical paths and identical underlying meaning are different relations. | `MULTI_REPRESENTATION` | L178 (`#L178`) |
| `SB-SRC-0557/ART-07` | A user-managed relocation does not erase the historical artifact record, although its old path may be unavailable without automatic rediscovery. | `EXTERNAL_MOVE_LIMIT` | L188 (`#L188`) |
| `SB-SRC-0557/ART-08` | A new calculation overwriting an earlier filename is generally a new content revision or Artifact, even with the same path. | `VERSION_LINEAGE` | L191 (`#L191`) |
| `SB-SRC-0557/ART-09` | File existence after a failed or partial write is not evidence that a workbook was validated or published. | `EXISTENCE_NONPROOF` | L458 (`#L458`) |
| `SB-SRC-0557/ART-10` | A minimal staged-file publish sequence requires completed staging, controlled finalization and an authoritative ready event; metadata detail may be proportional. | `PUBLISH_EFFECT_ORDER` | L477 (`#L477`) |
| `SB-SRC-0557/ART-11` | Filesystem bytes and relational metadata do not form one native ACID transaction; recovery must handle a committed file with missing metadata or vice versa. | `CROSS_PLANE_RECOVERY` | L481 (`#L481`) |
| `SB-SRC-0557/ART-12` | A package of independently useful files may validly be PARTIAL; all-or-nothing generation publishing is needed only for a genuinely consistent set. | `GROUP_PUBLICATION_COST` | L495 (`#L495`) |
| `SB-SRC-0557/ART-13` | Backend outage/denial must not be silently transformed into MISSING merely from an unsuccessful existence check. | `AVAILABILITY_TRUTH` | L565 (`#L565`) |
| `SB-SRC-0557/ART-14` | Visibility of an Artifact card does not entail permission to read its bytes or perform further effects on it. | `CARD_NOT_AUTHORITY` | L599 (`#L599`) |
| `SB-SRC-0557/ART-15` | Shared chats do not make host filesystem bytes anonymously available; remote authorization is checked by the actual host authority. | `SHARED_WORKSPACE_ACL` | L610 (`#L610`) |
| `SB-SRC-0557/ART-16` | An agent should use an authorized Artifact reference rather than arbitrary host paths; resolved access still requires scoped permission checks. | `AGENT_RESOURCE_BOUNDARY` | L627 (`#L627`) |

**Counterarguments:** A manually moved file can legitimately become unavailable in the historical chat rather than requiring aggressive global discovery. A cheap temporary CSV may not warrant permanent content-addressed storage. Conversely, an output path appearing after a failure must not be promoted to an accepted published accounting workbook, and a visible shared chat card does not confer download/delete rights on every viewer. The lowest trustworthy publication assurance is the one actually supported by the backend and observed effect receipt. A high-level staged publication model is a candidate, not installed generic code.

**Preservation limit:** the 16 original rows remain material partial coverage of this 986-line study; complete source-level lossless, the physical user DOCX hash and installed host/web tests remain open.

## Original Windows Study 0020: proposed client, artifact and collaboration maturity (source packet B)

**Source:** frozen 2026-10-06 Windows study, exact blob `225128f2599f0792422c0b31cb3cbe1437991ced`; a dated future-option/release-maturity study, **not** binding architecture, accepted permission semantics or an executed host. Each row retains a competing disconfirming case.

| Address · epistemic role | Original material proposal or observation | Counterexample / limit | Original span |
| --- | --- | --- | --- |
| `SB-SRC-0020/FUT-07` · `HISTORICAL_ARTIFACT_EXPANSION_CANDIDATE` | The proposed Artifact roadmap named preview metadata, lineage, hash, source links, retention, pin/favorite, controlled share/export and chaining. | A path-based ArtifactRecord does not already possess canonical byte digest, accessible generation, ownership grant, retention guarantee or safe remote publication. | L1490–L1502 (`#L1490-L1502`) |

**Evidence status:** a future AI actor label, mobile sketch, host execution backend or artifact field list cannot establish the relevant implementation or rights. This packet is a **producer source transfer**; independent review, complete source accounting and host/client release tests remain open. All frozen source dispositions are still `unaccounted`.

## Original automation Research 0041 — dated roadmap, logical architecture and example machine endpoints

**Frozen source:** primary automation/AI study, Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. These are historical engineering alternatives with explicitly limited authority. A phase number, API-like name or deployment box in the original document is not evidence of an actual provider, Product Decision, accepted schedule or real effect.

| Material address and epistemic role | Source-defined proposition | Defeater, cost, competing choice | Primary lines |
| --- | --- | --- | --- |
| `SB-SRC-0041/ROAD-04` · `HISTORICAL_ARTIFACT_PHASE_PROPOSAL` | The artifact-intelligence phase grouped stable IDs, hashes, lineage, previews, table queries, sensitivity labels and agent-readable resources. | Some outputs require only a path or validated report; a blanket artifact database and AI query engine may overengineer direct Python use. | L2063–L2071 (`#L2063-L2071`) |

**Conservation limit:** this is a producer source-first packet; independent reverse review, empirical release tests and whole-original material accounting remain open. The current accepted Strategy Box host requirement supersedes only conflicting historical ownership/timing assumptions, not the original's record as a real alternative.

## Original automation Research 0041 — state, typed router, bounded agent and artifact-provenance specifics

**Frozen original:** Strategy Box automation/AI study, Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. The entries conserve exact historical design suggestions, evaluation logic and failure constraints. Schema/URI examples are not the accepted runtime implementation; the current application/host and protected effect boundaries require their own authority and execution evidence.

| Address and original status | Material source meaning | Contrary condition or denied inference | Primary source span |
| --- | --- | --- | --- |
| `SB-SRC-0041/ART-01` · `HISTORICAL_EXPANDED_DESCRIPTOR` | The historical Artifact descriptor enumerated stable ID, carrier kind/MIME/URI, hash, size, creation chain, parent/source snapshots, schema/period, sensitivity, query and retention fields. | Making each optional field mandatory for every output increases storage/cost and cannot guarantee any bytes were verified or permission granted. | L727–L751 (`#L727-L751`) |
| `SB-SRC-0041/ART-02` · `HISTORICAL_HANDLE_AND_TOOL_SURFACE` | Artifact IDs and controlled get/preview/table-slice/compare/export/open tools were proposed instead of arbitrary filesystem paths for future agents and cross-device clients. | An opaque ID by itself is not a capability grant; each read/export must check current resource permission, output generation and actual availability. | L753–L775 (`#L753-L775`) |
| `SB-SRC-0041/ART-03` · `RESEARCH_CONTEXT_ECONOMICS` | The study called for bounded table descriptions and filtered column slices rather than inserting whole million-row tables into a model context. | A query limit does not automatically prevent expensive scans, inference of restricted rows or loss of significant outliers beyond the sampled slice. | L776–L794 (`#L776-L794`) |
| `SB-SRC-0041/LINEAGE-01` · `HISTORICAL_PROVENANCE_GRAPH_PROPOSAL` | The source required tracing from original snapshot through canonical and derived data to Excel/report and proposed produced-by/input/source/registry/parameter links on artifacts. | An incomplete lineage graph can make false reproductions; actual consumed inputs and output digest/receipts must be established, not inferred from intended dependencies. | L800–L829 (`#L800-L829`) |

**Scientific qualification:** the historical proposal makes no claim that SQLite, agent orchestration, a broad catalog, Artifact query APIs or a production machine-provider bridge were implemented. An application can use a deterministic direct Python operation with no large shared Work/Agent database. Conversely hosted cross-user effects and sensitive resource handles require independent permission, replay and proof-of-publication boundaries. These meanings are producer-traced only; no independent reverse review or complete original source disposition is asserted.

## Original Windows Study 0020 — executable Scenario, Case, Artifact and local-log limits

**Frozen study:** exact original Windows research, Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`. The study's optimistic characterization is qualified by [current direct code](../../current-how/windows-application.md) and 14 executed synthetic Windows Python source-characterization cases in Knowledge CI. Current observations, candidate target safeguards and source's historical opinion stay separate.

| Original position and evidence role | Primary material interpretation | Failing or limiting case | Original lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/RUN-10` · `DIRECT_CODE_WITH_EXECUTED_LOG_CASE` | ArtifactRecord records a random ID, local file path/type, author and Case/Operation context, inferring kind substantially from suffix. | A declared Excel/log kind or ID does not prove bytes exist, content validation passed or recipient may fetch the file; WEX-04 logs are ArtifactRecords even on failure. | L737–L755 (`#L737-L755`) |

**Status:** producer source-to-Science text preservation only, not accepted fixes, a host execution proof or independent semantic review. Static original source properties and successfully executed negative tests supply different evidence strengths. Source-wide `SB-SRC-0020` material state is `unaccounted` and no whole-file Research Amputation passed.

## Original May 2026 patch note: banking-file semantics and mutable-source limits

**Primary historical corpus:** May 2026 public-patch summary, exact pinned Git blob `a2339ebc79f72a075d290b761fda7b8997b15710`. The note is a **dated developer implementation summary**, not a current code-level conformance certificate; only public-safe domain consequences are included here. Current modules, official data and execution effects need their own evidence. Physical and restricted deployment internals are outside this Science scope.

| Original position and epistemic status | Source meaning | Counterexample or missing proof | Frozen original span |
| --- | --- | --- | --- |
| `SB-SRC-0015/FRG-04` · `HISTORICAL_MUTATING_FILE_PIPELINE` | Cleanup could copy or rename selected files, remove old recognized entries and build a dated FRG ZIP bundle. | Current direct FRG fault tests reproduced replacement-before-failed-copy/rename and archive-replacement hazards; an early summary claiming safe cleanup is not effect-atomicity proof. | L37–L39 (`#L37-L39`) |

**Scientific boundary:** these are twelve source-positioned historical statements across bank reporting, FRG, escrow and raw-source collection, with error, identity and version qualifiers. They do not certify content correctness, deployed package behavior or a complete independent source-to-Science audit. Any restricted source material remains outside public Science.

## Original business-logic refactor study 0016: domain capability, product layer and FRG pilot

**Source character:** dated historical primary study, exact Git blob `d04fece78c89063c2ac2dac775179f1517c7fea9` (1,927 physical lines), with an older in-core GUI layout that was superseded by the independent Windows repository. This source's domain and process proposals are preserved as conditional Science; the adopted application-host scope and existing core/source implementation retain separate authority.

| Source-material address / epistemic status | Original reasoning or candidate | Counterexample / present limit | Primary source location |
| --- | --- | --- | --- |
| `SB-SRC-0016/ART-01` · `HISTORICAL_RESULT_PRESENTATION_OWNER` | The source allocated the choice of primary output, timeline appearance, artifact actions and result labels to product projection rather than to raw domain parser internals. | Product layout cannot assert computed success if required steps or published bytes failed, or mint authority over raw technical logs. | L1729–L1739 (`#L1729-L1739`) |

**Coverage and authority:** the old plan's exact capability names, file paths and suggested sequence are not current public APIs, not guaranteed FRG effect safety and not accepted release architecture. This packet is producer source-position routing only; extensive original remaining material and independent evidence/reverse checking remain open.

## Original Topic 04: concrete Artifact alternatives, output status and permission countercases

**Primary dated source:** Strategy Box Artifact Research Topic 04, exact Git blob `57ae0d79c91b8a5839668f73abfd7af4284f1142`. Twelve source-defined material distinctions preserve original examples, competing design costs, and cases where future Product consent is required. These are producer source readings, **not** a currently installed server Artifact contract.

| Original unit and role | Source-supported meaning | Rejected inference / countercase | Exact source span |
| --- | --- | --- | --- |
| `SB-SRC-0557/ALT-01` · `RESEARCH_MINIMUM_ONTOLOGY` | The source separates an analytical result, file bytes, a concrete content revision, an Artifact identity and a materialization locator as five concepts, while expressly rejecting five mandatory tables in an MVP. | One result can yield XLSX and CSV while a file can exist outside an Artifact; collapsing them into a path string breaks later capability/evidence reasoning. | L168–L180 (`#L168-L180`) |
| `SB-SRC-0557/ALT-02` · `RESEARCH_IDENTITY_VS_AVAILABILITY` | A user-driven external file rename keeps the historical Artifact identity but can invalidate its locator; application-controlled relocation may update locator, while changed bytes or recomputation need qualified new revision identity. | Stable metadata ID does not warrant background search for moved files, restored bytes or proof of unmodified contents. | L182–L194 (`#L182-L194`) |
| `SB-SRC-0557/ALT-03` · `RESEARCH_EVIDENCE_PRESERVATION` | Availability is a new observation about a historic Artifact and must not retroactively erase the creation record; mutable user file and managed immutable revision are separate profiles. | A path that is now missing says nothing by itself about whether the original analytical computation was correct or its earlier bytes were retained. | L196–L222 (`#L196-L222`) |
| `SB-SRC-0557/ALT-04` · `HISTORICAL_COMPETING_ARCHITECTURES` | The study compared path-only cards, path plus validated readiness/catalog, selective staging/snapshots, full content-addressed storage and a complete data platform, preferring the proportional catalog-plus-validation minimum. | A full CAS duplicates editable large exports and increases garbage collection/retention burden; path-only cards risk false completed results. | L228–L238 (`#L228-L238`) |
| `SB-SRC-0557/ALT-06` · `RESEARCH_DATA_CONTRACT_PROPOSAL` | The proposed minimal ArtifactRecord v1 used stable ID, kind, display, scoped locator, origin, publication state and availability checked separately; UI selection, unread and visual pinning remain outside stable creation metadata. | An illustrative schema cannot make raw local file path an authorized client capability or imply fields exist in pinned Windows ArtifactRecord. | L334–L370 (`#L334-L370`) |
| `SB-SRC-0557/ALT-07` · `RESEARCH_EFFECT_TRUTH_REQUIREMENT` | The research proposed typed output roles primary, secondary, source bundle and diagnostic, each with its own publication status or pending locator, instead of reducing OperationResult to paths. | A failed operation can create diagnostic .log while the required analytical report is absent; conflating log with primary output misleads Case cards. | L402–L419 (`#L402-L419`) |
| `SB-SRC-0557/ALT-08` · `RESEARCH_PER_OUTPUT_COMMIT_MODEL` | The source recommends staged file writes, verification and metadata registration, distinguishing individually ready outputs from overall Run status and allowing already-published files before later Step failure. | A successful file close is insufficient for remote publication; a completed Run is not necessary for each valid earlier output, and catalog/file writes lack automatic cross-store transaction. | L447–L516 (`#L447-L516`) |
| `SB-SRC-0557/ALT-09` · `RESEARCH_TYPED_AVAILABILITY_AND_RECOVERY` | The source distinguishes file MISSING after a verified reachable locator from ACCESS_DENIED, BACKEND_UNAVAILABLE, CHANGED and OUTCOME_UNKNOWN, requiring preservation of historic metadata and bounded reconciliation after restart. | Current LocalFileStore empty listing on an absent path cannot certify a remote file is truly missing; never treat storage outage as user deletion. | L563–L593 (`#L563-L593`) |
| `SB-SRC-0557/ALT-11` · `HISTORICAL_PORTABILITY_UX_CANDIDATE` | The proposed user interaction keeps results in ordinary working Data folders, checks availability on requested open, displays per-output partial successes and provides optional safe streaming/preview for Web or Android. | A future platform-neutral operation may expose metadata without enabling arbitrary remote path access; full in-app spreadsheet rendering is not required for MVP. | L633–L664 (`#L633-L664`) |
| `SB-SRC-0557/ALT-12` · `RESEARCH_TENSIONS_AND_OPEN_PRODUCT_CHOICES` | The original explicitly reconciles persistent Artifact identity with no automatic relocated-file search, per-output ready while Run continues, technical logs outside user Data and versioned snapshots alongside editable XLSX. | Defaults for failed-Run partial outputs, overwrite, retained snapshots, card visibility and default Artifact meaning still require human Product decisions. | L826–L872 (`#L826-L872`) |

**Scientific limit:** creation history, current availability, byte retention, publication status, run completion and recipient authorization are separate evidence roles. This packet does not guarantee source-wide original losslessness, external filesystem semantics, implemented storage providers or independent semantic validation. The source remains `unaccounted`.

## Source-led native POSIX storage challenge: create-only versus overwrite and byte generation (2026-10-12)

**Source and evidence class.** The original Artifact research `SB-SRC-0557` proposes staged complete writes, verified bytes, acknowledgement and a catalog-level publication receipt, while expressly distinguishing a path from the exact content generation. A new **directly executed native experiment** on ordinary temporary Linux CI files tests eight constrained POSIX operations, not the Strategy Box target Windows/SMB backend. [CI 38221344760](https://github.com/ForestTiger-GH/stratbox/actions/runs/38221344760) at `ee40ca1794c3d3b5409df55110b92a9b43b953b6` **SUCCESS**. The experiment is a test of concrete kernel-mediated behavior under controlled mutation, not a production publisher.

The observed properties refine the proposed effect contract:

1. **Earlier containment check is not an authorization capability.** Resolve and approve a relative path; replacing the final component with an out-of-scope symlink before `open()` causes a later naïve read to access the target. On this Linux test, `os.open(..., dir_fd=opened_parent, O_NOFOLLOW)` rejects *that single final symlink component* with `ELOOP`. This does not establish safe arbitrary nested traversal or Windows reparse-point protection.
2. **Inode, name, file descriptor and byte content are separate identities.** A second writable descriptor can change the bytes under an already-open descriptor while `st_dev`, `st_ino` and `st_size` stay fixed. Consequently, an open FD by itself is not the immutable generation guarantee requested by the [Artifact LCD](../../lcd/artifacts/local-output-publication-construction.md).
3. **An atomic pathname replacement is not expected-generation compare-and-swap.** In the test, a competing writer changes the target after precheck; `os.replace(staged, target)` then overwrites the intervening winner. Ordinary rename atomic visibility and conditional mutation of an *identified target version* are different guarantees.
4. **A narrow create-only primitive can preserve an existing target.** POSIX `os.link(staged, target)` raises `FileExistsError` when the target name is occupied, and creates a previously unused name when free. This is bounded evidence for *no-clobber name creation* under that local POSIX profile, **not** for overwrite, immutable file content, crash durability, Windows semantics, cross-device links or an atomic database+filesystem publication.
5. **Timestamp is not byte generation.** Identical bytes at different observation times remain byte-equal. The source identity receipt may preserve observation time for chronology while actual hash and generation control publication equivalence.

**Boundary:** the candidate `StagingSeal` must be enforced by the **selected actual backend**, including all reads and the final conditional effect; matching a dataclass, path/mtime, ordinary FD or rename cannot substitute for it. A stable source hash also does not independently prove that the publisher is authentic, the XLSX semantically valid, or the recipient entitled to read the output. Host policy, file backend, conflict semantics and physical durability must be decided and tested by the relevant owners. These experiments do not close original-source independent semantic review or establish implementation readiness.

## Original Topic 04 — twenty exact output/publication failure cases and five storage conformance profiles

The frozen Artifact Research `SB-SRC-0557` §15 (L783–L824) proposed **twenty locally scoped `A01..A20` candidate checks**, then separate profiles for NTFS, Linux/POSIX, SMB/NAS, object storage and remote host/client. Previous source-aware Science preserved object identities, five-valued availability, per-output partial success and staging principles, but the precise **one-to-one test stimuli and expected distinctions** were distributed across articles. This table conserves each original identifier **without claiming the candidate host/filesystem has been tested**. All twenty are `SOURCE_RESEARCH_TEST_INTENTION / NATIVE_TARGET_UNEXECUTED`; a prior isolated core/Windows fake characterization is distinct evidence and cannot upgrade the whole row.

| Frozen original test | Specific tested stimulus | Proposed discriminating evidence and falsifier |
| --- | --- | --- |
| `A01` | Normal XLSX export completes publication. | Ready file is actually reachable and its Artifact card is linked to the correct Run **and Step**; a successful domain DataFrame alone is insufficient. |
| `A02` | Writer raises after opening/partially writing output. | Partially written output is **not** a ready Artifact; preserve error and staging/quarantine distinction. |
| `A03` | Handler returns a success result with a path that never existed. | Publication must be denied/failed and no ready card generated merely from the returned path. |
| `A04` | Failed Operation emits a useful diagnostic log file. | Diagnostic result can exist independently while **primary** analytical output is absent/failed; do not turn the log into a successful report. |
| `A05` | One of several generated files fails publication. | Other individually verified files remain ready with their own receipts; failed output remains separately failed even if total Run is partial. |
| `A06` | User renames published working file in native Explorer. | Old locator reports `MISSING` when checked, retains origin, and does **not** trigger an unauthorized filesystem-wide digest/name search. |
| `A07` | User moves that file to a different folder. | Old location is `MISSING` while the logical Artifact's provenance persists; relocation is not automatically discovered. |
| `A08` | User deletes the working file. | Artifact access is disabled/unavailable, and the system does not silently restore an unwanted file from an unapproved archive. |
| `A09` | Backing storage or network share is temporarily unavailable. | Return `UNAVAILABLE`, not a confirmed `MISSING` or evidence of user deletion. |
| `A10` | Object exists but current principal has no read permission. | Return `ACCESS_DENIED`, not `MISSING`; error payload must not reveal confidential path or protected existence. |
| `A11` | Publisher attempts replacement while `overwrite=false`. | Existing bytes remain intact; any failed candidate is staging/error, not a destructive pre-delete. |
| `A12` | Two workers concurrently publish to one requested path. | Compare-and-publish or deterministic distinct names yields a conflict; no hidden last-write-wins when overwrite is prohibited. |
| `A13` | Crash after physical finalize, before catalog registration. | Recovery uses recorded publication intent and actual generation; no unproven ready card and no blind duplicate write. |
| `A14` | Crash after durable catalog commit, before UI refresh. | Restart returns the already committed card/Artifact ID without publishing the same bytes again. |
| `A15` | Persisted state JSON or ledger is corrupted. | Explicit diagnostic/recovery outcome rather than silently replacing legitimate historical work with an empty timeline. |
| `A16` | Operation yields a legitimate result without a file. | A structured message/value/preview is possible, and physical Artifact ID is optional rather than invented. |
| `A17` | One result is a directory containing many mutable files. | Directory/card identity does not falsely promise an immutable byte bundle; visibility/availability are per qualified resource policy. |
| `A18` | File access tries `../` traversal or a symlink/reparse escape. | Verified root containment at actual mutation/open, not only string normalization or a pre-effect lexical check. |
| `A19` | An output is opened through another Thread/Chat context. | Originating Run, Step and author/caller identity remain correct; read still requires the current recipient's authorization. |
| `A20` | Two different Runs generate files bearing the same display filename. | Distinct logical Artifact identities survive name collision; location overwrite policy and per-Run history must not be conflated. |

**Original §15.2 — storage-profile separation, still UNEXECUTED on installed targets:**

| Profile | Original mechanism requiring independent native conformance |
| --- | --- |
| `NTFS/Windows` | Actual replace behavior with open Excel handles, sharing violations, antivirus locks, unexpected restart, reparse points and file permissions. |
| `Linux/POSIX` | Same-filesystem rename, `fsync(file)` and `fsync(directory)`, symlink race and `EXDEV` across filesystems. |
| `SMB/NAS` | Timeout/ACK loss, actual server-side rename guarantees and visibility, delete/rename permissions and streaming of large files. |
| `Object storage` | Conditional create/overwrite and generation/ETag fencing, interrupted multipart upload, delete markers and version semantics. |
| `Remote host/client` | Authorized Artifact read, streaming and per-client stale cache, reconnect deduplication, and the distinction between remote and local file availability. |

**Scope of verification:** a source-row/owner-route check can confirm these exact twenty identities and the five distinct backend topics, but **cannot** test a physical disk, remote service, user authorization or the validity of a rendered banking report. Artifact identity, file availability, catalog intent, output role, failure status and independent Run completion remain different claims. No Product Decision presently chooses universal immutable file snapshots, desktop automatic recovery, mandatory cloud storage or a particular backend transaction engine.

## Historical refactor 0016 — domain-by-domain candidate operation boundaries

A dated whole-product refactor proposal compared **existing reported domain APIs** and optional candidate changes. These Research statements are historical descriptions and design alternatives; the current `stratbox` codebase, tests and independently verified exports own present behavior. A candidate domain operation ID or type is not necessarily a shipped symbol or Product Decision. The original source contrasts proportionate canonical use cases with an indiscriminate global registry, and explicitly resists imposing a universal maximal metadata shape.

| Dated original route | Conserved difference and mechanism | Counterargument or evidence constraint | Frozen original source |
| --- | --- | --- | --- |
| `SB-SRC-0016/DOMAIN-08` · `HISTORICAL_OUTPUT_ROLE_AND_PREVIEW_OPTION` | The Artifact subsection expressly distinguished primary and secondary outputs, whether a result supports preview, and eligibility for product or external-platform presentation without mandating an oversized Artifact class. | Output kind and preview metadata do not certify the bytes, their availability or the viewer's authorization; actual published identity, source evidence and effect status stay separate. | L1564-L1574 (`#L1564-L1574`) |

**Proportionality and authority:** domain type declarations, product choices, authorized external exposure, verified published files and direct notebook consumption are distinguishable even when one physical implementation supplies several. This bounded producer packet does **not** imply a physical `stratbox-application` service, accepted new names, verified runtime support or full-original losslessness.
