# Independent standard data stages

Stratbox exposes material handling, physical decoding, semantic alignment,
retention and publication as separate commands and operations. Every call uses
the canonical capability catalog, preparation, admission and execution session.
Supplying a retained extract or view requires no source acquisition.

The supplied stages preserve the scope actually observed. Workbook decoding
preserves decoder-visible cells and formula evidence. Document decoding preserves
ordered DOCX body blocks, PDF page text or plain text lines, with explicit format
qualifications. Publisher interpretation belongs to a reviewed domain method.

## 1. Material handling and qualified native formats

| Capability | Input | Output |
| --- | --- | --- |
| `acquire.material` | URL and explicit acquisition limits | Original `SourcePayload` |
| `read.material_file` | File provider, path and byte limit | Original payload |
| `read.material_location` | File provider, path and optional expected identity/revision | Payload and verified `MaterialReference` |
| `read.material_reference` | Verified reference and file provider | Identity-checked payload |
| `preserve.material` | Payload, representation or qualified material and destination | Confirmed storage receipt |
| `transfer.material` | Verified material reference and destination | Confirmed destination receipt |
| `reconcile.material` | Prior receipt and source file provider | Verified receipt or an uncertain result |
| `archive.members` | Original archive and optional member names | Bounded members with container/member evidence |
| `archive.pack` | Selected named material members | Bounded ZIP original |
| `material.collection.snapshot` / `.replay` | Collection manifest / encoded manifest | Encoded manifest / qualified collection |
| `qualify.csv` | Native CSV, explicit schema/role and optional exact columns | Same bytes with a declared role and structural assessment |
| `qualified.snapshot` / `.replay` | Qualified material / portable encoding | Encoding / exact material, role and evidence |

CSV admission validates encoding, header uniqueness, row widths and resource
limits. It establishes structural validity. Economic meaning still requires the
appropriate source interpretation. One native CSV can have several independently
declared roles while retaining one physical byte identity.

Preservation uses an immutable create or an explicit expected-revision replace.
Acquisition and preservation have separate effects and receipts. Unknown write
outcomes require reconciliation rather than an automatic second write.

## 2. Physical evidence and semantic replay

`workbook.extract` and `document.decode` accept supplied originals with an explicit
series and issue identity. `readable.workbook` and `document.readable` produce
readable representations without assigning economic meaning to source fields.
PDF text is qualified as text extraction; table geometry and OCR remain outside
that decoder profile.

The following type-specific operations produce or restore logical snapshots:

| Value | Snapshot operation | Replay operation |
| --- | --- | --- |
| Observation batch | `observations.snapshot` | `observations.replay` |
| Integrated batch | `integrated.snapshot` | `integrated.replay` |
| Prepared view | `view.snapshot` | `view.replay` |
| Workbook evidence | `workbook.snapshot` | `workbook.replay` |
| Document evidence | `document.snapshot` | `document.replay` |

`snapshot.encode` creates a self-contained portable byte representation from a
complete logical snapshot. `snapshot.decode` verifies its fixed codec vocabulary,
component identities, table schemas and aggregate cell limit. It imports no
classes from encoded data. Observations retain exact decimals, raw tokens,
reported/withheld/dash/reconstructed distinctions, periods, units and scales,
source uses, lineage, profiles, reference fingerprints and assessments.

`save.artifact`, `read.artifact` and `transfer.artifact` retain an encoded value
with a separate semantic descriptor. The descriptor includes representation
evidence and computation lineage. A reference becomes available only after both
the data and descriptor have confirmed storage receipts. Descriptor schema
`stratbox.material.v2` carries representation assessments.

## 3. Alignment, ingestion and query

`align.observations` receives a batch, explicit subject/metric mappings and pinned
reference editions. It returns an `IntegratedBatch` in memory. Alignment preserves
source uses and values, records mapping and reference identities, and rejects
collisions at the resulting observation grain. It performs no implicit summation
of national, district or subject aggregates.

Metric renaming preserves omitted unit and definition metadata. A unit or scale
change requires an explicit exact multiplier. Converted reported values become
derived values; reconstructed uncertainty remains reconstructed. Expected and
observed coverage coordinates follow the same admitted mapping.

`resolve.reference_editions` verifies selected bundled reference assets and returns
their edition identities. The canonical reference IDs are
`reference.geography.names`, `reference.banks` and `reference.okved2`.
The catalog binds their editions into computation identity; an explicit reference
vector also participates in integration identity and retained snapshots.

`query.observations` and `query.integrated` select in-memory observations while
retaining source and reference evidence. `snapshot.query` performs bounded typed
component queries with predicates, projection and continuation offsets.

`ingest.observations` separately publishes a complete snapshot through the
`dataset_writer` provider. `query.dataset` resolves a supplied snapshot reference
through `dataset_reader`; `list.dataset_versions` uses `dataset_catalog`. Both
`MemoryDatasetStore` and `FileDatasetStore` support these contracts. Publication
uses immutable dataset/version identity and the common effect authority.

## 4. Comparisons and update planning

`workbook.compare` compares exact physical workbook evidence.
`observations.compare` distinguishes same-grain source revisions from explicit
period comparisons. A period comparison requires one observation per subject,
metric, dimensions and perimeter; duplicate grains are rejected.

`compare.source_versions` receives a candidate version and qualified baseline
state. Logical transition identity includes its predecessor. A source returning
from bytes A through B to A produces a new transition, even though the final
physical bytes can be reused. An unavailable baseline remains indeterminate.

`processing.plan_update` compares observed processing targets with caller-supplied
retained results. Source, schema, method and reference changes trigger
recomputation independently. Missing destinations can be written from a reusable
result. The planner is pure and makes no observation, deletion or delivery claim.

## 5. Products and coherent publication

`view.table` prepares a view from retained observations. `render.table` encodes
that view. `save.product` conditionally saves the encoded bytes. These operations
remain independently callable; changing rendering does not require source
decoding or calculation.

`prepare.release` builds a manifest from confirmed, identity-checked member save
receipts. A claimed input-version vector requires matching per-member vectors;
optional expected member identities pin the exact release membership.
`publish.release` additionally re-verifies the members in the selected output
store before one conditional manifest write, whose effect input basis is the
version-vector digest. An uncertain member
receipt prevents manifest publication while already saved members remain usable.
The supplied publisher supports members in one selected output-store scope.
Consumers verify member identities when resolving a manifest; an external writer
changing a member after the verification step cannot silently change its identity.
Notifications consume journal facts according to their own subscription policy.
