# Source observations, publication vintages and reproducible statistical calculations

**Scientific scope:** what can an analyst establish later about banking and macroeconomic data when one URL may serve revised bytes and the calculation method may also change? This bounded scientific model complements [source identity](source-identity-and-reproducibility.md). `FetchReceipt`, `RunProvenance` and R0–R4 are **research candidates**, not a shipped universal API or an approved Product commitment. A content hash is evidence of byte identity, **not an economic truth guarantee**.

## 1. The analyst's historical-evidence problem

The filename of an XLSX and the economic reporting date do not identify the actual downloaded publication. Publisher edition, acquisition rule, time of observation, actual bytes, Registry version, transformation revision and computed Result can vary independently. A reproducibility claim should answer **which publication, when acquired, what bytes, under which definitions/methods, with which retained inputs and whether a replay actually occurred**. A timestamp is weaker than a digest; a digest without retained bytes cannot by itself replay an earlier calculation. Repeating a calculation cannot prove its economic assumptions.

Late Research topic 09 (`#L14-L35`) reports the developer's preference for an **actual download timestamp, expert responsibility for interpretation, optional links to existing methodology, and no costly exhaustive catalog of every statistic**. The matching primary ten-topic annotated source was subsequently read in full; its original DOCX binary SHA-256 remains **unverified**. The content is supported by primary text, but exact byte identity and Product admission are distinct obligations. This supports a proportionate record of **actually consumed** inputs.

## 2. Six source roles plus the derived Result

| Role | Distinct meaning | Proof limit |
| --- | --- | --- |
| **Authority** | Issuing body and origin of publication | Official website does not prove particular downloaded bytes were issued there. |
| **SourceDefinition** | Discovery/acquisition rule and locator | Same URL can return a revision or HTML error. |
| **FetchReceipt** | One attempt and its observed response | `observed_at`, response status and actual/canonical locator; timestamp is not byte identity. |
| **SourceSnapshot/ByteIdentity** | Bytes actually consumed | SHA-256, size and validation, optional durable immutable copy. |
| **RegistryRevision** | Coherent edition of classifications, mappings and identity rules | Multiple OKVED resources may require a consistent bundle. |
| **TransformationRevision/MethodRef** | Specific method, code, parameters and important dependencies | Same workbook can produce different agricultural-sector results under revised methods. |
| **DerivedResult/Artifact** | Computed value versus materialized document/workbook | Retains links to used source/processing, without becoming a primary publication itself. |

`FetchReceipt` and `SourceSnapshot` are different **semantic roles**, not a mandate for separate database tables for every source file. A small Run manifest may carry both. A newly assembled ZIP and the original downloaded members have separate byte identities; the container digest does not identify every original input.

