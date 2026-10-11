# Extension configuration, capability catalog projections and product-owned surfaces

**Scientific question:** how can a user discover, configure, selectively enable and understand an environment-neutral capability provider without turning a business extension into an arbitrary UI or package-installation mechanism? **Primary Research:** full 2026-10-07 Strategy Box settings study, `SB-SRC-0044` at frozen blob `bedb3628f3a58a27c9de10b7a19043549c281dca`, especially §§9–12, 15, 36–40, 63, 68–70, 72–74 and 84–86. Its proposals require reconciliation with later [provider conformance science](provider-discovery-binding-readiness-and-conformance.md). **Status:** public-neutral contract reasoning only; it does not certify any installed provider, reveal deployment-specific implementation details or grant installation/activation authority.

## 1. Business contribution and interface rendering are different privileges

An extension can contribute a **declared, typed subject capability**, data source, operation, format codec, reporting style/template or required connection descriptor. The application may render those declarations through its own operation catalog, file chooser, artifact/style selector, standard forms or diagnostics. A declared feature appearing in the UI does **not** mean external code owns the UI.

The source rejects unrestricted application shell modification as a security, maintainability and portability boundary. Bounded general contracts should never grant a provider the ability to replace application themes, inject QSS/CSS, set shell fonts, insert Qt widgets, replace navigation/Settings, inject arbitrary menu actions or ship executable frontend rendering code. A product-owned, policy-validated `ActionDescriptor` is different from arbitrary menu injection.

Future Android and browser clients can consume the **same semantic descriptors**, using native presentation. The product may deliberately design specialized capability forms, but that becomes its own reviewed application feature and contract, not implicit plugin authority.

## 2. “Installed” is not “ready,” and “visible” is not “permitted”

The early settings source described staged states:

```text
installed distribution
  → discovered descriptor
  → compatible with this runtime
  → selected by environment/application policy
  → required configuration validated
  → provider binding/health checked
  → permission to expose individual capabilities or effects
```

The source's presentation statuses—Ready, Disabled, Needs configuration, Needs authorization, Incompatible, Unavailable, Error, Restart required—are human-facing **projections of multiple facts**, not one exclusive authoritative enum. The later capability research refines the boundaries between discovery, readiness and object-level permissions; no one list replaces that richer contract.

A “toggle” is appropriate only when the extension is **optional, locally activatable under current policy and safe to disable**. A required managed provider should show “managed by environment” and the reason it cannot be switched off. Disabling a provider affects **new admission**; it must not delete historical accepted Runs or artifacts that depend on its earlier semantic version. Existing in-flight work needs separately defined binding and effect fencing.

Multiple providers advertising one singleton capability must trigger deterministic selection by explicit policy, or a visible user choice when authorized. “First discovered wins” is not a safe contract. A provider with a missing required binding should give a typed readiness failure, not silently swap the physical environment or elevate a partial fallback to success.

## 3. Installation and user configuration have separate owners

The application may display installed version, compatible status, description, capabilities, configuration errors and a route to supported platform package management. Actual installation, uninstallation, update, resolver and Python-environment lifecycle belong to the **deployment owner**. The product must not embed `pip install/uninstall/upgrade` as end-user Settings actions.

The research deliberately rejects a premature plugin marketplace: public ratings, screenshots, purchases and an unrestricted community-store workflow are not requirements for a bounded managed-product catalog. A helpful first user experience consists of the installed/available inventory, authorized activation/configuration, compatibility and health diagnostics, and an external management handoff only when that external platform capability actually exists.

Names and descriptions should be the primary user view, with technical IDs in Details/Diagnostics. Detailed tracebacks and raw credentials are support evidence, not user-facing status strings.

## 4. A declarative, versioned configuration contract

The source proposes an extension-declared `SettingSpec` with stable key, title, purpose, type, scope, default, required/allowed values, sensitivity, restart requirement, visibility and schema version.

