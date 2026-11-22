# CBR publication registry and independent processing routes

Scope: the implemented CBR material and dataset routes in Stratbox 0.18.0.
Across the supported family routes, source acquisition, extraction, integration,
calculation, view preparation and rendering have explicit operation boundaries.
Exact originals, source
flakes, integrated tables and prepared products can each be retained through
caller-selected adapters and read again before continuing the route.

The implementation supplies the registered operations, their domain codecs and
reference file/memory dataset adapters. Runtime scheduling, mounted shares,
application database ownership and publication into an external corpus remain
explicit consumer responsibilities.

## 1. Identities and registries

`stratbox.domains.cbr.publications` is the common publication catalog. It keeps
three kinds of information separate:

| Registry value | Responsibility |
| --- | --- |
| `SourceSeries` | Stable logical series, family, issue model and supported format variants. |
| `AcquisitionProfile` | Official default acquisition route and filename recognition rules. |
| `ProcessingProfile` | Exact registered operation/version, accepted variants and interpretation scope. |

A URL, filename or file-store location is an acquisition detail. A publication
identity consists of `series_id`, `issue_id` and `asset_id`. Observation periods
inside a release remain separate domain values. Byte identity identifies the
exact retained edition, including revisions to an existing publication issue.

The catalog currently contains 57 series in 11 families:

| Family | Series | Implemented scope |
| --- | ---: | --- |
| `cbr.household_lending` | 6 | Original acquisition and retention. |
| `cbr.corporate_lending` | 17 | Originals; independent 0105a/0104a routes; explicit SORS input dependencies. |
| `cbr.securities` | 1 | Original acquisition and retention. |
| `cbr.borrowings` | 9 | Original acquisition and retention, including the separate escrow-balance series. |
| `cbr.household_assets` | 2 | Original acquisition and retention. |
| `cbr.monetary_statistics` | 6 | Original acquisition and retention. |
| `cbr.external_debt` | 3 | Original acquisition and retention. |
| `cbr.other_statistics` | 2 | Original acquisition and retention. |
| `cbr.reporting_forms` | 8 | All-member source extraction; six financial normalization/model families. |
| `cbr.project_finance` | 1 | Regional escrow XLSX flakes, integration, prepared views and rendering. |
| `cbr.service_network` | 2 | Bank/region and territorial releases, evidence-preserving snapshots and replay. |

These counts describe registered series, not reviewed historical completeness
or 57 independently implemented analytical parsers. An absent extraction profile
means that the catalog offers original retention only. SORS input parsers remain
bounded components of its explicit input bundle.

`cbr.publications.list_sources` can filter by family. `discover` accepts a supplied
index or acquires the declared index through an HTTP provider. Fixed-file routes
can be listed without a network call; availability remains unverified. An index
inventory records its exact input identity, candidate variants and rejected
links. Discovery does not manufacture absent historical releases.

`cbr.publications.identify` admits supplied material under explicit series,
issue, asset and format context. It verifies the relevant format boundary and
returns an original artifact. The context is caller-supplied; it is never
promoted into publisher-origin evidence merely because bytes came from a file
whose name resembles a public release.

## 2. Collections and independently selected stores

`cbr.file_collector.collect_materials` accepts a heterogeneous selection. Each
item can use exactly one supplied payload, pinned material reference or explicit
HTTP URL. Fixed publication profiles can also provide their registered default.
Each item can choose a named provider; one batch can read several independent
stores while leaving physical locations outside its logical identity.

An explicit failed input remains a failed input. The collector never substitutes
an Internet download for a missing retained file. With `continue_on_error=True`,
later independent items may still succeed. The result retains completed originals
and a disposition for every selected item: completed, failed, unsupported,
not attempted or unknown, according to the producer's observed outcome.

`CollectionManifest` is a shared contract, usable outside CBR. It records ordered
member names, exact hashes and sizes, media types, semantic roles, optional source
asset and artifact descriptor identities, input evidence and source coverage.
It carries neither a target path nor a destination provider. `manifest.complete`
describes the selected batch; `manifest.coverage` describes the claimed source
universe. A successfully collected batch can have unknown historical coverage.

The original fixed-file collector still offers a 41-item convenience selection,
derived from the common registry. Its in-memory and streaming ZIP operations now
embed the same common `manifest.json` format. The source files remain exact
originals; the generated archive has a separate product identity. A convenience
archive of successful files states that earlier failures and historical coverage
are unspecified. The richer collection route can retain its complete disposition
ledger when packaging the corresponding selected members.

`material.archive` accepts supplied bytes and references from independent stores.
Nested relative POSIX names support structures such as
`regulatory-reporting/2026/2026-10-01/form-0409803/nested/A.csv`.
Manifest membership, hashes and media types are checked before publication.
Case/Unicode aliases, traversal and file-versus-directory name conflicts fail.
Archive resource limits are explicit and no longer impose the former 500-member
streaming ceiling.

## 3. Processing boundaries by family

