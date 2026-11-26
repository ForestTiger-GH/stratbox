# Strategy Box: Operational Readiness and Coherent Completion — Functional Model

**Date:** 2026-11-27. **Status:** research findings and recommended target contracts; implementation remains separate work. **Implementation evidence:** Stratbox 0.26.0, commit `122db74ac1c3280a94580133d6e0ebfae61660dd`. **Scope:** analytical requests, accepted results, historical observations, effects, recovery, operating profiles and application boundaries.

The recommended next step is to complete the contractual backbone of Strategy Box and qualify a concrete operating scope. The existing command, operation, scenario and cascade model is an appropriate foundation. Its remaining important weaknesses concern the preservation of meaning across composition: a reported object can be mistaken for fulfilled work; a resolved history can lose its earlier evidence; a transport response can stand in for a different storage obligation; and retained results can affect later execution. Correcting these boundaries produces a more useful system than adding another execution layer or expanding the catalog before the existing promises hold.

This study defines the functional meaning of a launchable Stratbox, the common laws that the corrections should satisfy, and a dependency-based completion program. Verified counterexamples are explicitly separated from target recommendations and qualification work. The companion [architecture and implementation study](strategy_box_operational_readiness_architecture_and_implementation_2026-11-27.md) translates the same decisions into owners, candidate contracts, algorithms, cutover steps and verification gates. Neither document declares the proposed behavior implemented or the Windows application qualified for use with the examined core.

## Contents

1. Recommended target and first operating scope — what should be completed and what constitutes launch readiness.
2. Evidence that changes the development priorities — verified defects, performance evidence and unresolved qualification.
3. A request is a set of explicit obligations — selection, data, scientific meaning and requested effects.
4. Result acceptance and collection preserve the original promise — diagnostics, usable data and aggregate outcomes.
5. A history preserves candidates and resolves a view — revisions, equal values, certificates and composition laws.
6. Time, selection and comparability remain explicit — the conditions under which observations can be combined.
7. An external effect fulfills an exact obligation — destinations, acknowledgement levels and retry authority.
8. Recovery reconciles durable owners — uncertainty, projections, maintenance and sustained operation.
9. Logical demand, physical work and result ownership have separate lifetimes — sharing, deadlines and cancellation.
10. Efficiency and scalability are functional requirements — reuse, bounded work and workload envelopes.
11. Scientific readiness is scoped to the requested route — qualification and candidate launch workloads.
12. Applications consume one portable analytical model — Python, desktop, mobile and future analytical areas.
13. Worked situations connect the contracts — history updates, partial collections and interrupted publication.
14. Completion packages and launch gates — implementation order and conditions for practical use.
15. Functional acceptance situations — counterexamples that the target must handle consistently.
16. Alternatives and their consequences — why the recommended model is economical and extensible.
17. Decisions recommended now and evidence still required — concrete closure without fabricated certainty.
18. External sources — primary support for specific protocol and lifetime claims.

## 1. Recommended target and first operating scope

### 1.1. Complete one analytical engine

Stratbox should turn an explicit request into qualified, reusable results and confirmed effects through one visible graph of meaningful actions. The same contracts should apply to a direct command, a reusable operation, a scenario, a cascade and a caller-supplied prepared plan.

The library already has the appropriate responsibility structure: `capabilities` owns callable definitions and preparation; `core` owns execution and technical providers; `domains` owns scientific specialization; `shared` owns neutral values and their meaning; `sdk` exposes common discovery and invocation. The recommended work strengthens these responsibilities. It does not create a second orchestration framework, a publisher-specific runner or an application-owned interpretation engine.

| Code | Recommended decision | Practical consequence |
| --- | --- | --- |
| D01 | Make fulfillment of the requested obligation the meaning of completion. | A returned report, an accepted dataset and a confirmed save remain distinguishable. |
| D02 | Preserve exact historical candidates independently of the currently selected values. | Merging, saving and restoring a history cannot silently change an earlier vintage. |
| D03 | Admit external evidence against the exact retained intent. | Every confirmation identifies the right effect, provider, destination and promise. |
| D04 | Separate logical demand, physical execution and retained ownership. | Sharing and open results cannot distort later deadlines or cancellation. |
| D05 | Reuse sealed values and bounded metadata. | Efficiency follows valid identity and ownership rather than repeated traversal of large objects. |
| D06 | Qualify a precise operating profile. | The first usable release has a declared workload, provider set and recovery envelope. |
| D07 | Derive scientific readiness from reviewed source and method evidence. | Registration or physical decoding cannot imply an unreviewed economic model. |
| D08 | Migrate applications to the public SDK. | Desktop and future mobile surfaces preserve the same result and effect semantics. |

### 1.2. Use two distinct launch decisions

The first decision is **core readiness for a declared workload**, including its data contracts, providers, resource envelope and recovery requirements. A finite Python run can be useful before a desktop release is qualified. The second decision is **application readiness**, which additionally requires the chosen surface to prepare the same requests, preserve qualifications, handle result ownership and run against the actual packaged core.

This separation creates independent evidence requirements. It does not excuse a core defect that can return a wrong historical value or falsely confirm an effect. An advertised route must satisfy its contract in every supported entrance and composition.

For the first persistent operating profile, prefer one host, one coordinator and one journal writer, with bounded concurrent finite tasks and caller-owned persistent providers. A host can repeatedly submit finite work. Shared local processes, remote state services and mobile execution can be qualified later against the same interfaces. Concurrency inside a service and concurrency between independent services are different promises.

### 1.3. State readiness as a conjunction

For a workload `W` and environment `E`, the proposed launch rule is:

`Ready(W, E) = semantic correctness AND scientific competence AND execution integrity AND effect integrity AND recovery adequacy AND resource adequacy AND entry-surface compatibility`.

Every term is scoped. A raw-file collection requires physical preservation and destination fulfillment, while a financial calculation additionally requires reviewed economic meaning. A memory-only run has a different recovery promise from a recurring persistent host. A successful Linux exercise establishes evidence for its environment; it does not automatically qualify Windows locking or an Android runtime.

## 2. Evidence that changes the development priorities

### 2.1. Nine counterexamples reveal five common contract weaknesses

The following observations apply to the examined core commit. They are reproducible behavioral findings, rather than claims that every normal route encounters each defect. Paths in this section identify the current implementation owner of the relevant behavior.

