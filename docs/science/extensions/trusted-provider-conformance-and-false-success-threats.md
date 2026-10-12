# Trusted provider conformance, false-success threats and release evidence

**Problem:** a separately distributed extension that provides storage, network, secrets or passive report styling is often assumed trustworthy once Python can import it. Which specific conditions make this assumption false, and what should a future neutral public conformance contract test? **Status:** research-qualified design, not an approved versioned plugin API, deployed conformance runner, certified provider or endorsement of any closed implementation. Primary 2026-10-07 research: future neutral provider-contract study. External primary standards: [PyPA entry point specification](https://packaging.python.org/en/latest/specifications/entry-points/), [PyPA project metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/), [NIST Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf), [SLSA](https://slsa.dev/spec/v1.2/).

## 1. Installed is not selected, selected is not ready

A package distribution's entry point advertises a component; it **does not authenticate, authorize or activate it**. The PyPA interoperability specification explicitly leaves conflict policy for duplicate names from different distributions to the consuming application. Therefore a future Strategy Box provider boundary may use versioned, consumer-owned groups such as `stratbox.plugins.v1` only as **discovery**, with a separate trusted selection and binding step.

```text
PRESENT IN ENVIRONMENT
 → DISCOVERED in package metadata
 → COMPATIBLE with the selected core/API
 → SELECTED by explicit deployment profile
 → LOADED and ACTIVATED with permitted configuration
 → required capabilities READY
 → invoked under current product operation authorization
 → outcome independently reconciled
```

Each transition can fail for a different reason. A user-visible green “plugin enabled” toggle is an inadequate substitute for this state machine. Static compatibility does not establish that a network route, secret provider or storage namespace is accessible; successful health ping does not establish that a destructive move preserves data.

A duplicate provider identity must fail before trusting discovery order. A singleton slot such as `storage.workspace` has **one deliberate binding** or a declared built-in policy. A multi-contribution catalog such as style presets can accept several named contributions with collision detection; it cannot silently let the latest imported package redefine a semantic default.

## 2. Neutrality is a two-way dependency rule

The public analytical core owns stable meaning, operations and neutral capability ports. A separately installed trusted provider implements environment-specific physical access **without redefining the domain Result, SourceSnapshot, Artifact lineage, approval or user-visible policy**. Conversely, product code must not import deployment-specific packages by name or include environment-specific address, credential or internal topological detail.

| Port or contribution | Appropriate role | Prohibited semantic escalation |
| --- | --- | --- |
| Byte-oriented FileStore | File operations, declared atomicity, path/scoping and precise errors | Owns canonical bank dataset or published Artifact identity |
| Secret provider | Resolves a scoped credential, safe unavailable/auth-required state | Emits credentials, prompts a headless worker or silently changes trust sources |
| Network policy/transport | Applies allowed route/TLS/proxy and returns precise outcomes | Changes canonical source identity or presents policy denial as source absence |
| Passive style resources | Contributes namespaced fonts/tokens/templates under separate presentation contract | Alters economic calculation or captures global format default without selection |
| Health/diagnostics | Reports safe capability readiness, partial fault and correlation | Leaks private internals into public status or falsely asserts data correctness |

This infrastructure boundary is different from future *domain extensions* and UI extensions. Arbitrary frontend JavaScript can exercise browser privileges; a domain calculator requires economic validity and source evidence; physical storage has effects and data-integrity concerns. One magic “plugin” interface covering all of them would erase necessary assurance distinctions.

## 3. An in-process provider is trusted code, not sandboxed code

A Python package imported in process can generally use the host process's privileges. Declared `effects`, `readOnly` or `networkRequired` metadata improves visibility but does **not** enforce OS-level least privilege. A future untrusted third-party ecosystem would require a distinct out-of-process/sandbox profile, restricted service identities, content isolation and protocol-specific authorization.

Managed deployment should choose exact distribution versions and artifacts, record hashes, use reviewed package origins and avoid dynamic `pip install` during normal running. A wheel's presence is weaker evidence than a clean-environment install, a reproducible pinned dependency set, a reviewed build provenance and a successful isolated live-backend test. SBOMs and attestations are evidence of supply-chain facts, **not proofs of numerical validity or permissions**.

## 4. The highest-value failures are semantic false success

| Injection | Dangerous false inference | Required explicit behavior |
| --- | --- | --- |
| Missing backend/read timeout during `list` | Empty directory / source contains no files | `Unavailable`, `Timeout` or `AuthenticationRequired`, preserving old state |
| Permission denial | File not found / safe no-op | `PermissionDenied` and no fabricated success |
| Source copy stops at item N | Partial destination is complete; remove source | Partial failure, preserve source, record actual copied objects |
| Unsupported atomic move | Copy then delete is “equivalent” | Declare weaker semantics or return `UnsupportedOperation` |
| Secret store outage | Read from a less trusted fallback transparently | Required binding fails readiness; permitted fallback separately configured and observable |
| Invalid network route/policy | “Official source has no records” | Policy denial separated from source-state claims |
| Remote write commits before ACK loss | Failed means nothing happened; retry destructive action | `OUTCOME_UNKNOWN`, reconcile exact effect before repeat |
| Unexpected provider exception | Generic user traceback with tokens/paths | Stable safe problem ID plus access-restricted sanitized trace |
| Second provider with same identity | First one selected by random import order | Duplicate ID blocks selection; explicit singleton binding required |

Partial/unknown outcomes are especially important because a storage provider's API can return “success” long before an analytic artifact is actually verified or published. FileStore primitive semantics and Artifact publication are two separate layers.

## 5. Health has levels and privacy classes

At least three distinct checks have different semantics:

- **Static**: version compatibility, importability, schema shape, declared required contracts, public API dependencies. No network or secrets read during discovery.
- **Connectivity/readiness**: safe non-destructive access to a required namespace or service with permitted credential context.
- **Isolated deep roundtrip certification**: in a bounded test namespace, write/read byte equality, list, stat, rename/move if supported, integrity check and cleanup.

Run the third explicitly with appropriate permission. A normal startup readiness probe should not create/delete arbitrary business files. Statuses such as READY/DEGRADED/NEEDS_ACTION/NOT_READY/UNKNOWN need a particular capability and safe action hint; no internal endpoint, secret value or private path is necessary in the default public health response.

Provider concurrency declarations also require tests: `THREAD_SAFE`, `SERIALIZED` and `PROCESS_LOCAL` have distinct object lifetimes. A process-local connection must not assume an in-memory shared singleton across worker processes. An asynchronous facade cannot fix unsupported backend serialization without a real adapter guarantee.

## 6. Certification as profile-specific evidence

Certification should answer *which contract is established* under *which version and environment*, not award a single prestigious score.

| Profile | Required evidence | Cannot conclude |
| --- | --- | --- |
| core-contract | Side-effect-free discovery, stable unique ID, compatibility, activation, typed errors, redaction, shutdown | Storage integrity or live backend readiness |
| capability-storage | Byte equality, Unicode paths, missing/empty distinctions, safety guards, partial-write/move fault injection | Network/secret provider validity |
| capability-secrets | Resolved/missing/auth-required/unavailable distinctions, no logging/serialization of values | That every consuming operation uses appropriate scopes |
| capability-network | Source/URL identity preservation, route denial vs outage, TLS, redaction, deterministic transform | Correctness of downloaded financial statements |
| capability-reporting | Namespace merge, semantic role coverage, missing font behavior, deterministic effective style | Faithfulness of upstream economic claims |
| managed-production | Clean wheel install, exact hashes, trusted selection, required readiness, isolated production-backend smoke and release controls | Universal security or statistical assurance |

A machine-readable report can return `PASS`, `FAIL`, or `CONDITIONAL` **for a named profile and tested exact artifact** with individual blocking checks. “Bronze/Silver/Gold” would hide missing capabilities and make cross-profile comparisons misleading.

The original investigation enumerates a large concrete verification space: **25 storage vectors**, **10 secret vectors**, **10 network vectors**, **7 reporting vectors**, generic import/activation checks, a 20+ case fault-injection matrix, supply-chain and concurrency probes. Those inventories are preserved as specific test families here; they are **proposed**, not executed. When implementing a conformance harness, transfer every original test ID as its own exact executable or documented acceptance vector; do not replace 25 distinct storage cases with one smoke check.

## 7. Verification ownership and isolation

A public synthetic reference provider and fake backend suite allow reproducible core contract tests without access to organization-specific infrastructure. Independently, the provider's deployment owner runs isolated private integration, fault injection and managed installed smoke against an exact release, sharing only appropriately redacted conformance outcomes with the public consumer.

A provider may pass interface conformance while still yielding an invalid bank calculation due to upstream source schema changes. The domain Operation must validate its own inputs and semantic outcome. Conversely, domain correctness cannot repair a provider that silently loses bytes under a fallback move. Both proofs are necessary and neither should impersonate the other.

## 8. Open design choices and stopping conditions

Open: whether native entry points should be the single discovery path; whether provider methods are synchronous or support separate async contracts; what cardinality applies to each capability; which backend guarantees are mandatory; the versioning strategy for different contribution families; the exact isolation level and package attestation rules; and what Product owner authorizes each profile. No automatic legacy compatibility needs to be preserved for a newly approved version.

A general extension contract should be implemented only when at least one real consumer and failure profile justify its cost. Avoid empty catalog systems, global runtime plugin installers, implicit provider precedence, generic fallback that weakens security or domain correctness, and UI controls that pretend to manage deployment.

Related Science: [provider discovery and bindings](provider-discovery-binding-readiness-and-conformance.md), [extension configuration](configuration-catalog-readiness-and-surface-boundaries.md), [source and result failures](../execution-and-diagnostics/causal-observability-and-failure-truth.md), [artifact publication](../artifacts/output-identity-publication-and-availability.md), and [machine capability contracts](../capabilities/compiled-domain-capabilities-validity-and-deoptimization.md).
