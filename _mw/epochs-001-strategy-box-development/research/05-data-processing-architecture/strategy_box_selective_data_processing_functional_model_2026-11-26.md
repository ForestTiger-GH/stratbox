# Strategy Box: Selective Collection and Incremental Processing — Functional Model

**Date:** 2026-11-26. **Status:** research recommendation, awaiting implementation. **Scope:** reusable commands and operations for selected publication collection, physical table export, qualified histories, analytical products and repeatable application calls. **Implementation claim scope:** Stratbox `55306c27b402895a4608a37d6210fa3a7d0ddbc6`.

Strategy Box can support the seven investigated notebook workloads through its existing command and operation architecture once several common contracts are completed. The highest-value additions are explicit selection, a distinction between source change and remaining work, journal-derived retained-state lookup, a continuous bounded file path, qualified history assembly and complete per-member outcomes. Domain interpretation and most analytical products already have owners. The proposal strengthens those owners and their connections.

The concrete list of tables to download belongs to the external script or application request; a future scenario or cascade may also own that purposeful choice. Commands and operations receive the choice explicitly and apply general rules. This research defines proposed behavior, including acceptance requirements; it does not declare the proposed APIs implemented or establish historical publisher-data parity. The companion [architecture and implementation design](strategy_box_selective_data_processing_architecture_and_implementation_2026-11-26.md) assigns contracts to code owners.

## Contents

1. Recommended decisions — the reusable boundaries and the immediate scope.
2. Requested results — what each independently useful operation must establish.
3. Caller-owned selection — choosing sources, publications, observations and presentation.
4. Individual tables and dated publications — the CBR distinction and its generalization.
5. Discovery and update evidence — what a check can actually establish.
6. Processing need — deciding which work remains after a check.
7. Journal-derived retained state — persistent facts, projections and recovery.
8. Repeated application calls — a finite core inside a continuously running host.
9. Bounded materials and archives — keeping acquisition, conversion and verification efficient.
10. Completeness and partial results — assessing the requested scope precisely.
11. The seven workload contracts — detailed functional obligations.
12. Source-faithful DBF export — preservation, applicability and large-table behavior.
13. Historical observations and scientific selection — revisions, inputs and reference meaning.
14. Products, delivery and maintenance — independent effects and useful manifests.
15. Cross-domain applicability — proving generality without expanding economic scope.
16. Implementation priorities — coherent delivery slices and their dependencies.
17. Acceptance situations — evidence required before claiming support.
18. Boundaries and remaining evidence — what the research settles and what still requires verification.
19. Supporting references — implementation anchors and primary protocol evidence.

## 1. Recommended decisions

### 1.1. Extend common actions around existing domain knowledge

| Code | Recommendation | Practical consequence |
| --- | --- | --- |
| D01 | Keep one catalog of declared domain sources and methods. | Source discovery reads existing declarations; a separate notebook or collector registry is unnecessary. |
| D02 | Make concrete membership caller-owned. | An external script supplies IDs or a predicate; commands and operations contain no embedded CBR download list. |
| D03 | Freeze resolved membership for each finite pass. | A newly added catalog entry or publication cannot silently join work already in progress. |
| D04 | Separate source observation from required processing. | An unchanged source can still require extraction, rendering, retention or delivery. |
| D05 | Reuse the existing execution journal and effect authority. | Persistent lookup is an indexed projection of qualified facts, rather than another independent success ledger. |
| D06 | Carry large completed materials by verified references. | Downloading, unpacking, converting, packaging and verification remain bounded in memory. |
| D07 | Distinguish a complete requested subset from whole-source coverage. | Selecting three banks or two files can yield a fully satisfied request without claiming complete processing of the parent source. |
| D08 | Resolve publication revisions explicitly. | Duplicate observations, changed historical values and renamed files receive documented decisions. |
| D09 | Preserve domain input requirements before narrowing outputs. | APK calculations retain their source components; form models retain the required rows and measurement context. |
| D10 | Keep schedules and user preferences in the host. | The library performs finite calls; the application decides when and why to call again. |
| D11 | Preserve the existing command/operation execution path. | No separate notebook executor, large-file runner or permanent refresh loop is introduced. |
| D12 | Prove support at the promised boundary. | A declared source, a successful synthetic fixture and a validated historical publisher file establish different levels of readiness. |

The concrete source selection and its presentation defaults remain application data. A general operation may accept a selection, a query or exact material references. Its implementation must behave the same way for another compatible selection.

### 1.2. Limit the present development scope

The immediate subject is reusable commands, operations, typed values and the infrastructure required by their promises. Existing scenario and cascade definitions can remain available, but new purposeful notebook scenarios and permanent orchestration are outside this proposal.

The scope includes the mechanical work required to preserve the useful behavior of the seven notebooks: selected originals, archive export, source-faithful DBF tables, selected bank reports, industry histories, escrow histories and a Rosstat monthly workbook. It also includes the contracts needed to repeat those finite tasks safely after interruption.

The scope does not include new financial models for additional CBR forms, all-history scientific certification of every source, a general distributed workflow service, or a new desktop scheduler.

## 2. Requested results are independent promises

A caller should be able to request the smallest sufficient result. The following goals can share inputs without becoming a compulsory pipeline.

| Code | Requested result | Required evidence | Work that the goal does not inherently require |
| --- | --- | --- | --- |
| G01 | Retained original publication | Exact bytes, qualified source relation, confirmed immutable retention and selected membership. | Economic interpretation or spreadsheet rendering. |
| G02 | Source-faithful physical table export | Declared physical conversion policy, source/member identity, output identity and preservation evidence. | Financial-model semantics. |
| G03 | Accepted observations | Qualified interpretation, units, time, grain, source evidence and validation. | An XLSX product or external delivery. |
| G04 | Accepted derived values | Required input closure, method/reference basis, scientific applicability and diagnostics. | Reacquisition of already retained originals. |
| G05 | Rendered analytical product | Accepted values/view, content and presentation policy, reproducible basis. | Re-running unchanged upstream calculations. |
| G06 | Published archive or bundle | Frozen member names and identities, completion report, confirmed archive retention and any requested delivery. | Full processing of every source known to the domain. |
| G07 | Controlled file maintenance | A pinned plan, source/destination preconditions, required predecessor receipts and per-action outcomes. | Reinterpretation of the files being moved or copied. |

A report that has been rendered but whose requested save failed has satisfied a different boundary from a saved report. A raw original retained for diagnostics is not yet an accepted financial dataset. The result should expose those distinctions.

A goal can require several boundaries. For example, “provide a ZIP of these three original workbooks at this destination” requires three qualified originals, a complete selected-member package and a confirmed delivery. Reuse can satisfy the first obligations while a new destination still requires an effect.

## 3. Concrete selection belongs to the caller

### 3.1. Separate four kinds of selection

