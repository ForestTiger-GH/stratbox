# Selective processing, retained results and restart

Stratbox exposes source discovery, exact selection, finite processing and retained-state assessment through its ordinary command and operation path. An external script chooses the source IDs, dates, bank or group membership, requested products, destinations and observation cadence. Domain declarations describe intrinsic publisher facts and competent interpretation rules.

The runnable example [selective_originals.py](../../examples/selective_originals.py) performs one finite pass over explicitly selected rolling workbooks. It retains originals, uses qualified conditional HTTP evidence after restart, reuses an unchanged retained ZIP and verifies delivery to the requested local filename. It contains no curated source list.

For reporting-form files, [selective_form_exports.py](../../examples/selective_form_exports.py) observes the CBR form feed, resolves caller-supplied `--form` and `--issue` values with ordered `--format` preferences, receives only the selected assets and exports their selected DBF members. Every DBF contributes a CSV and a full preservation-evidence JSON to the retained ZIP and requested named delivery. Its explicit preservation policy includes deleted records and strict caller-selected encoding; unknown forms need no invented semantic parser. `--workspace` owns durable materials, journal and effect state, while `--output` names a path within its material store. Existing different output bytes require explicit `--replace` with the observed destination precondition.

## Discover declarations, then freeze intent

`box.sources.page()` and `box.sources.list()` provide bounded catalog discovery. Their records describe declared sources; they do not observe the publisher. `box.sources.descriptor(source_id)` returns the neutral `PublicationDescriptor`: publisher, target kind, issue model, delivery mode, artifact category, formats, families and available command stages. Feed and series targets have distinct catalog IDs.

Use an explicit `SourceQuery` to freeze an external workload:

```python
from stratbox.sdk import StrategyBox
from stratbox.shared.data.selection import SourceQuery

with StrategyBox() as box:
    selected = box.sources.select(SourceQuery(
        includes=tuple(source_ids_from_the_application),
        order=tuple(source_ids_from_the_application),
    ))
```

The returned `SourceSelection` records exact ordered membership, the query and the catalog declaration identity used to resolve it. Unknown include, exclude and order IDs fail explicitly. Predicate mode accepts neutral declared facets, such as `issue_model`, `delivery_mode`, `artifact_category` and `formats`; the caller should retain the resolved membership when a reproducible pass matters. Adding a source to a later catalog does not silently add it to an already resolved selection.

Concrete table lists remain external. A command or operation has no preset meaning of “the tables we normally collect.” A command that understands a CBR publication feed likewise has no implicit selected form numbers.

### Select actual publications

Publisher observation produces `PublicationListing`; `command.issue.select` applies an `IssueQuery` and returns `AssetSelection` plus `SelectionReport`. The common contract supports observed membership, exact issues, inclusive date ranges, latest observed issues, explicit expected calendars and rolling publications. Source IDs, asset IDs, exact locators and ordered format preferences can further narrow membership.

An issue coordinate and an asset coordinate have different roles. A monthly issue can contain several assets. A rolling source can keep one logical asset while its bytes change. Format preference chooses one representation where formats differ; two different candidates at the same source, issue, asset and format remain ambiguous unless the caller supplies a resolving locator or a competent revision rule.

`date_axis` identifies the intended date. Reporting date, measurement date, publication date and the publisher's intrinsic `issue_order` must not be substituted for each other. Latest selection is per source. It carries `latest_observed_only`; it does not assert that the publisher's entire historical inventory has been observed.

The report preserves requested, observed, selected, missing, ambiguous and excluded membership and the parent discovery assessment. Exact expected issues are checked per selected source and, when specified, per asset. A date observed for one source cannot conceal the same date missing from another selected source. Missing calendar issues remain missing; they are not synthesized as observed downloads.

## Complete for the requested scope

Selected completion and whole-source coverage are separate statements. An exact observed asset can satisfy the caller's selection while the parent listing remains partial. `coverage_intent="complete_inventory"` additionally requires complete parent inventory evidence. An incomplete empty listing does not prove that nothing is available. A deliberately empty exact selection is an explicit no-work result.

For observations, `ObservationQuery` carries filters, exact periods, date bounds, interval interpretation, subjects, metrics, ordering, limits and expected member keys. `subjects=None` preserves the existing subject scope; `subjects=()` selects no subjects. `SubjectChoice(namespace, subject_id, label, reference_identity)` preserves caller ordering and keeps a bank and a banking group with the same numeric code distinct.

