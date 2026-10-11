# Strategy Box as one product: purpose, actors, responsibility and physical boundaries

**Scope and status.** This is a bounded scientific synthesis of the independently read 2026-10-08 *System Model* research (frozen source `SB-SRC-0046`, blob `2be1cfd1615bcae34375947389bd355c7c07a7ad`, L1–L1878). It analyzes the boundary between an independently useful analytical Python library, a desktop application with current orchestration, a prospective application authority, presentation clients, and an external environment platform. It **does not adopt a Product Decision, prove the presence of a headless runtime, create a repository, or certify cross-client behavior**.

**Direct implementation scopes:** [`stratbox` frozen source](https://github.com/ForestTiger-GH/stratbox/tree/8459dc58922b7e8df853cf1d9e8131fa9e132580), [Windows implementation owner](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). Research descriptions of future components must be judged separately from those exact implementation snapshots.

## 1. Product identity: more than a library, less than a generic platform

Strategy Box's current mature substance is banking/macro data intake, transformation, validation, reconstruction and analytical outputs, accompanied by a Windows control surface. Its **candidate** long-term identity is an analytical working environment that connects authoritative external publication, observed bytes, canonical observations, reproducible calculations, qualified evidence, user Work, execution and managed artifacts. A path, DataFrame, UI message, displayed number or saved workbook is not enough to establish analytical validity, currentness or an accepted human outcome.

Two useful paths coexist. A notebook/Python caller can use domain functions directly without manufacturing a chat or an application-managed Run. A managed Work may instead need durable command admission, authorization, execution, review, artifact availability and shared projections. The second path **uses** the first; it does not replace the domain core.

The candidate product is neither an arbitrary Python-function GUI nor a new installation platform, universal enterprise ETL engine or separate cognition-only calculation system. Convergent research supports stable business capabilities with multiple human, scheduled and machine consumers; it does not justify one new engine per consumer.

## 2. Four responsibility planes, not four guaranteed repositories

| Plane | Semantic or operational truth | Existing implementation / future limit |
| --- | --- | --- |
| **Domain / analytical** | Banking/statistical subject meaning, source/registry interpretation, validated transformations, model results, provenance and domain output contracts | The `stratbox` package is independent and directly callable; contract maturity varies by domain. |
| **Application / accountable Work** | Work context, plan and admission, Run/Job/Attempt, product authorization, automations, approvals, shared history, artifact catalog visibility | Narrow, Qt-bound and locally persisted aspects exist in Windows; a durable headless application authority remains a proposal. |
| **Platform / environment** | Install, deployment, managed roots, Node/Session, process activation, platform health and operational recovery | An external platform owns its **own** lifecycle and identity facts; its health state cannot certify a banking result. |
| **Presentation / interaction** | Rendering, navigation, client drafts, accessibility, local OS interactions and safe permitted actions | Windows is the realized surface; Web and Android are prospective consumers of common application semantics. |

The phrase **presentation truth** in the original four-plane summary means authoritative state of a particular rendering or local preference, **not** authority over a shared banking observation or a Job. One semantic application owner may reside physically inside one process, or be served by a separate local/team process. The physical model is determined by independent consumers, restart/fault domains, security, release cadence and deployment constraints.

In a shared setup, multiple clients must not hold competing primary copies of the same Job, Work or user grant. In a standalone direct-Python setup there may simply be no shared Work authority; this is a different supported profile, not an inconsistency.

## 3. Actor, principal, participant, automation and executor

**Principal/session fact** answers who is connected to an environment; **product authorization** answers whether the verified subject may perform a specific action on a specific Work, artifact, data source or effect. A person shown as a participant is not automatically an authorized editor or cancellation actor. An automated trigger retains the identity of its rule and delegated authority; it should not masquerade as a live human.

An external cognitive planner or machine caller may inspect an authorized curated capability, propose a plan and request execution. It neither becomes owner of a bank formula nor receives intrinsic write authority. The **requesting actor, authorizing principal and physical executor** may all differ; accurate audit requires all three. An application worker's success is also a separate fact from content validity and human acceptance.

The current application contains user/session/node context and local Case/events/assignment/presence models. This does **not** prove authentication, durable cross-user permissions, a platform-independent Job service or safe remote AI invocation. See [identity and effects](../trust-and-assurance/identity-authorization-and-effect-boundaries.md) and [semantic lifecycles](semantic-identities-lifecycles-and-projections.md).

## 4. Three distinct runtime meanings

1. **Core provider runtime** selects a storage/network/secret capability for an independent Python operation. This has no inherent Work ledger.
2. **Strategy Box application runtime** would own managed Work/Run/Job lifecycle, admission, scheduling, resource coordination, cancellation/retry, product policy, shared projections and state recovery.
3. **Environment platform runtime** owns installation, Node/Session context, process launch/health, platform recovery and platform diagnostics.

The current Windows launch path composes a Qt-bound Scenario coordinator, a single active Scenario and separate JSON history projections; background, assignment and presence vocabulary exceeds what is yet demonstrated by authoritative backend behavior. A future host with a separate lifecycle is a **strong research option**, especially for uninterrupted background/team access, but not a completed migration or mandatory Git repository.

The original research favored the working name `stratbox-host` over creating another general `stratbox-core` repository. Its precise claim is: **the application authority is a durable logical boundary; the best physical packaging remains conditional**. An embedded single-user adapter, headless local process and shared team host make different truthful lifetime claims. The local-host proposal must pass startup, packaging, IPC, supervision, recovery and slow-device tests. A GUI close cancels nothing automatically unless the chosen execution profile specifies that lifecycle. See [deployment profiles and evidence gates](system-architecture-profiles-decisions-and-evidence-gates.md).

## 5. Work, data, capabilities and artifact ownership intersect but do not merge

A **Thread** holds discussion/context; a **Work** denotes an accountable objective; a **Scenario/Scheme** is a curated or reusable way to achieve some result; a **resolved plan** freezes effective inputs and effects; and a **Run/Job/Attempt** records actual execution. The original 2026-10-08 System Model deliberately left exact cardinalities and even the definitive Case/Run distinctions unresolved. A currently persisted `ScenarioRunCase` is a real narrower object, not a final Work ontology.

The domain core owns source interpretation, domain registry facts, canonical operation semantics, subject validity and output/provenance conventions. Application authority may own artifact indexing, Work linkage, ACL-scoped visibility and user-facing materialization records. A file backend owns actual bytes and its write/rename guarantees. A path belongs to a storage representation, not durable Artifact identity. Optional heavy universal Claim/Knowledge stores require separately demonstrated consumers.

For a domain operation, invocation through notebook, desktop, schedule and authorized machine client should have **the same subject capability identity**, with different admission/application contexts. A `background` flag is an execution characteristic rather than an independent business ontology. The scheduler interprets product triggers in application semantics; the platform may supervise the underlying long-running process. See [execution truth](../capabilities/definitions-plans-and-execution-truth.md), [artifact publication](../artifacts/output-identity-publication-and-availability.md) and [automation](../automation/trigger-occurrence-identity-and-governed-execution.md).

## 6. Three failure planes and two distinct design vocabularies

Domain diagnostics describe invalid source, unsupported interpretation, partial result and analytical provenance. Application execution state describes admission, progress, retry, cancellation, permission, final/UNKNOWN effects and Work acceptance. Platform health describes process availability, session or environment startup and infrastructure recovery. Neither a green platform indicator nor a successful workbook write certifies the other two planes.

Likewise, **interface design tokens** (semantic status colors, typography, motion, density, accessible controls) and **report/artifact style sets** (XLSX/DOCX/PDF/PPTX visual outputs) have different consumers and version/lifetime rules. A common design language is a valid logical responsibility. A mandatory standalone design repository is currently **unsupported** because independent frontend/package consumers have not yet been proved. Future Android should reuse semantic forms, status, actions and artifact projections—not Qt widgets or Windows layout.

Public extension integration is described only by environment-neutral declarations, versioned bindings, availability, error and conformance contracts. Discovery, selection and readiness are different events; no concrete deployment-specific implementation knowledge belongs in public architecture.

## 7. Fifteen source-proposed invariants, deliberately not test results

The original System Model explicitly proposed **15** invariants. They are retained as research constraints:

| ID | Candidate invariant and falsifiable risk |
| --- | --- |
| I01 | One primary semantic authority per durable fact; independent Windows/host/platform writes may not disagree silently. |
| I02 | Domain core remains callable without a GUI/client. |
| I03 | UI cannot rewrite domain statistical meaning or source/evidence validity. |
| I04 | Application runtime coordinates execution without reimplementing bank domain rules. |
| I05 | Environment platform lifecycle is distinct from Strategy Box product Work/schedules. |
| I06 | Foreground, background, timed, API, remote and machine-triggered actions share one governed execution semantics. |
| I07 | Client closure does not by itself determine accepted Job lifetime. |
| I08 | Initiator, authority and actual executor remain distinct audit relations. |
| I09 | Artifact identity is independent from storage pathname. |
| I10 | Public extension declarations remain neutral and bounded. |
| I11 | Application UI theme and produced-report style remain independent. |
| I12 | UNKNOWN source, backend and effect outcomes are preserved rather than converted into false success/emptiness. |
| I13 | Ontology follows semantic responsibilities, not current package locations. |
| I14 | Direct Python use remains possible without mandatory Work/Job records. |
| I15 | New repositories require independent lifecycle, consumer, trust, deployment, failure or maintenance evidence. |

None is asserted as enforced by current code. An explicit negative test is needed for every guarantee claimed by a future managed profile.

## 8. Conflicts, historical supersession and open admission gates

Eight original conflict families are preserved:

| Original family | Research disposition; Product commitment status |
| --- | --- |
| **C1** general application library vs dedicated headless service | Logical authority established at research level; `stratbox-host` strong **physical hypothesis**, not ordered repo split. |
| **C2** product scheduler vs environment platform scheduler | Product schedule/Job meaning on application side; platform service supervision separate. |
| **C3** domain Artifact Catalog vs application catalog | Domain result/manifest/provenance; application ACL/Work index; bytes backend. |
| **C4** Scenario as primary goal vs Thread/Work | Later durable Work direction stronger; Case/cardinality still undecided. |
| **C5** background as special Scenario kind | Rejected as target ontology; preserve current enum as observed historical implementation. |
| **C6** platform directly owns product files/logs/jobs | Clarified to platform infrastructure capabilities versus application/domain meaning. |
| **C7** dedicated design repository now | Logical design responsibilities, physical packaging open. |
| **C8** universal graph-shaped Knowledge infrastructure | Epistemic distinctions useful; universal storage/schema still unproven. |

Historical alternatives **H1–H8** in the source concern: homemade launcher as lifecycle authority, GUI co-located inside the domain library, combined domain/GUI monolith, background Scenario type, platform/external scheduler as the sole product automation owner, all work inside Scenario, platform-owned user artifact meanings, and bespoke application glue inside the domain repository. All should retain their **historical** role, including the valuable simplicity/direct-library motivations behind some of them. They are not commands to delete source history or break users' saved records.

Open questions from original §24 include the exact Work/Thread/Case/Job ontology; local IPC and remote command/event API; embedded versus separate desktop authority; state backend and transactional guarantees; platform-to-product principal mapping and authorization; client-specific versus shared settings; notification semantics; artifact retention, search, backup, resource budgets, schema/client version negotiation, claim granularity, design packaging and extension loss/version lifecycle. The source's §29 decision register, §30 priority problems and §31 provenance distinguish **current code mismatches** from these future choices.

**First review gates:** resolve demonstrated core/Windows version and manifest/docs/tests mismatch on exact snapshots; establish a canonical semantic model **before** freezing host API/database schema; prove one typed, authorized, observable Run from notebook and a managed client; inject lost-ACK, permission change, client restart and artifact-finalization failures; only then choose physical deployment/retention contracts. Reopen this Science article when direct implementation evidence or an approved decision changes its claims.

**Related work:** [whole-system physical profiles](system-architecture-profiles-decisions-and-evidence-gates.md), [semantic ownership matrix](semantic-ownership-and-contract-boundaries.md), [cross-client behavior](../surfaces/semantic-portability-and-client-authority.md), [fault and assurance claims](../trust-and-assurance/system-quality-assurance-threats-and-failure-gates.md).
