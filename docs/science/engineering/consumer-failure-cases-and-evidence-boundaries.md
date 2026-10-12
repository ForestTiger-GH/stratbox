# Fourteen Strategy Box consumer cases: answers without historical Research

**Publication status:** bounded scientific/application explanation. The examples combine directly observed public implementation limits, scientific inference and expressly conditional host designs. They are **not executed target acceptance tests** or independent semantic preservation certification.

**Reading contract:** every case is answerable with the statements below and the linked **maintained Knowledge topics**, without historical research, source-to-claim ledgers or Work notebooks. Exact source evidence is useful for independent verification but is not a dependency of comprehension. An authenticated hosted Strategy Box is **planned**, not a shipped component. A candidate failure response must not be described as present implementation.

## 01. Same publisher URL, new bytes, earlier financial report

**Question.** A publisher silently replaces an XLSX at the same URL. A report retains its collection date, but neither the used bytes nor a digest is saved. Can its original numbers be reconstructed exactly?

**Bounded answer.** The source locator identifies where acquisition was attempted, and the recorded date is one observation-time clue. Neither identifies the bytes actually used. Today's response might be a different publisher vintage. Unless some independently retained equivalent content or an actual used-input receipt survives, the old report's exact computational inputs and replay cannot be demonstrated. Previously published numbers can be cited as *previously reported*, with weakened provenance, not re-certified as reproducible or as definitely unchanged. A later digest of new bytes does not repair the missing old proof. [Source observation and replay](../data-and-knowledge/source-observation-vintages-and-replay.md) separates locator, bytes, observation and method revisions.

## 02. HTTP 304 without a cached body; unstable validator

**Question.** The collector gets `304 Not Modified` while cached bytes are absent, or sees one ETag reused with changed content. Does that prove no source change?

**Bounded answer.** A `304` validates a conditional request under an assumed available cached representation. Without the old body it supplies no usable source bytes for computation, even though the HTTP exchange itself succeeded. If a publisher reuses a validator inconsistently, ETag equality is not byte equality: content must be acquired and, when the case warrants, compared with a retained digest/identity. The honest product state is **insufficient source evidence, unavailable cached input or failed observation**, never an invented empty table or confirmed `NO_CHANGE`. [Source-vintage identity](../data-and-knowledge/source-observation-vintages-and-replay.md) and [current transport/collector boundaries](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md) distinguish the actual implementation from a proposed stronger receipt.

## 03. Optional registry components and mixed editions

**Question.** An OKVED2 consumer requests `data` but lacks optional `meta` and `structure`; another process combines all three from different local editions. Which outcome is observed and which is a future risk?

**Bounded answer.** The current basic `read()` route is scoped to its `data` resource and therefore should not be equated with a universal triple-resource verification. Separately requesting optional metadata or structure can fail when unavailable. The potential **cross-edition mix** is a design/evidence problem for consumers that require a coherent registry bundle: independent file-selection timestamps do not prove a single official edition. Do not promote a proposed bundle-identity guarantee into the existing loader; do not call a valid data-only response a complete verified registry set. [Pinned registry Current HOW](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md); [source/registry scientific identities](../data-and-knowledge/source-identity-and-reproducibility.md).

## 04. Identical publication bytes, different rounding model

**Question.** Two SORS reconstructions use byte-identical publications; the second changes rounding assumptions. Is the resulting number an exact official latent amount?

**Bounded answer.** Matching bytes proves only input byte identity for that acquisition, not identical computation assumptions or official interpretation. Under unit-step rounding a published six identifies a latent interval `[5.5, 6.5)`, with an **open upper endpoint**, rather than `x=6`. Changing the rounding policy, solver objective or evidence tier can change an admissible reconstruction while the publisher bytes remain identical. Label the observed publication, mathematical feasibility, preferred reconstructed representative and official latent truth separately; identify both model and source vintages. [Rounding and claim strength](../data-and-knowledge/publication-rounding-and-claim-strength.md); [bounded current restoration](../../current-how/sors-restoration-evidence-and-inference.md).

## 05. Required Scenario step fails but a log file appears

**Question.** A composite Windows Scenario continues after a failed required Step and produces a diagnostic `.log`. Can the enclosing Case claim full success and one valid data Artifact?