`command.observations.select` and dataset-store queries use the same projection helper and `SelectedScopeCoverage`. A subset of a scientifically complete parent can be complete for that subset. Scientific gaps in the parent remain visible. Reading a retained dataset with no query, an empty mapping or a default `ObservationQuery()` restores its exact retained identity; it does not add a synthetic projection layer.

## Finite commands and operations

All entries below use `prepare`, `invoke`, `submit` and the normal execution service. Direct command calls, operation graphs and later application composition share their contracts.

| Purpose | Public call and essential inputs | Result and completion boundary |
|---|---|---|
| Observe a publication source | `operation.source.check`, target plus optional locator, query and baseline | Observed listing, selection/report and source assessment. For a declared direct asset, the acquired material is available for subsequent work without another GET. |
| Receive and retain an original | `operation.material.receive`, target/locator/query, destination and optional `RetainedRepresentation` | Raw immutable reference, admitted material, inspection, acquisition evidence, assessment and confirmed retention receipt. Physical retention and source admission have separate outputs. |
| Inspect/select an archive | `command.archive.inspect`; `command.archive.unpack` with optional `ArchiveMemberSelection` | Inventory, exact selected members and qualified coverage; selected extraction retains evidence about the inspected parent. |
| Build and retain a ZIP | `operation.archive.publish`, members and destination | Retained reference, manifest, assessment and receipt. Optional named destination adds a required delivery receipt. Member names and compression are caller parameters. |
| Preserve DBF as CSV | `operation.dbf.export_csv`, material, explicit `DBFPreservationPolicy` and destination | CSV reference, preservation-evidence reference, physical assessment, summary and both required receipts. A retained CSV alone does not complete this operation. |
| Interpret a selected source | `operation.series.extract_any`, target and the appropriate admitted entrance | Descriptor-based physical dispatch followed by extraction, interpretation and validation. Existing physical or table evidence can be a late entrance where the operation declares it. |
| Resolve publication vintages | `command.observations.resolve_revisions`, datasets and `RevisionPolicy` | Explicit selected values, decisions and retained alternatives; unresolved conflicts fail. |
| Assemble a requested history | `operation.observations.history`, datasets, revision policy and optional observation query | Revision resolution, merge, optional projection and validation; per-issue membership and missing expected issues remain explicit. |
| Retain portable observations | `operation.dataset.retain` or `command.dataset.ingest` | Portable encoded reference or dataset snapshot, with confirmed storage authority. Restoration uses the appropriate codec or dataset query. |
| Publish a product | `operation.product.publish` with its declared dataset/view/product/reference entrance | Rendering and retention can be skipped when an appropriate later entrance already exists; named delivery remains a separate required obligation when requested. |
| Read retained processing evidence | `command.source.state.read`, keys, journal stream and optional minimum horizon | A bounded typed state snapshot and its projection checkpoint. This call observes mutable provider state. |
| Decide necessary next work | `command.processing.assess`, goal, state, explicit evaluation time and optional candidate/basis/policy | Pure finite decisions such as reuse, observe, verify, acquire, interpret, render, retain or reconcile. It does not execute those decisions. |

### Readable bytes and lifetime

Physical commands accept the supported readable carriers: buffered `Material`, complete session-owned `StagedMaterialRef`, immutable retained references and identified wrappers. Format helpers open streams or seekable readers through the execution context. A staged result owns a completed immutable temporary object; it is not a promise that a writer may still be changing it.

Maps and collections return keyed `MemberOutcome` records in the original selected order. A failed required member preserves the outcomes of all settled selected members, including later successful members and their available retained stages. `eligible_subset` is an explicit map completion policy; it preserves excluded failures in the report. Uncertain external effects remain uncertain even when another member succeeds. Cancellation settles active members and marks known unstarted members as cancelled without expanding more work.

Keep producing `RunResult` objects open while dependent submissions are being admitted. The runtime pins declared staged inputs for admitted work, then releases their ownership when dependants and results finish. Close results deterministically with `with` or `close()`. Staged tokens are not portable storage references: portable serialization rejects them, and restart requires an actual retained reference. Immutable content receipts and named-delivery receipts describe different storage obligations.

The service controls live staged bytes, objects and readers. Per-run budgets separately count cumulative work such as transferred, decoded, temporary and output bytes. Streaming does not imply that every decoder has constant memory: a particular physical format may still need bounded materialization. The caller and command declare the corresponding limits.