A renderer may map `boolean` to a toggle, a small enum to radio/combo, scalar strings/integers to validated text/numeric fields, a resource reference to an authorized selector and `secret_ref` to a **reference-only** credential picker. It must not instantiate a provider-supplied GUI class.

Potential scopes:

| Scope | Meaning / boundary |
| --- | --- |
| **USER** | Personal preference with an allowed local owner and explicit sync rules. |
| **WORKSPACE** | A shared business default or provider selection that can affect other authorized users. |
| **NODE** | Environment-specific binding or capacity under node/product policy. |
| **MANAGED_ONLY** | Controlled externally or by an administrator; may be displayed read-only when useful. |

Potential sensitivity classes are **PUBLIC**, **PRIVATE** and **SECRET_REFERENCE**. The last is **not** a masked raw token stored in `app.json`; use an authorized secret provider's opaque handle and never expose the underlying credential in distributed settings snapshots, logs, reports or artifacts. User-editable values must be schema-validated and interpreted under product authorization and external platform policy. A provider can declare a need for a workspace setting, but it cannot grant itself permission to mutate it.

Configuration carries `provider_id`, distribution/version, `config_schema_version` and values. A schema change can require explicit migration/revalidation, a `CONFIG_MIGRATION_REQUIRED` state, replacement of old bindings or a controlled cutover. Since preserving indefinite public API compatibility is not the project goal, compatibility shims are not automatic; **old accepted execution provenance and meaningful saved user data still need a governed disposition**.

## 5. Where the capability appears determines which choice the user makes

The **Extensions** page should manage existence, readiness, compatible binding and optional configuration. The **Scenarios/operations catalog** displays offered business methods. The **Sources/Explorer** surface displays available data-related choices. The **Artifacts and reports** section lists reporting profile resources by their business meaning, with a selectable default. Provider details may state “contributes two report profiles,” but the user should choose the profile while configuring reports, not among distribution metadata.

The source thereby separates three actions:

```text
configure a provider                  (Extensions)
choose a subject use case or source  (Scenarios / Explorer)
choose a reporting style             (Artifacts and reports)
```

Even though they are related, they do not have one owner, permission or storage location. A style contribution cannot access financial source files merely because it supplies colors or fonts. An AI or machine actor can **use** an authorized effective configuration in a particular execution; modifying persisted user/workspace configuration is another explicit authorized command.

## 6. Conformance, fallback and historical stability

A legitimate configurable contribution should demonstrate, at the relevant runtime/profile revision: schema validation, namespace uniqueness, explicit selection, health/readiness, denied policy behavior, secure reference resolution, missing resource behavior, provider-version compatibility, restart requirements, inability to change the shell, safe cancellation/readiness transitions and provenance of actual use.

Failure examples include: two providers advertising one singleton without a resolution rule; missing authorizing grant for an optional enable switch; a secret value accidentally serialized; a workspace change silently broadcast to other users; an unavailable provider silently replaced by another; report profile selected despite incompatible export format; config save acknowledged despite failed durable write; past artifacts disappearing from history when the producing provider is later disabled.

For a required provider, failing closed may be necessary. For an optional reporting style, a visible fallback to a permitted standard profile can be acceptable **only when the effective resolved identity and reason are saved**. Those two cases cannot be merged under a generic “everything available” user badge.

No installed profile, engine, remote host, policy API or credential manager is certified by this source. Reopen on implemented test harnesses, a second client renderer, real policy/configuration owners, provider failures or user workflow observations that justify additional surface features.

**Related science:** [provider discovery, binding and conformance](provider-discovery-binding-readiness-and-conformance.md), [minimal settings UX](../application-state/settings-feature-admission-and-contextual-controls.md), [settings/state/policy authority](../application-state/settings-policy-preferences-and-drafts.md), [reporting style evidence](../artifacts/report-formatting-profiles-metadata-and-evidence.md), [identity and effects](../trust-and-assurance/identity-authorization-and-effect-boundaries.md).