**Bounded answer.** In the pinned local Windows runner there is a demonstrated **aggregate-success hazard** when a step fails and continuation is allowed: a later terminal Case projection need not represent all required step outcomes truthfully. A diagnostic path or file-like output does not certify an analytically valid data result, a validated Artifact or an accessible published workbook. Inspect required/optional step policy, per-step outcome, actual file bytes and Artifact publication separately. This is observed at a particular source revision and partially characterized with synthetic execution; its correction and host semantics are **not implemented by this document**. [Windows Current HOW](../../current-how/windows-application.md); [Artifact identity and publication](../artifacts/output-identity-publication-and-availability.md).

## 06. Lost GUI signal, corrupt history and stale platform `active_job`

**Question.** A GUI worker stops emitting signals, local JSON Case history cannot be parsed and the surrounding platform still reports `active_job`. Which record is authoritative?

**Bounded answer.** A worker signal is a client observation, a platform continuity field is an external status hint, and a corrupt JSON history file is an **observation failure**, not legitimate evidence of no past Cases. None of those facts proves a surviving accepted Job with completed effects. Preserve/quarantine the corrupt bytes and qualify the local recovery; seek a separately attested actual execution or effect receipt from the relevant owner, if one exists. Where there is no durable host, mark outcome **unknown** rather than synthesizing a complete or empty history. [Current Windows persistence](../../current-how/windows-application.md); [observed error versus uncertain outcome](../trust-and-assurance/uncertain-outcome-vs-observed-error.md).

## 07. Browser closes while Windows is executing; proposed remote host differs

**Question.** If a browser tab closes during local Qt execution, must the domain computation stop? Could a proposed remote host keep a Job alive?

**Bounded answer.** A browser close cannot be used to infer the state of an independent local Qt worker, and the current Windows app is **not proof of a detached server**. Local foreground close/cancel policy and a separately admitted remote host's durable Job life cycle are different application profiles. A future authorized host *could* continue accepted work beyond client disconnect when its real process, state, admission and recovery contracts support that; this is a planned requirement, not a shipped guarantee. The physical location of shared logical host semantics is still an open design decision. [Host commitment](../../what/strategy-box/host-deployment-commitment.md); [Current Windows process reality](../../current-how/windows-application.md).

## 08. Shared warning but protected detailed logs

**Question.** One team member sees a node-wide problem and asks to expose another user's full operation logs to all members. What may safely be shared?

**Bounded answer.** An audience-safe condition may disclose a scoped condition class, time, affected resource category, availability impact and remediation path without leaking secrets or personal work. Detailed logs can contain paths, private parameters, source bytes, bearer tokens and principal identity. Each viewer's permission must be evaluated against the particular log/Case/Artifact when accessed; membership or a simple display name is not sufficient. A remote Web deployment needs authenticated principals and server-side enforcement. [Shared conditions and protected logs](../collaboration/shared-conditions-and-log-access.md); [identity and effect authority](../trust-and-assurance/identity-authorization-and-effect-boundaries.md).

## 09. Expired stream cursor with independent per-person read positions

**Question.** User A has read a Case; User B has not. A reconnects with an expired cursor after access rights change. Can the server fast-forward all participants?

**Bounded answer.** A read receipt is **per authorized principal**, separate from global event order and delivery acknowledgement. An expired cursor must lead to an authorized resynchronization or explicitly bounded history-gap state, not a fabricated continuation. Reevaluate present access when constructing the reconnect snapshot and subsequent feed; never expose events on the basis of stale former rights. Resynchronizing A does not rewrite B's read position. [Authorized streams, scoped cursor and reads](../collaboration/authorized-streams-read-cursors-and-private-work.md).

## 10. Excel bytes produced, publication interrupted, metadata changed later

**Question.** File generation finishes but the Artifact catalog commit or remote acknowledgement fails. Later, the user edits the XLSX document's creator field. Which claims remain trustworthy?

**Bounded answer.** Successfully written bytes mean **physical output existed at one point**, not that stable Artifact identity, catalog publication, safe remote availability or user receipt succeeded. Failure of acknowledgement after the effect may leave the remote outcome **unknown**, requiring reconciliation rather than blind repeat. A user-editable creator or other Office property is presentation metadata; it does not rewrite the authenticated initiating principal or scientific provenance. Maintain separate content digest, actual-used-source receipt, render profile and verified publication/effect state. [Artifact publication and uncertainty](../artifacts/output-identity-publication-and-availability.md); [report author versus provenance](../artifacts/report-formatting-profiles-metadata-and-evidence.md).

