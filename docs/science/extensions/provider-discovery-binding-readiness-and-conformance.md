# Provider discovery, explicit binding, readiness and extension conformance

**Domain:** a versioned, platform-neutral extension boundary for statistical-data, storage, secret, report-style, format and execution capabilities without confusing an installed Python distribution with an authorized, healthy business operation. **Status:** evidence-qualified technical Science. The target lifecycle, descriptors and tests below are *candidates*, not a released extension SDK, accepted security tier or certified provider framework. This article describes only public, general-purpose interfaces; no closed implementation is a source of public application semantics.

## 1. The current seam, observed limits and non-evidence

At the [pinned core implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/runtime.py), Python package entry-point discovery can select infrastructure provider implementations for filesystem and secrets. Error handling can warn and fall back to local providers, and with multiple candidates may use the first successful one. Discovery, explicit policy selection, activation, readiness and grant evaluation are not a common verified lifecycle. The [Excel style discovery path](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/styles/excel/plugin.py) independently aggregates style contributions and can suppress errors into an empty result. These are dated public-code observations, not installed package or runtime compatibility tests.

The [pinned Windows registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/registry.py) manually lists three subject actions and marks eligibility with static metadata. Fields such as `enabled`, `ai_visibility`, `dangerous` or an importable handler are **descriptors**, not live source availability, consent or per-principal permission. The [background process store](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) is an in-memory state facade, not evidence of a durable scheduler.

The studied packaging graph had core distribution metadata `0.8.0` while a Windows dependency/manifest expected `0.2.1`; this is **declared version drift at the dated revisions**, not a completed clean-install failure test. A working Python import, an advertised plugin feature, a green process indicator and a shell menu entry individually prove neither semantic availability nor safe effect authority.

## 2. Five logical catalogs and eight independent capability gates

| Logical plane | Owned truth | What another plane must not infer |
| --- | --- | --- |
| **Definition catalog** | Stable domain Operation/Capability semantics, typed contracts, effects | A discovered provider has already implemented the definition |
| **Contribution inventory** | Packages/descriptors discovered with source, version and claimed slot | Selection, installation trust, activation or readiness |
| **Selection/Binding register** | Chosen provider for each slot/profile with validation and provenance | Current authorization for every user's effect |
| **Availability projection** | Dependencies, credentials, Data/source status, backend support and reasoned readiness | Permission for a particular principal or output target |
| **Authorized catalog view** | Actions the actual caller may see/request in its context | Ultimate approval or effect confirmation |

An illustrative `invocable` decision needs all of: a compatible definition; a validated binding; required providers ready; typed parameters; source/registry applicability; required backend features; current principal/object/effect authorization; plan-bound approval where necessary; and available resources or an explicit queue policy. Client UI may separately show `discoverable`, `visible`, `selectable`, `ready`, `permitted`, `needs_approval`, `queueable` and `executable_now`. One Boolean `enabled` loses critical reasons.

These are *logical roles*, not five databases or independent services. A modest single-process implementation can compute them from stable descriptors and verified bindings while retaining different authority for each field.

## 3. One package can contribute different, differently trusted things

| Contribution type | Contract owner | Distinct admission/conformance concern |
| --- | --- | --- |
| **Infrastructure service provider** | Public FileStore/network/secret ports and managed activation | Backend read/write/rename semantics, error, secrecy, lifecycle |
| **Source contribution** | Source discovery and source-specific validator | Authority, exact publication identity, freshness, schema, no credential leakage |
| **Reference/registry contribution** | Domain registry governance | Effective date, provenance, aliases/overlays, conflicting definitions |
| **Domain Operation contribution** | Named algorithm/semantic release owner | Financial/measurement meaning, typed Request/Result, evidence, effect and review |
| **Artifact style provider** | Artifact formatting/renderer contract | Declarative fonts/tokens/palette/templates, supported formats and safe fallback |
| **Format adapter** | Data/file codec owner | Read vs write capability, streaming, encoding, loss, hostile archives |
| **Execution backend adapter** | Application execution authority and backend port | Locality, isolation, start/stop proof, leases, output staging, fencing/reconciliation |

A common descriptor envelope can carry `extension_id`, version, declared contribution IDs/slots, required contract versions, distribution/source/owner and dependency/permission declarations. Its *typed per-kind profiles* remain separate: a font resource cannot fulfill a secret-provider slot; a parser codec cannot claim authority to revise a bank's accounting definition. Publishing a third-party domain operation should demand stronger semantic ownership and validation than admitting a non-executable style set.

