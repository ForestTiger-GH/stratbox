# File and artifact layer Research — material-unit extraction

**Source:** `SB-SRC-0027`, full original L1–L2935, pinned blob `12c68fd388cabd4b5c3b9e228491201d2160a8b3`. 42 provisional units in `units/BASE-STUDY-0027.jsonl`. Stable source ID/revision/blob preserved, source read state marked `full_read`, source material-unit certification stays `unaccounted`.

## Distinctions and competing approaches

The study proposes treating path-based **FileStore** (physical bytes and mutable namespaces), **Workspace** (user-editable files), **Blob** (immutable bytes), **Artifact** (logical identity and manifest), **Artifact Catalog** (metadata/state/query), **SourceSnapshot** (exact externally obtained data) and **Materialization** (one path-based copy) as different objects. A remote client cannot safely use a local host path as globally portable artifact identity.

It compares (A) paths only, (B) sidecar metadata, (C) artifact service/catalog over FileStore, (D) full content-addressed object store and (E) event-sourced artifact infrastructure. The author favors a bounded version of (C), considers small local CAS, and rejects immediate full distributed infrastructure. **Those choices are research evaluations, not accepted Target HOW.** Current Windows artifacts remain path-based metadata and core FileStore is a separate infrastructure contract.

Key candidate invariants: staging and verification before visible catalog commit, immutable committed bytes, reference-aware tombstone/GC, explicit backend capability rather than fake POSIX rename, streaming limits, differentiated `NotFound/Unavailable/PartialFailure`, separation of cache from retained artifacts, byte/provenance hashes, and restricted machine consumer actions. Both implementation and actual guarantees require evidence and owner-approved policy.

**Important non-goals/unknowns:** no assertion of installed BlobStore, CAS, artifact database or remote transport; no accepted SQLite, fixed retention period, release-ready publish API, exact-once effect guarantee or deployed server. The study describes fault-injection scenarios but did not execute them. Its external literature (filesystem abstraction, storage descriptors, provenance standards) is supplementary support, not independent validation of Strategy Box behavior.

**Reconciliation:** earlier published LDD `docs/ldd/artifacts/staged-publication.md` is already marked **CANDIDATE**, which remains correct. This source expands possible mechanisms and alternatives but does not authorize promoting the LDD to implementation or releasing new API fields.

**Next:** original FileStore/format research `SB-SRC-0028`, exact source and IO direct-code checks, then merge artifacts/source/registry Science only after source-to-owner challenge.
