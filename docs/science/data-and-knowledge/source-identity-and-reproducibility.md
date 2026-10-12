# Source identity, registry identity, and reproducible statistical inputs

**Scope:** bounded scientific and engineering explanation of a recurring provenance problem in financial-statistical data processing. **Evidence:** exact core implementation at `8459dc58922b7e8df853cf1d9e8131fa9e132580`, source semantics and formal examples. This article does **not** announce a deployed universal Source Catalog or registry manifest.

## Three objects that must not be conflated

A **reference entity** is what an external classification or institution defines: a bank, economic-activity code, or geographical entity. A **source definition** describes *how to retrieve* data: an endpoint, publication family, or collection rule. A **source snapshot** denotes *what was actually retrieved*: observed bytes, source context, time, validation and a content identity. They have different change conditions.

A bank can retain its registration identity while changing its displayed name. An official statistics URL can remain identical while the publisher replaces the XLSX bytes. A new downloaded filename can also represent the exact same bytes. These examples show why a display label, URL, local path or modification timestamp is insufficient by itself to express content revision.

**Reproducible result** means a consumer can identify the relevant inputs, transformations, assumptions and versions under a declared preservation boundary. It does not mean that a URL will always serve its former payload or that all past bytes remain available without a retention arrangement.

## Direct implementation: a selector whose identity is weaker than the data

The current registry resource loader provides `pick_latest_by_suffix()` and `pick_latest_by_prefix()`, both using `_resource_mtime()` to select the maximum filesystem `stat().st_mtime`. If stat fails, the helper substitutes `0.0`. [Direct code](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py).

This reliably states how the *current selector* operates. It does not establish which specific file is chosen in every deployed environment. A copied tree or repackaged installed resource may acquire new filesystem times without a corresponding change to its substantive publication. Consequently, “latest by mtime” is not by itself proof of “most recently published by the authority.”

The current [bank registry implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/cbr_banks.py) reads several resource families: official bank information, name-replacement policy, selected list and legacy list. These need distinct provenance roles even if one convenience reader joins them. The [classifier loader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) reads separate classifier resource forms. A mixed bundle cannot be assumed to represent one consistent source revision merely because its files share a directory.

## The content-identity argument

Let two source downloads have the same filename and URL but different byte strings, `b1` and `b2`. If only URL and filename are recorded, they are observationally indistinguishable to a later consumer. If cryptographic digests differ, that consumer at least has evidence that the bytes differed; a digest alone does not prove which publication was authoritative, correct, timely or permitted.

An identity/provenance record therefore has several independent dimensions:

| Dimension | Explains | Does not automatically establish |
| --- | --- | --- |
| Authority and source definition | Who/where the data purportedly came from | Actual content, official validity |
| Retrieved byte digest and size | Which bytes were observed | Semantic correctness, long-term retention |
| Publication/effective period | Which statistical period/meaning applies | Download date or file freshness |
| Registry/classifier version | Which mappings were used | That all transformations were sound |
| Transformation and code version | How a result was constructed | User acceptance of its conclusions |
| Validation state and assumptions | Which checks/qualifications hold | Absence of other unknown defects |

For composite resources, one bundle may contain several files representing different roles. They should be verified together against their declared source/profile rather than independently sorted by mtime and silently mixed.

## Alternatives, limitations, and negative results

- **Filesystem mtime as currentness:** simple and useful for ad hoc local files, but insufficient as an immutable authoritative revision selector.
- **Filename/URL:** useful stable source locators, but may be reused by publishers for changed content.
- **ETag or Last-Modified:** helpful hints when available; the transport server controls their presence and semantics, so they should not be silently equated with a universal byte digest.
- **Immutable manifest plus digest:** a plausible controlled package contract, but it is a **target design option**, not something the current loader implements. It requires explicit source, validation, package/update and failure rules.
- **Keep every snapshot forever:** helps historical replay, but increases storage and governance costs. A bounded retention/version-pinning policy is a separate product decision.

**Current unknowns:** latest authoritative external-bank and classifier publication revisions have not been rechecked in this article; actual installed-resource selection and historical retention are unmeasured; no package or user acceptance claim follows. Reopen when loader logic, source publisher behavior, resource packaging or required reproducibility changes.

This article supports a reader's understanding of source truth without depending on prior Research reports. It does not set an approved catalog schema, registry update workflow or runtime permission model.

## Source-governance Research: nine anti-patterns and fifteen proposed choices (24 pinned items)

The frozen 2026-10-07 registry/source-governance study, §§48–49 (`#L2105-L2164`), blob `0d2a15a8b3630805a65b00dbba2e324cd2e7accf`, proposed nine pitfalls and fifteen implementation directions. The English items below preserve their **source identity, original line and research-proposal status**, not an approved global catalog architecture.