**A powerful extension is not automatically a sandboxed extension.** Trusted in-process Python executes with the host interpreter's privileges. A truly untrusted provider needs an independently designed out-of-process restriction, OS-level rights, IPC and threat model. Merely labelling a provider `untrusted` in JSON does not isolate it. Physical placement (in-process, isolated subprocess, remote endpoint or declarative data-only) and contribution type are orthogonal.

## 4. Stages from package to usable capability

```text
PACKAGE_AVAILABLE
   → DISCOVERED (metadata read only; no provider startup effects)
   → DESCRIPTOR_VALIDATED / INVALID_DESCRIPTOR
   → COMPATIBLE / INCOMPATIBLE
   → SELECTED / NOT_SELECTED
   → AUTHORIZED_TO_ACTIVATE / BLOCKED
   → ACTIVATING / CONFIG_REQUIRED / AUTH_REQUIRED / ACTIVATION_FAILED
   → BOUND (resolved exact provider implementation and profile)
   → READY / DEGRADED / NOT_READY / REVOKED / REQUIRES_RESTART
   → INVOCABLE only after live operation/person/resource authorization
```

Names and transitions above are illustrative. Distinguish **static compatibility** (declared API and package versions), **actual activation** (provider instantiated, config/secrets resolved), **health** (a live backend check), **capability-specific readiness** (e.g. safe write supported under the selected root), and **principal permission** for a concrete operation. Passing a Python import or a network connectivity check does not prove an atomic file replace or permissible delete.

**No side effect during discovery** is a valuable test property. Module import in Python can run arbitrary code, so production discovery should prefer static package metadata with explicit activation after trust checks. A failing optional style contributor can be marked unavailable without hiding all other styles; a required storage/security binding failing in a managed profile must not be transformed into unrelated “local success.”

## 5. Selection: deterministic merging versus single-owner slots

Two slot families call for different algorithms:

- **Singleton service slot:** one explicit resolved provider per activation profile. If multiple candidates exist, selection follows an approved pinned binding with stable validation, not enumeration order or “first that did not throw.” Missing, incompatible or ambiguous required provider means a typed failure and withheld effect.
- **Mergeable contributions:** separate versions of styles, sources or operation descriptors can coexist *if* every published contribution has a stable namespaced identity and deterministic, conflict-detecting merge. Duplicate IDs with incompatible definitions are an error; silent last-writer override makes Work irreproducible.

Record an immutable `BindingSnapshot` with package identity/version, selected provider, provider API/slot version, validated descriptor digest, activation profile/policy revision, relevant configuration/secret **references** and known capability condition. Never include secret values in a Run, browser descriptor, trace or workbook metadata. If the active package set changes, new managed admissions must be re-resolved; an already-running Run retains its prior binding identity and should not silently switch implementation.

A fallback is allowed only if the replacement **actually satisfies** the required semantic, authorization and effect guarantees. A backend that implements `rename` as copy-then-delete is not interchangeable with proven atomic replace. A valid optional read-only local profile differs from a managed write profile; the UI must display that different promise.

## 6. Capability conformance differs from descriptor validation

A bounded reference conformance suite should use **synthetic** provider packages with deliberately successful, malformed, duplicate, missing, incompatible, unauthorized and crashing implementations.

| Test class | What a valid result demonstrates |
| --- | --- |
| Descriptor schema | Stable IDs, exact contract version, no invalid aliases/undefined slots |
| Side-effect-free discovery | No network/file/secret use merely to enumerate metadata |
| Deterministic binding | Reversed entry-point order produces the same selected binding digest |
| Collision | Duplicate style/source/operation ID rejected with safe typed diagnostic |
| Optional vs required | Required inactive provider blocks risky operation; optional absence only degrades permitted features |
| Provider health | Import succeeds yet write probe fails: report `NOT_READY`, not success |
| Backend guarantees | Atomic rename, CAS, directory semantics and multi-part behavior checked on actual supported provider |
| Isolation/trust | No false claim that an in-process arbitrary library is sandboxed |
| Typed failures | Auth denied, missing resource, unsupported, timeout, partial, ambiguous effect remain distinct |
| Version/binding changes | Running Run pins old binding; new Run re-evaluates active contract |
| Public safety | Catalog/trace reveal no secret, internal path or restricted implementation |
| Release graph | Core/Windows/distribution/manifest requirements agree under clean-install tests |

