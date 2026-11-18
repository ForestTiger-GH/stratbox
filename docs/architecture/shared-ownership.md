# Shared semantic ownership and dependency direction

**Scope and status:** This article defines the implemented responsibility boundaries of the shared library; it does not establish source accuracy or an application deployment. It distinguishes the five independently evolving semantic owners from executable technical operations and domain-specific interpretation.

## Navigation

1. Ownership table — which package contains each type of meaning.
2. Dependency graph — permitted import directions and forbidden couplings.
3. Provenance versus data identity — preservation of computation meaning.
4. Reference authority — explicit editions, names and scope limits.
5. Domain boundary — localized parser integrations without rekeying data.

## 1. Ownership table

| Code | Owner | Authoritative responsibility |
| --- | --- | --- |
| SH-I | `shared.identity` | Exact byte digest/size and canonical manifest encoding. |
| SH-E | `shared.evidence` | Exact source payloads, acquisition, used-input, material, publication and write receipts. |
| SH-D | `shared.data` | Dataset versions, computation receipts, observations, releases, comparisons, representations and table identity. |
| SH-R | `shared.reference` | Manifest-pinned packaged reference editions, material verification, bank and classification data, approved name mappings. |
| SH-T | `shared.time` | Date-only calendar grids and periodic anchor points. |

## 2. Dependency graph

```text
             domains  ------> core
                |               |
                v               v
              shared (reference, data, time)
                |                 |
                v                 v
             evidence  --------> identity
```

`identity` has no dependency on `evidence`, `data` or `reference`; `evidence` depends on `identity` but not on concrete references; `data` can use evidence and identity, not specific registries; `reference` can reuse the pure semantic contracts. Shared modules never import executable `core` or any `domains`. Generic network, storage, format decoding, scheduling, observability and notifications belong to `core`. Publishing criteria and source interpretation belong to the relevant domain.

## 3. Provenance versus data identity

The pair `ByteIdentity(sha256, size)` is a reproducible byte statement. `DatasetVersion` hashes exact inputs, method and output identity; `ComputationReceipt` associates a computation with its claimed lineage; `Observation` carries an observation perimeter, metric and value status. Those models do not prove that source bytes are authoritative or that an inferred number is economically valid. Modules are relocated without changing the logical operation identifiers, status vocabulary or evidence failure classifications.

## 4. Reference authority

A `ReferenceEdition` selects explicitly declared assets; `LoadedReference.snapshot_identity` represents a stable hash over role/path/byte identities. Each `read(role)` verifies the asset bytes against SHA256 and size before parsing, and optional `UsedInputReceipt.version` identifies the selected snapshot. An edition may contain multiple related files; no `mtime`, URL, directory iteration order or filename alone selects the active edition. A null publication date asserts no publication date.

The bank registry contains an official workbook and separately maintained name aliases and selection policies. OKVED2 references contain classification rows and publication metadata. Geography aliases assert a reviewed relationship between a label and an explicitly namespaced subject; a territory's identity is separate from the statistical perimeter of a particular series.

## 5. Domain boundary

Parser-local source structures, period restrictions, geographic ordering, numeric parsing, source officialness, crosswalks and metric definitions remain owned by domains. Pilot consumers may request read-only name diagnostics. They do not mutate published literal columns, source codes, observation fact hashes or the CBR 96-row source layout. An unresolved or ambiguous name never yields a fabricated SubjectRef.