| Code | Verified observation | Functional consequence | Current owner |
| --- | --- | --- | --- |
| R01 | Merging a resolved history with a disjoint dataset drops revision decisions and alternatives. Resolving an earlier vintage can then return the later value with a complete assessment. | Historical answers can change while still appearing complete. | `src/stratbox/core/commands/observations.py::observations_merge`; `src/stratbox/shared/data/history.py::resolve_revisions`. |
| R02 | A failed optional producer can return a diagnostic that a required collection counts as a succeeded member. | A report's availability can incorrectly fulfill selected work. | `src/stratbox/core/execution/service.py`, collection settlement. |
| R03 | A qualified HTTP 304 receive can reuse the old retained reference despite a newly requested retention destination. | Source reuse can falsely settle a different storage promise. | `src/stratbox/core/commands/acquisition_http.py::material_receive`. |
| R04 | Reconciliation can accept a notification acknowledgement naming another intent or effect kind through an unchecked alias, then retire the pending notification. | An unrelated external reply can become completion authority. | `src/stratbox/core/execution/service.py::_reconciled_confirmation`; `src/stratbox/core/commands/notifications.py`. |
| R05 | Coalescing economically equal revision rows keeps multiple member identities but only one member's exact row provenance. An earlier vintage can carry the later issue's provenance and fail certificate verification. | Numerical equality conceals loss of evidential identity. | `src/stratbox/shared/data/history.py`, equal-candidate resolution. |
| R06 | A process crash after acquiring the directory sentinel leaves subsequent conditional writes blocked. | Safe failure becomes persistent unavailability requiring intervention. | `src/stratbox/core/storage/filestore/local.py`, directory guard. |
| R07 | A completed result kept open can contribute its old unlimited deadline to a new physical execution with the same work key. | Result ownership changes the deadline of unrelated later work. | `src/stratbox/core/execution/context.py::remaining_seconds`. |
| R08 | One live service can keep a cached unknown effect after another service confirms the shared durable receipt. | Valid progress remains blocked by stale local knowledge. | `src/stratbox/core/execution/service.py::lookup_effect`. |
| R09 | A hand-constructed prepared plan can contain a cyclic nested map template that passes outer admission and remains pending. | The exposed plan entrance accepts a graph that cannot complete. | `src/stratbox/core/execution/service.py`, root validation and dynamic instantiation. |

R01, R02, R03 and R04 are immediate completion-integrity priorities: they can expose a wrong result or a false success. R05 belongs in the same history correction as R01. R06 through R09 belong in the launch program because recovery, deadlines, shared state and validated admission are part of the advertised engine, even when their demonstrated consequences are conservative blocking rather than data corruption.

### 2.2. Performance, durable growth and application integration add separate obligations

| Code | Evidence or boundary | Interpretation |
| --- | --- | --- |
| R10 | On an offline industry fixture with 14,976 observations, individual full dataset identity and value-key traversals took approximately 1.65 and 1.32 seconds. The complete suite passed, while repeated canonicalization appeared in coordinator work. | Repeated full traversals are a demonstrated cost. A quadratic complexity claim and universal timing prediction are unproved. |
| R11 | The inspected Windows application declares core 0.2.1 and uses core namespaces absent in 0.26.0. The current SDK namespace is available. | Updating the dependency alone is insufficient. Application adapters require an explicit migration and packaged integration gate. This is a boundary inspection, not a full Windows runtime audit. |
| R12 | The persistent source-state provider has capacity limits, but its current compaction preserves source observations, persistent outputs and authority records. | Finite safety bounds exist. Indefinite recurring use additionally requires a retention, archival and recovery policy for every growing state class. |

The full core test run produced 1,360 passes and seven skips on the evaluated environment. A separate 128 MiB stream exercise kept chunks bounded through its tested read, package, retention and reconciliation route. These results establish useful foundations. The targeted counterexamples demonstrate why a passing suite and one bounded-byte route cannot substitute for the missing cross-contract cases, broader scientific evidence or platform qualification.

### 2.3. Preserve the foundation already present

The examined implementation has bounded admission, explicit service lifecycle, result-owned staged values, persistent effect claims, contiguous journal-page validation, transactional notification preparation and source-state projection, cold receipt evidence and conditional maintenance. These mechanisms should be retained and completed at their existing boundaries.

The most economical correction is therefore a small number of strengthened shared laws with broad acceptance coverage. Nine independent special cases would leave their underlying ambiguities available to the next command or application.

## 3. A request is a set of explicit obligations

### 3.1. Freeze what the caller actually requests

A request identifies a subject, exact selected membership, supplied entrances, desired outputs, acceptance policy and external effects. Its preparation resolves the effective method, settings, reference basis and required input closure. Later catalog additions or a newly observed issue do not silently expand an admitted occurrence.

| Code | Obligation dimension | Example |
| --- | --- | --- |
| OB01 | Selected membership | These sources, publication assets, banks, territories, periods and measures. |
| OB02 | Data representation | Original bytes, a physical CSV with preservation evidence, semantic observations or a rendered workbook. |
| OB03 | Scientific acceptance | Reviewed units, reporting perimeter, temporal meaning, layout and formula basis. |
| OB04 | Historical intent | Latest admitted vintage, a specified publication cutoff or an exact resolved history. |
| OB05 | Coverage | Every required selected member, a stated eligible subset or a complete publisher inventory. |
| OB06 | Persistence and delivery | Immutable retention, a requested named destination, an archive or a channel handoff. |
| OB07 | Operational envelope | Deadline, resource limits, allowed retry, available provider guarantees and recovery scope. |

These dimensions belong to existing request, port, selection, plan and effect contracts. They do not require a new universal workflow object containing every application concern.

### 3.2. Completion follows dependency closure

An obligation is satisfied only by accepted evidence bound to that obligation. Required effects and checks remain in preparation closure even when their outputs are not displayed. Supplying a valid later-stage entrance removes unnecessary earlier work, while preserving the remaining checks and effects.

For example, a supplied accepted dataset can eliminate download and interpretation when the requested operation supports that entrance. Requesting delivery to a new destination still creates a new obligation. Requesting a derived metric still requires its complete operand closure, including periods or components beyond the final display selection.

### 3.3. No-work is a qualified result

An unchanged source, an empty explicit selection and a fully satisfied goal are three different reasons for doing no additional work. The decision should state which reason applies and the exact evidence horizon used.

“The publisher has no relevant publication” requires adequate inventory evidence. “The explicitly selected membership is empty” follows from the caller's frozen selection. “Every requested output already exists” additionally requires matching scientific basis, acceptance and present access to the required retained values or effects. A stale index or an absent record does not prove the last statement.

## 4. Result acceptance and collection preserve the original promise

### 4.1. Keep the independent facts

| Code | Fact | Meaning |
| --- | --- | --- |
| RF01 | Execution outcomes | Separately recorded outcomes of the logical task and its physical attempt; one consumer can expire while shared work succeeds for another. |
| RF02 | Output availability | Which named objects or reports were produced and remain readable. |
| RF03 | Output eligibility | Whether a particular output satisfies a particular consuming port. |
| RF04 | Scientific qualification | What the value establishes, including limitations and findings. |
| RF05 | Selected-scope coverage | Which requested members or coordinates are fulfilled or missing. |
| RF06 | Effect certainty | Which requested external actions have competent confirmations. |
| RF07 | Aggregate fulfillment | Whether the enclosing purpose's declared obligations are satisfied. |

The engine may expose a convenient summary status, but it must derive that status from these facts. The summary cannot replace them in dependency scheduling, state projection or application display.

### 4.2. A diagnostic remains useful without becoming successful data

A failed interpretation can produce an explanatory report and even retain an intermediate original. Those objects can be valid outputs for a diagnostic consumer. They do not automatically satisfy an observations port or the selected source's successful processing obligation.

