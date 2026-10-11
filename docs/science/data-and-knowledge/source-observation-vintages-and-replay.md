# Source observations, publication vintages and reproducible statistical calculations

**Scientific scope:** what can an analyst establish later about banking and macroeconomic data when one URL may serve revised bytes and the calculation method may also change? This bounded scientific model complements [source identity](source-identity-and-reproducibility.md). `FetchReceipt`, `RunProvenance` and R0–R4 are **research candidates**, not a shipped universal API or an approved Product commitment. A content hash is evidence of byte identity, **not an economic truth guarantee**.

## 1. The analyst's historical-evidence problem

The filename of an XLSX and the economic reporting date do not identify the actual downloaded publication. Publisher edition, acquisition rule, time of observation, actual bytes, Registry version, transformation revision and computed Result can vary independently. A reproducibility claim should answer **which publication, when acquired, what bytes, under which definitions/methods, with which retained inputs and whether a replay actually occurred**. A timestamp is weaker than a digest; a digest without retained bytes cannot by itself replay an earlier calculation. Repeating a calculation cannot prove its economic assumptions.

[Late Research topic 09](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/09_Источники_данных_версии_и_воспроизводимость_Strategy_Box_2026-10-10.md#L14-L35) reports the developer's preference for an **actual download timestamp, expert responsibility for interpretation, optional links to existing methodology, and no costly exhaustive catalog of every statistic**. The matching primary ten-topic annotated source was subsequently read in full; its original DOCX binary SHA-256 remains **unverified**. The content is supported by primary text, but exact byte identity and Product admission are distinct obligations. This supports a proportionate record of **actually consumed** inputs.

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
