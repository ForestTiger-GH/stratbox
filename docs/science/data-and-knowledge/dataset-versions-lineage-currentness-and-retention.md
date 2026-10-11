# Dataset versions, lineage, currentness and retention of analytical evidence

**Problem domain:** carrying a concrete source publication through decoding, a versioned semantic dataset, domain validation, computed results and published artifacts—then explaining what remains valid after the publisher, classifier, method or physical files change. **Status:** maintained explanatory model with explicitly unapproved API, storage/retention and revalidation proposals. **Evidence baseline:** [core at `8459dc58922b7e8df853cf1d9e8131fa9e132580`](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580) and [Windows at `959e9c4ce1441124af5111c1e025041714e04d3b`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). Scientific interpretations are not product decisions or runtime certification.

## 1. Two linked but nonidentical chains

**Data and reproducibility chain:** source authority → a rule for acquisition → actual receipt and byte snapshot → physical decoding → semantically typed observation → accepted DatasetVersion → validated transformation → qualified AnalyticalResult → materialized Artifact and lineage.

**Evidence and meaning chain:** MeasureDefinition → Observation → transformation/assumptions/model → evidence argument → bounded Claim → suitability for a specific use → currentness challenge and re-assessment.

A file can be valid without its parsed observation being economically comparable. A canonical dataset may correctly reflect an erroneous publisher figure, which does not make the figure externally true. An Operation can succeed without its resulting claim being justified. A published Artifact can be a faithful presentation of an uncertain conclusion. Maintaining these distinctions is an analytic obligation, not a reason to deploy an all-purpose knowledge graph now.

## 2. Source catalog, acquisition receipt, and exact publication revision

A `SourceDescriptor` (target semantic role) specifies which authority/publication family and expected statistical series are being sought, with discovery method, locator/selection rule and validation expectations. A **FetchReceipt** records an actual attempt, time, requested and final locator, status and observed server hints. A **SourceSnapshot** describes the particular content bytes, size/digest, validation, declared release/effective period and retained-content availability. Multiple fetch attempts may point to one identical byte snapshot; two downloads from the same unchanged URL may point to different bytes.

A 200 response can contain an HTML error page, a ZIP missing one expected component, an XLSX with altered schema or an invalid business period. Hence a transport success is not yet an admitted semantic SourceSnapshot. Content hashing demonstrates observed byte identity, **not publisher authenticity**. Network redirects/TLS/source page and optional official signatures are other evidence classes.

Time coordinates: covered statistical period, publisher release date, time information was available, actual acquisition time, statistical vintage/revision, classification validity dates and computation time. `latest` relative to filename or file mtime is not a defensible universal vintage identifier. [The pinned registry resource selector](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) still chooses by filesystem mtime; this is a direct current mechanism, not a content version policy.

**Important historical research tension:** earlier studies proposed a broad managed Source Catalog and automated source monitoring; later explicit user clarification prioritized **compact factual receipts for inputs actually used** (acquisition time, digest/size where useful, optional existing method reference) and rejected indiscriminate indexing/surveillance of every statistical series. The semantic distinction of SourceDefinition and SourceSnapshot survives, but universal catalog membership is **not a prerequisite** for an ad hoc user-supplied Excel source. For operational levels and R0–R4 see [source observation/vintage Science](source-observation-vintages-and-replay.md).

## 3. A source registry is not the same as a semantic reference registry

Five roles should remain distinct: official **reference identity** (banks, classification codes, geography), **human/policy overlays** (aliases and user-selected sets), **source acquisition definitions**, **domain rule families** (form model, FRG family, SORS crosswalk), and **capability/style registries**. Each can have an independent editor and effective time; they should not be combined into one physical “God Registry.”

A candidate `RegistrySnapshot` pins `registry_id`, official upstream edition, effective-from/to, exact content-part digests, schema/transform revisions, validation and policy overlays. Selection through a package version or `mtime` alone may miss incompatible combinations.