An explicitly requested validation report can itself complete successfully while describing invalid data. Its contract promises a report, and the report's conclusion remains invalid. This differs from returning a diagnostic from a failed producer and counting the producer as a successful member of a required analytical collection.

The proposed rule is: **each consumption evaluates the original logical member or scope obligation, the accepted/reported output record, its qualifications and the consumer's own requirements**. A successful forwarding task cannot relabel a failed member's diagnostic as fulfilled analytical work. An unrelated failed ancestor also cannot invalidate an independently accepted output. A permissive continuation setting only permits later graph work; it cannot erase an independently required collection member.

### 4.3. Collection policies must preserve membership

| Code | Policy | Completion rule | Required report |
| --- | --- | --- | --- |
| CP01 | All required members | Every required member fulfills its data and effect obligations. | Every selected member, including failed, unknown, cancelled and unstarted members. |
| CP02 | Explicit eligible subset | The accepted subset satisfies the declared eligibility and minimum coverage rule. | Selected membership, accepted subset, exclusions and unresolved obligations. |
| CP03 | Diagnostic aggregation | The requested report is assembled from available evidence. | Original member outcomes; no promotion to successful source processing. |
| CP04 | Explicit empty selection | The caller's allowed empty goal is fulfilled. | Empty scope and the reason; no claim about an unobserved publisher inventory. |

`min_items` counts the collection's declared eligible member occurrences for the specified output contract. It does not count any object that happens to be returned. A general collection can require datasets, receipts or reports according to its purpose. An analytical collection can preserve useful retained originals from failed semantic members while reporting that the semantic goal remains incomplete.

For partial success, distinguish “the requested eligible-subset purpose completed” from “the original selection is fully covered.” Both statements may be visible at once. An unknown required effect remains unknown after successful processing of another member.

### 4.4. Acceptance remains consistent through every route

Direct calls, map members, collection assembly, scope outputs, retained-state projection and restored data must use compatible acceptance rules. A diagnostic recorded for inspection must not reappear after restart as a reusable accepted scientific stage.

A result reference carries the qualified acceptance context needed by its consumer. Copying its bytes or attaching a complete-looking assessment does not create new validation authority. This applies equally to caller-supplied certificates, cached values and values forwarded through an operation.

## 5. A history preserves candidates and resolves a view

### 5.1. Separate evidence from the chosen answer

A history needs two related structures: the admitted candidate evidence and the resolved view under a stated policy. The candidate evidence records exact source-member-to-row relations. The resolved view selects candidates for each observation coordinate. A later policy may select different candidates without reconstructing lost values from member names.

| Code | Entity | Functional meaning |
| --- | --- | --- |
| HI01 | Observation coordinate | Economic grain: measure, subject and namespace, territory/perimeter, temporal coordinate and other declared dimensions. |
| HI02 | Publication member | An admitted source, issue, asset and source-content occurrence. |
| HI03 | Exact candidate | A member's exact row and provenance at an observation coordinate. |
| HI04 | Economic payload | The numerical/status meaning used by a competent equality rule. |
| HI05 | Resolution decision | Selected candidate identities, retained alternatives and the exact policy/order basis. |
| HI06 | Resolved history view | Selected values plus coverage, qualifications and links to their candidate evidence. |
| HI07 | Validation witness | Authority for exact source rows or a declared derived scope, with its rule and basis. |

Economic equality and evidential identity are different relations. Two issues can report the same number while providing different source cells, publication dates and validation witnesses. W3C PROV-DM distinguishes entities, activities and derivations; that distinction supports retaining their separate relations. The candidate/view model proposed here is a Stratbox design choice, rather than a requirement to adopt RDF or a provenance server. [E02]

### 5.2. Two counterexamples define the necessary correction

First, suppose issue A reports January as 1 and issue B revises January to 2. Resolving latest gives 2 while retaining A's candidate. Merge this history with a disjoint February coordinate. A subsequent as-of-A request must still yield 1, or explicitly report that the necessary evidence is unavailable. Returning 2 with complete coverage is invalid.

Second, suppose both issues report January as 1. Coalescing the displayed value is permissible under the declared economic equality rule. The exact A row and the exact B row must remain separately bound to their publication members. As-of-A selects A's evidence even though the displayed number is unchanged. Replacing A's provenance with B's row breaks the scientific trace.

These examples should be resolved by one representation law: **a decision refers to retained candidates; it never substitutes a surviving row for a member whose original row is absent**.

### 5.3. History composition laws

| Code | Law | Scope and qualification |
| --- | --- | --- |
| HL01 | Candidate preservation | Merge, retain, restore and projection preserve every candidate needed for the advertised later vintage queries. |
| HL02 | Exact binding | Each candidate retains its member, coordinate, exact row identity and witness links. |
| HL03 | Equality preserves provenance | Coalescing equal economic values preserves the distinct evidence bindings. |
| HL04 | Resolution changes the view | A new resolution selects candidates; it does not rewrite earlier publications. |
| HL05 | Strict merge stays strict | Visible observation coordinates must be disjoint, including when duplicated values are equal. Explicit revision resolution owns overlap and optional equal-value coalescence. |
| HL06 | Candidate union is stable | For compatible grain and admitted identical candidate identities, union is associative, commutative and idempotent up to declared presentation ordering. Conflicting records under one identity are rejected. |
| HL07 | Coverage is scoped | Expected and missing issues retain source/asset/selection scope; another source's observation cannot fill the gap. |
| HL08 | Projection does not resurrect exclusions | Resolving a projected history later cannot recover excluded coordinates through hidden alternatives. |
| HL09 | Certificates bind exact evidence | A source certificate remains a witness for its exact admitted rows; aggregate validation has its own contract. |
| HL10 | Evidence loss is explicit | Pruned or unavailable alternatives reduce supported vintage scope; labels cannot reconstruct them. |

HL06 applies to candidate evidence, not to blindly concatenating resolved datasets or mixing incompatible resolution policies. HL08 permits retaining inaccessible audit evidence separately, provided it cannot silently re-enter the selected view. Coordinate-only filters can have commuting selection/resolution behavior under fixed policy; value-based filters, ranking and truncation generally require explicit order.

Two further equivalences make the reversible-view promise precise. With sufficient retained evidence and the same active scope, `resolve(resolve(H, P1), P2)` must agree with `resolve(H, P2)`. For compatible disjoint coordinate scopes and the same policy, resolving their merge must agree with merging their resolved views in values, candidate provenance and qualified coverage. Candidate-union idempotence does not make public strict merge accept duplicated visible coordinates.

Candidate content identity remains separate from accumulated validation evidence. Revalidation under another competent rule adds a witness; it does not create a conflicting candidate merely because certificate sets differ. Reject different immutable member/coordinate/row bindings under one identity and combine compatible witness attachments by their own identities.

### 5.4. Keep the model economical

An immutable candidate ledger can share exact row payloads by identity and keep small member-to-row bindings. Only the selected view needs to be materialized for an ordinary calculation. The initial representation should have explicit member, candidate and payload-byte limits: one visible row can still have many retained candidates. A later partitioned or artifact-backed representation requires explicit hydration before the same pure resolver runs.