| Original research item | English material finding or candidate | Frozen source line |
| --- | --- | --- |
| `SB-SRC-0035/RISK-01` | A single giant registry module conflates banks, geography, source URLs, formats and operations | L2107 (`#L2107`) |
| `SB-SRC-0035/RISK-02` | Selecting a 'latest' source solely by local file mtime is a weak production identity guarantee | L2111 (`#L2111`) |
| `SB-SRC-0035/RISK-03` | Bank/industry/geographic entities need stable official or canonical IDs, not a translated display label | L2115 (`#L2115`) |
| `SB-SRC-0035/RISK-04` | Official source publication must remain separate from user aliases, organizational labels and selection policy | L2119 (`#L2119`) |
| `SB-SRC-0035/RISK-05` | Geographical totals/aggregates are not automatically region observations | L2123 (`#L2123`) |
| `SB-SRC-0035/RISK-06` | Embedding Git write credentials into the end-user application would add excessive risk and complexity | L2127 (`#L2127`) |
| `SB-SRC-0035/RISK-07` | Implicitly refreshing packaged registries on application startup changes reproducible calculations | L2131 (`#L2131`) |
| `SB-SRC-0035/RISK-08` | Silently falling back to outdated registry after update failure misrepresents selected version | L2135 (`#L2135`) |
| `SB-SRC-0035/RISK-09` | Stable filenames do not establish version identity when source bytes can change | L2139 (`#L2139`) |
| `SB-SRC-0035/RECOMMENDATION-01` | Keep general reference registries owned by the domain core | L2147 (`#L2147`) |
| `SB-SRC-0035/RECOMMENDATION-02` | Treat external acquisition catalogs/source snapshots as a separate semantic family | L2148 (`#L2148`) |
| `SB-SRC-0035/RECOMMENDATION-03` | Separate common bank/classification/geography reference data from domain-specific FRG, forms and solver rule registries | L2149 (`#L2149`) |
| `SB-SRC-0035/RECOMMENDATION-04` | Replace purely mtime-selected release choice with an explicit manifest where material | L2150 (`#L2150`) |
| `SB-SRC-0035/RECOMMENDATION-05` | Give registry editions stable identity, digest and source metadata | L2151 (`#L2151`) |
| `SB-SRC-0035/RECOMMENDATION-06` | Separate official bank entities, names/aliases and curated entity sets | L2152 (`#L2152`) |
| `SB-SRC-0035/RECOMMENDATION-07` | Do not perpetuate a redundant legacy registry compatibility path once active consumers have migrated | L2153 (`#L2153`) |
| `SB-SRC-0035/RECOMMENDATION-08` | Model canonical geography entities and source-specific aliases; preserve aggregate publication nodes | L2154 (`#L2154`) |
| `SB-SRC-0035/RECOMMENDATION-09` | Consider moving hardcoded regulated-source acquisition lists to a maintained source catalog if demand warrants | L2155 (`#L2155`) |
| `SB-SRC-0035/RECOMMENDATION-10` | Author or review registry updates through controlled versioned source changes | L2156 (`#L2156`) |
| `SB-SRC-0035/RECOMMENDATION-11` | Treat packaged runtime registry resources as immutable for a given release | L2157 (`#L2157`) |
| `SB-SRC-0035/RECOMMENDATION-12` | Expose only status and allowed source/registry links to ordinary client surfaces | L2158 (`#L2158`) |
| `SB-SRC-0035/RECOMMENDATION-13` | Connect actually used registry/source editions to significant analytical Result provenance | L2159 (`#L2159`) |
| `SB-SRC-0035/RECOMMENDATION-14` | Use content hashes for safe change detection and cache eligibility | L2160 (`#L2160`) |
| `SB-SRC-0035/RECOMMENDATION-15` | Consider a reviewed updater/PR workflow instead of mutating package reference assets silently during runtime | L2161 (`#L2161`) |

**Material alternative:** the same original study argues against immediately building a separate registry server or new data package: this would impose network availability, independent API/version contracts and additional ownership/packaging costs without demonstrated need. Packaged small immutable reference snapshots remain a serious default for direct offline Python analytics. The later developer-annotated source explicitly prefers **actual-used-source timestamp evidence and expert judgment**, not permanent monitoring of every statistical indicator. Therefore a central Source Catalog, per-entity registry database, automatic pull-request updater or always-on service is an *admission-dependent option*, not a user-approved baseline.

**Current/target separation:** direct code at the pinned baseline chooses some packaged registry resources by local filesystem `mtime`, as described in [Current HOW](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md). That is observed behavior, not an assertion that official release version ordering is correct. This appendix retains 24 original proposals; the other material content in the 2,353-line source requires a separate source-wise reconciliation and independent technical/financial-domain challenge.

## Original topic 09: nineteen source identity, vintage and replay distinctions

The dated Source Data, Versions and Reproducibility study separates source publication identity, acquisition event, observed bytes, registry revision, computation method and subsequent Artifact. The **19 English original-source interpretations** below preserve important negative outcomes and cost controls. The user's expressed preference for lightweight timestamps and selective method references is represented only to the extent supported by the separately recovered annotated questionnaire; its **raw DOCX SHA remains unverified**. No universal provenance API or live data freshness monitor is claimed implemented.

