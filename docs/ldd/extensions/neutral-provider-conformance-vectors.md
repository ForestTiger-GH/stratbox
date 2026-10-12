# Candidate LDD: neutral provider conformance and negative-case matrix

**Identity:** `LDD-SB-NEUTRAL-PROVIDER-CHECKS-01`. **Status:** `CANDIDATE / NOT IMPLEMENTED / NOT PRODUCT-ADMITTED`. This is a **source-faithful catalog of test intents**, not an approved public API, a tested implementation, a security certificate, or a direction to install any provider. It contains only environment-neutral labels. **Primary source:** dated future provider-contract original, blob `72b251d992c2b001c179a23d1bb1ac100f8e1d36`, sections 33–37. Exact code/wording is retained below to preserve diagnostic nuance. This candidate should be reconciled against the [Science of provider failure semantics](../../science/extensions/trusted-provider-conformance-and-false-success-threats.md) before any Product/Implementation admission.

## How to interpret and execute these vectors

- Test the **exact supported distribution, capability binding and runtime/deployment profile**, not an unversioned “plugin”.
- `MUST`/source `yes` here means **research-proposed blocking criterion** where declared, not already accepted product policy.
- A result of `FAIL` or `CONDITIONAL` must identify exact vector(s), observed failure class, effect knowledge and safe remediations. Do not infer a global `PASS` from one happy-path import.
- For destructive storage tests, use isolated namespaces and nonproduction fixtures; never run fault injection against user data.
- Separate static configuration and reference fakes from real backend integration, wheel-installed smoke and release provenance.
- Preserve `UNKNOWN`, `PartialFailure`, `PermissionDenied`, `Unavailable` and `UnsupportedOperation` as different outcomes; a false successful empty directory or network observation blocks conformance.
- A clean wheel/build/install and SBOM provide different evidence from domain correctness, object authorization and actual artifact publication.

## Core-neutral contract — 46 source-preserved checks

| ID | Requirement | Source priority |
| --- | --- | --- |
| ARCH-001 | Core imports plugin only through versioned entry point | MUST |
| ARCH-002 | Plugin imports only documented public core API | MUST |
| ARCH-003 | No monkey patch / `sys.path` mutation | MUST |
| ARCH-004 | Import has no external I/O side effects | MUST |
| ARCH-005 | Domain/business logic is outside infrastructure plugin | MUST |
| PRIV-001 | Public core contains no private implementation details | MUST |
| PRIV-002 | Public core has no dependency on named private distribution | MUST |
| DISC-001 | Stable unique plugin ID | MUST |
| DISC-002 | Versioned entry-point group | MUST |
| DISC-003 | Duplicate ID detected as error | MUST |
| ACT-001 | Installed plugin is not auto-authorized | MUST |
| ACT-002 | Managed activation is explicit | MUST |
| ACT-003 | Required plugin failure cannot silently switch provider | MUST |
| VER-001 | Plugin API version checked before activation | MUST |
| VER-002 | Core compatibility spec checked | MUST |
| VER-003 | No legacy alias compatibility in new API | MUST |
| CAP-001 | Capabilities declared before activation | MUST |
| CAP-002 | Conflicting singleton bindings fail explicitly | MUST |
| CAP-003 | Optional features are truthfully declared | MUST |
| ERR-001 | Errors never masquerade as successful empty results | MUST |
| ERR-002 | Partial failure represented explicitly | MUST |
| ERR-003 | Unexpected exception wrapped into stable provider error | MUST |
| OBS-001 | Structured event sink used for diagnostics | MUST |
| OBS-002 | Secret redaction tests pass | MUST |
| OBS-003 | Fallback/retry observable | MUST |
| HLT-001 | Plugin exposes static health | MUST |
| HLT-002 | Active external capability exposes readiness | MUST |
| HLT-003 | Health output is safe/redacted | MUST |
| CFG-001 | Production configuration is deterministic | MUST |
| CFG-002 | Sensitive fields marked and redacted | MUST |
| CFG-003 | Unknown keys rejected in strict mode | SHOULD |
| SEC-001 | Runtime dynamic package install forbidden | MUST |
| SEC-002 | Declared privileged side effects | MUST |
| SEC-003 | Destructive operations preserve contract guarantees | MUST |
| PKG-001 | Clean wheel build succeeds | MUST |
| PKG-002 | Clean wheel install succeeds | MUST |
| PKG-003 | Runtime assets are present in wheel | MUST |
| PKG-004 | No source-tree accidental dependency | MUST |
| TST-001 | Public conformance suite passes | MUST |
| TST-002 | Capability-specific fault injection passes | MUST |
| TST-003 | Production backend smoke exists privately | MUST |
| TST-004 | Concurrency behavior tested | SHOULD |
| SUP-001 | Exact deployment artifact identity/hash recorded | MUST for managed production |
| SUP-002 | Reproducible dependency set | SHOULD |
| SUP-003 | SBOM generated | SHOULD |
| SUP-004 | Build provenance/attestation | SHOULD |