**Five time axes:** (1) `observed_at/fetched_at` actual acquisition, preferably UTC with precision; (2) `source_published_at`, publisher issue time, possibly UNKNOWN; (3) `reference_period` of the economic observation; (4) `effective_from/to` of classifier, mapping or regulation; (5) `computed_at/exported_at` for calculation and output. An economic series has reporting period `t` and possibly revised **information vintage** `v`. [ALFRED](https://alfred.stlouisfed.org/) and [FRED vintage API](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html) exemplify this. A global bitemporal SQL design is **not** automatically necessary.

## 3. Five different kinds of equality

Equal URL/name says nothing conclusive about bytes; different byte digests demonstrate distinct byte representations. Equal SHA-256 under normal assumptions is strong practical evidence of byte identity, **not publisher authenticity**. Two XLSX archives can differ in ZIP metadata but express the same economic table; equality of values across different methods also does not establish shared provenance. Distinguish **locator equality, byte identity, statistical-semantic equality, method revision equality and output-value equality**.

**Example A — unchanged locator:** July source downloaded in August is replaced at the same URL in October. Two timestamps say when retrieval occurred; two hashes distinguish bytes; retained August raw inputs are necessary for exact replay. A qualified analyst still decides whether revised figures should replace an issued analysis.

**Example B — changing method:** identical XLSX input processed with different agricultural/OKVED group definitions may give different results. Retain `method_ref`, registry revision and core build, separately from input SHA.

**Example C — weak evidence despite exact bytes:** published rounded amount `6` with unit rounding allows latent values `[5.5,6.5)`, **not exact latent `6`**. Byte certainty does not strengthen a solver's assumption tier; see [publication rounding](publication-rounding-and-claim-strength.md).

## 4. Acquire and retain an actual source version

```text
actual request / response
  -> observed_at (UTC) + source identity
  -> canonical versus actual locator, HTTP status, redirect provenance
  -> bytes actually consumed + SHA-256 + size
  -> container / file validation and domain checks
  -> source receipt linked to one Run
  -> optional comparison to previous receipt of same source meaning
  -> optional retained raw snapshot when later replay is material
```

Hash the bytes **actually parsed**: a separate `stat` and later `read` can race with file replacement, binding one checksum to another payload. Read-once/hash-on-read or a controlled immutable snapshot can prevent that mismatch. Streaming hashing needs `O(1)` extra memory relative to input length and `O(N)` work; keeping each additional raw edition needs `O(N)` storage.

**HTTP validators are hints, not SHA-256.** [RFC 9110 §8.8](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8) distinguishes strong/weak `ETag` and `Last-Modified` from a client-computed digest. HEAD alone cannot certify bytes. A conditional `304 Not Modified` can reuse an **available matching cached object**; without retained bytes the result is INPUT_UNAVAILABLE.

| Observation | Bounded supported conclusion | Invalid inference |
| --- | --- | --- |
| Same URL/name, different SHA | Different received bytes | A confirmed official economic correction without publisher/domain verification |
| Different name, same SHA | One byte identity under checksum assumptions | New economic release by filename alone |
| Different ETag, same SHA | Server metadata/validator changed | Underlying economic series changed |
| Same ETag, different SHA | Actual byte difference despite validator claim | Unchanged bytes by ETag alone |
| 304 without previous raw copy | Requested input unavailable | Fresh downloaded payload |
| 200 containing HTML | Format/domain mismatch | Valid empty XLSX |
| Raw available, old parser schema | Schema mismatch, preserve original evidence | Legitimate zero observations |
| Historical URL fails | Fetch failed; old cached object has old freshness | Cached input freshly acquired |
| ZIP reassembled with other metadata | New container bytes | Underlying economic values necessarily changed |

**Source authenticity is separate:** a checksum compares bytes; the publisher may offer identified sources, secure provenance, official checksums or signatures. Record the actual network route separately from canonical publisher identity and redact tokens, sensitive paths and authorization details from shared views.

## 5. Minimal actually-used input receipt

A candidate `BASIC` profile can retain the following without registering every source in a global database:

| Field | Evidence meaning |
| --- | --- |
| `observed_at` | Actual acquisition, distinct from report export time |
| `source_label/source_id` | Publisher/source meaning; global catalog ID optional |
| `source_locator` | Sanitized URL or workspace-relative input path; separate origin and route |
| `sha256 + size` | Byte identity when actually captured; `null` with reason rather than invented digest |
| `outcome + validation` | Distinguish success, fetch error and invalid content |
| `reference_period` | Economic period when source semantics supply one |
| `retained_ref` | Optional immutable raw reference with disclosed retention lifetime |

Derived Results can additionally retain `operation_id`, Run/Case, relevant parameters, core **build revision**, actually consumed inputs and RegistryRevisions. `method_ref` can point to `operation@commit`, `path@revision#anchor` of an existing explanation, official methodological edition or a combination; a pure collector may have no separate methodology document. Mandatory new essays for every formula add work without necessarily adding evidence. A human `method_note` is helpful but does not prove a computation. Multiple parallel Runs require their own identity even with the same timestamp.

**Privacy:** do not publish credentials, Authorization headers, protected filesystem paths, token-bearing query strings, sensitive raw data or private cache names just to make provenance “complete.”

## 6. Replay evidence scale R0–R4 (research proposal, not an industry standard)

| Grade | Defensible statement | Missing or limited proof |
| --- | --- | --- |
| **R0 undocumented** | Result exists without recoverable source/method evidence | Input and method unknown |
| **R1 traceable observation** | Source, observation time and operation known | Old bytes may no longer exist |
| **R2 byte-verifiable** | Digest/size/validation enable verification of a supplied copy | Original raw was not necessarily retained |
| **R3 replay-capable** | Inputs, Registry/method/code revisions, relevant parameters/environment recoverable | Replay may not yet have been executed |
| **R4 replay-verified** | Replay executed, output compared under an explicit criterion, with a test witness | Repeated equality does not prove the economic formula was sound |

Replay ability, **integrity** and **semantic assurance** are independent axes. Even R4 can repeat weak SORS assumptions. If a formerly retained user raw file disappears, replay becomes `unavailable_now` while its digest and original Run can remain. For numerically sensitive methods, solver, numpy/pandas, floating point/Decimal, seeds, locale, timezone, registry and execution configuration may matter; a full `pip freeze` for every ordinary XLSX is disproportionate.

## 7. Direct pinned core evidence: where the chain stops

The generic [HTTP downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) returns `DownloadResult` with status, bytes, error, URL and headers, but **no universal actual-acquisition timestamp or byte snapshot ID**. Retry and minimum-size control do not by themselves give historical provenance.

[Collector contracts](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/contracts.py) expose source IDs/URLs, filenames, sizes and failures, but `CbrCollectedFile` lacks a compulsory per-input digest or observed time. [Downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/downloader.py) rejects obvious HTML and invalid small responses but does not establish semantic validity of every bank value. [File save](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/save.py) writes ZIP or files, with overwrite options, not a universal member-digest manifest. Good **capture points** exist; a universal receipt has not shipped.

**Crucial disconfirmation:** one ZIP helper's filename-keyed dictionary suggests possible overwrites, but the [normal public collection operation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/operations.py) first calls [unique-name normalization](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/file_names.py). Therefore same-name inputs are **not shown** to be lost through the normal collection route. A direct low-level helper caller has different preconditions. This does not solve source-edition retention.

[Escrow sources](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/escrow/sources.py) calculate source ID as SHA-1 of the **URL string**, not response body; revised bytes under the same URL retain that ID. [CBR industries](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_industries/sources.py) may derive reporting hints from filenames, not full publication revision. The [Registry loader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) selects packaged resources using local `mtime`, **not verified official release date**.

Domain-specific differences matter: raw CBR collector, escrow discovery/layout, physical/semantic bank forms, derived industry groupings, SORS detailed solver/evidence/crosswalk, and FRG file maintenance. Generic receipt must **not replace SORS proofs** or assert official source publication for a locally managed FRG input. A user-supplied XLSX should be fingerprinted from bytes actually used and marked `user_provided`.

### Registry bundles: logical edition versus local file timestamps

[CBR bank registry](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/cbr_banks.py) manages names, aliases and lists; [OKVED2 loader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) reads `data/meta/structure` separately. Material replay needs an exact **compatible combination**, not necessarily whichever resource was last copied. Core code revision may pin packaged resources under a reproducible build/manifest but cannot pin files downloaded after installation.

## 8. Ownership, storage and cost

**Core:** actual input capture, timestamp/fingerprint, source semantics, method and Registry refs, domain validation. **Application:** Run linkage, state persistence and audience. **UI:** short readable source/time/availability projection and deeper inspector. **External management platform:** installed-build identity and its own authorized managed storage, **not** economic SourceSnapshot. This is a conditional target responsibility split, not an existing end-to-end storage API.

Data root and protected operational state need not coincide. Proposed raw-capture status progression is `FETCHED → HASHED → VERIFIED_FORMAT → STORED → PUBLISHED`; missing storage acknowledgment requires `OUTCOME_UNKNOWN` and reconciliation, not a fabricated `RETAINED`. [Staged publication LDD](../../ldd/artifacts/staged-publication.md) remains candidate. A possible `CapturePolicy: off/basic/replay` offers proportional storage levels. A small receipt may remain in a Python Result or one adjacent JSON manifest; there is no obligation for a giant global SQL store, separate methodology note per worksheet or machine registration of every value. Protected external data must not be uploaded to public Git without authorization.

## 9. Standards and competing approaches, without assuming one giant stack

[W3C PROV-DM](https://www.w3.org/TR/prov-dm/) models upstream Entity, Activity, output Entity and Agents; RDF/OWL per workbook is optional. [FAIR principles](https://www.nature.com/articles/sdata201618) and [Ten Simple Rules](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285) encourage identity and reproducibility without prescribing one platform. [SDMX](https://sdmx.org/standards-2/) and [DDI Lifecycle](https://docs.ddialliance.org/DDI-Lifecycle/guide/Structural%20Features/Versioning/) fit genuinely versioned statistical structures; [Frictionless Data Package](https://specs.frictionlessdata.io/data-package/), [RO-Crate](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html), [OpenLineage](https://openlineage.io/docs/spec/facets/) and [DataCite](https://schema.datacite.org/versions.html) address different packaging/lineage/publication needs. DVC, lakeFS, Delta Lake and ReproZip offer different retention/replay cost models. None is a compulsory unified stack for a few XLSX workflows, and small receipts do not replace specialist SORS evidence.

**Research-favored minimum, not Product Decision:** actual time, source locator/label, byte digest+size when available, validation/outcome and selected method/Registry refs, with optional raw retention.

## 10. Negative examples for future tests (NOT executed)

| Fault injection | Difference that must survive |
| --- | --- |
| Two HTTP 200 at same URL with different bytes | Two observed hashes/times, one locator |
| Two names, equal bytes | Two locators, same byte identity |
| Same ETag, altered body | Client content digest independent of server validator |
| 304 without retained payload | Unavailable input, not successful fresh download |
| 200 HTML rather than XLSX | Domain validation error, not valid empty data |
| Deleted old raw file | R3 replay unavailable now; original digest retained |
| Replacement between stat/hash/read | Hash of actually consumed payload |
| OKVED data and structure from different editions | Bundle validation failure, no silent relabel |
| Same SHA, different method revisions | Separate method lineage and outcomes |
| Crash after staging before publication | STAGED cannot appear as PUBLISHED |
| Python notebook without GUI | Receipt accessible outside Thread or desktop state |
| Concurrent Runs with same timestamp | Distinct Run identities |
| Token embedded in URL | Shared receipt redacted |
| SORS evidence assumption changes | Equal source bytes do not strengthen domain claim |
| Two XLSX packages with equivalent values | Different byte identity, semantic equality needs validation |
| Different client clocks | UTC precision and uncertainty explicit |
| Storage ACK lost after write | Unknown effect plus reconciliation |
| Package version unchanged but Registry differs | Manifest/content identity detects changed bundle |

These are *proposed* negative tests, not a report of execution. A bounded pilot should prioritize changed bytes at same URL, same bytes under different URLs, HTML invalid content, missing raw for replay, method/Registry revision, Python-only invocation and redaction. Before R3 is promised for effectful storage, failure simulation is needed.

## 11. Open decisions, alternative scopes and reopening

Still open: compulsory SHA per source or selected material inputs; clock precision; retention periods; private/public receipt policy; source IDs without a global catalog; domain provenance volume; `method_ref` grammar; publisher-edition trust; equality criteria for R4; packaged Registry versioning; host/AI/Web presentation; physical storage and publication durability; measured cost.

The conflict between earlier **governed global source catalog** proposals and the user-endorsed lightweight record of **actually used inputs** is resolved conceptually by separating responsibilities: optional curated catalog for recurring critical publishers; per-Run receipt regardless of global registration. Expert economic interpretation remains essential.

**Reopen when:** actual downloader/registry implementation changes, a source receipt/retained store is shipped, publisher validators or reporting editions change, replay becomes a concrete user requirement, authorized Product profile changes, independent integration evidence arrives or material runtime costs are measured. Every CURRENT promise must name exact source, build and deployed profile.

## 12. Additional original-source distinctions: method pointers, artifact carriers, historical registry use

The original Topic 09, §6.4 (`#L277-L295`) distinguished **no separate method**, **versioned domain operation**, **existing internal methodological document**, **versioned publisher/regulatory specification**, and **compound references that distinguish official rules from internal assumptions**. These are research-proposed alternative reference roles, not five required classes or an adopted serialization. A bare link to a mutable `main` page is insufficient to identify an old method; `operation_id + exact build revision` can be a minimal substitute. An analyst's optional `method_note` or `assumption_note` is context and interpretation, **not** independent proof that code used that methodology.

An original storage/replay caveat, §8.5–8.6 (`#L395-L410`) also limits the carrier of provenance. A Python/Colab-only call may return an in-memory receipt; an application may retain one short run record; a multi-input Artifact may have one associated manifest instead of copying identical metadata into every Excel sheet. **Excel/PDF/image properties are lossy carriers:** editing, export, or format conversion can discard them. A user-facing “Sources/Method” sheet may help communicate attribution but is not an authoritative substitute for a separately identified receipt with a controlled lifecycle. For a shared host, the actual execution authority, not each client's local UI copy, must own any admitted authoritative run record. This is a conditional placement model.

**Historical registry semantics cannot be reduced to newest local file.** The original registry discussion, §9 (`#L411-L433`) noted that today's bank classification/alias rules may silently change a historical grouping even with identical original observations. The two legitimate questions are **recalculate past data using current rules** versus **reproduce the interpretation at its historical method/registry edition**. Pin the *actually used* compatible component bundle (for example, a classifier's data, metadata and structure), and treat older revisions as selectively retained input, not as a mandatory complete registry archive bundled in every Python wheel. A code Git commit identifies packaged resources at that revision; it does not identify data fetched months afterward. Conditional SORS crosswalk mappings remain separate assumptions rather than official statistical source evidence.

These examples close a **bounded previously over-compressed Science explanation**, not every material obligation of the original. Product policy still governs capture defaults, retention, artifact disclosures, user-visible indicators and historical revision selection. A source-to-Science author check and reverse source challenge are required independently before material units can be declared conserved.

## 13. Original Topic 09 provenance counterexamples, source-line preserved

The dated original source-vintage research, §15 (`#L563-L586`) specified **18 individually falsifiable tests**. The table below preserves each test's originating row, concrete failure input and intended qualification as an **English research interpretation**. It is not a claim that the tests have been executed or accepted for a product release, and the original wording and uncertainty remain the authoritative Research evidence. Its first-vertical-slice suggested priority covered T01, T02, T05, T06, T09, T11, T13 and T18; T10/T17 are additionally important before claiming stronger retained-replay guarantees. These priorities are source-reported proposals, not binding release gates.

| Source test | Fault/contrast | English research-proposed outcome | Original row |
| --- | --- | --- | --- |
| `SB-SRC-0562/T01` — **Same locator, changed bytes** | Two HTTP 200 responses use the same URL and filename, but payload bytes differ. | Keep distinct SHA-256 values and acquisition timestamps; identify a new byte revision without asserting the publisher corrected the economics. | L567 (`#L567`) |
| `SB-SRC-0562/T02` — **Renamed source, same bytes** | Two names or URLs deliver byte-identical payloads. | Keep the same byte identity and two locator observations; no invented content revision. | L568 (`#L568`) |
| `SB-SRC-0562/T03` — **Contradictory server validator** | An ETag is unchanged even though observed payload bytes change. | The observed content SHA takes precedence for byte identity; retain the validator discrepancy as diagnostic evidence. | L569 (`#L569`) |
| `SB-SRC-0562/T04` — **304 without retained data** | A server returns 304 Not Modified when the previous payload is absent. | Mark the input unavailable; a conditional HTTP response alone is not a successful data acquisition. | L570 (`#L570`) |
| `SB-SRC-0562/T05` — **Wrong response format** | An HTTP 200 returns HTML instead of the expected XLSX. | Fail domain/format validation and keep a typed receipt; do not interpret HTML as an empty statistical sheet. | L571 (`#L571`) |
| `SB-SRC-0562/T06` — **Historical raw input removed** | A digest/manifest survives but a prior source file was removed. | Report replay unavailable; do not silently substitute bytes from the current URL. | L572 (`#L572`) |
| `SB-SRC-0562/T07` — **Source mutation during read** | The input file is rewritten between stat and actual parsing. | Detect non-consistent input or hash the actual data bytes read; never join an old file stat to newly read content. | L573 (`#L573`) |
| `SB-SRC-0562/T08` — **Incompatible registry components** | A revised classification data file is paired with an older structure file. | Reject or qualify the incompatible bundle; do not silently select unrelated files by latest local mtime. | L574 (`#L574`) |
| `SB-SRC-0562/T09` — **Same bytes, changed method** | One input digest is used with two core revisions or calculation-method references. | Preserve separate run/method lineage; different results do not imply a source-byte revision. | L575 (`#L575`) |
| `SB-SRC-0562/T10` — **Crash before artifact publication** | A process crashes after writing staging bytes but before accepted publication. | Do not display the output as a completed artifact; preserve the source receipt only if it was actually committed. | L576 (`#L576`) |
| `SB-SRC-0562/T11` — **Direct Python notebook call** | The domain core is invoked from Jupyter without a desktop application. | Return in-memory provenance and allow explicit portable JSON export; no GUI or platform dependency is required for subject provenance. | L577 (`#L577`) |
| `SB-SRC-0562/T12` — **Parallel chats fetch simultaneously** | Different chats request source inputs at nearly the same observed time. | Assign distinct Run identities and source references; an acquisition timestamp is not a globally unique primary key. | L578 (`#L578`) |
| `SB-SRC-0562/T13` — **Secret-bearing locator** | An input URL or request header contains a token. | Redact shared receipts and preserve restricted diagnostics separately; never serialize the secret into a public Artifact. | L579 (`#L579`) |
| `SB-SRC-0562/T14` — **Same snapshot, changed solver premise** | A SORS calculation is repeated with identical source bytes but a changed assumption/evidence tier. | Keep domain epistemic qualification independent from source-byte digest and computation replay status. | L580 (`#L580`) |
| `SB-SRC-0562/T15` — **Equivalent values, different XLSX containers** | Two workbook packages encode equivalent table numbers using different bytes. | Keep distinct raw hashes; assert semantic equivalence only after a declared typed comparison. | L581 (`#L581`) |
| `SB-SRC-0562/T16` — **Different clocks and time zones** | Two client devices disagree on clock or time-zone settings. | Record acquisition time in an explicit UTC convention and disclose the actual clock uncertainty/authority. | L582 (`#L582`) |
| `SB-SRC-0562/T17` — **Lost storage acknowledgment** | Remote storage commits a write, but the acknowledgment is lost. | Record OUTCOME_UNKNOWN and reconcile before retrying; do not falsely assert RETAINED or safely absent data. | L583 (`#L583`) |
| `SB-SRC-0562/T18` — **Same package version, changed embedded registry** | A package rebuild keeps a version string while bundled registry bytes differ. | Compare actual build identity or a bundled registry manifest digest; package version alone is insufficient. | L584 (`#L584`) |

**Evidence-strength boundary:** matching source bytes is not publisher authentication, domain interpretation or forecast skill. A runnable reproduction (R3) differs from demonstrated replay (R4); even a successful rerun does not make a model's conditional assumptions true. Error receipt, source/registry/method identity and Artifact publication remain separate owners. All 18 rows are **producer-translated and source-line traced; independent bilingual semantic assessment and actual execution remain OPEN**.


## Original implementation-scope clarification: optional OKVED auxiliaries (2026-10-12)

A scientific model may reasonably propose a **consistent multi-component classifier revision** when one calculation actually consumes related classifier data, metadata and structural resources. The [pinned current `rosstat_okved2.read()` code](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py#L97-L145), however, reads only the `data` component for the default table; separate `read_meta()` and `read_structure()` paths are optional. Consequently **the failure case of mixed `data/meta/structure` editions is a research-proposed cross-component risk, not evidence that normal `read()` already loads or miscombines all three**. A future revision guard should bind the resources *actually used* by the relevant operation, while selective extended claims may require a coordinated bundle. See [current code bounds](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md).


## Collector completeness as a separate evidence dimension — source-tested 2026-10-12

A source-acquisition `ok` flag can truthfully describe one narrow outcome while being **insufficient evidence of selected-source completeness and economic validity**. The frozen [CBR raw-file collector](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md) was characterized by **four executed offline tests**: (1) an explicitly empty requested registry yields `ok=True` and no output, (2) fail-fast with three selected sources attempts only the first, leaving two unattempted yet absent from `failures`, (3) one recorded retry-round count of two can correspond to 16 physical URL-case variant calls, and (4) non-HTML JSON bytes can be acquired under a filename resembling XLSX without workbook validation.

A **consumer-specific completeness model** may partition `selected = attempted + not_attempted` and separately classify actual acquired bytes, rejected/failed responses and publish/retention outcomes. The existing API does **not** provide this full partition, and a successful download is not equivalent to the actual source bytes *consumed* by a statistical calculation. A physical network-call quota cannot use an outer retry-round count without unit conversion. Source identity, transport evidence, format validation, domain validation, intended coverage and Artifact publication remain separate questions.

**Countercase:** for an intentionally empty optional collection, vacuous Boolean success is mathematically defensible; early abort can be sensible for a strict collector; and keeping raw-file collection free of a spreadsheet parser is a legitimate responsibility boundary. The problematic inference occurs only when a high-consequence bank report asserts **complete, validated inputs** from those narrower facts. The four passing CI tests use fake HTTP and no-op save, and support only the present-source control-flow observations, not source authenticity, economic correctness, an installed host or a new Product Decision.

## Original automation Research 0041 — orchestration comparisons and roadmap basis (source packet A)

**Provenance:** frozen original automation research, Git blob `dee8958b16b3fe08042b5212d35fcc8424db28e3`. Tool names and dated preferences are **competing research examples** rather than installed dependencies, measured tool benchmarks or a commitment to outsource Strategy Box domain authority.

| Material original address | Source-qualified meaning | Countercase, cost or error boundary | Frozen original span |
| --- | --- | --- | --- |
| `SB-SRC-0041/FRAME-04` · `HISTORICAL_ASSET_ORCHESTRATION_REFERENCE` | Dagster was cited for asset-centric materialization and blocking checks so dependent analytics can follow validated upstream data. | No data-version or checksum boundary is secured merely by adopting an orchestration vocabulary; source/data validity and permission remain separate. | L1483–L1495 (`#L1483-L1495`) |

**Conservation limit:** dated comparative judgment and engineering proposal only; no live evaluation of current third-party APIs/versions, host, worker, schedule or domain service is asserted. Independent original→Science semantic certification remains open, as does full source material accounting.

## Original May 2026 patch note: banking-file semantics and mutable-source limits

**Primary historical corpus:** May 2026 public-patch summary, exact pinned Git blob `a2339ebc79f72a075d290b761fda7b8997b15710`. The note is a **dated developer implementation summary**, not a current code-level conformance certificate; only public-safe domain consequences are included here. Current modules, official data and execution effects need their own evidence. Physical and restricted deployment internals are outside this Science scope.

| Original position and epistemic status | Source meaning | Counterexample or missing proof | Frozen original span |
| --- | --- | --- | --- |
| `SB-SRC-0015/CBRFILES-01` · `HISTORICAL_SOURCE_COLLECTION` | A raw statistical-file collector combined a manually maintained URL registry, source-byte download and FileStore folder/ZIP storage paths. | An HTTP 200 plus a saved file does not prove primary issuer authority, immutable source vintage or replay evidence. | L82–L90 (`#L82-L90`) |
| `SB-SRC-0015/CBRFILES-02` · `HISTORICAL_RAW_FILE_AND_PARTIAL_OUTCOME` | The collector intended raw CBR files to remain untransformed, with provider/URL-derived names, collision uniquification and continued batch download after individual failures. | A continued batch run does not imply all requested sources succeeded; unattempted sources and actual delivered bytes need separate accounting, especially after stop-on-error. | L92–L100 (`#L92-L100`) |

**Scientific boundary:** these are twelve source-positioned historical statements across bank reporting, FRG, escrow and raw-source collection, with error, identity and version qualifiers. They do not certify content correctness, deployed package behavior or a complete independent source-to-Science audit. Any restricted source material remains outside public Science.

## Historical May domain patch 0015 — bounded public-safe residuals

These are **four historical change-log claims**, not present-day code or runtime tests. The frozen source is used as internal Work evidence for the *public-safe claims only*, and this publication intentionally omits links into protected legacy material. The older original has additional publication constraints; its full-source material disposition remains `unaccounted`.

| Source-row class | Conserved public-safe meaning | Limit / negative case | Original span |
| --- | --- | --- | --- |
| `SB-SRC-0015/PUBLIC-SAFE-03` · `HISTORICAL_RAW_FILENAME_SPECIAL_CASE` | The raw-source archiver history preserved publisher bytes and filenames, explicitly removing one prior special filename rewrite while retaining response/URL-derived naming and collision disambiguation. | Byte-preserving download and a de-duplicated local filename do not establish source authenticity, immutable content vintage, or that two filename aliases imply two independent publisher releases. | `L92-L98` |
| `SB-SRC-0015/PUBLIC-SAFE-04` · `HISTORICAL_MOCK_TEST_AND_PUBLIC_IMPORT` | The old archiver change note recorded a domain-level public import, notebook/network-file examples and limited compile/import, ZIP and mock-batch checks. | Historical mock checks are not observed execution here, prove neither real central-bank download nor installed runtime availability, and cannot certify provenance of the live inputs. | `L102-L106` |

A historical change note is distinct from live implementation, original input bytes, validated source provenance and executed test results. No current support guarantee or protected integration contract follows from these entries.

## Binary identity, analytical equivalence and capture-clock counterexamples

Two XLSX packages can contain semantically comparable numerical tables while having **different raw byte digests** because ZIP entry order, internal metadata or encoding differs. Conversely, equal byte digests establish equality of the actual byte streams only, not independent official publisher authenticity, currentness, method assumptions or economic comparability. A **semantic comparison** must declare parser and normalized representation versions, dimensions, bank/reporting perimeter, period, currency, precision and acceptable value equality; it is a separate, fallible computation. Without such a declared profile, different source bytes are two distinct byte revisions even if a human sees the same visible cells. [Candidate test PR-27](../../ldd/data/used-source-receipt-boundary.md) preserves the negative case.

A source observation timestamp must identify the **actual capture point** and its UTC clock basis. Two Windows/remote clients can report different wall-clock times for one causal sequence due to zone settings, clock skew, service clock drift or delayed ingestion. A normalized UTC string improves unambiguous representation but does not magically certify trusted time; store timing uncertainty where material and use explicit source/revision identity and authority-owned event order for concurrency. Run and source IDs are **not timestamp-derived primary keys**. [Candidate test PR-28](../../ldd/data/used-source-receipt-boundary.md) addresses this. Both proposed cases are unexecuted and do not imply a new metadata service or acceptance of universal raw archival retention.
