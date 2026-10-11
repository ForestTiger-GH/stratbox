# Strategy Box — purpose, boundaries and operating profiles

**Product baseline:** `TW-SB-2026-10-09-CANDIDATE-1`. **Status:** `BOUNDARY_ACCEPTED` for the established mission and component responsibility boundaries; expanded functions and deployment promises are **not** automatically admitted.

**Current Product Decision override (2026-10-12):** Host execution is now **admitted and planned** for both Web-accessible and AppDock-managed Windows-host arrangements. The full [host deployment commitment](host-deployment-commitment.md) supersedes only earlier *host-existence* conditional wording. Physical services/repos, host-exit continuity and precise security/retention policies remain open; no host is yet implemented.

## Purpose

Strategy Box supports analysis, verification, modeling and presentation of **external banking and macroeconomic statistical data**. Its principal users and collaborators include financial analysts, domain-operation developers, client-application users and operators of a managed working environment. The intended analytical path is from an identifiable statistical publication and structured input data toward a qualified result whose source, method, assumptions and limitations remain intelligible.

## Present owners versus conditional product scope

| Component / operating profile | Admission | Responsibility |
| --- | --- | --- |
| `stratbox` analytical core | `BOUNDARY_ACCEPTED` | Banking/macro domain methods, transformations, canonicalization, neutral infrastructure ports and registries. |
| Windows application and surface | Separate ownership `BOUNDARY_ACCEPTED`; particular features `CURRENT_OBSERVED` | Discovering and composing user scenarios; mediating interactions with core analytical operations. |
| Managed-platform integration | Existing desktop activation `CURRENT_OBSERVED`; future profiles `CONDITIONAL` | Consume verified external installation/session/runtime context, without inventing ownership of the external platform's lifecycle. |
| Portable semantic application/surface concepts | Reuse direction `BOUNDARY_ACCEPTED`; specific common modules `CANDIDATE` | Define platform-neutral meaning separately from each platform's rendering and device-specific adapters. |
| Future Android companion | `CONDITIONAL` | Potential remote-first client; actual release features, permissions and local-compute support remain open. |
| Web and shared host | `PRODUCT_DIRECTION_ACCEPTED / PLANNED` | Host is necessary; Web-accessible and Windows-managed host profiles are target; remote interfaces, reliability and security details require engineering and policy decisions. |

The existing desktop implementation is established by its source code and tests at an exact revision, not by aspirational statements in this Target WHAT page.

## Responsibility boundary

Subject-matter correctness and statistical computation belong in the independent core. User-directed composition, execution lifecycle and capability availability require an application authority appropriate to each **actually deployed** profile. The host authority is a planned Target WHAT obligation; its physical implementation, durable storage and host-exit continuity remain open. The external platform governs only the capabilities in its own verified versioned contracts; Strategy Box owns its side of those integrations.

Authorized machine/AI consumers may become **clients of scoped capabilities** under appropriate identity and permission checks. Their possible existence is not evidence that a machine interface has already shipped or that the core's domain architecture must be driven by an AI framework.

## What this baseline does not promise

- A particular server framework, physical application-service process, distributed queue or new repository. The **host capability itself is planned**.
- Production Web/Android release, fully autonomous mobile execution or implemented remote host access.
- Quantitative SLO, RPO, RTO or performance guarantees without tested workloads and Product decisions.
- Automatic atomic durability for every current output, permanent retention of all source files or approval-free destructive actions.
- Automatic promotion of any helper, research proposal, integration, third-party extension or AI feature into an available public capability.

**Acceptance boundary:** the target mission and separation of responsibilities are sufficiently stated for continued design; full Product commitments require admitted profiles and observed acceptance criteria. This identity page is not a complete product specification.