| Code | Selection level | Meaning | Example |
| --- | --- | --- | --- |
| S01 | Source catalog | Which continuing publication objects matter to this task? | A caller-selected set of individual CBR workbooks. |
| S02 | Publication/asset | Which observed issues and representations are required? | XLSX issues within an explicit reporting-date range. |
| S03 | Observations | Which interpreted coordinates are required? | Specific bank registrations, regions, measures and periods. |
| S04 | Product | Which accepted values and labels should appear? | Sheet ordering, display names and a monthly-only view. |

These selections have different consequences. Choosing an output metric does not establish which source operands can be omitted. Choosing one file from an archive does not automatically prove that the remaining archive members are irrelevant to its interpretation.

### 3.2. External configuration chooses the membership

The external caller can supply exact source IDs, a structured catalog predicate, or a predicate with explicit additions and exclusions. The library resolves and validates that request against the declared catalog.

A caller-owned configuration might mean:

- domain CBR;
- publication topology rolling;
- artifact category statistical workbook;
- allowed representation XLSX;
- explicit exclusions selected by the user.

That configuration is an example of an external task, not a special mode to embed in `operation.source.check` or an acquisition operation. The same mechanism can select one workbook, another publisher's current document, or a bounded set of local publication families.

The precedence rule should be explicit: validate all mentioned IDs; combine predicate matches and explicit additions; apply explicit exclusions; preserve the caller's requested order where supplied; otherwise use a declared deterministic order. Unsupported selector fields and unknown explicit IDs reject the request before network work with actionable diagnostics. A valid predicate matching no sources is a separate empty-selection result, whose acceptability follows the caller's goal.

An omitted selector must not mean “everything in this publisher catalog.” Selecting all known sources is an explicit caller decision.

### 3.3. Resolve a selection once, then carry its identity

A resolved source selection should retain the requested predicate, exact selected IDs, ordering, excluded matches, invalid requests, declaration basis and a content fingerprint. A publication selection similarly records the exact selected assets and unresolved requirements.

The result is a data value that can support preview, execution, manifests and later explanation. It is not another authored registry or a workflow definition.

If a user later adds a table, the next request receives another selection identity. Previously completed members remain reusable when their own basis matches. The aggregate archive membership changes even if every original file was already available.

### 3.4. Catalog description is distinct from task selection

The domain catalog remains responsible for what a source is and how supported actions interpret it: publisher, stable identity, publication topology, formats, access rules, measurement meaning and qualified methods.

The caller remains responsible for what to do now: chosen sources, periods, output goals, destinations and tolerances.

An implementation must not move a useful external preset into a standard operation merely to shorten a notebook cell. A future scenario or cascade can own a purposeful preset when it becomes a stable reusable user task.

## 4. An individual updated workbook is different from a dated issue collection

### 4.1. Publication topology is independent of observation frequency

One workbook at a stable address can contain many years of monthly observations. It remains a single independently updated publication object. A separate collection can publish a different workbook or RAR archive for every month. Both contain monthly data; their acquisition and history contracts differ.

Useful neutral descriptors therefore separate:

| Code | Descriptor | Question answered |
| --- | --- | --- |
| P01 | Continuing source identity | Which logical publication is this? |
| P02 | Issue topology | Is there one rolling object, dated issues, publisher-defined editions, or captures? |
| P03 | Delivery/discovery mode | Is the material addressed directly, listed on an index, returned by an API, or delivered locally? |
| P04 | Artifact category and representation | Is it a workbook, a form archive, a document, or a page capture? |
| P05 | Measurement frequency | What periods do the observations represent? |
| P06 | Supported processing stages | Which material, physical, semantic, calculation and product promises have qualified support? |

The selector consumes these declared facts. It does not infer publication topology from a filename, an ID substring or the monthly frequency of the underlying data.

### 4.2. The fixed-table collector has a precise scope

At the inspected implementation, the CBR catalog declares 57 continuing series. Of these, 42 are rolling fixed XLSX publications. The remaining records cover dated corporate-lending issues and reporting forms, project-finance escrow issues, a captured page and territorial publication indexes. This is a catalog classification, not a recommended automatic download set. [I01]

The original simple collector selected 41 individual XLSX publications. Those publications have corresponding qualified IDs and the same source addresses in the inspected catalog; the additional rolling workbook is `cbr.corporate_lending.sme_ie_debt_activity`. The initial external notebook configuration can preserve the earlier membership or deliberately select the expanded set. Either choice must remain visible outside commands and operations.

The original count is migration context for that external request. It must not become a hardcoded “41-table” or “42-table” library mode.

### 4.3. Three CBR file tasks must remain distinguishable

| Code | Task | Selection unit | Required processing |
| --- | --- | --- | --- |
| CBR01 | Archive individual statistical workbooks | Caller-selected continuing rolling publications. | Acquire/validate originals and package selected files. |
| CBR02 | Export physical tables from regulatory-form archives | Observed form/date archive assets and their DBF members. | Physical archive extraction and source-faithful CSV export. |
| CBR03 | Produce bank financial-model workbooks | Reviewed forms, reporting dates and subjects. | Semantic interpretation, model calculation and rendering. |

A raw form-archive exporter can support a newly observed form number without a financial model for that form. A fixed-workbook collector should not acquire dated form archives merely because both are associated with CBR.

## 5. Discovery, freshness and source change establish different facts

### 5.1. State the comparison scope

| Code | Evidence level | Legitimate finding | Finding it does not establish |
| --- | --- | --- | --- |
| E01 | Catalog declaration | A source and its configured methods are known. | The current remote publication exists or is reachable. |
| E02 | Observed listing | Particular candidates appeared within a bounded observation. | Each candidate's bytes are unchanged. |
| E03 | Representation validation | A retained representation is reusable under an admitted validation policy. | Independent equality of all remote bytes or all downstream values. |
| E04 | Exact material bytes | A byte identity matches or differs. | The economic facts necessarily changed. |
| E05 | Physical table evidence | Layout, formulas, tokens or cells differ under a declared comparison. | The interpreted statistical meaning necessarily changed. |
| E06 | Accepted observations | Qualified facts differ under a compatible semantic basis. | Every requested product or destination is already fulfilled. |

The current CBR comparison methods already distinguish several of these levels and explicitly qualify unchanged index links as insufficient evidence about asset bytes. That distinction should become consistent across common check contracts. FNS and Minfin listing comparisons also need an explicit scope before their results can drive acquisition decisions. [I02]

The check result should identify the compared source/asset subset, candidate evidence, baseline evidence, observation time, comparison method and qualification. Whole-feed comparison remains useful when the caller requests it. It must not accidentally stand in for a selected-table comparison.

For a directly addressed fixed workbook, one eligible request can both observe and acquire the candidate. The returned material or retained reference and its observation evidence should be passed downstream within the same observation scope. A subsequent acquisition step must reuse that admitted candidate instead of automatically requesting it again. An index request has a different purpose: observing its links does not acquire the linked asset. Additional requests remain justified by changed freshness requirements, missing bytes or explicit revalidation policy.

### 5.2. Conditional retrieval is useful, subject to its evidence