The initial correction does not require a general temporal database. It requires preserving candidates in the existing history values and portable codec, validating their relations, and making merge and resolution operate on the same evidence. A future indexed store can implement the same contract when measured history volume requires it.

### 5.5. Preserve validation meaning after composition

A source validation certificate proves the rule it actually checked at its original scope. It does not automatically establish aggregate completeness, cross-issue comparability or a new formula's validity. History validation checks member bindings, selected row witnesses, policy admissibility, scientific compatibility and selected-scope coverage.

If an already retained history lacks alternatives because of an earlier representation loss, the target code should reject unsupported vintage claims or rebuild from competent retained originals. An old artifact can be promoted only when its exact bindings are proved lossless; otherwise a usable current view can retain explicitly narrowed vintage support. An old schema alone proves no loss, while absent alternatives prove no uniqueness. Certificate hashes cannot reconstruct missing rows. Copying the latest row into all older members would preserve the defect under a new schema.

## 6. Time, selection and comparability remain explicit

### 6.1. Several time axes answer different questions

| Code | Axis | Question answered |
| --- | --- | --- |
| TM01 | Measurement time | When did the measured stock exist or the flow occur? |
| TM02 | Reporting/issue coordinate | Which publisher reporting issue contains the observation? |
| TM03 | Publication/revision time or order | When, or in what competent order, did the publisher release this candidate? |
| TM04 | Local observation time | When did this installation obtain evidence of the publication? |
| TM05 | Analytical evaluation time | At which explicit time is freshness or work necessity being assessed? |
| TM06 | Execution deadline | How long may this logical demand remain active under the current process clock? |
| TM07 | Acceptance/journal order | At which ordered system fact was an observation, validation or effect accepted? |

An issue label can support a vintage cutoff only under an admitted ordering rule. A filesystem modification time cannot supply publisher revision order by itself. “Published or available from the publisher by time T” and “observed by this installation by time T” require different evidence. If only issue ordering is available, expose an issue-order vintage rather than inventing a wall-clock publication history.

Several revisions can share a nominal issue label; they need qualified revision identities. An observed A → B → A content sequence can reuse A's bytes while preserving separate admitted occurrences. Repeated polling of unchanged A does not itself establish a new publisher revision.

A current source-state projection's `minimum_applied_through` is a lower-bound freshness requirement. State applied through sequence 150 can satisfy a minimum of 100; it does not represent state as of 100. Exact historical projection queries are a separately declared capability, distinct from publication-vintage resolution.

### 6.2. Selection and scientific input closure are separate

The caller chooses desired output periods and subjects. The method determines the inputs necessary to calculate those outputs correctly. A year-on-year measure can need an earlier period outside the requested display range; an APK calculation requires its reviewed components; a coupled numerical model can require more regions than its final projection.

A history projection should preserve the exact query and its coverage, and its effect on the candidate set should be explicit. Selecting one bank cannot accidentally include a banking group with the same number. Selecting a month cannot substitute a publication date for the measured interval.

A value predicate also preserves literal operation order. Selecting coordinates whose latest value is positive and then resolving an older vintage can reveal negative older values at those same selected coordinates. Enforcing positivity at the older vintage requires selection after resolution. Complete selected-scope evidence does not create completeness of the parent publication or historical inventory.

### 6.3. Integration requires a comparability decision

Units, price basis, currencies, stock/flow meaning, population/perimeter, territorial references, category definitions and time aggregation must be compatible or explicitly transformed. These are scientific contracts supplied by domains and shared semantic values.

An unchanged numerical cell can still require recomputation when its reference mapping or method meaning changes. Conversely, a new publication time or an unchanged HTTP validator need not invalidate a calculation whose admitted semantic input basis is identical. Reuse should follow the exact dependency basis needed by the action.

## 7. An external effect fulfills an exact obligation

### 7.1. Separate content identity from effect identity

The same bytes can be retained in one content store, copied to a second store, materialized at a named path and handed to a notification channel. Those are distinct obligations even when no numerical computation or rendering changes.

| Code | Promise | Minimum relevant evidence |
| --- | --- | --- |
| EF01 | Immutable retention | Content identity, competent store scope, retained location and confirmed receipt. |
| EF02 | Named delivery | Requested destination, conflict policy/precondition, actual content and destination-qualified confirmation. |
| EF03 | Channel handoff | Exact intent, recipient/channel scope, payload identity and the channel's admitted acknowledgement level. |
| EF04 | Conditional replacement | Expected destination revision and competent evidence that the requested transition or sufficient postcondition holds. |
| EF05 | Destructive maintenance | Exact planned subject, prerequisite receipts, current preconditions and effect-specific confirmation. |

Changing a destination may reuse the source bytes and the prepared product. It must still settle the newly requested effect. A receipt for a previous destination remains evidence for that previous destination.

### 7.2. HTTP validation settles a transport question

HTTP 304 has no representation body and directs the client to use an applicable stored representation. Its semantics concern the conditional request and representation, while cache matching constrains which retained response can be reused. [E01, E03]

The functional consequence for Stratbox is precise: a qualified 304 can eliminate another transfer. It cannot prove that a newly requested local destination exists. The receive operation should reuse verified retained bytes, then evaluate the actual retention/delivery obligation through the ordinary storage path.

Representation compatibility still matters: request method/body, access context, representation headers and `Vary` context can distinguish sources of bytes. A digest or URL alone is insufficient transport authority. The underlying received bytes, their source observation and a destination receipt remain separate facts.

### 7.3. Confirmation must match the retained intent

Every acknowledgement should be admitted against the expected effect identity, kind, provider scope, request/payload basis and relevant destination or precondition. Initial execution, retry reconciliation and explicit reconciliation require the same rule.

If an adapter supplies several aliases for an identifier, every supplied alias must agree. A response containing `status=confirmed` and a different `intent_id` cannot confirm the expected notification. A storage acknowledgement cannot settle a channel handoff. Missing binding requires competent adapter evidence or an unresolved result; a status word does not establish authority.

A channel's acceptance can satisfy a handoff contract. It does not establish human reading. A current byte comparison can satisfy an ensure-content contract. It does not necessarily identify the actor that performed an earlier replacement. The effect contract determines the strength of evidence required.

### 7.4. Retry authority is independent of uncertainty

| Code | Observed situation | Allowed interpretation |
| --- | --- | --- |
| ER01 | No attempt was authorized or started. | A bounded first attempt may be admitted. |
| ER02 | Competent evidence proves rejection before mutation. | Retry under policy and current preconditions can be eligible. |
| ER03 | The external action may have occurred and acknowledgement was lost. | Preserve unknown; reconcile or use a proven idempotency/conditional-mutation guarantee. |
| ER04 | Matching sufficient confirmation exists. | Preserve and reuse its historical effect authority; a current ensure-content request separately checks present availability. |
| ER05 | Lookup returns no result without a strong absence guarantee. | Preserve uncertainty. |
| ER06 | Evidence contradicts identity or scope. | Preserve conflict and pending work; refuse confirmation. |

RFC 9110 constrains automatic retry of non-idempotent requests to cases where idempotent semantics or evidence of non-application justify it. [E01] Stratbox should apply the same discipline to provider-qualified external effects. Expiring a local claim or observing a process crash does not prove that the external action failed.

