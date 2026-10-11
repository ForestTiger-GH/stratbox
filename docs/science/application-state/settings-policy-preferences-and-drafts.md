# Settings, managed policy, drafts and immutable invocation parameters

**Problem domain:** configuration often appears as a single “Settings” page while its entries have incompatible owners, lifetimes, sensitivity, synchronization and recovery. This article distinguishes state semantics, not current UI sections, accepted setting names or a universal platform configuration API. **Status:** proposed portable model with direct current Windows limitations and explicit open Product Decisions.

## 1. Settings is a label, not one authoritative object

| State category | Examples | Ownership and intended persistence | Failure semantics |
| --- | --- | --- | --- |
| **UserSettings** | Theme/accent, default output reporting profile, author metadata preference, semantic notification choice | User-scoped durable, optionally synchronized after an approved policy; small versioned config may suffice | Invalid entry can be rejected or safe default offered without erasing accepted Work |
| **SurfaceState** | Window geometry, active tab, scroll, pane width, focus | Client/device-specific convenience; reconstructible or local small file | May reset with visible notice |
| **DraftState** | Unsubmitted Scenario parameters, unfinished message, working notes | User/device/Thread scoped; sensitive values excluded and expiry/version applied | Reject stale schema rather than silently execute changed effects |
| **RecentState** | Last visited Work/Artifact, local filter/picker | Device preference/cache | Regenerable; must not change Work |
| **ManagedPolicy** | Allowed operations, data scopes, retention/quota, delegated grants, forced UI restrictions | Versioned deployment/Workspace/Node administrator or trusted platform policy owner | Denial/forced value is authoritative, not a mutable user default |
| **RunParameters** | Actual period, source, output target, optimization method, partial-failure policy | Immutable effective input admitted into a specific Run or Attempt | Previous Run must not change when preference changes |
| **AutomationSettings** | Timezone, trigger, misfire/overlap, enabled, authorized run-as | Durable revisioned Automation authority, not a local checkbox | Disabled rule stops future occurrences, not a previously admitted Job by default |

A default report author is not the same as the authenticated requester, executor, Work owner or publisher. A preference for that metadata can influence an output under a permitted policy, while the *actual resolved value* used in the Artifact must be recorded. The visual user-interface theme is likewise distinct from a versioned `ArtifactStyleSet` used by an XLSX/PDF renderer.

The current pinned [Windows user config](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/config.py) combines window, shell, chat, last scenario/workspace and scenario-form values in `app.json`. Its invalid JSON raises `AppConfigError`; separate history JSON uses a different silent-empty failure path. These are dated code facts, not proof of intended cross-device synchronization or a safe unified store.

## 2. Effective values need an explicit precedence contract

A possible conceptual resolver is:

```text
Product default
    + approved Workspace default
    + optional UserSettings
    + non-bypassable ManagedPolicy constraints/forced values
    → EffectiveSetting(value, source, editable, allowed_values, explanation, restart_required)

Scenario/Composition definition + approved preset + explicit invocation
    + current grants/capabilities and semantic validation
    → frozen RunParameterSnapshot with version and provenance
```

This formula is **not** a license to merge JSON dictionaries blindly: `forced policy`, `allowed range`, `inherited` and `user_override` require distinct resolution rules. A user-facing disabled setting should state which authority controls it, why it is locked and what permissible alternatives remain. A value omitted in an older config should not silently become a privileged authorization.

At Run admission, the application resolves actual parameters, checks schema versions, source/registry/binding availability, active policy and effect class, and seals the parameters relevant for scientific reproducibility. UI remembered values or a mutable personal preset are proposals until verified and admitted. A later update to a default cannot retroactively modify the historical numerical result of an earlier bank-statistics Run.

## 3. Physical storage requirements are proportional

A tiny local preference with no shared writer can be held in validated versioned JSON with temp write, adequate flush and an atomic replace **only if** the chosen filesystem and deployment guarantees are proven. The state writer may use a separate managed user-private directory offered through actual platform activation. This has a weaker operational burden than a shared Node Work store.