HTTP validation can avoid transferring a body. A `304` response has no replacement content and refers to a retained representation; validation metadata is scoped to the relevant request representation. [EHTTP01, EHTTP02]

The proposed acquisition policy therefore verifies that the retained object is accessible, matches the recorded identity and belongs to that representation. If the required body is missing, a normal body request is needed. A validator is not a replacement for retained bytes.

A publisher may omit reliable validators. In that case, some checks must download the candidate before discovering that its bytes already exist locally. The system can avoid redundant storage and downstream work, but cannot promise zero repeated transfer without sufficient remote evidence.

A strict archival policy may require periodic unconditional retrieval or a fresh byte observation. This is a caller-selected assurance requirement with a finite core action. It is not a reason to turn every publication check into a complete semantic parse.

Dated publications also need an explicit revisitation policy when earlier issues can change. A caller can select a bounded recent-issue count, a time window or an occasional bounded historical sweep. Checking only the latest issue cannot detect revisions to older dates. Revisit settings govern new observations; they do not redefine the historical membership requested for a report. Notebook-specific recent-issue counts remain external configuration.

### 5.3. Preserve distinct kinds of novelty

The following events are different:

- a source was first observed by this installation;
- a previously unobserved historical issue was discovered;
- a genuinely newer publisher issue appeared;
- the bytes of an existing issue changed;
- a locator changed while logical identity remained stable;
- an old byte revision reappeared;
- only interpretation or presentation dependencies changed.

For a rolling file observed as A → B → A, preserve three observations, two content changes and two reusable byte identities. The initial first-seen admission remains distinct from a content change. A content-addressed store can reuse the bytes for A while the journal still records the later return to A.

A hash does not establish publisher chronology. Local observation time is also not automatically a publisher revision number.

### 5.4. Requested dates and discovered availability are separate

The query must identify its date axis: reporting date, measurement period, publication date or local observation time. It must also distinguish a bounded search of actual publications from a request for expected calendar membership.

| Code | Coverage intent | Appropriate behavior |
| --- | --- | --- |
| Q01 | All observed issues in a range | Select actual index entries; qualify the listing's scope and completeness. |
| Q02 | Exact requested issues | Account for every requested issue, including unavailable or ambiguous ones. |
| Q03 | Expected publisher calendar | Apply a reviewed source-specific calendar and account for due, not-due and missing issues. |
| Q04 | Latest eligible issue | Use declared ordering and representation policy, recording the chosen candidate and alternatives. |
| Q05 | Rolling current publication | Observe the selected object and its revisions; do not manufacture monthly issue identities. |

The investigated notebook's quarterly date selection for form 802, its monthly selections for other forms, date-specific FNS requests and irregular local publications illustrate why a universal month-generation loop would be incorrect. Historical calendar applicability still requires reviewed publisher evidence; the notebook's date-generation rule alone does not establish it.

## 6. A separate work assessment decides what remains to be done

### 6.1. Assess the desired result, not only the source

The proposed processing assessment consumes:

1. the caller's requested goal and selected scope;
2. qualified source evidence;
3. retained accepted originals, datasets or products;
4. effective method, settings, reference and presentation dependencies;
5. destination requirements and effect state;
6. the completeness and checkpoint of the retained-state lookup;
7. an explicit `evaluation_time` and the applicable freshness/retry policy.

It returns a finite decision with reasons and required next stages. It does not start hidden work or discover another source list.

Freshness and retry eligibility are evaluated against the supplied time. With identical evidence, policy and evaluation time, the assessment should produce the same decision; it must not read an unrecorded wall clock while claiming to be pure.

| Code | Situation | Required next action |
| --- | --- | --- |
| W01 | No adequate source observation or retained original | Observe or acquire under the requested policy. |
| W02 | Current original already retained; original-only goal satisfied | Reuse the original and record a no-work outcome for acquisition. |
| W03 | Original retained; extraction absent | Decode, interpret and validate that retained original. |
| W04 | Bytes unchanged; interpretation/reference basis changed | Reinterpret from the original; reuse acquisition. |
| W05 | Dataset accepted; calculation absent or stale | Run the required calculation with its input closure. |
| W06 | Accepted view/data exists; workbook absent or style changed | Prepare or render the product from the nearest valid retained entrance. |
| W07 | Product exists; requested destination differs | Fulfill the new delivery effect without recomputing the product. |
| W08 | Prior receipt exists; required artifact is missing or corrupt | Repair retention or reacquire the needed source; qualify the lost guarantee. |
| W09 | A required effect is uncertain | Reconcile before an eligible repeat. |
| W10 | Projection is behind or has a gap | Catch up or report insufficient state; avoid a false “already done” or “never seen”. |
| W11 | Every selected obligation is satisfied | Return a qualified no-work result. |
| W12 | A required publication is absent or ambiguous | Preserve the unresolved requirement and its reason. |

The implementation can represent several required actions for one member. For example, a new remote observation may require acquisition, while the exact content obtained can then eliminate extraction and rendering. The decision should be reevaluated at explicit evidence boundaries.

### 6.2. Dependency identity determines reuse

Reuse must distinguish source bytes from interpreted meaning, derived values, representation settings and destination effects. Semantic reuse also requires compatible issue/asset attribution, measurement-period context and applicable reference identities: the same bytes assigned to a different issue can imply different periods. Physical acquisition or decode reuse does not erase that distinction.

Changing a bank selection can change a report without changing its original archive. Changing number formatting can change an XLSX without changing accepted observations. Changing a source decoder can invalidate semantic reuse while exact original retention remains valid.

A package build or effective dependency fingerprint qualifies the code basis. Independent hand-maintained method-version counters would create another authority to maintain. Where precise dependencies cannot be established, conservative invalidation is preferable to unproved reuse.

### 6.3. No-work is a normal outcome with a reason

“No acquisition needed” is not “no requested publications exist.” A recurring pass can succeed with no new work after confirming that its selected obligations are satisfied.

Conversely, an empty discovery caused by an incomplete index or a failed request cannot establish a complete historical report. Acquisition should retain its nonempty-input requirement where a material is required. A no-work result belongs at the decision boundary.

## 7. Use a journal-derived index for efficient persistent lookup

### 7.1. Preserve one authority for execution facts

The existing file journal already provides bounded pages, a stream identity, consumer cursors, segment archival and guarded pruning. The existing effect state records confirmed or uncertain effects. These mechanisms should be extended and connected, rather than replaced. [I03]

The remaining gap is the content of the accepted facts. At the inspected implementation, ordinary `output.accepted` events do not persist the complete value/source/retained-reference basis needed for later per-table work decisions; some of that information exists only in live execution metadata. [I03]

The proposal adds compact accepted-output and effect references to the journal, then maintains an indexed projection for fast lookup. The index answers a specific question such as “which accepted original and downstream results are known for this source/issue/asset and this dependency basis?”

### 7.2. Keep observation, accepted work and storage availability distinct