These are **proposed tests**, not results. Tests must exercise the actual runtime/storage profile, not rely solely on descriptor metadata.

## 7. Domain, data, styles, machine exposure and effects

A source adapter can contribute a publisher locator and fetch/validation logic, but cannot declare arbitrary obtained bytes authentic solely because the URL looks official. Reference registries and source catalogs are distinct; a human overlay cannot silently override an official classification snapshot. A format adapter may read DBF but lack safe write/reversibility; capability classification must state that asymmetry.

For styles, declarative report profiles can supply versioned typography, color palette and semantic document roles, plus approved metadata such as document author. The **UI theme** is separate from the **exported file style** and neither can change source numbers or grant a write. Direct code injection into Qt widgets, arbitrary shell-navigation modification and unrestricted postprocessing are separate, unapproved extension surfaces. An author metadata field is not the verified causal principal who produced the file.

A machine projection should expose the already curated domain Operation, its type/effect requirements and permitted scope through a separately versioned protocol adapter. Machine visibility is **not execution permission**. An AI-generated PlanDraft must pass deterministic ID/version/type/rights/effect checks under a real principal; retrieved documents are data, not instructions that can enlarge privileges. A tool result that says “done” is not an Artifact receipt or Work acceptance.

## 8. Twenty-five source conflicts, thirty-two gaps and candidate gates

The dated `03` capability/automation synthesis registers **25 conflict identities (CF-01–CF-25)**. Their semantically important groups remain explicit:

- **CF-01–06:** technical Command, automatic Scenario per helper, background/assignment kinds, Scheme vs Cascade, Case vs Work have differing identity rules. Separate definition/projection/execution; do not mandate five engines.
- **CF-07–10:** Qt single-run, in-memory pseudo-background, external platform scheduler and unproven remote host; independent authorities and tested process lifetimes.
- **CF-11–16:** installed provider vs activated, first-found selection, implicit fallback, different contribution trust classes, style default provenance, arbitrary UI code injection. This article's lifecycle and conformance address their logical causes, not actual implementation.
- **CF-17–21:** AI visibility vs permission, separate AI engine vs shared admission, MCP serialization vs domain meaning, source vs operation catalog, raw bytes vs result/artifact.
- **CF-22–25:** source/repository count vs real lifecycle, public-neutral supply, Job completion vs accepted analytical result, and nested retry budgets.

The study lists **32 unresolved questions (U01–U32)**. These include headless imports and two real operations; schema roundtrips; exact capability/grant matrices; whether third-party domain operations are justified at all; per-contribution profile vs a giant descriptor; durable Automation/Run/Binding owner; revoked approval, frozen binding and ambiguous effect; machine composition IR; normalized applicability reasons; timezone/DST/misfire; per-node quotas; trust/isolation; host repo; CSS/Qt/UI scope; and safe one-time user history transfer when old APIs are retired. They are not resolved by naming an SDK.

Its **32 candidate CX invariants** cover pure core import, no discovery effects, binding determinism/collisions/fail-closed, machine and AI safety, automation occurrence identity, effect uncertainty, style versioning, immutable binding, package contract drift and cross-client shared state. Treat them as **future conformance criteria only**; no integrated host or general external extension suite was run.

## 9. Physical architecture and reopening criteria

Logical responsibilities: domain core owns statistical semantics and neutral service ports; application owns capability visibility, operation admission, product scheduler, effect safety and Work/Run truth; deployment platform supplies packages/Node/Session/verified activation and process health; Windows/Web/Android are presentation/protocol consumers; extension owners maintain their own code or declarative resources.

A new shared package, process or repository is justified only by actual independent consumers, delivery lifecycle, trust boundary or performance constraint. A small first pilot should bind a real read-only source operation, a file-producing export and synthetic providers under clear version/permission/failure tests **before** implementing arbitrary user-installed operations or a general extension marketplace.

**Open Product/Engineering decisions:** slot taxonomy, binding policy, trusted/isolated execution profiles, allowed contribution categories, semantic operation admission authority, full cancellation/renderer contracts, package supply and update boundaries, physical persistent storage, external platform capability revision, and user UX for unavailable extension features. Later evidence should reopen this research at exact core/Windows code revisions, successful clean-install conformance, revised platform adapter contracts and measured workloads, not merely because a new entry-point package appears.