A volatile tab selection needs no server transaction. A shared automation with two editors needs revision conflict detection and permission checks. An immutable Run input snapshot needs a stronger guarantee than a forgotten sidebar width. If two devices update one durable preference simultaneously, server revision/known conflict or an explicitly allowed last-write policy is needed; their unsynchronized local wall clocks are not a trustworthy order. Cosmetic display values may tolerate last-write-wins; retention or effect safety policies generally may not.

Do not store credentials, raw headers, passwords or sensitive absolute paths in widely visible preferences or share them with every client. A Run/Automation record can carry an opaque secret reference, while actual credential value follows an authorized secret provider's lifecycle. Rotation/rebinding after a long-running job must preserve semantic meaning without leaking raw secrets to historic manifests.

## 4. Cross-platform synchronization is selective

A theme/accent or report-style preference may be useful across Windows/Web/Android, but platform-specific geometry, Android notification permission, browser clipboard and native file picker paths do not belong in a common DTO. Some drafts may be too sensitive or structurally tied to one GUI version to synchronize; opt-in per-Work drafts can be a controlled shared document with ACL and revision.

Client offline settings edits must not alter a server Work, Artifact or automation. A reconnect may revalidate a draft against updated Scenario schema and current rights. A resettable UI layout and a sealed Run/plan must never share a uniform “overwrite” operation.

## 5. Extension configuration is a third trust boundary

A generic extension package descriptor, validated Provider, activated binding and user preferences are distinct. A `PluginDescriptor` names declared slots/resources/dependencies and version; a `ProviderBinding` selects a permitted implementation for the actual environment; provider data may have a namespaced validated schema. Installing an extension does not imply activation or permission to run effects, and configuring a palette does not grant access to financial source files.

For style/template extensions, distinguish `user`, `workspace`, `node` and `managed` scope; validate resources, source/version/provenance and actual renderer support. These are generic public capability conditions and contain **no proprietary/private implementation details**. A change to a style provider should not silently change analytical method identity, nor should a catalog entry bypass authorization.

## 6. Negative and counterexample tests

| Case | What should remain true |
| --- | --- |
| Corrupted `app.json` | Clear user-visible config diagnostic, not destruction of Work/Artifact history |
| Window resized on one device | No change to another user's shared Work status |
| User changes default reporting period | Previously accepted Run retains exact earlier period |
| Policy disallows a destructive effect | Cosmetic setting or prepared preset cannot override it |
| Two devices edit accent | Deterministic documented conflict/resolution without changing node policy |
| Two operators edit an Automation schedule | Expected revision and occurrence version protect against duplicate Runs |
| Scheduler enabled without a worker | UI cannot imply currently running Job |
| Browser saves sensitive draft and user logs out | Defined expiry/deletion and access boundary |
| New Scenario schema removes a parameter | Offline draft cannot execute an unsafe old command automatically |
| One output has a corporate metadata author and another executor | Both identities remain distinguishable |
| User theme changes during a report | Numerical content and evidence do not mutate |
| External style provider missing a declared font | Explicit fallback/validation, not fake exact appearance |
| Extension installed but denied | “Installed” distinct from “Available/Authorized” |
| Platform Data root moves | Binding follows trusted activation; local file picker default is not storage authority |
| File-backed state cannot persist a policy change | Failure explicitly signaled; no success acknowledgement |

These are candidate tests, not results of an installed build. The major open decisions concern which settings are truly needed, sync eligibility, authorization/administration, sensitivity, artifact authorship, policy precedence, exact node/private user-root binding, drafts retention, style provider trust and physically supported schema migration.

**Conclusion:** a small visible Settings screen can sit over several distinct state authorities. Simplifying UX is compatible with preserving independent scientific input, shared policy, local convenience and future extension capability boundaries.