| Code | Retained state | Meaning |
| --- | --- | --- |
| J01 | Last observed source evidence | What was seen and compared at a stated time. |
| J02 | Accepted original revisions | Which exact retained bytes passed the required physical/source admission. |
| J03 | Accepted processing outputs | Which interpretation, calculation or product basis completed. |
| J04 | Confirmed effects | Which destination transitions were confirmed or remain uncertain. |
| J05 | Projection position | Through which journal position the lookup is complete. |
| J06 | Availability observation | Whether required retained content is still accessible under its provider guarantee. |

An observed new revision must not overwrite the last successful downstream checkpoint when its parsing fails. Repeated checks should still show that the source changed, while the current product remains based on an earlier accepted revision.

### 7.3. Advance projection state only with durable coverage

The projector reads bounded journal pages, applies facts idempotently and commits its updated rows together with its cursor. Only then does it acknowledge that page to the journal.

A crash before acknowledgement permits harmless replay. A crash after an external write but before a completion fact requires reconciliation from the persisted effect intent and destination evidence.

A projection can be rebuilt from retained facts or a verified retained projection checkpoint. If required historical facts and checkpoints have both been pruned, reconstruction is incomplete. The system must expose that limitation rather than fabricate a full history.

A requested journal horizon is a minimum freshness requirement: the lookup must cover at least that position and report the position it actually covers. It may include later accepted facts. This is distinct from a historical as-of request, which needs its own observation/vintage cutoff and sufficient retained history; a minimum cursor alone cannot reconstruct an earlier state.

UI progress callbacks remain observation conveniences. They are not a durable basis for deciding which publications to skip.

### 7.4. Retention rules follow actual consumers

Publication history, stored originals, generated products and execution events can have different retention periods. A short UI history must not authorize deleting the only evidence needed by the incremental-processing index.

Once the index has a durable compacted checkpoint, older journal segments can be pruned only when all registered consumers' acknowledgement floors and the declared recovery/retention policy permit it. The index cannot override another consumer's requirement. Artifact retention remains separate: an old event can describe bytes that are intentionally no longer available.

## 8. A continuously running host repeatedly submits finite work

### 8.1. Keep the long lifetime outside the operation

The future application owns schedules, user selections, destinations, process startup, credentials and provider configuration. It decides when another check is due and whether overlapping occurrences should coalesce.

The library owns a bounded check, work assessment, acquisition, transformation, publication or maintenance call. A single long-lived `StrategyBox` session can serve many finite calls and share providers and resource limits.

A permanent polling loop inside a domain method, operation or `RepeatUntil` would mix application lifecycle with a reusable analytical action.

### 8.2. A finite polling pass

A host pass should:

1. capture the caller's selection and policy;
2. choose a bounded observation scope and source-state checkpoint;
3. obtain or reuse qualified listing/representation evidence;
4. assess work for the selected members;
5. submit eligible finite calls with bounded concurrency;
6. retain goal-required outputs/evidence and explicitly selected recovery checkpoints, preserving successful members under their ownership policy and accounting for unresolved obligations;
7. expose a positioned report for the host;
8. schedule another occurrence according to host policy.

New publications discovered after the frozen pass belong to a later pass or an explicit new evaluation. Recovery of an interrupted historical request keeps its pinned inputs; it does not silently substitute today's latest publication.

### 8.3. Reuse the existing session and maps

The current runtime already supports bounded maps and independent calls in one session. A map template currently has one prepared target. Heterogeneous sources can therefore be submitted as bounded per-target calls; maps can process issues or assets within the target. General dynamic target binding is not a prerequisite. [I04]

Successful independent members remain useful when another source fails. The host should not redownload all completed originals because one report or one later archive delivery failed.

### 8.4. Avoid stale completion becoming “current”

If a slow older pass completes after a newer pass, both results can remain valid for their pinned basis. Publishing a current pointer additionally requires a conditional destination transition and an admitted source-ordering policy.

Storage compare-and-replace alone does not decide which publication is scientifically newer. Publisher chronology and destination concurrency are separate responsibilities.

## 9. Large-file support must remain bounded across the whole route

### 9.1. Existing acquisition is only the first segment

`command.material.receive` already streams a response into content storage and returns an immutable reference. The present archive, conversion and verification routes still often require complete `Material.data` bytes. Consequently, a streamed download can become a large memory allocation downstream. [I05]

The target is a continuous route through completed readable materials: exact originals, selected archive members, converted tables, packaged archives, retention and readback.

Large local deliveries need the same bounded entrance as remote originals. A local read can copy an explicitly selected, provider-scoped file into a sealed stage while verifying its expected state and complete byte identity. The staged placement of `command.material.read` is a proposed extension; its buffered placement remains an explicit bounded choice. Frank RG packaging must therefore be able to start from a large delivered file without first allocating the whole file in memory.

### 9.2. Three material lifetimes

| Code | Carrier | Promise | Lifetime |
| --- | --- | --- | --- |
| B01 | Buffered material | A bounded complete byte sequence is available in memory. | Ordinary value/result ownership. |
| B02 | Sealed staged material | A complete verified representation is readable from controlled temporary storage. | Its owning execution/result and admitted consumers. |
| B03 | Immutable retained material | Exact bytes have confirmed persistent retention and an addressable receipt. | The storage retention contract. |

A sealed staged value is not an open stream and is not a durable recovery promise. A failed writer cannot publish it as a completed representation.

The existing result lifetime must gain explicit ownership of staged files. Closing a producer result after another consumer has been admitted should release only the producer's ownership. A live consumer must retain access.

### 9.3. Bound the expensive parts

Limits must cover response bytes, cumulative input, live staged bytes, archive member count, unpacked size, expansion ratio where applicable, DBF rows/cells, generated evidence, output bytes and elapsed time.

Streaming a file does not make an unbounded inventory, a million-element diagnostic list or a full deletion-ordinal JSON list acceptable. Metadata must also be bounded, pageable or represented by an exact retained sidecar.

Capacity waiting must respect dependencies. A map that holds completed stages until final packaging cannot wait indefinitely for space that only that blocked packaging step could release. The request must fit an admitted aggregate allowance, retain and release members incrementally, or finish with a qualified capacity failure. Boundedness includes freedom from this dependency deadlock.

A semantic workbook decoder may still require a bounded in-memory cell representation. Its resource claim should be explicit; “file-backed input” does not imply that every parser is constant-memory.

### 9.4. Archive semantics

An archive has a frozen member plan: portable entry names, source references, exact identities, ordering, compression and completion policy. Input changes, collisions and unsupported representations are diagnosed before a complete archive is claimed.

ZIP and RAR extraction should share inventory, selection, resource and provenance semantics. The RAR backend's actual ability to read the requested members must be checked; an installed Python import alone does not establish that capability.

The reusable streaming ZIP mechanics already include chunked copying and identity verification. They should be integrated under the standard execution/effect path. Direct notebook invocation of an alternate storage helper would recreate an uncoordinated path. [I05]

### 9.5. A snapshot archive and an incremental archive are different products

For a selected snapshot, the archive contains all required selected members, combining newly acquired and reusable originals. For an explicit delta archive, it contains only members meeting the caller's transition criterion.