### Conditional HTTP is qualified evidence

`RetainedRepresentation` binds immutable body identity to a request representation, validators, `Vary` context and accepted acquisition evidence. The representation key includes the actual request representation and access context while omitting conditional retry controls. New credentials, representation headers, method or body can invalidate a prior conditional basis.

A usable 304 requires a compatible retained body, confirmed physical retention, current availability and authoritative acquisition evidence. A constructed `FetchEvidence` attached to a storage-only commit grants no transport authority. A response without a usable retained body cannot become a successful zero-byte material; the bounded acquisition path can retry without conditions once. If 304 omits validators or `Vary`, the compatible retained evidence supplies them.

Current validators and original retention receipts have independent lifetimes. A later observation may return the same bytes with a new ETag. The immutable receipt keeps its original physical effect identity; the new accepted acquisition evidence records the fresh validator. The source-state projection retains both relations. A raw acquisition observation may have no retained reference; a caller can pair its exact material identity with a qualified current retained output.

## Source novelty and requested completion

An unchanged observed body says nothing by itself about whether a requested Excel report, CSV sidecar or named file exists. Source state records observed revisions separately from accepted processing outputs. Physical raw acquisition is distinct from inspection and admitted original material. Scientific stages additionally require their assessments and applicable rules.

`ProcessingGoal` contains a logical source key and explicit requirements. Each requirement can specify a stage, current basis identity, destination identity, output port, persistence and partial-data policy. Output ports matter for operations with two required results: `csv` and `evidence` are separate representation obligations. A summary or a returned effective request is not an independently completed processing stage.

Compute the desired work basis from the actual current inputs and bound command:

```python
from stratbox.shared.data.processing import ProcessingGoal, ProcessingRequirement
from stratbox.shared.data.values import fingerprint

desired = box.processing_basis(
    "command.observations.validate",
    inputs={"dataset": dataset},
    target=selected_series_target,
)
goal = ProcessingGoal(source_key, (
    ProcessingRequirement("observations", fingerprint(desired), output_name="dataset"),
))
```

The helper prepares a direct command without executing it. Its three-part basis contains named input content/context, bound method/settings/parameters and implementation identity. Known byte and scientific inputs preserve bytes, rows, semantics, source/issue/asset coordinates, qualifications, filenames and member names while excluding polling timestamps, evidence-reference labels, temporary ownership and native caches. Unknown values retain their full canonical identity, which can cause conservative extra work. Explicit query fields, product labels and reference inputs continue to affect the basis. An operation's intermediate inputs are unresolved until its finite command stages have actual values, so this helper requires a direct command.

The basis is a comparison key. It does not establish provenance, validate scientific meaning or prove that a destination is still present. `ProcessingPolicy` supplies explicit freshness thresholds, reference-availability observations and confirmed or uncertain effect IDs. `evaluation_time` is mandatory and timezone-aware. Decisions do not consult a hidden clock.

`processing.assess` asks for verification when a retained object has no current availability evidence. It asks for reconciliation before dependent work when a required effect is uncertain. Missing processing basis never implies that current interpretation rules equal old rules. Retained semantic results can be restored through `command.value.decode` or `command.dataset.query`; the returned decision states the restoration route.

## Durable state for an external background host

One application session owns one `StrategyBox` and one shared resource coordinator. The application submits a bounded number of selected targets; operations can use their existing bounded maps within a target. The core has no background scheduler, cadence configuration, endless polling loop or automatic selection preset.

| Provider | Purpose | Persistence and authority |
|---|---|---|
| `FileJournal` | Durable ordered execution facts and consumer horizons | Global pages, stream identity, acknowledged consumer cursors and explicit archive/prune lifecycle. |
| `FileEffectState` | Existing authority for storage and other external effects | Durable claims and confirmed/unknown/rejected receipts, including archive-transparent receipt lookup. |
| `SQLiteSourceState` | Indexed derivative of accepted source and processing facts | Transactional records and projection cursor, current/history views, bounded reads and explicit checkpoint backup. It owns no effects. |
| `LocalFileStore` or another qualified provider | Original bytes, portable representations and named deliverables | Immutable content and verified mutable postconditions according to provider contracts. |