A destination can disappear after a valid confirmation. Preserve that historical receipt and admit a new repair/delivery occurrence under current preconditions when requested. Reconciliation of an unknown original attempt and recreation after later loss are distinct actions.

## 8. Recovery reconciles durable owners

### 8.1. Each fact has an authoritative owner

The execution journal records admitted execution facts. The effect ledger records intents, claims, uncertainty and competent receipts. A notification outbox records pending delivery obligations and the covered event cursor. A source-state projection indexes journal-derived observations and accepted outputs. Retained artifact providers own readable content and their storage guarantees.

These owners can recover through their explicit cross-references. A projection is useful for lookup but cannot create scientific acceptance that its input facts never established. A cached unknown receipt cannot overrule a newer competent durable confirmation. A receipt that survived a failed journal append remains effect evidence; recovery must publish a new qualified observation rather than invent an earlier journal fact.

### 8.2. Recover the smallest sufficient remaining work

An interrupted product publication may leave a valid retained dataset, a rendered product, a confirmed content-store receipt and an unknown named copy. Recovery should inspect the last obligation and reuse the earlier accepted stages. Re-running the whole pipeline wastes resources and can accidentally switch to a newer source vintage.

Every recovery decision states the pinned basis, actual available values, unresolved effects and evidence horizon. A newly observed publisher issue is recorded separately. It changes the resumed request's pinned basis only through an explicit caller decision.

### 8.3. Sustained operation needs an explicit retention contract

Finite quotas prevent uncontrolled growth. A recurring host also needs rules for what happens before those quotas are exhausted.

| Code | State class | Required long-term policy |
| --- | --- | --- |
| RT01 | Active work and temporary values | Release after physical users, graph consumers and result owners finish. |
| RT02 | Unconsumed journal facts | Preserve until every protected consumer has durably covered them. |
| RT03 | Consumed historical facts | Archive or prune according to declared replay and reconstruction requirements. |
| RT04 | Current accepted source basis | Keep enough competent evidence and retained entrances for advertised reuse. |
| RT05 | Historical candidate evidence | Declare vintage retention scope and preserve its queryable bindings. |
| RT06 | Unknown effects and pending notifications | Retain until resolved or explicitly disposed of by a competent policy. |
| RT07 | Terminal deduplication evidence | Preserve for the advertised occurrence namespace and retry horizon. |
| RT08 | Projection recovery anchors | Verify scope, watermark and dependencies before relying on them after journal pruning. |

An unlimited retry-deduplication promise over an indefinitely growing namespace requires retained identifying evidence. Bounded storage therefore needs a declared horizon, archival tier or namespace retirement rule. Silent eviction cannot preserve an unlimited guarantee.

Explicit abandonment changes the disposition of requested work. It establishes neither rejection nor successful delivery nor non-occurrence of the external effect. Identity evidence or a closed namespace marker remains while the original occurrence could otherwise be retried.

The first persistent profile should have a finite, resumable maintenance pass and a tested restore route. Its host chooses when to run maintenance. Domain methods remain independent of cadence, backup directories and disk thresholds.

Restoring an older consistent backup can still lose knowledge of external actions performed after its cut. Missing records in that restored ledger cannot prove that those actions were never attempted. Recover the authoritative tail or reconcile through adequate provider evidence; otherwise keep affected prior occurrences unresolved or closed to automatic replay.

## 9. Logical demand, physical work and result ownership have separate lifetimes

### 9.1. Three identities are necessary

| Code | Lifetime | Owner and ending condition |
| --- | --- | --- |
| LT01 | Logical demand | An admitted task's need for a value/effect under its own deadline and acceptance policy. |
| LT02 | Physical work generation | One actual execution and its attached active consumers; ends when the worker settles. |
| LT03 | Retained result/value ownership | Readable values pinned by results, graph users or readers; ends when those owners release them. |

A work key describes shareability. It is not an execution occurrence. A completed result can keep bytes alive without keeping its old demand or deadline active. A new execution with the same key has a new physical generation.

### 9.2. Sharing preserves independent consumers

Two consumers can share eligible work when its semantics, source-observation scope, method basis and operational constraints agree. Each retains its own acceptance, deadline, cancellation and purpose outcome. Only active demands attached to the same physical generation contribute to its cooperative remaining-time calculation. One consumer timing out does not cancel work still needed by another; one unlimited live consumer can legitimately keep compatible shared work active, while a completed open result cannot.

The provider's actual attempt timeout also matters. A late consumer cannot assume that an already-started network call acquired a longer timeout. If its requirements cannot be met by the active attempt, admission must use a separate generation only when the command's replay/effect rules permit it, or report the limitation.

### 9.3. Cancellation does not erase physical reality

A cancellation request can prevent unstarted work and detach eligible logical demand. A running provider may settle later, and its actual receipt still has to be preserved. Python futures cannot cancel a call once it is running; therefore a thread-based provider requires cooperative checks or a separately qualified isolation mechanism for stronger termination guarantees. [E04]

The application must distinguish request cancellation, deadline expiry, physical settlement and effect certainty. It must also retain values until admitted dependent work has pinned them. Closing a result releases ownership; it cannot retroactively cancel another admitted consumer.

### 9.4. Every exposed plan entrance is validated

Prepared plans are data submitted through a public boundary. Root tasks, nested templates, dispatch branches and runtime expansions must satisfy the same structural contract: known dependencies, valid ports, bounded expansion and acyclic ordinary dependencies. Scientific iteration uses its explicit bounded iteration contract, rather than a hidden dependency cycle.

Validate every statically supplied nested template at submission. Validate runtime-bound or generated expansions before their atomic publication and before affected work starts. A finite library cannot promise completion for a cyclic graph merely because its compiler usually emits acyclic plans.

## 10. Efficiency and scalability are functional requirements

### 10.1. Optimize identities at the proper meaning

| Code | Identity | Reuse it can justify |
| --- | --- | --- |
| ID01 | Exact byte content | Reusing the same sealed bytes. |
| ID02 | Exact semantic value | Reusing a value with its relevant rows, semantics and provenance. |
| ID03 | Processing basis | Reusing the result of admitted inputs, method/settings/reference/build context. |
| ID04 | Acceptance context | Reusing competence for an exact logical source/selection and contract. |
| ID05 | Physical work key | Attaching compatible active consumers to one generation. |
| ID06 | Effect intent | Avoiding unintended repetition of the same external obligation. |
| ID07 | State revision | Determining whether a durable mutable record is newer. |

Using one enormous hash for all seven purposes causes unnecessary traversal and obscures semantics. Using a small caller-supplied hash without trusted content admission risks incorrect reuse. The target is sealed values with verified content identity and compact, explicitly distinct contextual identities.

### 10.2. Efficiency must preserve scientific evidence

Candidate payloads can be deduplicated while their provenance bindings remain distinct. A shared workbook can be decoded once while two series retain independent interpretation and coverage. A new destination can reuse a rendered artifact while creating its own effect. A projection query can use an indexed basis while retaining its exact horizon and authority links.

