# Future client surfaces — user intent, capabilities and release decisions

**Status:** USER-EXPRESSED DIRECTION / CONDITIONAL IMPLEMENTATION; this is not an approved delivery scope, deployed product or authorization to create repositories. Related evidence-calibrated analysis: [semantic portability and client authority](../../science/surfaces/semantic-portability-and-client-authority.md). Existing [Windows Current HOW](../../current-how/windows-application.md) remains the only directly studied application surface.

## Intent now distinguishable from the older exploratory proposal

The later architecture research records **Web as an explicit desired user-facing product**, not merely a theoretical fallback for mobile portability. The preferred access mode is through a website/domain with simple, operator-provisioned accounts. **Android is a strong prospective remote-first client direction**: connect to a real host, view work and progress, submit allowed lighter scenarios, open results and receive relevant notices. A native full analytical Python runtime and advanced offline processing on the phone were discussed as hypothetical future options, not minimum-release requirements.

The user also suggested two separate future client repositories and shared interface components. The number and launch timing of repositories remain **implementation hypotheses**. Shared *semantics and design roles* take precedence over identical Qt/CSS/native widgets.

## Product capabilities that still require explicit admission

| Surface/profile | Evidence-supported intended use | Required preconditions | Unsettled choices |
| --- | --- | --- | --- |
| Existing Windows local | Run core analytic operations from a desktop GUI | Current pinned local runtime; improve correctness and persistence per accepted scope | Multi-run support, actual durable state and cleanup of build/version drift |
| Windows remote client | Act as one of multiple clients of the same host | Independently running host authority, authenticated session, artifact references | Whether and when to ship |
| Web browser | Dense workspace and tables, scenarios, shared history, status and permitted output download | Real host API, identity/TLS, server-side authorization, Run/admission/effect truth | First-release feature coverage, framework, deployment domain ownership |
| Responsive Web/PWA | Mobile-size access for read/status/light command operations | Same Web authority; honest stale/offline semantics | Push, install and offline caching eligibility |
| Native Android remote client | Lightweight companion with run/status/artifact operations | Authenticated remote host, semantic DTOs, OS integration | Native toolkit, notification policy, release scope |
| Native Android local compute | Possible future domain execution on device | Independent Python/mobile toolchain, resource/data/source/security profile | Whether demand justifies development |

**Critical distinction:** a source manifest or platform field expressing a possible host/client profile does not prove that a server process, APIs, session/identity transport, or mobile release is available. All unsupported profiles must be represented as unsupported/deferred rather than emulated.

## Common product meaning, distinct rendering

Clients should agree on operation identity, parameter/effect meaning, accepted Run ID, terminal outcome, progress truth, access-scoped artifacts and state revisions. They may use separate navigation, controls, file pickers, accessibility semantics and device preference storage. Identity must distinguish verified principal, member display name and device session; the display name alone is never an Internet credential.

Future machine and agent consumers are considered only as permissioned invocation channels, with no rights inferred from `actor_kind` or discovery metadata. Public Web access requires a real minimal security floor (TLS, credential protection, sessions, authorization and object-level file access); absence of self-service registration is compatible with these protections.

## Product Decisions still open

An authorized owner must specify the earliest useful Web workflow, Android companion scope and offline support, whether host execution persists after any client exits, node membership/visibility rules, data retention and recovery goals, supported connection/deployment modes, physical repository/package topology, and UX/performance/accessibility acceptance thresholds. Research recommendations for SSE, React/Expo/Compose/Flutter, local SQL, and a separate host repository are alternatives, not approved choices.

**Verification boundary:** no browser/Android application, real host, multi-client test, package build or publicly exposed authentication deployment is certified by this document. Reopen on direct Product Decision, real host slice, exact external platform capability change or device tests.