For **OKVED2**, `data/meta/structure` must represent a consistent accepted bundle when used together. For banking, identity, aliases and policy sets can have separate amendment histories. For SORS, its mapping from legacy classification to domain-specific publication rows remains a **methodologically qualified projection**, not a new universal official classifier. Geography requires historical entity relationships plus source-layout mapping; national, federal district, region and publication-only aggregate row must remain distinguishable. Updating a classifier is not the same as “fixing” all old observations.

An authoring pipeline could fetch candidate registry revisions, validate semantic compatibility, review/admit and package an explicit manifest, while the installed package treats bundled assets as immutable. This is an engineering candidate. A release commit may identify packaged registry bytes, but **does not capture all external statistics downloaded after installation**. Retaining every old spreadsheet inside every wheel is not a default obligation.

## 4. Dataset definition, version, materialization and view

| Role | Identity | Why independent |
| --- | --- | --- |
| `DatasetDefinition` | Stable semantic construct/schema, dimensions, measures and domain owner | Meaning may outlive one download or run |
| `DatasetVersion` | One accepted set of observations with source/mapping/algorithm versions and validation | New data or method may alter actual values without renaming the series |
| `DatasetMaterialization` | Physical bytes in CSV, Parquet, XLSX, database or object store | One dataset version can be represented in several formats |
| `DatasetView` | Pivot/filter/region or subset representation with parameters | View can be a lightweight projection or a new version when it substantively transforms meaning |
| `AnalyticalResult` | Findings/claims/evidence/limitations from analyzing versions | Not equivalent to a dataset or file |
| `Artifact` | Published logical output with bytes/manifest/permissions and availability | Not identical to its path and not necessarily accepted knowledge |

A DataFrame is an excellent in-memory analytical representation, but its **current memory address or variable name is not a historical dataset revision**. An economic semantic version needs something like `dataset_id/version_id`, semantic schema revision, exact `SourceSnapshotRef[]`, `RegistrySnapshotRef[]`, operation/algorithm and effective-parameter versions, reporting period/vintage, validation evidence, optional rows/columns, provenance and optional physical materializations. This is an illustrative contract, not implemented universal `DatasetVersion` API.

Content digest is computed for a particular byte representation. Reordering rows, different Parquet dictionary encoding, timezone/precision and serialization version may produce different hashes for semantically identical datasets; conversely the same bytes could be interpreted under different measure definitions. **Semantic equivalence requires an explicit domain canonicalization/comparison rule**, not `SHA-256(any parquet)`.

## 5. Validation and typed provenance are linked

The validated path uses separate checks for transport, format, source schema, semantic interpretation, domain identities/constraints, claim evidence and intended consumer use. Each gate has its own evidence and may fail/return a qualified partial result. A new file with wrong periods is not fixed by a successful ZIP reader. A bank balance converted to the right currency remains uncomparable if its consolidation perimeter differs.

A small candidate `RunProvenanceManifest` can include: actual run/operation/build revision; frozen effective params, safe digest; exact source and registry snapshots; semantic schema and relevant model/method/solver version; validation reports; output dataset/Result/Artifact refs; progress/failures/partial/unknown; executed and finished times. A domain-specific SORS result can attach its richer proof ledger and conflicts; a raw source collector only needs relevant byte observation facts.

A typed lineage graph has edges such as `used`, `generated`, `derived_from`, `validated_by`, `depends_on_registry`, `represented_as`, `materialized_at`, `supersedes`, `challenges`, `revalidates`. The simplest useful chain is:
```text
Official SourceSnapshot S1 + RegistryRevision R1
                   ↓ used by domain operation T1
         DatasetVersion D1 + validation
                   ↓ analysis T2
       Qualified AnalyticalResult A1
                 ├─ rendered view V1
                 └─ published Artifact F1 → workspace materialization
```

**Lineage of files alone is insufficient.** One CSV can contain several datasets; one dataset can support many reports; one Claim can depend on several source families and assumptions. A copy of the same publication on five websites is not five independent evidence grounds. A stable `ArtifactRef` can survive a move to another physical root, while its user-controlled materialized output may simply become unavailable.

## 6. Freshness is a use-scoped assessment, not file age

