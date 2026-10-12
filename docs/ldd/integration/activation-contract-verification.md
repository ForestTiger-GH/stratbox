# LDD candidate — activation, package binding and diagnostics conformance

**Status:** `CANDIDATE / NON-DEPLOYED`; this is a testable, public-safe design for a known cross-repository failure risk, **not** a new AppDock manifest, wire contract, host daemon, installer or Product Decision. **Scope:** existing Windows local surface and exact pinned AppDock interface versions. **Baselines:** `stratbox-windows@959e9c4`, public `AppDock@a4d87c6`; source-to-current-state audit evidence.

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


## Runtime continuity and interaction-negative extensions (source-first, no execution)

| Vector | Failure setup | Exact question and necessary verdict |
| --- | --- | --- |
| AX-11 | Kill the process between runtime-state JSON truncation and write completion | Does next managed startup classify existing corrupted continuity data separately from a genuinely absent state file, without falsely claiming domain Job loss or success? |
| AX-12 | Two active clients attempt concurrent runtime-state JSON read/modify/write | Detect conflict/lost updates or explicitly declare the single-writer constraint; do not claim atomicity for plain `write_text`. |
| AX-13 | Project a stale `active_job` or `clean_shutdown` hint after client termination | Treat as continuity projection, **not** an authoritative durable Job state or proof of cancellation/completion. |
| AX-14 | Construct `RuntimeInteraction` payload with fabricated `capability_refs` and `diagnostics_safe=true` | A successfully decoded DTO alone must not authorize a real effect; any dispatcher needs independently verified principal/resource/effect policy. |
| AX-15 | Round-trip a Windows state payload through exact external `RuntimeState 1.0` and Windows `RuntimeStateRecord` | Compare strict required fields, optional unknown fields, extensions, warnings and safe path redaction; report compatibility failures, not silent migrations. |

These are negative acceptance intentions derived from pinned [public contract code](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/src/appdock/contracts/runtime/runtime_state.py) and [Windows runtime-state consumer](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/session_runtime.py), **not an adopted live interaction API, executed test suite or confirmed host capability**. A Product Decision about shared authority and durability remains a prerequisite for stronger promises.

## Release provenance and local configuration failure vectors — AX-16..18