Both need an exact manifest. “Only download necessary files” must not accidentally turn a requested complete archive into a delta archive. Download decisions concern acquisition; archive membership concerns the requested product.

## 10. Completeness belongs to a declared scope

### 10.1. Track separate dimensions

| Code | Dimension | Example |
| --- | --- | --- |
| K01 | Discovery coverage | Which pages, directories or date scopes were successfully inspected? |
| K02 | Requested membership | Were all requested sources/issues identified or accounted for? |
| K03 | Selected-member processing | Which selected members reached the required stage? |
| K04 | Physical table coverage | Which members, rows or cells were decoded or exported? |
| K05 | Semantic coverage | Which source values were interpreted and scientifically validated? |
| K06 | Product coverage | Which requested outputs and cells were produced? |
| K07 | Effect completion | Which required retention and delivery effects were confirmed? |

A deliberate subset is a relation to its parent, not inherently a processing failure. A selected monthly view can be complete even when the parent also contains annual and quarterly observations.

At present, shared selection helpers mark reduced datasets/material collections partial, while some product methods retain the parent assessment after filtering. A common selected-scope contract should remove this inconsistency. [I06]

### 10.2. Per-member dispositions must explain partial results

Useful dispositions include selected-and-complete, reused, deliberately excluded, not due, observed absent, requested-but-missing, ambiguous, unsupported, failed, cancelled, not attempted and effect unknown.

These are dimensions or reason codes, rather than an invitation to replace the runtime's outcome vocabulary with dozens of states. The report preserves the execution outcome, requested requirement, availability evidence and effect status separately.

A complete partial report is possible: it can accurately account for every selected member while the requested all-members result remains unsatisfied. The API must expose both truths.

### 10.3. Failure should propagate through actual dependencies

An unsupported DBF member may block a full physical export of that archive while leaving an independently acquired original valid. A missing form 802 issue should not erase a confirmed form 101 workbook. A final ZIP save failure should not invalidate accepted source datasets.

The root result remains qualified according to the caller's completion policy. Required failures must not disappear merely because an unrelated member succeeded.

## 11. Detailed contracts for the seven workloads

### 11.1. Individual CBR workbook collection

The external script chooses individual publications. The common route acquires or reuses each original, performs lightweight physical/source admission, records its exact identity and packages the selected set.

Required behavior includes per-source deadlines, bounded retries and total budgets; explicit case-safe entry names; requested/attempted/completed/failed/not-attempted reporting; and a clear partial-output policy. If an archive effect is uncertain, publication or maintenance must wait for reconciliation.

Economic extraction is unnecessary for an original-only goal. A server-generated HTML error page must not qualify as the requested XLSX merely because the HTTP status was successful or the URL ended in `.xlsx`.

### 11.2. Physical DBF table export from CBR form archives

The caller chooses date and form criteria. Discovery uses actual official-index entries unless an explicit, qualified calendar-request policy is selected. The exported unit is every selected physical DBF table, including support tables that a semantic form extractor can omit.

This route preserves row and field order within each physical table, with an explicit deterministic archive-member order, lexical values, encoding decisions, deleted-record evidence and source/member provenance. It must support known raw publications independently of whether their financial-model semantics are implemented.

A publication-feed target can describe the collection of form archive assets using the existing feed/catalog mechanism. An observed unknown form code gains physical provenance; it does not gain a fictitious reviewed financial model. Moving a known form into semantic interpretation requires its exact feed, form asset, issue and material relation to be established. A recognized-series metadata hint is insufficient; the admitted series use must preserve the original feed provenance.

### 11.3. Six-form semantic bank workbooks

The investigated task concerns reviewed models for forms 101, 102, 123, 135, 802 and 805. Existing methods already enforce substantial unit, period, account, namespace and evidence requirements. Additional models for 134 or 803 are outside this workload. [I07]

The external caller selects forms, reporting scope and bank/group subjects. A named bank reference selection is explicit; an absent subject argument must not silently change an intended selected-bank report into an all-bank report.

The route must preserve registration identity, namespace, requested ordering and display-label policy. Group registration for form 802 differs from bank registration. Form 102 requires reviewed reporting-interval resolution. Missing archives, source decoding failures and missing model operands have different consequences.

Deleted DBF rows are excluded from semantic reporting under its source rules, while the physical export route retains their evidence. The two results intentionally promise different things.

### 11.4. Industry histories for APK and publisher total

The current APK calculation requires five admitted source components and produces derived APK/LPK rows. Publisher total remains an original source metric. The external task combines the appropriate outputs for separate requested workbooks; it must not expect total to appear automatically in the calculation result. [I08]

Validation of each source issue precedes a narrow analytical materialization. Output selection cannot discard APK operands. A history must retain the evidence of per-issue validation without depending on a live parser-native object.

The 0105A debt values are as-of stocks, while the reviewed 0104A issuance values cover a preceding-month interval. Selecting publications by reporting date and selecting observations by measurement month can therefore produce different sets; the request must state which dates it constrains.

The 2019-onward use case can cross changes in geography descriptors and publication layouts. A historical product policy must state its display edition or historical naming behavior while retaining the original territorial evidence. Suppressing a geography-conflict check would not establish correctness.

The selected debt and issuance metrics, workbook names and optional metadata sheets remain external product choices passed to general product contracts.

### 11.5. Project-finance escrow history

The dated project-finance escrow collection is distinct from the individual funding escrow workbook. The caller must select the intended source and representation.

The current product supports ten metric sheets and latest-period or explicit region selection. The required addition is a reliable history/coverage basis: a string qualification alone cannot prove that a requested date range has been covered. [I08]

If a listing includes historical HTML as well as XLSX, representation applicability must be explicit. Discovery of a format does not prove that every historical layout is semantically supported. Missing or unsupported periods remain visible.

### 11.6. Frank RG large archive and optional maintenance

The external task selects a directory, family scope and mode. The operation chain recognizes delivered files, freezes candidates, resolves latest eligible publications, verifies selected identities and produces a streamed archive.

The modes archive-only, copy-latest and rename/remove-older are external task compositions. General commands provide inventory, selection, archive creation, materialization and conditional maintenance. They must not embed a Frank RG folder-management scenario.

Unrecognized files are reported and left outside the selected maintenance scope. Concurrent arrivals belong to a later inventory. Same-issue alternatives with different contents remain ambiguous unless an explicit revision rule resolves them.

Maintenance requires a confirmed prerequisite matching the selected archive plan. The original behavior preserves the selected latest publications before removing older recognized versions. A policy to archive every version being removed is a different, stronger request and must be stated separately. [I09]

Numerical interpretation readiness for all fourteen declared families is independent of the metadata-based archive goal.

### 11.7. Rosstat KEP monthly workbook

The library already owns physical decoding, reviewed KEP interpretation and an eleven-indicator monthly product. The migrated task should use these owners, preserving reported absolute values and source indices, monthly interval meaning, next-period-start display dates, missingness and row order. [I10]