The example constructs this profile explicitly. Reopening the same directories restores the state; keeping only the SQLite projection while discarding effect authority or retained bodies does not restore completed effects.

`box.advance_source_state(max_pages=..., page_limit=...)` consumes a bounded number of **unfiltered global** journal pages. For each page, the index commits records and cursor in one provider transaction, then acknowledges that exact page to the journal. A crash between commit and acknowledgement causes idempotent replay. A filtered page cannot establish a global replay horizon. Journal pruning must respect registered consumer acknowledgements; a new projection cannot reconstruct a pruned prefix without an appropriate retained checkpoint.

State reads carry stream ID, applied sequence, retained horizon and the caller's minimum required sequence. `view="current"` folds repeated equivalent work and keeps the latest observation by observation time; a slow earlier request completing later does not replace a newer observed revision. `view="history"` retains observed transitions, including A → B → A. Pagination is explicit: a truncated page and a continuation page alone cannot claim a complete snapshot. Projection capacity fails before committing the new cursor, so missing state is never silently treated as no work.

The host owns storage maintenance and recovery policy. It can export a SQLite checkpoint, archive completed effect receipts and advance/prune journal segments under their existing contracts. Unknown effects remain authoritative until resolved. The state provider's compaction removes eligible old ephemeral output diagnostics; it does not silently delete retained publication history. Configured capacity limits and incomplete-page results remain observable operational conditions.

### Explicit file maintenance

`command.material.maintenance_plan` freezes the requested `copy`, `move` and `delete` actions with their exact source `ByteIdentity`, declared scope, retained prerequisites and stable `action_id`. Each action can name earlier action IDs in `depends_on`. Omitted dependencies mean an independent action; list order determines execution order without creating a hidden dependency. Duplicate IDs, forward references and paths outside the scope reject the whole plan before any mutation. A move stays within one directory. A copy can deliver to another directory inside the scope and preserves its source.

A copy freezes `policy="create_only"` or `policy="replace_if_matches"` with an exact `expected_destination`. Its bounded writer is the same named-delivery mechanism used by `command.artifact.materialize`; the provider observes and persists a destination revision before conditional replacement. Optional `retained_ancestor` binds a confirmed immutable copy for later recovery. Required archive receipts are verified against their exact ordered members and bytes before an affected action can run.

`command.material.maintenance_apply` makes one finite pass through the plan. A failed or uncertain action blocks its explicit dependants; independent actions continue. The `outcomes` tuple reports every action's ID, ordinal, dependencies, result, findings, blocking IDs and associated effect ID/status. The `receipts` tuple retains every attempted effect, including rejection or uncertainty. Mixed confirmed and failed actions produce `partial`; an unresolved external effect keeps the overall result `unknown`. Failure and cancellation preserve the explicitly declared report outputs. For failed, unknown or cancelled commands, those diagnostic outputs use `output.reported` and do not establish accepted scientific or processing authority; they never promote the failed task or unblock its dependants.

Reapplying the exact plan reuses confirmed effect identities, verifies current postconditions and observes uncertain effects through their persisted typed intent. `command.artifact.reconcile` can also inspect a single effect independently. A missing move/delete source alone cannot prove that the requested transition occurred. A missing copy destination can be recreated only through an explicit permitted recovery with a verified retained ancestor; a conflicting destination remains protected. The [maintenance tests](../../tests/core_target/test_maintenance.py) cover frozen copy preconditions, independent progress, blocked dependants and cold reconciliation without replaying confirmed copies.

## Portable history and revision evidence

The reference period measured by an observation, its reporting issue, its publication revision and the installation's observation order are independent coordinates. `RevisionPolicy` declares the observation grain, equal-value treatment, conflict rule, ordering basis, expected scope and optional as-of boundary. An issue-order policy uses `ordered_issues`. Revisions inside one issue require explicit `PublicationRevision` bindings and `ordered_revisions`; local observation order must be identified as local evidence rather than publisher chronology. Unequal values at the same admitted revision remain ambiguous.

```python
from stratbox.shared.data.history import (
    PublicationRevision, RevisionPolicy, bind_publication_revision,
)

initial = PublicationRevision("example.series", "2026-01", "initial")
correction = PublicationRevision("example.series", "2026-01", "correction")
parts = (
    bind_publication_revision(initial_dataset, initial),
    bind_publication_revision(corrected_dataset, correction),
)
policy = RevisionPolicy(
    conflicts="latest",
    ordered_revisions=(initial.identity, correction.identity),
    ordering_basis="publisher.correction_notices",
    as_of=initial.identity,
)
```