## 11. Android client cannot run Windows Qt or the Python core

**Question.** Must a lightweight Android client import PySide6 or execute the Python analytical library to view permitted Scenarios and their results?

**Bounded answer.** No. Cross-device reuse concerns **application meaning**: allowed Scenario definition, parameter semantics, Run/Case references, access-scoped state transitions, Artifact identity and permitted commands. A remote Android client can render those semantics through an appropriate authenticated client contract without importing the Windows presentation toolkit or executing Python core locally. Whether a particular Android feature, remote API and offline mode are supported remains contingent on actual implementation and Product choice. [Semantic portability](../surfaces/semantic-portability-and-client-authority.md); [accepted host deployment profiles](../../what/strategy-box/host-deployment-commitment.md).

## 12. HTTP 200 but broken Artifact store; DB-only backup

**Question.** A hypothetical host returns HTTP 200 while shared output bytes are unavailable; the DB backup exists but Artifact bytes do not. Is the service ready and fully restorable?

**Bounded answer.** Process liveness and **readiness of the promised analytical workflow** are different. A listening HTTP handler may be alive while requested Artifact access is degraded or impossible. Metadata-only backup cannot restore absent output bytes, unless explicitly declared recomputation inputs, versions, method and rights make recreation independently feasible. Restore receipts must identify what was included, a consistent generation boundary, missing files and the exact degraded outcome after trial restoration. These are target verification conditions, not observations of an installed host. [Hosted readiness trade-offs](../deployment/headless-host-web-security-and-persistence-tradeoffs.md); [consistent backup and retention](../state-and-recovery/shared-state-backup-generation-and-retention.md).

## 13. Provider reports `ready`, operation says `retryable`, effect unknown

**Question.** A requester lacks permission and the prior external attempt might have succeeded. May the product repeat the operation because provider flags say it is ready and retryable?

**Bounded answer.** No. Provider readiness is only one prerequisite; the concrete principal/resource authorization must pass **at admission and again before the effect**, and any plan-specific approval must remain valid. `retryable` is descriptive metadata, not evidence of idempotence after an uncertain external mutation. Reconcile the prior effect with a stable command/idempotency identity or make the residual unknown explicit. No automatic repeat or publication is justified by two flags. [Capability validity](../capabilities/compiled-domain-capabilities-validity-and-deoptimization.md); [authorization](../trust-and-assurance/identity-authorization-and-effect-boundaries.md); [uncertain effects](../trust-and-assurance/computation-reuse-and-external-effects.md).

## 14. Strong historical host/registry recommendation versus actual Product Decision

**Question.** Earlier technical proposals strongly preferred a named host repository and one global source registry. Does the Product currently require those exact physical structures?

**Bounded answer.** The **logical need for a Strategy Box-controlled application host** in two future deployment arrangements is admitted. A particular `stratbox-host` or `stratbox-application` repository, process/DB topology, API transport, universal source catalog, mandatory archival policy and global value-level monitoring are **not** automatically admitted. Minimal used-source receipts and independent core operation contracts can satisfy a narrower scope; greater infrastructure requires measured consumer value, authorized Product decisions and implementation evidence. [Product host decision](../../what/strategy-box/host-deployment-commitment.md); [source identity and proportionality](../data-and-knowledge/source-identity-and-reproducibility.md); [ownership alternatives](../architecture/architectural-convergence-conflicts-and-supersession.md).

## How these answers should be challenged

These fourteen cases are a **producer-written, published-only consumer rehearsal**. The file contains no route into the historical Research/Work archive. Each answer is bounded by available scientific/current-code evidence and labels when the real host, permission model, native client or fault test is absent.

A **different competent verifier** must independently attempt the same jobs from a frozen standalone `docs/` copy, record an answer or an honest `UNKNOWN`, and then compare the outcomes to authorized original Research **outside this publication**. This article does **not** perform that independent check, cannot prove every earlier material assertion was preserved and is not a `LOSSLESS_PASS`.
