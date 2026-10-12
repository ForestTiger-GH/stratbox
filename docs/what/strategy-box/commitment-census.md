# Strategy Box Product Commitment Census — admitted direction and open goals

**Revision:** `PC-SB-2026-10-12-1`; **status:** `PARTIAL_AUTHORITY_BOUND / OPEN_CENSUS`. **Product:** Strategy Box banking/macroeconomic analytical core, application host and Windows/Web/Android client direction. **Authority boundary:** direct Product owner instructions received within the active project and the subsequent **explicitly accepted host Decision**; the ten recovered original questionnaire answers are **user-intent evidence** but do not automatically approve all Research implementations. The original annotated questionnaire text is available in the maintained [annotated goals owner](research-annotated-user-goals-and-open-admission.md), while the original DOCX binary has been declared **LOST** by the owner; its extracted text remains an unattested representation.

## Accepted present direction and provenance

| ID | Product meaning or maintained boundary | Current normative force | Consumers and unresolved implementation scope |
| --- | --- | --- | --- |
| `PC-SB-001` | Independent, directly callable `stratbox` owns bank/macro statistical methods, data normalization and neutral core utilities. | **BOUNDARY_ACCEPTED**, confirmed by project ownership and current code | Python notebooks, host executor and all clients; source/calc specifics owned by core |
| `PC-SB-002` | AppDock remains an **external managed platform** and owns its own installation/node/session capability; Strategy Box owns domain and application outcomes. | **BOUNDARY_ACCEPTED**; integration is actual version-scoped | Current Windows managed activation; future host/client AppDock contracts require verified capability |
| `PC-SB-003` | Common **host-based execution and application state** is necessary and planned. Two target deployments: **Web-host** attached by browser via site/domain and permitted Windows/Android clients; **Windows/AppDock host** attached by distinct Windows/AppDock client installation. | **EXPLICIT_PRODUCT_DIRECTION_ACCEPTED**, direct [PD-SB-HOST-2026-10-12-01](host-deployment-commitment.md) | [Host HOW](../../how/hosting/host-and-client-deployment.md), [Engineering Architecture](../../architecture/responsibility-allocation.md), [Host LDD](../../ldd/hosting/host-client-attachment-boundary.md); no shipped host |
| `PC-SB-004` | An analytic result and a host/desktop client's view must preserve the same statistical meaning without implementing banking calculations in each frontend. | **BOUNDARY_ACCEPTED**, with concrete cross-client behavior **PLANNED** | Versioned semantic contracts and host/client conformance; transport and renderers free |
| `PC-SB-005` | Windows/Web/Android product semantics should be portable while native GUI interactions can differ. | **USER-EXPRESSED DIRECTION**; host-side cross-client relationship now part of accepted `PC-SB-003` | Windows host/client supported profile; Android client feature set and release timing open |
| `PC-SB-006` | Breaking core/application APIs need not preserve old signature compatibility simply because there was a prior prototype; retained user data and artifacts have separate integrity/retention duties. | **PROJECT ENGINEERING CONSTRAINT / BOUNDARY_ACCEPTED** | Data import/legacy reading requires a separate decision; no automatic authorization to discard useful existing files |
| `PC-SB-007` | Public core/Windows repositories must provide generalized, environment-neutral extension contracts while retaining privacy of non-public implementations. | **PUBLICATION/ENGINEERING CONSTRAINT / BOUNDARY_ACCEPTED** | Every public research/WHAT/HOW/LDD/release or implementation change; no internal identities or private integration facts |
| `PC-SB-008` | Maintain a self-contained, source-conserving scientific and engineering Knowledge Product from Science through Current HOW, WHAT, HOW, Architecture, LDD and independent assurance. | **HUMAN COMMISSION ACCEPTED** for this Work Program, **not** an assertion of completion | Work owner `_mw/.../consolidation/`; all global preservation and release gates remain open |

## Original annotated user goals with *unsettled admission*

The ten-topic annotated user replies are primary **developer intent evidence**, separated here from Product Decisions. These rows prevent their disappearance from WHAT while explicitly leaving the developer's tentative wording, implementation cost and safety choices visible. They are **not** eight more automatic accepted commitments.