| Source ID | Qualified original claim | Disposition | Frozen line |
| --- | --- | --- | --- |
| `SB-SRC-0562/SOURCE-01` | Publisher identity is not a fetch address; one authority can publish many independently revised file families. | `PUBLISHER_SOURCE` | L102 (`#L102`) |
| `SB-SRC-0562/SOURCE-02` | SourceDefinition describes acquisition/discovery, not the bytes obtained on one attempt. | `FETCH_RULE_NOT_SNAPSHOT` | L103 (`#L103`) |
| `SB-SRC-0562/SOURCE-03` | FetchReceipt is one observed source access attempt, with observed time, actual locator and outcome, not the accepted statistical content. | `RECEIPT_OBSERVATION` | L104 (`#L104`) |
| `SB-SRC-0562/SOURCE-04` | SourceSnapshot identifies actual accepted bytes and their digest, distinct from the download attempt and publisher semantics. | `BYTE_REVISION` | L105 (`#L105`) |
| `SB-SRC-0562/SOURCE-05` | RegistryRevision binds actual reference-table content and effective semantics, which may change independently of raw observations. | `REFERENCE_VERSION` | L106 (`#L106`) |
| `SB-SRC-0562/SOURCE-06` | TransformationRevision identifies algorithmic/method interpretation and significant configuration beyond the package import name. | `METHOD_REVISION` | L107 (`#L107`) |
| `SB-SRC-0562/SOURCE-07` | Acquisition timestamp is distinct from publisher release date, economic reference period, classifier effective dates and computed/exported time. | `FIVE_TIME_AXES` | L140 (`#L140`) |
| `SB-SRC-0562/SOURCE-08` | Matching SHA-256 supports byte identity, not official publisher authenticity or economic correctness. | `BYTE_HASH_LIMIT` | L153 (`#L153`) |
| `SB-SRC-0562/SOURCE-09` | Semantic equivalence of two differently packaged XLSX files requires a separate measurement comparison, not just ZIP-byte hashes. | `SEMANTIC_EQUIVALENCE` | L154 (`#L154`) |
| `SB-SRC-0562/SOURCE-10` | An HTTP 304 allows reuse only when the prior content snapshot actually remains available and identified. | `HTTP_304_GUARD` | L185 (`#L185`) |
| `SB-SRC-0562/SOURCE-11` | A server 304 with no retained previous payload cannot count as a successful new statistical data download. | `HTTP_304_WITH_MISSING_BYTES` | L197 (`#L197`) |
| `SB-SRC-0562/SOURCE-12` | Source byte hash does not certify origin: publisher identity, safe redirects/TLS and optional authoritative signatures are different evidence. | `ORIGIN_AUTHENTICITY` | L206 (`#L206`) |
| `SB-SRC-0562/SOURCE-13` | R0–R4 proposed reproducibility tiers distinguish undocumented results, observed provenance, byte verification, replay-ready and replay-tested outputs. | `REPLAY_LADDER_CANDIDATE` | L297 (`#L297`) |
| `SB-SRC-0562/SOURCE-14` | Integrity, replay readiness and semantic correctness are separate axes; a successful deterministic replay may repeat a wrong bank interpretation. | `REPLAY_NOT_TRUTH` | L311 (`#L311`) |
| `SB-SRC-0562/SOURCE-15` | Retained digests may prove historical bytes differed without enabling replay if the original bytes were later deleted. | `HASH_NOT_RETENTION` | L317 (`#L317`) |
| `SB-SRC-0562/SOURCE-16` | Exact Python build may be insufficient for sensitive numerical replay without selected library, solver, locale, seed and registry versions. | `NUMERICAL_ENVIRONMENT_VINTAGE` | L321 (`#L321`) |
| `SB-SRC-0562/SOURCE-17` | A registry used for bank classification should pin the actual read asset bundle rather than selecting an arbitrary newest resource mtime. | `REGISTRY_BUNDLE_IDENTITY` | L417 (`#L417`) |
| `SB-SRC-0562/SOURCE-18` | For a mutable file, the checksum must cover the exact bytes actually consumed, not an earlier stat observation susceptible to TOCTOU. | `HASH_CONSUMED_BYTES` | L547 (`#L547`) |
| `SB-SRC-0562/SOURCE-19` | Default provenance should remain scoped to actually used inputs; globally retaining every source byte and continuously polling all statistical series has material cost. | `PROPORTIONAL_CAPTURE` | L555 (`#L555`) |

**Strong counterarguments and non-implications:** An observed timestamp is useful context, not an evidence-based historical data vintage. Matching URL, byte hash, economic data or calculation result are four noninterchangeable equality relations. A replayed calculation can remain semantically wrong, while a missing historical source payload may make byte-identical rerun impossible despite preserved digests. Exhaustive versioned storage is expensive and often unwarranted for disposable inputs; a small source-used manifest can improve actual auditability without becoming a global master-data platform. Publisher legitimacy and currentness still need domain-level checks beyond transport metadata.

**Preservation limit:** nineteen source-grounded material items, not all material meaning of the 684-line original or independent proof of published external statistics.