These are valid optimizations because they reuse work at the same promised meaning. Dropping alternatives, replacing source-specific rows with equal-looking rows, skipping acceptance or treating any receipt as sufficient would reduce cost by weakening the product.

### 10.3. Define a measurable operating envelope

An operating profile should state publication count and cadence, issue depth, selected row/cell volume, maximum original and archive size, concurrency, retained history horizon, backlog tolerance and supported recovery time. These are workload inputs and measured limits, not hidden constants in domain code.

For the first release, performance evidence should include a representative history, a large-byte path, concurrent shared consumers, repeated polling and at least several maintenance cycles. The 128 MiB probe establishes its tested byte path; it does not qualify every decoder or multi-year history. The architecture study specifies measurements and structural budgets without treating arbitrary wall-clock targets as established facts.

## 11. Scientific readiness is scoped to the requested route

### 11.1. Readiness belongs to the actual action and evidence

The readiness question is: can this method, for this source/layout/date/subject scope and this requested stage, establish the required meaning in this environment? It combines declared applicability, implemented behavior, reviewed scientific evidence, composability and current provider access.

| Code | Readiness dimension | Distinction that must survive |
| --- | --- | --- |
| RD01 | Applicability | Scientifically inapplicable versus applicable but unavailable. |
| RD02 | Implementation | Registered declaration versus implemented callable route. |
| RD03 | Scientific evidence | Synthetic structural test versus reviewed real publisher material and method. |
| RD04 | Scope | Supported layouts, periods, fields, territories and formula families. |
| RD05 | Composition | A valid single step versus compatible late entrances and complete dependent route. |
| RD06 | Environment | Unreachable source or missing backend versus an invalid scientific method. |
| RD07 | Operational qualification | Proven resource/recovery behavior under the selected provider/platform profile. |

A generic DBF reader establishes physical format competence. It does not create a reviewed financial model. An actual publisher fixture can establish interpretation evidence even when the live site is temporarily unavailable. A ready physical route and an unready analytical route can legitimately coexist for the same publication.

### 11.2. Candidate workloads for the first operating profile

The following is a qualification matrix, not a hardcoded source list or a declaration that every listed route already passes. Concrete membership remains caller-owned.

| Code | Workload | Required result promise | Specific gate |
| --- | --- | --- | --- |
| LW01 | Selected rolling originals | Qualified current source observation, exact retained bytes and requested delivery/archive. | Conditional retrieval, destination changes, restart and byte limits. |
| LW02 | Selected reporting-form archive exports | Selected DBF members, CSV and complete preservation evidence under an explicit codec policy. | Actual dialects, memo companions, deleted/blank values and both retained outputs. |
| LW03 | Reviewed reporting-form analytics | Source fields plus only the formulas supported by reviewed models. | Period/perimeter semantics, required operands and exact metric qualification. |
| LW04 | Industry or escrow histories | Selected comparable observations with stable vintage evidence and valid products. | Revision laws, real historical layouts, geography and calculation closure. |
| LW05 | Delivered-file selection and archive | Correct observed membership, exact package and conditional maintenance where requested. | Recognition scope, ambiguity, retained prerequisites and mutation recovery. |
| LW06 | Reviewed Rosstat monthly tables | Accepted selected indicators and a qualified workbook. | Reviewed table layout, period semantics, missingness and index interpretation. |
| LW07 | Additional FNS/Minfin or supplied-data routes | The exact physical or analytical stage supported by the selected methods. | Representative material, action-specific applicability and cross-domain reuse of common contracts. |

The examined maintained domain description explicitly retains gaps in financial models for forms 134/803, economic mappings for delivered-file series and portions of document/table interpretation. Those gaps need reviewed source material and scientific work. They should appear as precise readiness findings, rather than be hidden by generic extraction success.

### 11.3. Narrow scope while preserving foundational guarantees

The first launch can select a useful subset of qualified workloads. It should not require every historical publisher layout or every future forecasting function. Within the selected scope, history integrity, truthful acceptance, exact effect evidence, bounded work and recoverability remain mandatory.

When a layout changes outside admitted evidence, the system preserves originals and reports the unmet semantic stage. It can continue independent eligible tasks. This is the desired behavior of a dependable analytical tool, not evidence that every route must become universally permissive.

## 12. Applications consume one portable analytical model

### 12.1. Keep the application boundary thin and purposeful

| Code | Owner | Responsibility |
| --- | --- | --- |
| AP01 | Stratbox | Data meaning, methods, common actions, preparation, execution, acceptance, resource contracts and neutral provider interfaces. |
| AP02 | A Python caller | Concrete membership, supplied files, desired outputs, provider lifecycle and display. |
| AP03 | Strategy Box application | User work items, settings, recurring schedules, presentation, user decisions and orchestration of finite SDK requests. |
| AP04 | Platform adapter | Paths, file access, credentials, delivery adapters, process lifecycle and operating-system facilities. |
| AP05 | AppDock | Its external installation, activation and environment responsibilities; Strategy Box owns its side of that integration. |

A user work item can span multiple finite core runs. Its application status may include review or approval beyond core execution. The application should preserve links to run, selected member and effect identities rather than replace core outcomes with one independent boolean.

### 12.2. Desktop adoption is a separate completion package

The inspected Windows boundary targets an earlier core interface. The recommended target is a direct application adapter over the current SDK, shared discovery contracts and typed result projections. Legacy core imports should be removed as part of that migration. Restoring obsolete core namespaces would add a second architecture solely to preserve an unqualified client path.

The adapter owns one service lifecycle per intended application scope, maps user intent to finite calls, observes progress without blocking the execution coordinator, preserves result pins through downstream admission and retains artifacts before later reopening them. Application-level scheduling uses finite runs and explicit overlap policy.

Desktop readiness requires an actual packaged exercise on Windows: prepare, submit, progress, successful and partial results, cancellation/draining, artifact access, restart and provider failure. The core audit establishes no substitute for that exercise.

### 12.3. Universality for Android concerns contracts first

Portable request/result models, scientific rules and application use-case logic should remain independent of widgets, shell paths and native callbacks. The existing separation between common presentation meaning and a concrete desktop UI is a useful direction.

Future Android can use an admitted local runtime or a remote host through a portable boundary. That choice depends on packaging, scientific backends, filesystem guarantees and measured workloads. Copying Qt-specific workers, embedding Python object references in messages or assuming the desktop filesystem would constrain that choice prematurely.

A portable result must describe accepted values, qualifications, selected membership, receipts and durable artifact references. A session-owned temporary token cannot serve as a cross-process or post-restart artifact reference.

### 12.4. Future analytical areas should reuse the same foundations

A forecasting area can introduce scenario values, editable revisions, calendar transformations and reviewed consistency calculations. It should reuse semantic observations, exact derivation bases, qualified products and effect contracts. Human review and collaboration have their own application/service ownership.

This extension fit is an architectural test, not a launch requirement for the present data-processing scope. The history correction should avoid publisher-only assumptions that would later prevent distinguishing a published observation, an analyst-entered forecast and a derived value.

## 13. Worked situations connect the contracts

### 13.1. A revised source updates an analytical history