The binding helper consumes an original dataset, preserves its content and attaches the declared revision coordinate. It supplies no publisher-order or validation authority by itself. An asset-specific revision must agree with the dataset's source-use asset. A qualified `occurrence_id` can preserve an observed A → B → A sequence while its two A occurrences share exact row payloads. Repeated checks of unchanged A do not automatically establish another publisher revision.

`SourceDataset.rows` is the selected view. Its versioned `HistoryMembership` separately retains original members, exact `HistoryRow` payloads, `HistoryCandidate` bindings, an active coordinate scope, `RevisionDecision` candidate IDs, scoped expectations and validation references. Equal economic values can coalesce in the view while every exact source row remains bound to its real member. Unknown row fields remain part of the equality comparison; `provenance_fields` declares the recognized provenance projection, and economic value/grain fields cannot be excluded through it.

Resolution preserves every retained candidate in the active scope, including candidates beyond an earlier cutoff. Latest → earlier → latest therefore restores the same supported values and evidence. Strict merge requires disjoint visible coordinates, including when overlapping values are equal. It unions their evidence and preserves the selected decisions; explicit revision resolution owns overlap. For compatible disjoint scopes and the same policy, resolving a merge gives the same values, candidate provenance and coverage as merging the separately resolved views.

Selection freezes its coordinate scope and records its parent coverage separately. A later resolution cannot reopen an excluded coordinate through an alternative row. A value filter uses literal operation order: selecting positive latest values and then resolving an earlier vintage can expose negative earlier values at those selected coordinates. Apply the filter again after resolution to ask for positivity at the earlier vintage. Selected scope records survive merge and portable replay. Optional parser-native objects are omitted from the history/selection identity basis; exact execution work keys remain independently responsible for methods that consume native objects.

`HistoryExpectation` binds expected membership to a source, issue, optional asset/revision and optional coordinate scope. Another source or asset with the same issue label cannot fulfill that expectation. `RevisionPolicy.expected_issues` is a convenience expanded across the admitted source/asset scopes; `expected_members` supplies explicit qualified expectations. A new resolution recomputes its policy-specific expectation and cutoff findings from that policy. Source qualifications and explicit validation requirements remain inherited. A partial finding caused only by an earlier cutoff does not permanently contaminate a later complete vintage. Missing active coordinates remain explicit even when no eligible candidate exists at the requested cutoff.

`ValidationCertificate` binds exact portable source content, stable semantics, source/issue scope, competent rule/method/build, material identities and row hashes. Candidate content identity excludes validation attachments, so a second competent rule can add a witness without changing the historical candidate. The verifier checks exact member-to-candidate-to-row bindings and accepted authority for the retained active evidence. Matching a coordinate alone cannot authorize another value, another member's provenance or a relabelled source. Restored history also validates that its displayed rows are exactly the representatives declared by its ledger. Aggregate comparability and purpose-specific scientific checks remain separate obligations.

`HistoryLimits` bounds members, all candidates, unique payload bytes, witness references, active coordinates and encoded ledger size. `RevisionPolicy.max_rows` additionally bounds displayed output rows. A single visible row with many revisions consumes the full candidate budget. Portable encoding and retained dataset providers apply their independent total byte limits. The initial representation is an inline normalized ledger; resolution performs no hidden storage reads.

The canonical codec and memory/file dataset stores round-trip the ledger, active scope, candidates and witness references without native parser state. History envelopes without the exact candidate schema fail with `history.unsupported_schema`. Rebuild from competent retained originals when earlier values cannot be reconstructed exactly; hashes and issue labels cannot recreate missing rows. A usable latest-only artifact never acquires unsupported vintage authority through a format change. The generic validator checks supplied portable evidence and cannot bless a caller-constructed domain certificate. Partial source checks remain visible through composition.

## Mapping the seven notebook workloads

The mapping describes implementation responsibilities and available finite entrances. It does not certify every historical file the publishers have ever released.