| Target | Meaningful question | Outcomes can include |
| --- | --- | --- |
| SourceDefinition | Is the acquisition channel reachable and when checked? | reachable/unavailable/unknown |
| SourceSnapshot | Has this particular publisher resource been revised? | same/new/revised/unknown |
| RegistrySnapshot | Is mapping appropriate for required effective date? | current/stale/manual/unknown/not applicable |
| DatasetVersion | Are its inputs/method still appropriate? | valid/impacted/needs review/invalid |
| QualifiedClaim | Are the supporting premises still sufficient for the current use? | supported/contested/stale/withdrawn/unresolved |
| AnalyticalResult | Is this the appropriate result for this question and as-of? | current for use/historical/revalidate/superseded |
| Artifact | Are the promised bytes accessible and hash-matched? | available/missing/integrity-failed/quarantined |

These are often **orthogonal** questions: a still-accessible old Artifact may remain historically valid even if superseded for today's new analysis. A new publisher file may revise only an unused month or cosmetic cell; global downstream invalidation would be unjustified. A `FreshnessAssessment` (candidate) ought to carry target, use-context, policy revision, assessment time, supporting facts, reason and next review, without mutating the original immutable snapshot.

An impact/revalidation algorithm would compare new source/registry versions, determine whether change is byte-only, semantically relevant or unknown, traverse recorded dependencies, filter by used periods/measure/entity mapping where available, and flag **only plausibly affected** Results/Claims for review. It should not automatically rerun or republish destructive actions; these require separate authorization/effect policy.

**A legitimate historical backtest** intentionally uses a vintage available to an analyst at the past as-of, while a contemporary view may prefer a newer revision. `latest_committed`, `latest_validated`, `current_for_use`, `historical_at_time` and `superseded` are different selectors. Choosing the newest filename in an output directory has no epistemic authority.

## 7. Cache, immutable evidence, physical retention and garbage collection

A cache is disposable only when its contents can be reconstructed without violating promised historical replay. If the *only copy* of a used source is in a cache directory, calling it disposable changes the effective evidence contract without informing the analyst. Three meaningful storage profiles: transient calculation, reproducible result with retained immutable inputs or verified immutable source locator, and long-lived/regulated evidence with explicit backup/retention/access constraints.

A safe compute-cache fingerprint needs actual input byte identities, semantic schema and measure versions, registry snapshots, operation/parser/algorithm revision, normalized relevant parameters and policy selection identity. Filename, directory and filesystem mtime are weak hints. Even matching fingerprints need compatibility and authorization checks before reuse.

“Immutable” means that a committed logical object cannot be modified *silently*. It does **not** mean it can never be deleted. Distinct relations:
- `superseded_by` names a successor, preserves the predecessor's historic truth;
- `tombstoned` removes normal availability while retaining a trace;
- `quarantined` flags unsafe/corrupt bytes and blocks ordinary use;
- `retained_due_to` records an actual legal/operational/lineage hold;
- `materialized_at` references a physical copy whose lifetime may differ from logical object.

A managed GC procedure should first check current references, retention policy/holds, active readers and backup responsibilities. Deleting a UI entry is not authority to delete source evidence needed for still-retained Results. Conversely the user may deliberately move or delete an ordinary workspace XLSX; in a lightweight product this can simply produce “file missing” on next attempt to open it. A universal eternal CAS/archive is **not** approved.

## 8. Source-to-result worked examples

**CBR reporting form 0409802:** official ZIP/DBF byte receipt → physical rows/field locations → versioned semantic form mapping → observation (`bank REGN`, measure, period, unit, missingness) → DatasetVersion → validation → Result → styled XLSX Artifact. The same sheet location in a newer physical source layout is only equivalent if the domain mapping confirms semantic identity. This is a target end-to-end trace, not a currently deployed universal manifest.

**Escrow revised monthly XLSX:** July source initially appears as snapshot A, then publisher changes the bytes at the same URL and basename in a later vintage B. Results D1/R1/X1 stay meaningful for their as-of; D2/R2/X2 may be computed with the new bytes, and only after validation marked current for an intended use. If one month was unavailable, partial collection must not falsely become a full series.