The caller freezes selected issues, measures and output periods. Acquisition admits issue A and a later revision B. Interpretation produces exact candidates and source validation witnesses. Resolution selects B for the latest view while preserving A. A disjoint new period is merged through candidate-preserving composition.

A latest report uses the new view and its exact processing basis. An as-of-A query uses A's candidates. If a new method or territorial reference changes, dependent interpretation or calculation is reassessed under a different basis. The original publication candidates remain unchanged. Saving and restoring the history retains these relations and their supported query scope.

### 13.2. A collection has useful diagnostics and incomplete data

Three selected sources enter a map. The first produces accepted observations. The second retains an original but fails semantic interpretation and emits a report. The third produces observations but its required named copy has an unknown outcome.

The result reports all three members in selected order. The second contributes a diagnostic and available original, while its observations obligation remains failed. The third has accepted observations and an unresolved effect. Under an all-required policy, the aggregate purpose is incomplete. A separately requested diagnostic summary can complete. Under an explicit eligible-subset analytical policy, the first member can feed a qualified partial analysis while the other outcomes remain visible. The enclosing request still retains its partial/unknown disposition wherever the third member's save remains required; completing the subset output cannot retire that obligation.

After recovery, the second can be reinterpreted from its retained original, and the third can reconcile delivery. The first is reused if its basis remains adequate. No collection rule turns the second's diagnostic into accepted observations.

### 13.3. An unchanged source is delivered to another destination

The source returns a qualified 304. The retained representation supplies verified bytes under the appropriate request context. The caller now asks for destination B, while the earlier receipt covers A.

The engine reuses the bytes and fulfills B through the common storage command. If the acknowledgement is lost, B's effect remains unknown and is reconciled under the same intent. The old A receipt remains a valid historical fact for A; current availability is checked separately when required. A conflicting lookup identity is recorded as a conflict and cannot retire B's pending obligation.

### 13.4. A recurring host restarts after a crash

Before the crash, the effect ledger confirmed a named artifact, the journal recorded its accepted use, and the source-state projector was behind. Recovery reads authoritative state, replays the bounded journal suffix and reconstructs only the missing projection. If the journal append itself was lost after confirmation, recovery records a new qualified reconciliation fact from the receipt.

The host resumes finite work under the pinned selection and goal. It does not infer source acceptance from the presence of a file alone. Maintenance protects unresolved effects and consumer watermarks. An older slow run finishing after a newer source observation remains an older valid result rather than automatically replacing the current projection.

## 14. Completion packages and launch gates

### 14.1. Implement coherent packages

| Code | Package | Main closure | Completion evidence |
| --- | --- | --- | --- |
| W01 | Acceptance and obligation preservation | R02; consistent data/report roles, collection policy and stage projection. | Failed and unknown diagnostic producers cannot fulfill required analytical members; explicit report and subset policies still work. |
| W02 | Historical evidence and vintage integrity | R01, R05; candidate-preserving merge, resolution, projection and codec. | Earlier vintages, equal-value provenance and certificates survive the complete route. |
| W03 | Effect fulfillment and recovery evidence | R03, R04, R06, R08; destination-specific obligations, common acknowledgement admission, live durable lookup and crash-safe guards. | Wrong evidence never confirms; lost replies reconcile; crash leaves a recoverable provider. |
| W04 | Admission and physical work lifetime | R07, R09; recursive graph gate and generation-bound active consumers. | Nested invalid plans reject before work; closed demand never contributes to a new deadline. |
| W05 | Sealed identities and efficient coordination | R10; compact trusted references, bounded scans and reduced critical-section work. | Representative route measurements show bounded overhead without identity or provenance weakening. |
| W06 | Persistent operating profile and scientific qualification | R12 and workload-specific evidence; maintenance, restore, platform/provider tests and readiness admission. | Chosen workloads pass their scientific and operational gates through repeated cycles. |
| W07 | Desktop adoption of the current core | R11; SDK adapters and faithful result presentation. | Packaged Windows application passes the declared end-to-end profile. |

W01 through W04 can proceed in parallel after the small shared contract decisions are explicit. W05 should begin with measurement and be completed against the corrected value and acceptance contracts. W06 starts with scope and fixture selection immediately; its launch decision follows the functional packages. W07 can adapt stable SDK contracts in parallel, while final application qualification follows the selected core/profile release.

### 14.2. Use gates rather than speculative calendar estimates

| Code | Gate | Passing condition |
| --- | --- | --- |
| G01 | Truthful completion | No accepted composition turns a failed/unknown required obligation into success through a surviving object. |
| G02 | Historical integrity | Supported vintage queries preserve values, exact member provenance, coverage and validation through composition and restart. |
| G03 | Effect integrity | Every confirmation matches its intent and required evidence level; destination changes create the right obligation. |
| G04 | Execution integrity | All admitted graph layers are valid; sharing, cancellation, deadlines and ownership remain independent. |
| G05 | Resource adequacy | The declared workload fits measured memory, temporary storage, coordinator and provider budgets. |
| G06 | Persistent operation | Interruption, reconciliation, replay, maintenance and restore pass for the advertised profile. |
| G07 | Scientific competence | Representative reviewed material and method evidence cover the exact launched stages and scope. |
| G08 | Application compatibility | Each launched surface uses the packaged current contract and faithfully presents qualifications and remaining work. |

A useful core release can launch after its applicable G01–G07 conditions are met. A desktop release additionally requires G08. Scientific routes outside the admitted scope remain discoverable with explicit limitations, or are rejected at preparation when the requested promise exceeds their evidence.

### 14.3. Prioritize the first useful result without accumulating architectural debt

The immediate priority is the false-completion and historical-evidence group. The second is recoverability and execution integrity. The third is measured operating capacity and the selected scientific contour. These priorities overlap in implementation: a candidate ledger and sealed identity work should share representations, while effect normalization and destination fulfillment should share one confirmation boundary.

The program should not begin with distributed scheduling, a universal temporal database, complete coverage of every publisher, or a new mobile UI. Those are separate future needs. Completing the existing common route provides the necessary foundation for them when demand is concrete.

## 15. Functional acceptance situations

