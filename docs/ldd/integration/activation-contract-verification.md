# LDD candidate — activation, package binding and diagnostics conformance

**Status:** `CANDIDATE / NON-DEPLOYED`; this is a testable, public-safe design for a known cross-repository failure risk, **not** a new AppDock manifest, wire contract, host daemon, installer or Product Decision. **Scope:** existing Windows local surface and exact pinned AppDock interface versions. **Baselines:** `stratbox-windows@959e9c4`, public `AppDock@a4d87c6`; source-to-current-state [audit evidence](../../../_mw/epochs-001-strategy-box-development/consolidation/coverage/WINDOWS-TESTS-PUBLIC-CONTRACT-BOUNDARY-2026-10-12.md).

## Governing authority and invariants

- **Platform owns** connector parsing/admission, environment materialization, package provenance, activation planning, node/session state and platform error semantics.
- **Windows surface owns** its manifest content, safe entry adapter, strict Context decoding, AppDock compatibility tests, application diagnostics and user-facing readiness representation.
- **Core owns** bank/macro domain operations; neither Windows nor platform manifest can grant analytics accuracy.
- Distinguish manifest `4.0`, surface activation `4.0`, Context `3.0` and each Python package version as **separate** compatibility axes.
- Failure of a required interface check blocks the **affected activation**; no silent fallback to a legacy schema or remote execution variant. Environment-ready is different from scenario-ready; a diagnostic `PASS` is not permission for a destructive action.
- No confidential credentials, internal extension data, technical tracebacks or unredacted remote paths in a shared error projection.

## Testable release and runtime contract

| Vector | Setup / injection | Required observation to verify | Status in pinned code |
| --- | --- | --- | --- |
| AX-01 | Parse real manifest through exact pinned AppDock validator | Version, identity, surface and package graph either admitted with reasons or rejected by stable issue | **Not executed**; a validator script exists in Windows |
| AX-02 | Local smoke test compares actual manifest `4.0` and `package_requirement` | Both assertions track admitted schema; no contradictory legacy field | **Known static failure** in pinned smoke assertions |
| AX-03 | Install and execute test suite on advertised Python minor versions | Tests load or dependency matrix explicitly narrows supported minors | **Known Python 3.10 `tomllib` gap** in pinned test |
| AX-04 | Remove required runtime binding | Surface exits with safely classified configuration failure | Present in source/unit assertions, not executed here |
| AX-05 | Change world or surface identity | Strict rejection with no application startup | Present in source/unit assertions, not executed here |
| AX-06 | Two distribution bindings in different environments | Reject mixed runtime graph | Entry source contains equality guard; test execution absent |
| AX-07 | Malformed digest and forged *well-formed* digest | Reject syntax; verify provenance separately against platform-owned bytes/receipt | Syntax-only test exists; byte attestation absent from inspected consumer |
| AX-08 | Invalid/unknown Context fields or legacy version | Deterministic failure; no hidden coercion to accepted version | Static tests exist; live runtime unverified |
| AX-09 | Diagnostic path fails after launch | Safe error projection and application readiness distinguished from node health; log reference kept under owning access controls | End-to-end failure injection absent |
| AX-10 | Request hosted or Android execution against local-only manifest | Clear unsupported capability, never guessed remote fallback | Target conditional; no declared remote capability in pinned manifest |

## Proposed gate sequence (conditional engineering HOW)

1. Build a pinned **version-compatibility matrix** from resolved published platform schema, implementation validator, active manifest and actual package source metadata. A prose-only conformance page is insufficient to establish schema validity.
2. Enforce static manifest-schema tests and internal assertions; distinguish mutually independent contract versions.
3. Run a Python-version matrix from the actual supported interpreter range. Dependency errors are **test failures**, not platform unsupported-feature findings.
4. Validate the manifest with a pinned real AppDock checkout via the existing explicit Windows contract-check script; record checkout SHA and installed package identity.
5. Run local activation/diagnostics in a genuine managed Windows runtime with negative Context, missing resources and corrupted-state probes; record execution/skips separately. A successful `--diagnose` remains distinct from successfully completing a domain scenario.
6. Report pass/fail for each level independently: **schema admission**, **binding and actual bytes**, **runtime activation**, **diagnostics**, **scenario effect**. A single aggregate `OK` cannot erase a failed higher-risk check.

**No requested new low-level signature or manifest field is admitted here.** The design constrains an implementation/testing discussion; final validators, supported interpreter versions, package-version policy and release conditions remain with the respective owners. For shared application authority or remote hosting, a separate profile-specific LDD and Product Decision are necessary.

**Reopen:** changed external contract revision, package graph, native Windows verification, actual host profile, accepted user requirement or a counterexample in fault testing.
