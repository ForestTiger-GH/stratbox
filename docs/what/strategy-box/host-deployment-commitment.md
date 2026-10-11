# Host-based Strategy Box — admitted target operating capability

**Product Decision:** `PD-SB-HOST-2026-10-12-01`. **Authority:** direct developer/owner clarification of 2026-10-12, received within the existing continuous Knowledge Product Commission. **Status:** `PRODUCT_DIRECTION_ACCEPTED / PLANNED / NOT IMPLEMENTED`. **Target WHAT delta:** the Strategy Box host is necessary and planned, replacing the earlier purely conditional existence of a shared host. This is a product-scope commitment, **not** authorization to deploy a service, create repositories, select a host executable, invent platform manifests or claim host conformance.

## User outcomes and concrete target profiles

Strategy Box must be able to execute and manage common application semantics on a **host**, while client installations attach to that authority instead of each independently recomputing shared Case/Job/Artifact truth. Both of these target deployment arrangements are deliberately in scope:

| Admitted target arrangement | Host-side role | User-facing attachment | Product status and remaining design freedom |
| --- | --- | --- | --- |
| **Web-accessible host profile** | Strategy Box host runs in an addressable deployment and serves authorized application execution/state and Web access. | Browser via configured website/domain; Windows and Android clients may attach as permitted. | `PLANNED HOST PROFILE`; URL/domain provisioning, transport, real auth, installer, processes and first release workflow are open. |
| **Windows-managed host profile** | A host-capable Windows/AppDock installation supplies Strategy Box application authority. | A second, connecting Windows/AppDock installation can function as a client of that host, with host/client roles and installation states unambiguously separated. | `PLANNED HOST PROFILE`; one or two repositories, installer/package identities, binary/process layout and AppDock host declaration remain **UNDECIDED**. |

**Cross-client aspiration:** Windows, browser and Android should use compatible application *meaning* for any supported remote connection, with platform-specific UX. This does not assert that every connection/protocol/feature combination is already implemented or must appear in the first release. A Web-accessible installation must truly expose its browser experience at its authorized domain; the Windows-managed host profile need not be assumed browser-public by default.

**Host versus local:** direct Python/notebook analytic core remains usable without launching the host. Existing *local foreground* Windows execution is a separate current mode and may end with its GUI. When a host has accepted work, disconnecting **one client** is not equivalent to shutting down the host or cancelling that work. Exact Job durability when the **host itself** stops, recovery of effects, data-retention guarantees and which work can run without a client remain explicit follow-up Product Decisions, not implied exactly-once promises.

## Accepted outcome constraints (observable, technology-neutral)

- `HOST-O1`: a host-capable Strategy Box deployment provides an identifiable running application authority independently of any **connecting** client process.
- `HOST-O2`: the Web-accessible profile permits an authorized browser through a configured domain/site to read its permitted state and perform its supported operations. Compatible Windows/Android attachment is a planned profile subject to explicit client capability and authority.
- `HOST-O3`: the Windows-managed profile supports a host-capable AppDock installation and a distinct connecting Windows/AppDock client installation. Host and client may have separate packages or one role-selectable package; neither physical option is approved yet.
- `HOST-O4`: a client can identify which host owns accepted execution and results; client disconnects or process termination cannot silently change host-side outcome truth. User-visible state after a network outage must be qualified until refreshed.
- `HOST-O5`: domain computation and source interpretation remain in independent `stratbox`, not duplicated across hosts or clients. Host application lifecycle and permissions are distinct from external platform installation/node/session lifecycle.
- `HOST-O6`: a deployed remote/shared profile must check applicable identity, object access and consequential effects on its actual authority boundary. A navigational or display-only permission is insufficient.
- `HOST-O7`: unsupported/degraded connectivity, incompatible client contract, missing Artifact bytes and uncertain side effects have truthful observable outcomes rather than fabricated success.

These are **target obligations**, not test results. Tests must bind a concrete host configuration and installed clients; current Qt run and filesystem history do not satisfy them by declaration.

## Product decisions explicitly *not* made

| Open decision | Authority needed | Impact |
| --- | --- | --- |
| Physical `stratbox-application` package/repository; separately named host executable; one vs two Windows repositories or AppDock deliverables | Product owner and implementation maintainers | Release ownership, dependencies, deployment and host/client role packaging |
| Host state/durability SLA, storage model, authentication scheme, multiuser permissions and network exposure policy | Product owner, security and operations | Acceptance, data custody, incident and recovery guarantees |
| Browser and native Android first-release parity, which Windows profile is shipped first, remote access across node boundaries | Product owner and client owners | Supported client matrix, compatibility testing and delivery priorities |
| Exact AppDock lifecycle, host endpoint, remote attachment, manifest names and permissions | External platform contract owner and Strategy Box integration owner | Concrete operational integration; never inferred from Research |
| Cancellation, retry, effect reconciliation, background scheduler, concurrency and host-exit recovery | Product owner plus engineering/risk review | Job state and testable execution semantics |

**Exclusions:** no accepted OCI/SQL/HTTP/Qt stack, prescribed platform naming, public Internet exposure without authorization, mandatory all-in-one host UI, or guarantee that a Windows host and Windows client live in separate repositories. The selected Science and candidate HOW/LDD must implement these obligations without turning old Research architecture sketches into additional owner commitments.

**Reopen:** owner revises host requirement, valid platform contract contradicts packaging assumptions, validated workload/authority demands a specific split, or independently tested client-host behavior falsifies this target. **Publication:** this document is a product-direction record, not a release or security certification.