| Route | Source-local value | Integrated or calculated value | Presentation value |
| --- | --- | --- | --- |
| Reporting forms | All regular archive members and decoded DBF records | Selected normalized history and bank/model calculations | Form views and XLSX, or source CSV collection |
| Corporate debt 0105a | Publication-local regional debt observations | Selected debt stream and APK calculation | Prepared debt pivots and XLSX |
| Corporate issuance 0104a | Publication-local issuance observations | Monthly flow stream and APK calculation | Prepared issuance pivots and XLSX |
| Project finance/escrow | Source cells, row/column dimensions, tokens and statuses | Selected period history and indicator definitions | Prepared views and formatted XLSX |
| Service network | Qualified ParsedRelease or explicit ambiguous territorial candidates | Release comparison; complete retained evidence | Existing neutral and tabular outputs |
| SORS restoration | Publication observations loaded by composition; reusable 0105a flake | Validated source bundle, strict restoration grids and classification crosswalk | Pivots and workbook outputs |

Every supported snapshot codec reconstructs the complete domain value required
by its next operation. It preserves types, axes, source context and lineage,
rather than restoring a single display table and guessing the omitted context.
Domain restoration requires all declared components. Generic selected-component
reads remain available for inspection.

SORS `load_sources` remains a declared composition of source extraction and
semantic integration. Its validated `SorsSourceBundle` already has the
`integrated` role. A separately retained full 0105a flake can supply its regional
debt input without reopening that workbook.

Snapshot constructors encode values in memory and advertise the `render` stage.
`dataset.write_snapshot` performs `ingest` and `preserve` through the receiving
adapter. Domain decoders advertise `read_extract`. This classification describes
the actual operation boundary and does not turn a prepared snapshot into a
confirmed durable write.

The family guides document exact API names and admission rules:

- [Reporting forms and notebook-style DBF exports](cbr-reporting-forms.md).
- [Corporate lending flakes, streams, calculations and views](cbr-corporate-lending.md).
- [Escrow cells, datasets, views and workbook replay](cbr-escrow.md).
- [Service network releases and explicit dates](cbr-service-network.md).
- [SORS dependencies and complete calculation snapshots](cbr-sors-snapshots.md).

## 4. Universal retention and publication

The same storage choices apply at every boundary:

| Value to retain | Neutral operation or interface | Resume point |
| --- | --- | --- |
| Exact original bytes | Source save/read or complete material artifact | Domain identification and extraction. |
| Encoded material with its semantic descriptor | Material save/read/transfer | Matching domain decoder. |
| Complete typed dataset snapshot | Dataset write/read with a pinned reference | Matching domain restore operation. |
| CSV collection and companion schema/manifest | Material save/archive or receiving file adapter | Complete collection decoder where provided. |
| Prepared view snapshot | Dataset write/read | Renderer without original acquisition. |
| Rendered workbook | Material save/transfer/archive | Distribution or user consumption. |

`FileDatasetStore` and `MemoryDatasetStore` implement the same immutable logical
dataset contract. The file adapter preserves canonical typed components, reuses
identical component objects and commits the manifest last. Distinct component
names survive even when their table content is identical. A new process can
reconstruct the adapter, read a pinned version and restore the domain value.

A mounted network share or checked-out Tabularium corpus can be used through a
file provider. A receiver with repository publication rules can accept the exact
original, flake collection, dataset representation or rendered workbook through
its own adapter. A local write proves that write only; remote repository commit,
publication acknowledgement and access policy belong to the receiver. Source
parsers and renderers contain no destination-specific branching.

The complete synthetic offline example is
[cbr_reporting_form_flow.py](../../examples/cbr_reporting_form_flow.py). It retains
a form-803 original, restores its typed DBF flakes through a newly constructed
file adapter, exports a CSV collection and replays that collection. Run from the
repository after installing the required dependencies:

```sh
PYTHONPATH=src python examples/cbr_reporting_form_flow.py
```

## 5. Deliberate limits and extension rules

The initial DBF codec accepts classic text-oriented dBASE III versions `0x03`
and `0x83`, preserving lexical values and physical deletion flags. Memo/binary
fields and other dialects require reviewed profiles. Explicit partial extraction
retains unsupported original members and diagnostics. Forms 134 and 803 have a
source route without a financial normalization model.

Historical escrow HTML remains an original-only variant. The supported regional
XLSX layout has reviewed source extraction and integration. Differences such as
average versus weighted-average rates retain distinct indicator identities;
historical definitions are not merged through title similarity.

Capture date, official as-of date and observation period remain separate.
Ambiguous blocks, unresolved formulas, duplicate releases and conflicting
versions require explicit decisions. A CSV lacking acquisition evidence cannot
recreate that evidence. Its supplied dates remain qualified caller context.

Resource limits, partial source coverage and unavailable adapters remain visible
in operation results. Dataset snapshots are bounded in-memory values; partition
large histories by release or a bounded period set. A future SQL adapter must
preserve the same schemas, identities and commit evidence. Additional querying,
mutable row updates and cross-version transactions require explicit capabilities.

## 6. Verification for this implementation

The 0.18.0 local regression run completed with **1,092 passed and 7 skipped**.
The skipped checks require the separately configured full real SORS dataset or
opt-in performance gates. Synthetic cold-process tests exercised actual HiGHS
restoration and crosswalk computation, retained release comparison, stored-view
rendering and complete form CSV-collection replay.

The release-integrity check, internal-import boundary check, maintained README
link check and offline reporting-form example also passed. The implementation
contains 104 registered CBR operations, including explicit persistence/replay
operations; registry coverage resolves every delegated stage to an available
operation. These local checks establish the implemented contracts and fixtures,
while live publisher inventory, full historical layouts and external receiving
adapters retain their own verification scope.