| Original topic | User goal / protected intent | Status of additional product obligations |
| --- | --- | --- |
| `U-01` | Organize numerous domain operations as discoverable human scenarios/cascades; permit Python/notebook and authorized machine use; explore structured Schemes. | `USER_GOAL / DETAILS_OPEN`: taxonomy, Scheme API, effect/actor admission and composition policy |
| `U-02` | Ordinary **local foreground** work may stop with its window; failures and significant partial progress should remain intelligible. | `USER_GOAL / PROFILE_BOUND`: do not confuse with newly planned host/client separation; host crash/recovery and cancellation guarantees open |
| `U-03` | Prefer simple, reliable growth of state, with fewer losses and avoid speculative infrastructure. | `USER_GOAL / DESIGN_CRITERIA`: exact data store, retention, reliability targets and cost budget undecided |
| `U-04` | Show non-file outputs in work chat; keep user-controlled files in Data workspace; tolerate missing/moved files with honest status. | `USER_GOAL / ARTIFACT_POLICY_OPEN`: permanent immutable storage/catalog or automatic recovery not implicitly required |
| `U-05` | Trusted team UX with legible participant labels and scoped shared problem notices, while technical diagnostics remain appropriately available. | `USER_GOAL / SECURITY_POLICY_OPEN`: public host authorization cannot rely on a nickname |
| `U-06` | The same domain capabilities should remain available from authorized Python, UI and machine clients. | `USER_GOAL / INTERFACE_CHOICE_OPEN`: no particular agent transport or universal action bus accepted |
| `U-07` | Web through a real website/domain and future remote-first Android companion are desired; native UI may differ. | `USER_GOAL` partly **promoted** by `PC-SB-003` to planned host/Web attachment; mobile native stack and delivery features open |
| `U-08` | Concurrent commands in different chats and a usable team workspace; visible status/errors and controllable work. | `USER_GOAL / EXECUTION_SCOPE_OPEN`: do not infer unrestricted parallel writes or that chat storage owns Jobs |
| `U-09` | Record when source files were actually acquired; preserve method and statistical evidence proportionately. | `USER_GOAL / SOURCE_POLICY_OPEN`: no mandatory global series catalog or indiscriminate permanent raw input retention |
| `U-10` | Keep meaningful task/data state where execution occurs; local device for local work, common host for hosted work. | `USER_GOAL` **aligned with admitted host**, but SQL choice, migration and retention still open |

## Decision boundary, target completeness and active questions

The Product host existence question is **closed positively** by `PC-SB-003`. Do not leave a stale question asking **whether** a host will exist. These questions instead remain for the Product owner, corresponding implementation owners and the external platform:

1. Which of Web-host and Windows/AppDock-host arrangements ships first, and which client features constitute a minimum supported slice?
2. Can a single `stratbox-windows` repository produce host and connecting-client deliverables, or do independent Windows code/release owners warrant two repositories? Separate **installations and roles** are target; separate **repositories** are undecided.
3. How is host application authority maintained after its own process interruption, worker crash, external-effect ambiguity and local-history import? What are accepted storage/retention and incident guarantees?
4. What authentication, membership, sharing, permission and browser exposure policies are approved for a publicly reachable domain and a Windows-managed host?
5. What does the exact released AppDock revision actually implement for host lifecycle, remote attachment and delegated work, beyond optional schema vocabulary?
6. Which first-release actions are available from Android, browsers and Windows clients, and what protocol/version/evidence is required before release?
7. Can the remaining independent Research→Science material accounting, blind Research Amputation, current code/test conformance be completed by authorized verifiers, with the original DOCX explicitly excluded as lost and its textual witness kept at reduced evidence weight?

**Non-goals of this census:** prescribing a DB or backend framework, formalizing Research hypotheses as decisions, inventing a host protocol or asserting shipped/migrated runtime. **Product completeness status:** partial; historical user acts beyond the actively bound inputs may require source recovery and future Product Authority. No whole-product acceptance or `LOSSLESS_PASS` follows from this document.

**Reopen:** new direct owner decision, new admitted input, source-carrying human document revalidation, tested host/client behavior, external platform published capability change or scope conflict.