Subtracting 100 from a reported index is a separate requested calculation. It is not part of reproducing the original index workbook.

The old notebook's fuzzy sheet selection, accidental duplicate-function replacement, implicit duplicate-cell averaging and overwritten title are not desirable compatibility requirements. The accepted contract should explicitly reject ambiguous cells and preserve source precision.

Sheet language, header position, frozen panes, number formats and evidence-sheet visibility are declared product settings. They can evolve without changing the scientific values.

## 12. Source-faithful DBF export requires a stated preservation profile

### 12.1. Preserve the intended representation precisely

| Code | Obligation | Required result |
| --- | --- | --- |
| DBF01 | Row and field order | Preserve source order, including deleted-record positions. |
| DBF02 | Character fields | Decode using the admitted encoding and remove only declared fixed-width padding. |
| DBF03 | Numeric text fields | Preserve decimal lexemes without a float conversion. |
| DBF04 | Blank values | Keep blank distinct from zero and from an inferred missing-status label. |
| DBF05 | Textual dates/logicals | Preserve their source tokens unless a separate semantic transformation is requested. |
| DBF06 | Deleted records | Export under the stated policy and retain exact deletion evidence. |
| DBF07 | Physical metadata | Retain dialect, header date, geometry, language driver, field schema and encoding basis. |
| DBF08 | Source relation | Record original archive, member path, DBF identity, output identity and transformation basis. |
| DBF09 | Output format | State UTF-8, delimiter, quoting, line termination and filename mapping. |
| DBF10 | Failure behavior | Unsupported dialect/type, truncated record or unavailable memo companion remains explicit. |

CSV is a decoded physical representation, not a byte-reversible replacement for DBF. Exact source retention is a separate obligation. If the caller requests archival reproducibility, retain the original DBF or its containing archive alongside the conversion evidence.

The current strict DBF reader preserves classic textual fields and deletion flags, but the standard command drops some physical header metadata and does not forward all resource limits into parsing. Both gaps are concrete targets. [I11]

For the physical-export task, the caller supplies the following initial preservation policy. These values are task configuration consumed by a general exporter; they do not create a CBR-specific conversion command or an independently versioned profile registry.

| Code | Policy field | Initial requested behavior |
| --- | --- | --- |
| DP01 | Text encoding | CP866 with strict decoding. An exact override is scoped by form code, reporting date and member path; an unambiguous filename can identify that member. Record the effective codec and the reason it was selected. |
| DP02 | Character padding | For C fields, remove only trailing space/NUL padding; preserve leading whitespace and the remaining text. |
| DP03 | Textual number/date/logical padding | For N/F/D/L fields, remove declared space/NUL padding from the ends and preserve the remaining lexeme, including zeros and decimal precision. |
| DP04 | Physical records | Export all records in source order, including deleted records, and retain their one-based ordinals in exact deletion evidence. |
| DP05 | CSV representation | UTF-8, comma delimiter, double-quote quoting with `QUOTE_MINIMAL`, LF line endings, and the original field order. |
| DP06 | Override ambiguity | Reject ambiguous member matching or a decoding failure; a guessed codec or replacement character does not satisfy this preservation policy. |

### 12.2. Binary types need dialect evidence

The old script contains binary integer, currency, double and timestamp branches beyond the current strict classic decoder. Those branches cannot be accepted solely because the script once produced output.

| Code | Physical class | Proposed admission |
| --- | --- | --- |
| DBFT01 | Classic C/N/F/D/L | Preserve the reviewed lexical contract and validate actual publisher examples. |
| DBFT02 | Binary integer/currency | Candidate mappings are signed little-endian `I/+` integers of 2/4/8 bytes and eight-byte `Y` currency scaled by 10,000 using exact decimal arithmetic. Admit only the dialect/type/width combinations established by fixtures. |
| DBFT03 | Binary floating point | The candidate `B/O` mapping renders an eight-byte double with 17 significant digits (`.17g`). Establish the dialect and exceptional-value policy; this is binary-value rendering, not lexical preservation. |
| DBFT04 | Binary timestamp/opaque fields | The candidate `T/@` mapping represents nonblank eight-byte payloads as deterministic hexadecimal text and preserves declared blank handling. Admit an explicit reversible physical encoding where calendar interpretation is unsupported. |
| DBFT05 | Memo or external companion fields | Require the companion-file contract or return unsupported. |

This keeps the mechanism general while refusing unsupported scientific or physical assumptions.

### 12.3. Stream evidence as well as CSV rows

A large DBF can have millions of deleted-record ordinals. Its preservation evidence must use a bounded sidecar or exact range representation, not an unbounded Python list embedded into a single journal fact.

Header geometry and row/cell limits are checked before allocation. Buffered decode and streamed export should share the strict physical parser. The export command consumes records internally; a live generator is not an ordinary portable graph output.

The export is logically complete only when both the CSV and its required preservation evidence have confirmed retention. Their physical commits may occur separately. A confirmed CSV with failed or uncertain evidence retention remains a partial export with separately resumable receipts, rather than an atomic multi-object publication claim.

## 13. Historical observations require explicit revision and validation policy

### 13.1. Keep simple merge strict

The existing merge checks semantic equality and duplicate grain. That remains useful for disjoint compatible observations. It should not acquire an implicit “last row wins” rule. [I12]

A history-specific operation should establish requested membership, resolve candidate revisions under an explicit policy, preserve per-issue admission evidence, merge compatible observations and assess coverage.

Stable scientific semantics must remain separate from the list of contributing issues. Appending another issue should not fail merely because an earlier merged result stored membership metadata in its semantic dictionary.

### 13.2. Distinguish equal duplicates, revised values and incompatibility

| Code | Situation | Resolution |
| --- | --- | --- |
| H01 | Identical qualified observation repeated | May be coalesced with all contributing provenance preserved. |
| H02 | Same grain, changed value and admitted revision order | Select according to the requested vintage/as-of policy and retain the rejected alternative. |
| H03 | Same grain, conflicting values without order evidence | Return an explicit ambiguity. |
| H04 | Different units, perimeter or period meaning | Require an admitted transformation or keep incompatible partitions separate. |
| H05 | Changed geography/reference meaning | Preserve historical context and apply a declared reconciliation/display policy. |
| H06 | Requested issue absent | Record the missing requirement; do not infer coverage from available rows alone. |

Publisher revision choice and observation overlap choice are separate. Two workbooks can cover the same month while being different releases, and one workbook can revise several earlier months.

### 13.3. Validation must survive retention and composition

A source dataset needs portable evidence of what was validated, by which rules, over which scope and with which result. An opaque parser object should not be the only carrier of that evidence.

This matters concretely for industry histories: per-issue extraction can pass, while later generic merging loses the native parser evidence required by the domain validator. The proposal replaces that accidental lifetime dependency with an explicit validation basis. [I12]

A retained validation record must be bound to the dataset/material identity and effective rule basis. It cannot be a caller-authored boolean that silently bypasses validation.