**Exact source-reliance boundary:** the pinned [Windows version helper](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/version.py) and [user config serializer](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/config.py) were executed with controlled inputs in [CI 38191345551](https://github.com/ForestTiger-GH/stratbox/actions/runs/38191345551). WEX-07..09 (real current Python code) **passed as characterization**; all AX-16..18 below are **conditional target acceptance proposals and UNEXECUTED**.

| Candidate | Setup or injected failure | Required future claim boundary |
| --- | --- | --- |
| AX-16 | Build/package is materialized without `.git`; `get_version_info` returns `unknown` | Installed binary/package/source provenance must come from an independently bound release identity and actual platform installation receipts; never manufacture `dirty=False` as attestation of a clean known build |
| AX-17 | Local Scenario form persistence receives a synthetic credential-like value, then a host client connects | Local saved form fields must be classified and scoped; secrets or unsupported fields must never enter cross-user sync, common Events, logs or machine tool projections merely because JSON serialized them |
| AX-18 | User config JSON is well formed but contains invalid number for `window.width` | Application startup must return a controlled, diagnosable configuration error or a specifically accepted recovery, with neither silent state loss nor a bare traceback presented as a successful startup |

**Responsibility and testing:** local user configuration belongs to Windows presentation unless a valid Product Decision admits a synchronization scope. A managed installation or external platform must attest package provenance only through its actually supported versioned contracts. Tests of installed app activation, native Windows OS paths and cross-principal confidentiality remain open. Neither an unknown Git SHA nor a synthetic unredacted local value proves an actual security incident. These vectors do not select a new host process/repository, transport or general settings schema.

## Schema-valid but authority-unproven handoff: AX-19..26 (2026-10-12)

**New primary evidence:** exact public AppDock `SurfaceActivation 4.0` and `Activation Context 3.0` Python decoders at pinned `AppDock@a4d87c643e620e54e04083d4d0b8d867513e7065` plus the existing local Windows entry consumer; see [direct Current HOW](../../current-how/appdock-activation-host-attachment-boundary.md). All eight are **PROPOSED / UNEXECUTED** future conformance scenarios, not defects demonstrated in a deployed platform. The trust model and binding provenance are deployment-owner responsibilities.

| Vector | Controlled setup | Falsifying observation / required scope-qualified outcome |
| --- | --- | --- |
| AX-19 | Supply well-formed Context 3.0 from an untrusted file outside the authenticated platform handoff | DTO decode is insufficient: an application-side authenticated host profile must reject untrusted origin or explicitly limit itself to an unauthenticated local development profile. Do not claim principal authority from parsing. |
| AX-20 | Set a nonempty invalid `generated_at_utc`, then a plausible but expired value | The inspected decoder checks nonemptiness, not timestamp parsing or age. Any target freshness requirement needs a separate owner, clock/skew policy, trust evidence and negative test. |
| AX-21 | Provide a syntactically correct but false `payload_digest` for a declared package | The inspected decoder only validates hex shape. Native package-byte verification and signed/attested provenance must be proven through the actual platform custody interface, if admitted. |
| AX-22 | Provide two bindings with the same `binding_id`, different package/version or environment | Determine whether the authoritative producer/manifest and consumer jointly reject duplicates; do not rely on the first-match helper as a security boundary. Inspect other platform validation paths before calling this a released-platform defect. |
| AX-23 | Add `available_route_groups` or set `activation.attach_mode` to an arbitrary string | Decoding of a route or attach hint must never grant execution, read permissions or host attachment. The chosen host owner must authorize each real action at use time. |
| AX-24 | Provide plausible `node`, `user` and `session` identifiers absent matching trusted session evidence | Treat decoded identity fields as metadata until a verified platform or application authority binds actor, audience, node and resource. |
| AX-25 | Declare `dedicated_server` with background launch and observe spawned process only | Require separate authenticated application-service readiness, live listener, Job/Run durability and client attachment receipts; a process launch result or manifest Boolean is insufficient. |
| AX-26 | Use a legal `explicit` working-directory policy or string-valued env override which passes DTO validation | Validate final resolved host path, sandbox/confinement, reserved variables and secret handling at the execution boundary; decoder strictness is a distinct weaker gate. |

**Readiness verdict:** AX-19..26 are a **candidate negative test catalogue**, `LCD_BLOCKED` for any actual remote/host/deployment integration until a Product Authority selects an executable trust/session/provenance contract, and **not** eight currently failed test cases. Native platform/Windows tests, authorization, byte custody, physical host and browser attachment remain independent evidence requirements.

## Connector Manifest shape versus semantic admission: AX-27..32 (2026-10-12)

**Primary owner limit:** pinned public AppDock `connector_manifest.schema.json` has external `$ref` dependencies; the frozen Windows JSON manifest is an application-owned declaration, not a signed or verified deployment. All tests below remain `PROPOSED / UNEXECUTED` on the genuine external schema resolver and installed platform. The limited required-field JSON-object comparison from Current HOW is not full schema validation.

| Vector | Fixture or challenge | Acceptance proof needed |
| --- | --- | --- |
| AX-27 | Run the actual AppDock JSON Schema resolver on frozen Windows manifest and all required external URNs | Report the exact schema revision, referenced schema set, parser version and failures; accept neither a missing-ref shortcut nor mere top-level field checks as full PASS. |
| AX-28 | Two distinct runtime binding objects carry the same `binding_id` but different package or environment | The semantic manifest validator must reject ambiguous logical IDs before a first-match consumer chooses an arbitrary binding; `uniqueItems` alone is insufficient. Repeat for source/package/surface logical IDs. |
| AX-29 | A `default_surface_id`, `package_ref`, `source_id`, `required_by_surface_ids` or `depends_on` points at a nonexistent target | Resolve references against the admitted graph and reject a dangling edge rather than silently dropping it. |
| AX-30 | Introduce a binding dependency cycle while maintaining distinct JSON objects | Prove the package/runtime graph validator rejects the cycle before environment materialization or execution. |
| AX-31 | Declare `supports_remote_attach`, `supports_delegated_jobs` or `dedicated_server` in a schema-valid manifest without an installed supported backend | A declaration cannot make an unavailable host listener, authenticated attachment, durable Job or user authorization real. Check each runtime gate separately. |
| AX-32 | Compare `stratbox 0.2.1` in the frozen Windows package declaration with a candidate installed package at another version | Record actual resolver decisions and distribution bytes/attested package ID, not just nominal `stratbox` import success; select supported dependency policy by owner. |

**Decision and implementation freedom:** public platform owns semantic graph admission and manifest schema registry; Windows distribution owns its declared package/activation requirements and package compatibility; Strategy Box application owner must separately admit host/session authority. Specific real package, host and auth implementations remain `LCD_BLOCKED` without product/external decisions. These six vectors prescribe no private connector implementation, runtime production edit or new Strategy Box host API.