| External workload | Selection and finite route | Details retained by the contracts |
|---|---|---|
| ZIP of individually chosen current CBR tables | External exact `SourceSelection`; receive each declared rolling workbook; archive publish/materialize | The selected table IDs live in the script. A dated issue series is a different declared issue model. Conditional evidence, individual original receipts and archive membership remain separate. |
| Observed CBR form archives and physical DBF-to-CSV conversion | Explicit feed/form assets and issues; acquire; inspect/select archive members; DBF export | The observed regulatory archive feed is broader than the reviewed semantic form catalog. Unknown forms can be retained physically without a fabricated financial parser. CSV and full preservation evidence are both required. |
| Reviewed reporting-form tables and bank/group calculations | Exact forms/issues; domain extraction and validation; observation/subject selection; calculation and product calls | The reviewed forms have explicit domain methods. Bank/group namespaces, requested subject order, reference identity and per-member outcomes remain visible; numeric codes do not collapse across namespaces. |
| Industry/APK histories and source totals | Selected original workbooks; per-issue interpretation/validation; explicit revision history; requested products | Source-owned published totals stay distinguishable from arithmetic sums of subcategories. Portable certificates preserve source checks across native-state loss and restart. |
| Dated escrow history | Actual observed issues and preferred formats; source interpretation; revision policy and expected calendar | Date axes, revised publication values and missing expected issues remain explicit. Same workbook bytes attributed to a different issue do not automatically satisfy semantic reuse. |
| Frank RG delivered reports and file maintenance | Delivered inventory; explicit issue/order/member selection; standard interpretation/product route; explicit maintenance plan/apply | A delivered directory is the observed inventory scope. Cleanup uses observed preconditions and required retained prerequisites. Moving/deleting a path needs qualified transition evidence; absence alone is insufficient. |
| Rosstat KEP history and selected products | Observed release selection; admitted materials; appropriate physical/document route; explicit history/product scope | Publisher inventory may remain unknown while an exact selected asset is complete. Selected periods and product coverage follow the actual observations and reviewed source rules. |

FNS and Minfin use the same selection and comparison contracts where their existing declarations support them. Their domain settings remain the owner of intrinsic delivery and issue facts. A selected recognized attachment can be complete while an unrelated unclassified attachment keeps parent discovery partial. These shared contracts do not invent additional publisher series or interpretation rules.

## Verification and practical bounds

The selected behavior is exercised by [source selection tests](../../tests/capabilities_target/test_source_selection.py), [selected value tests](../../tests/core_target/test_selected_values.py), [portable history tests](../../tests/core_target/test_history_contracts.py), [projection tests](../../tests/core_target/test_source_state_projection.py), [work-basis tests](../../tests/core_target/test_processing_basis.py), [pure assessment tests](../../tests/core_target/test_processing_assessment.py) and [restart integration](../../tests/integration/standard_routes/test_selective_restart_state.py). The [collector integration fixture](../../tests/integration/standard_routes/test_selective_collector_example.py) exercises an explicit rolling source, restart, 200/304 evidence and retained archive reuse through the real SDK path using an offline HTTP provider.

The [form-export integration fixture](../../tests/integration/standard_routes/test_selective_form_exports_example.py) observes an index containing multiple forms and alternative formats, downloads only the requested representation, and verifies two DBF exports with their two required evidence sidecars, confirmed receipts and exact final ZIP membership through the real SDK. It performs no live download.

For physical streaming, run the reproducible local probe:

```sh
python scripts/probe_physical_streaming.py --size-mib 128
```

For the 5 GiB qualification, select an existing directory with enough free space for multiple simultaneous source, staging and retained copies:

```sh
python scripts/probe_physical_streaming.py --size-mib 5120 --root /path/to/existing/roomy-directory
```

The probe creates an isolated temporary child there, places its stages inside that child and removes only files it owns. The 5 GiB local run completed all five stages with the same 1 MiB maximum provider read/write chunk. This is evidence for the bounded physical path; it does not establish the locking or deployment guarantees of a different host platform.

It creates its own temporary child directory and checks staged read, ZIP packing, immutable commit, release assembly and reconciliation. The probe distinguishes bounded stream calls and retained-result memory from whole-process resident memory; it does not claim that the entire interpreter fits within the configured retained-result budget. [Physical streaming tests](../../tests/core_target/test_physical_streaming.py) cover malformed metadata, archive member selection, chunk limits and preservation sidecars. Named output recovery remains subject to the provider's actual postcondition and transition-proof guarantees.

An offline fixture establishes the specified contract and failure behavior. Current remote availability, a new historical layout, an installed host and a complete multi-year scientific dataset each require their own qualified evidence.