## 14. Products and maintenance have their own obligations

### 14.1. Name, retain and deliver separately

An immutable content reference is useful for reuse and provenance. A human-readable output filename is useful for Colab downloads and application folders. These are separate representations of delivery.

A common bounded materialization/copy action should take an accepted reference, a destination and a conditional write policy. It returns a destination-specific receipt. Reusing the original bytes does not automatically confirm the new named file.

Before changing the destination, persist a typed effect intent with provider scope, destination, expected content identity and conditional-write basis. After a lost acknowledgement, recovery checks that destination against the intent even if a temporary source stage has disappeared. A matching result can be confirmed under the provider's actual guarantee; otherwise retain the uncertain/conflicting state or regenerate from a retained ancestor before an eligible retry. A mutable named copy never inherits the original's immutable-storage guarantee merely by containing the same bytes.

### 14.2. Archive manifests explain membership

A useful manifest records:

- the exact requested and resolved selection;
- observed source/issue/asset coordinates;
- each included member name, identity and origin;
- reused versus newly acquired material;
- unavailable, failed, excluded and not-attempted members;
- comparison and processing basis;
- completion policy and actual coverage;
- archive representation settings;
- related effect references.

Large detailed reports can be retained separately and addressed by digest. The journal records references to them. The manifest does not include its own digest recursively; the outer receipt identifies the completed manifest or archive.

### 14.3. Conditional maintenance uses a pinned plan

A maintenance plan identifies source scope, exact expected source bytes, destination preconditions, ordered dependencies, prerequisite receipts and per-action outcomes. It can include copy, move and delete where supported.

The archive prerequisite must match the actual selected identities. A successful archive created for another selection cannot authorize deletion. Changed inputs, destination conflicts and unknown effects stop only the affected dependent actions.

A partial maintenance failure leaves a valid completed archive valid. Recovery reconciles applied, pending and uncertain actions individually. Blanket directory deletion or blind replay of all actions would violate the intended contract.

Copy, move and delete intents must retain their expected source/destination states and prerequisite receipt identities independently of transient stages. Recovery uses those persisted intents and competent provider evidence. Source absence alone cannot prove that the intended deletion or move occurred; insufficient evidence remains unresolved.

## 15. Generality should be demonstrated across existing domains

| Code | Existing domain situation | General contract exercised |
| --- | --- | --- |
| X01 | CBR rolling workbook with monthly rows | Publication topology separate from observation frequency. |
| X02 | CBR dated form archives | Calendar membership, physical members and semantic model readiness separated. |
| X03 | FNS date-specific read-only POST | Request identity includes method and form/body, rather than URL alone. |
| X04 | Minfin attachment rename | Logical publication identity survives filename and locator changes. |
| X05 | Frank RG delivered directory | Inventory evidence, ambiguity, stable local references and conditional maintenance. |
| X06 | Rosstat mixed-frequency workbook | Shared physical material with a precise monthly observation/product subset. |

These are acceptance examples for common mechanisms. They do not add new FNS/Minfin analytical features to the present work. Their existing source methods remain the owners of publication-specific facts. [I13]

A useful extension test is straightforward: adding another compatible publication changes domain declarations or a narrow method, while common selection, work assessment, file handling and effect semantics remain unchanged.

## 16. Deliver coherent slices in dependency order

| Code | Slice | Main outcome | Dependency |
| --- | --- | --- | --- |
| F01 | Explicit selections and scoped outcomes | Caller-owned source/issue/observation selection with truthful membership and no-work semantics. | Existing catalog and contracts. |
| F02 | Continuous bounded byte path | Sealed staging, reference inspection, archive member handling and bounded verification. | Existing ownership, storage and effect mechanisms. |
| F03 | Qualified journal facts and work assessment | Efficient repeated checks with persistent retained-state lookup and honest recovery. | F01 and stable retained-reference facts. |
| F04 | Archive and physical-table export | General selected archive publication and source-faithful DBF CSV with evidence. | F01–F02. |
| F05 | Histories and analytical products | Explicit revisions, portable validation, bank/region selection and declared presentation. | F01 and existing domain methods. |
| F06 | External notebook adaptation | Thin caller configuration, composed operations and user-facing outputs. | The relevant earlier slices proven for each workload. |
| F07 | Host recurrence qualification | Restart, repeated checks, state retention and destination concurrency under a real host profile. | F03 and the host's persistent providers. |

F01 and the design of F02/F03 can progress together. A narrowly chosen fixed-table collection can demonstrate selection, exact retention, conditional checks and restart. Rosstat can independently demonstrate offline semantic processing and product projection. DBF and large Frank RG archives exercise the strongest streaming requirements.

Do not delay every notebook until all possible background-host features exist. Conversely, do not advertise 24/7 restart-safe incremental behavior after testing only an in-memory Colab run.

## 17. Acceptance situations define completion

| Code | Situation | Required observable result |
| --- | --- | --- |
| A01 | Caller requests individual rolling CBR workbooks | Exact resolved membership; dated issue collections excluded by the caller's predicate. |
| A02 | Caller changes membership or a new catalog entry appears | A new explicit selection; an active pass remains frozen. |
| A03 | Unsupported selector field or unknown ID | Actionable rejection, without silent unrestricted acquisition. |
| A04 | Stable URL is observed as A → B → A | Three observations, two content changes and two reusable content identities. |
| A05 | Listing unchanged but one asset changed | No false asset-byte unchanged conclusion. |
| A06 | HTTP validation succeeds but required retained body is missing | Reacquisition or explicit unsatisfied requirement. |
| A07 | Bytes unchanged but extraction rules change | Retained original reused; semantic processing refreshed. |
| A08 | All selected obligations already satisfied | Successful no-work report with its evidence basis. |
| A09 | Required historical publication absent | Missing membership remains visible; no complete-history claim. |
| A10 | One issue has conflicting candidates among many dates | Ambiguity detected for that coordinate. |
| A11 | Select three banks or monthly rows only | Complete requested subset with qualified parent coverage. |
| A12 | Large original passes receive → package → verify → reconcile | Bounded memory throughout, including readback. |
| A13 | Producer result closes while an admitted consumer reads staged bytes | Consumer remains valid; final release removes the stage. |
| A14 | Crash after destination commit but before acknowledgement | Reconciliation establishes the actual effect before repetition. |
| A15 | Journal projection lags, gaps or loses a required checkpoint | Explicit incomplete state, not a fabricated reuse decision. |
| A16 | DBF blank/zero/leading zeros/high precision/deleted row | Declared token and sidecar preservation without coercion. |
| A17 | Unsupported DBF dialect or missing memo companion | Qualified unsupported result before misleading CSV publication. |
| A18 | Source changes during archive copying | No confirmed package containing unproved mixed bytes. |
| A19 | RAR provider unavailable or incompatible | Preflight/environment diagnosis distinct from source corruption. |
| A20 | Unknown numeric form code exists in official listing | Physical acquisition/export possible without false semantic-model support. |
| A21 | Industry APK requested with publisher total | Full APK operands and distinct source-total route retained. |
| A22 | Industry history is restored and extended | Validation remains usable without parser-native objects. |
| A23 | Form102 and bank/group subjects | Correct interval, namespace, ordering and missingness. |
| A24 | Rosstat index 105.3 requested | 105.3 preserved unless a growth conversion is explicitly selected. |
| A25 | Same product delivered to another destination | New confirmed delivery effect, no unnecessary recalculation. |
| A26 | Archive succeeds and maintenance partly fails | Archive remains valid; exact unresolved actions retained. |
| A27 | Source-state evidence survives restart but raw source was pruned | Availability and processing promises remain accurately qualified. |
| A28 | Slow older pass finishes after a newer pass | Older valid result retained without automatic current-pointer regression. |
| A29 | Large local delivered file enters archive processing | Bounded staged read with expected-state/identity verification; no forced full-buffer entrance. |
| A30 | A map fills staging while its final consumer waits | Admitted aggregate capacity, incremental release or qualified failure; no dependency deadlock. |
| A31 | Named-copy acknowledgement is lost and its stage disappears | Persisted typed intent permits qualified destination reconciliation without restoring a stage token. |
| A32 | DBF encoding override or CSV dialect differs | Exact scoped codec, strict decoding, quoting and LF policy are applied and recorded. |
| A33 | CSV commits but required preservation evidence fails | Partial logical export with independently recoverable receipts. |
| A34 | Same evidence is assessed at the same supplied evaluation time | Repeatable decision; freshness/retry assessment has no hidden clock input. |
| A35 | Lookup has advanced beyond the requested minimum horizon | Actual covered horizon reported; historical as-of semantics are not implied. |
| A36 | Fixed-workbook checking already returned the candidate | Downstream work reuses it within the observation scope; an index response remains distinct from an asset response. |