| Code | Situation | Required target behavior | Package |
| --- | --- | --- | --- |
| FA01 | A failed producer returns a readable diagnostic to a required collection. | Preserve the report and failed member; required analytical fulfillment remains unsatisfied. | W01 |
| FA02 | An unknown effect producer returns a receipt-shaped object. | Preserve unknown until competent matching confirmation. | W01, W03 |
| FA03 | The caller explicitly requests a diagnostic aggregate. | Complete that report without changing underlying member outcomes. | W01 |
| FA04 | An eligible-subset policy excludes a failed member. | Explain selected, accepted and excluded membership; preserve exact partial coverage. | W01 |
| FA05 | Latest January value 2 is merged with disjoint February; as-of-A originally reported 1. | As-of-A remains 1 or reports missing evidence; complete value 2 is forbidden. | W02 |
| FA06 | Two issues report equal numbers with different source rows. | Coalesce display if allowed; retain both exact provenance bindings. | W02 |
| FA07 | A history is selected, encoded, restored, merged and resolved again. | Preserve selection, allowed vintage scope, candidate/witness bindings and missing issues. | W02 |
| FA08 | The same issue label appears for two sources or assets. | Coverage and candidates remain scoped to their real members. | W02 |
| FA09 | A caller fabricates a complete-looking certificate. | Require competent authority and exact binding before scientific acceptance. | W01, W02 |
| FA10 | HTTP 304 is received while the requested destination changes. | Reuse bytes and separately fulfill the new destination. | W03 |
| FA11 | Reconciliation returns another intent, kind, scope or contradictory alias. | Preserve pending obligation and reject confirmation authority. | W03 |
| FA12 | A provider performed the action but its reply was lost. | Reconcile; retry only under a sufficient guarantee. | W03 |
| FA13 | Another live service confirms an unknown durable receipt under a provider that supports shared service use. | The first service observes authoritative progress before deciding the next action; full multi-process profile qualification remains separate. | W03 |
| FA14 | A process dies while holding a local mutation guard. | The qualified provider recovers without blind removal of a live owner's protection. | W03 |
| FA15 | A completed open result has no deadline; a new same-key run has five seconds. | Only the new generation's active demand affects its remaining time. | W04 |
| FA16 | One active shared consumer cancels while another needs the result. | Preserve compatible physical work and independent outcomes. | W04 |
| FA17 | A supplied plan has a nested template cycle, or a runtime expansion becomes invalid. | Reject the static template at submission or the generated slice before atomic publication; no affected effects start. | W04 |
| FA18 | A real scientific iteration converges or reaches its bound. | Use explicit iteration semantics and preserve qualified termination. | W04 |
| FA19 | Two consumers receive a large already admitted immutable dataset. | Reuse verified identity and ownership; no repeated full scan solely to attach consumers. | W05 |
| FA20 | A caller mutates nested content after submission. | Accepted work uses a sealed snapshot or rejects unsafe admission. | W05 |
| FA21 | A new source layout arrives beyond reviewed competence. | Retain useful physical evidence; refuse an unsupported semantic completion. | W06 |
| FA22 | Journal/projection coverage is missing. | Report incomplete state and rebuild only from competent surviving evidence. | W06 |
| FA23 | Repeated polling reaches an archival/compaction boundary. | Preserve pending obligations and advertised recovery/vintage scope under bounded maintenance. | W06 |
| FA24 | A backup is restored without one required artifact or effect segment. | Detect the missing dependency; do not advertise complete recovery. | W06 |
| FA25 | Desktop receives partial data and an unknown named save. | Display both accurately and offer only semantically valid next actions. | W07 |
| FA26 | An admitted downstream task needs a staged value after its producing result closes. | The downstream pin keeps the value readable; final release reclaims it. | W04, W07 |
| FA27 | A calculation's displayed output is narrow but its model is coupled. | Preserve full required input closure and project only the result. | W06 |
| FA28 | A forecast value and a publisher observation share numerical coordinates. | Keep their origin, scenario/revision and derivation meaning explicit. | Future fit |
| FA29 | A retained history is resolved newest → oldest → newest. | Each view agrees with direct resolution of the same retained evidence and active scope. | W02 |
| FA30 | An old valid backup is restored after a later external action whose local evidence was lost. | Obtain sufficient reconciliation/tail evidence or refuse replay of affected occurrences; restored absence cannot authorize duplication. | W03, W06 |

## 16. Alternatives and their consequences

| Code | Alternative | Assessment |
| --- | --- | --- |
| AL01 | Patch each reproduced branch independently. | Useful for immediate containment, insufficient as the final model unless shared invariants and every equivalent entrance are corrected. |
| AL02 | Refuse all outputs from unsuccessful work. | Loses valid diagnostic and explicitly qualified partial-result use cases. |
| AL03 | Keep only the latest row and a list of old issues. | Cannot support honest historical resolution or exact provenance. |
| AL04 | Retain every full dataset copy everywhere. | Preserves information but repeats payload, hashing and ownership cost; a shared candidate ledger is more economical. |
| AL05 | Treat a matching digest as universal acceptance. | Confuses bytes, semantic context, competence and effect fulfillment. |
| AL06 | Retry every unknown action after a timeout. | Can repeat a completed external effect; provider-qualified reconciliation is required. |
| AL07 | Make every component a separately deployed service. | Adds distributed ownership and recovery problems before the finite core/profile is qualified. |
| AL08 | Freeze development until all scientific gaps are filled. | Delays useful qualified workloads without improving foundational guarantees. |
| AL09 | Declare readiness from catalog size and passing unit tests. | Omits scientific scope, counterexamples, resource evidence and surface compatibility. |
| AL10 | Restore old core interfaces for the current desktop. | Preserves duplicate architecture and weakens the target migration. A direct SDK adapter is preferable. |

## 17. Decisions recommended now and evidence still required

### 17.1. The recommended decisions are concrete

Adopt obligation-based acceptance, exact candidate evidence for histories, one effect-evidence admission path, physical-generation ownership, recursively validated plans and trusted sealed identities. Keep the existing standard action hierarchy and five implementation owners. Qualify one bounded persistent operating profile and a caller-selected scientific workload. Migrate applications through the same public SDK.

These decisions fit together: the history model supplies trustworthy immutable inputs; the acceptance model determines their eligible uses; compact identities make those uses economical; the execution model manages their physical lifetimes; effect evidence settles requested external obligations; durable projections make future work selective and explainable.

### 17.2. Implementation must establish the remaining facts

The exact supported source/layout/period set, provider acknowledgement strength, platform lock behavior, effective performance budget and packaged application compatibility remain verification obligations. They should be closed through representative fixtures, contract tests, interruption exercises and workload measurements. Proposed names or diagrams in the companion study are design aids, not evidence that these facts already hold.

The research recommends a clean cutover. Derived state can be rebuilt when its basis changes. Retained effect authority and historical evidence need an explicit preservation or rejection decision; absence of backward-compatibility requirements never authorizes silently forgetting a performed effect or inventing a lost vintage.

## 18. External sources

| Code | Primary source | Specific supported claim and use |
| --- | --- | --- |
| E01 | [RFC 9110: HTTP Semantics, sections 9.2.2, 13 and 15.4.5](https://www.rfc-editor.org/rfc/rfc9110.html) | Conditional representation reuse and retry constraints, used in sections 7.2 and 7.4. Stratbox's obligation model is a design inference. |
| E02 | [W3C PROV-DM, Recommendation of 30 April 2013](https://www.w3.org/TR/prov-dm/) | Entities, activities and derivation relations are distinct provenance concepts. Used in section 5.1 to motivate exact candidate and witness relations; no RDF adoption is implied. |
| E03 | [RFC 9111: HTTP Caching, sections 4.1 and 4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html) | Stored-response reuse and validation depend on matching the applicable representation. Used in section 7.2; a new local destination remains a separate application obligation. |
| E04 | [Python 3.12: concurrent.futures, Future.cancel and Executor.shutdown](https://docs.python.org/3.12/library/concurrent.futures.html) | Cancellation cannot stop a running future, and executor shutdown distinguishes pending and running calls. Used in section 9.3 to qualify physical-stop claims. |