## File/byte storage — 25 source-preserved checks

| ID | Test vector | Blocking if feature declared |
| --- | --- | --- |
| STO-001 | write → read byte equality | yes |
| STO-002 | empty file | yes |
| STO-003 | Unicode filename/path | yes |
| STO-004 | exists semantics for missing path | yes |
| STO-005 | empty directory ≠ unavailable backend | yes |
| STO-006 | permission denied distinct from not found | yes |
| STO-007 | stat fields coherent | yes |
| STO-008 | list empty directory returns success empty | yes |
| STO-009 | list backend outage raises `Unavailable` | yes |
| STO-010 | recursive mkdir semantics | yes |
| STO-011 | file delete semantics | yes |
| STO-012 | directory delete semantics | yes |
| STO-013 | recursive delete reports partial failure | yes |
| STO-014 | root destructive guard | yes |
| STO-015 | move file preserves content | yes |
| STO-016 | move directory does not delete source after partial copy | yes |
| STO-017 | `atomic_move` claim verified | yes |
| STO-018 | interrupted write does not publish committed artifact | yes where supported |
| STO-019 | stream behavior checked | yes if declared |
| STO-020 | checksum semantics | yes if declared |
| STO-021 | capability profile stable after activation | yes |
| STO-022 | backend timeout mapped correctly | yes |
| STO-023 | authentication failure mapped correctly | yes |
| STO-024 | retry/fallback emits structured event | yes |
| STO-025 | cleanup certification area | yes |

## Secret resolution — 10 source-preserved checks

| ID | Test vector |
| --- | --- |
| SECRES-001 | Existing secret resolves |
| SECRES-002 | Missing secret distinguishable from backend outage |
| SECRES-003 | AuthenticationRequired distinguishable |
| SECRES-004 | PermissionDenied distinguishable |
| SECRES-005 | Secret value absent from `repr` |
| SECRES-006 | Secret absent from logs/events/health |
| SECRES-007 | Secret absent from exception message after sanitization |
| SECRES-008 | Provenance may be reported without value |
| SECRES-009 | Managed runtime does not block on terminal prompt |
| SECRES-010 | Strict backend policy does not silently downgrade |

## Network policies — 10 source-preserved checks

| ID | Test vector |
| --- | --- |
| NET-001 | Canonical source identity preserved |
| NET-002 | Policy transformation deterministic |
| NET-003 | Query/fragment semantics preserved where contract requires |
| NET-004 | PolicyDenied distinct from connectivity failure |
| NET-005 | Timeout distinct from auth failure |
| NET-006 | TLS/certificate failure distinct |
| NET-007 | Sensitive URL/query redacted |
| NET-008 | Health can test route without leaking endpoint details |
| NET-009 | No direct private package import from core |
| NET-010 | Domain parsers do not know physical gateway route |

## Passive reporting contribution — 7 source-preserved checks

| ID | Test vector |
| --- | --- |
| REP-001 | Theme loads through generic addon contract |
| REP-002 | IDs stable and collision-safe |
| REP-003 | Addon does not contain domain calculation logic |
| REP-004 | Semantic role mapping complete |
| REP-005 | Missing optional font/resource fails predictably |
| REP-006 | Global default not silently hijacked in multi-plugin environment |
| REP-007 | Registry merge deterministic |

## Required adverse-case families beyond the table

The original also calls for injections of: dependency missing, incompatible/bad config, expired credentials, auth backend unreachable, permission denial, network timeouts and resets, partial streams/writes, malformed metadata, unsupported operation, primary/fallback outage, simultaneous requests, shutdown during work, restart after partial effect, corrupted configuration, unexpected provider exception and hung health backend. For destructive copy/move also inject: the Nth object fails to copy; destination digest mismatch; source deletion fails; cleanup fails. Each needs observable, fail-closed and reproducible outcome semantics.

## Candidate certification evidence

A test report should bind `capability_id`, `provider_id`, exact installed wheel/package hash, public API/contract versions, test profile, individual vector IDs, outcome, safe problem ID, known/unknown external effects, timestamp and test environment identity. Separate `core-contract`, capability-specific and `managed-production` profiles. In particular, **managed-production status requires live isolated integration** beyond public fake conformance and package provenance.

## Scientific and product boundary

This file preserves 98 explicit source verification vectors but does **not** prove all of the original source's architecture, configuration, lifecycle, concurrency, data-integrity or supply-chain propositions were losslessly transferred. A future public contract may refine IDs and levels without legacy-compatibility obligations, but must document reasoned dispositions rather than silently dropping safety-critical cases. Any concrete private deployment validation belongs to the authorized deployment owner outside public code and this LDD.

**Reopen:** admitted capability protocol and cardinalities, accepted runtime profile, direct service implementation, security review, real negative-case test results and owner-approved release criteria.