**SORS rounding/inference:** exact source publication bucket and its revision → classification/crosswalk version → mathematical constraint/proof tier → feasible latent interval/selected value and evidence ID → qualified Claim → Result/Artifact. Matching input bytes or successful export does not convert weak `ROUNDING_SELECTED` into official certainty; preserve domain-specific epistemic detail.

**Mixed bank comparison:** standalone RAS and consolidated IFRS can appear in one Excel sheet but remain incomparable without an explicit constrained bridge. The output renderer cannot decide economic equivalence.

## 9. An artifact's identity and style live at different layers

An `Artifact` is not only a file locator; a managed logical descriptor may link part byte digests/sizes, producer Run/Result, dataset versions, access and owner scope, lifecycle and a manifest. The existing physical backend's `FileStore` operations are **not** automatically transactional publication or an Artifact Catalog. At the target boundary, domain core defines meaning and output/provenance schema; application authority owns shared catalog/work/user visibility and retention; storage backend owns bytes/receipt; platform assigns permitted roots/bindings. Physical CAS, database and explicit immutable manifests are candidates whose necessity must be tested by real workloads. For detailed publication/effect outcomes see [Artifact Science](../artifacts/output-identity-publication-and-availability.md).

**Interface theme and report style are separate contracts.** A theme describes Qt/Web/Android presentation; an `ArtifactStyleSet` (candidate shared domain formatting description) captures fonts, palette and semantic visual roles for generated documents. A template chooses workbook/slide/page structure, a renderer materializes a format, and `ArtifactMetadataContext` supplies author/title/provenance. The author of a report may differ from the human requesting it, code executor, publication authority or corporate title. A report's reproducible appearance may require pinned style-set digest, renderer, template, fonts and metadata policy; identical source data does **not** imply bit-identical XLSX bytes after a new writer version.

A neutral extension may supply validated versioned style/template resources under public generic contracts, without publication of any closed implementation. Treating metadata authorship as merely a color setting would lose a substantive requirement.

## 10. Contradictions, rejected simplifications and future assurance

Preserved technical conflicts:
- **CAS immediately** versus pilot with content identity and verified manifests; physical CAS is unapproved without measured duplication/concurrency.
- **Artifact catalog in domain core** versus shared application authority; semantic data/result contracts remain in core while user lifecycle/search/rights live in application.
- **Global Source Catalog and monitoring** versus later small used-input receipt preference; curated source definitions may exist, but every ad hoc file need not be registered centrally.
- **One `latest` flag** versus object/use-scoped freshness and statistical vintage.
- **One `ok`/confidence field** versus validation, evidence tier, currentness, artifact availability, and intended-use approval.
- **Historical registry snapshots all in wheel** versus explicit build revision with only needed retained inputs.
- **One universal ClaimStore/knowledge graph** versus typed Claims in domain Results until real consumers justify a store.
- **Theme equals document style** versus independently versioned content, style, template, author metadata and renderer.
- **Semantic normalization equals truth** versus contingent domain evidence and human reliance.

Candidate falsification tests (not executed): same URL/new bytes; bank classifier mtime changed without content change; blank and zero roundtrip; differing IFRS/RAS perimeters; missing source month; same DatasetVersion to XLSX/CSV; crash between blob and index commit; stale source with historically valid result; altered unused period leaving dependent Result unchanged; user deletes artifact without deleting Run provenance; changed style without altered economic value; source author and report creator diverge. A negative result remains meaningful only with stated test scope, actual source/environment and witnessed output.

**Open Product/Engineering decisions:** exact SourceSnapshot receipt and retention depth, required DatasetVersion identity, evidence ref granularity, common geography, linked ClaimStore and currentness policy, CAS versus ordinary managed files, artifact lifecycle/GC, user and legal holds, multi-file publication and backup, range of certified formats, cross-format style compatibility, privacy-safe metadata, Web/host read refs, and actual performance budgets. Use direct domain/packaging fault-injection fixtures rather than promoting conceptual model names to release guarantees.