The criteria require both deterministic failure fixtures and representative publisher files. Synthetic tests can prove byte limits, identity, ownership and crash behavior. They cannot establish every historical form dialect, region transition or publication layout.

## 18. Boundaries and remaining evidence

### 18.1. Settled recommendations

The research recommends caller-owned membership, standard finite actions, one qualified event/effect path, staged completed bytes for large transformations, explicit processing need, scoped coverage and domain-owned scientific rules.

These choices address the recurring patterns across all seven tasks. They avoid assigning the table list, background schedule or notebook UI to low-level library actions.

### 18.2. Evidence still required during implementation

The following matters remain verification obligations:

- real DBF dialect/type combinations required by the selected archives;
- the historical layout and geography ranges needed for industry and escrow products;
- CBR form102 measurement contexts over the selected historical periods;
- the actual validator behavior of each selected publisher endpoint;
- large-file memory/disk behavior under chosen providers;
- restart and locking behavior on the host platforms that claim it;
- the intended product-layout settings for the adapted notebooks.

These are bounded questions. They should result in explicit applicability and evidence records, rather than a blanket claim that every source or every history is supported.

The research itself changes no product code. The proposed implementation work is complete only when the corresponding behavioral acceptance situations pass and the external scripts can express their requests through the common contracts.

## 19. Supporting references

Implementation references below identify specific evidence for the adjacent claims. All code anchors refer to Stratbox `55306c27b402895a4608a37d6210fa3a7d0ddbc6`; proposed filenames and APIs elsewhere are marked as proposals. Unless prefixed with `src/stratbox/` or `examples/`, implementation paths below are relative to `src/stratbox/`.

- **[I01] Publication topology and catalog selection:** `src/stratbox/domains/cbr/common/contracts.py::Publication`, `domains/cbr/series/`, `domains/cbr/domain.py` and `sdk/client.py::SourceAPI` establish the declared CBR classifications and the present limited catalog-filtering interface.
- **[I02] Comparison scope:** `domains/cbr/methods/actions/publications.py::assess` and `workbook_comparison.py` distinguish listing, bytes and table evidence; `capabilities/preparation/recipes/source_check.py` supplies the present whole-listing comparison route.
- **[I03] Durable facts and their limits:** `core/observability/journal/stream.py`, `shared/data/journal.py`, `core/execution/service.py::_fact/_settle/_register_value` and `core/execution/effect_state.py` establish bounded journal/cursor behavior, current event payloads and persistent effect authority.
- **[I04] Finite composition:** `capabilities/model/graph.py::MapCall`, `capabilities/preparation/compilation.py` and `core/execution/service.py` establish current bounded maps, fixed prepared targets and multicall execution.
- **[I05] Streaming boundary:** `core/commands/materials.py::material_receive`, `core/commands/archives.py`, `core/formats/archives/store.py::zip_to_store`, `core/commands/artifacts.py` and `core/commands/_storage.py::_verify_member` establish streaming acquisition and the remaining buffered downstream boundaries.
- **[I06] Selected-scope qualification:** `shared/data/values.py::select_dataset`, `core/commands/materials.py::material_select` and `domains/rosstat/methods/products.py::monthly` show differing current assessment treatment of intentional subsets.
- **[I07] Reviewed form semantics:** `domains/cbr/series/reporting_forms.py`, `domains/cbr/methods/actions/forms.py`, `domains/cbr/calculations/reporting_forms/methods.py` and `shared/reference/banks/registry.py` establish form applicability, measurement and subject-reference responsibilities.
- **[I08] Industry and escrow products:** `domains/cbr/calculations/industry/actions.py`, `domains/cbr/products/industry.py` and `domains/cbr/products/actions.py` establish APK input/output behavior and existing history-product settings.
- **[I09] Delivered-file maintenance:** `domains/frank_rg/methods/publications.py` and `core/commands/maintenance.py` establish recognition/selection and current conditional move/delete behavior.
- **[I10] Rosstat interpretation and product:** `domains/rosstat/methods/kep2.py`, `domains/rosstat/methods/products.py` and `examples/rosstat_kep2_offline.py` establish the reviewed route, source-index preservation and offline entrances.
- **[I11] DBF preservation:** `core/formats/dbf_lossless.py`, `core/commands/decoding.py::dbf_decode` and `shared/data/values.py::DbfEvidence` establish the strict dialect scope and metadata/resource seams.
- **[I12] History composition:** `core/commands/observations.py::observations_merge` and `domains/cbr/methods/actions/industries.py::validate` establish strict merging and the current parser-native validation dependency.
- **[I13] Cross-domain identity:** `domains/fns/methods/publications.py` and `domains/minfin/methods/publications.py` establish date-specific POST preparation and attachment/document identity.

### Primary external protocol evidence

- **[EHTTP01]** [RFC 9110, HTTP Semantics, sections 13.1 and 15.4.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4.5) supports the limited claim that conditional retrieval and a bodyless 304 concern reuse of a selected representation; it does not establish Strategy Box processing completion.
- **[EHTTP02]** [RFC 9111, HTTP Caching, sections 4.1 and 4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4) supports representation-specific validation and matching retained responses; the source-state and processing design in this research is a proposed application of those constraints.
